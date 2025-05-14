import asyncio
import io
import struct
import time

from machine import RTC # type: ignore
from esp32 import gpio_deep_sleep_hold # type: ignore

from .enums import (
    WalterModemOpState,
    WalterModemNetworkRegState,
    WalterModemRspParserState,
    WalterModemCmdState,
    WalterModemState,
    WalterModemCmdType,
    WalterModemRspType,
    WalterModemRat,
    WalterModemOperatorFormat,
    WalterModemSimState,
    WalterModemHttpContextState,
    WalterModemSocketState,
    WalterModemMqttState,
    WalterModemMqttResultCode,
    WalterModemCoapReqResp
)

from .structs import (
    ModemSocket,
    ModemHttpContext,
    ModemTaskQueueItem,
    ModemBandSelection,
    ModemSignalQuality,
    ModemHttpResponse,
    ModemGNSSFix,
    ModemCellInformation,
    ModemGNSSSat,
    ModemGNSSAssistance,
    ModemCmd,
    ModemRsp,
    ModemMqttMessage,
    ModemCoapRing,
    ModemCoapContextState,
    ModemCoapResponse,
    ModemCoapOption
)

from .utils import (
    parse_cclk_time,
    parse_gnss_time,
    modem_string,
    log
)

class ModemCore:
    CR = 13
    LF = 10
    PLUS = ord('+')
    GREATER_THAN = ord('>')
    SMALLER_THAN = ord('<')
    SPACE = ord(' ')

    DEFAULT_CMD_ATTEMPTS = 3
    """The default number of attempts to execute a command."""

    PIN_RX = 14
    """The RX pin on which modem data is received."""

    PIN_TX = 48
    """The TX to which modem data must be transmitted."""

    PIN_RTS = 21
    """The RTS pin on the ESP32 side."""

    PIN_CTS = 47
    """The CTS pin on the ESP32 size."""

    PIN_RESET = 45
    """The active low modem reset pin."""

    BAUD = 115200
    """The baud rate used to talk to the modem."""

    CMD_TIMEOUT = 5
    """The maximum number of seconds to wait."""

    MIN_VALID_TIMESTAMP = 1672531200
    """Any modem time below 1 Jan 2023 00:00:00 UTC is considered an invalid time."""

    MIN_PDP_CTX_ID = 1
    """The lowest possible pdp context ID"""

    MAX_PDP_CTX_ID = 8
    """The highest possible PDP context ID"""

    DEFAULT_PDP_CTX_ID = 1
    """The modem's default PDP CTX ID, if none is specified"""

    MAX_SOCKETS = 6
    """The maximum number of sockets that the library can support."""

    MAX_HTTP_PROFILES = 3
    """The max nr of http profiles"""

    MAX_TLS_PROFILES = 6
    """The maximum number of TLS profiles that the library can support"""

    OPERATOR_MAX_SIZE = 16
    """The maximum number of characters of an operator name"""

    MQTT_TOPIC_MAX_SIZE = 127
    """The recommended mamximum number of characters in an MQTT topic"""

    MQTT_MAX_PENDING_RINGS = 8
    """The recommended maximum number of rings that can be pending for the MQTT protocol"""

    MQTT_MAX_TOPICS = 4
    """The recommended maximum allowed MQTT topics to subscribe to"""

    MQTT_MIN_KEEP_ALIVE = 20
    """The recommended minimum for the MQTT keep alive time"""

    MQTT_MAX_MESSAGE_LEN = 4096
    """The maximum MQTT payload length"""

    COAP_MIN_CTX_ID = 0

    COAP_MAX_CTX_ID = 2

    COAP_MIN_TIMEOUT = 1

    COAP_MAX_TIMEOUT = 120

    COAP_MIN_BYTES_LENGTH = 0

    COAP_MAX_BYTES_LENGTH = 1024

    def __init__(self):
        gpio_deep_sleep_hold(True)

        self._op_state = WalterModemOpState.MINIMUM
        """The current operational state of the modem."""

        self._reg_state = WalterModemNetworkRegState.NOT_SEARCHING
        """The current network registration state of the modem."""

        self._socket_list = [ModemSocket(idx + 1) for idx in range(ModemCore.MAX_SOCKETS) ]
        """The list of sockets"""

        self._socket = None
        """The socket which is currently in use by the library or None when no socket is in use."""

        self._http_context_list = [ModemHttpContext() for _ in range(ModemCore.MAX_HTTP_PROFILES) ]
        """The list of http contexts in the modem"""

        self._http_current_profile = 0xff
        """Current http profile in use in the modem"""

        self._gnss_fix_lock = asyncio.Lock()
        self._gnss_fix_waiters = []
        """GNSS fix waiters"""

        self._mqtt_status = WalterModemMqttState.DISCONNECTED
        """Status of the MQTT connection"""

        self._mqtt_msg_buffer: list[ModemMqttMessage] = []
        """Inbox for MQTT messages"""

        self._mqtt_subscriptions: list[tuple[str, int]] = []

        self._proc_queue_rsp_rsp_handlers = None
        """The mapping of rsp patterns to handler methods for processing the rsp queue"""

        self._proc_queue_rsp_cmd_handlers = None
        """The mapping of cmd patterns to handler methods for processing the rsp queue"""

        self._application_queue_rsp_handlers: list[tuple] = None
        """The mapping of rsp patterns to handler methods defined by the application code"""

        self._application_queue_rsp_handlers_set: bool = False
        """Whether or not the application has defined/set queue rsp handlers"""

        self._begun = False
        """Whether or not the begin method has already been run."""

        self.coap_context_states = tuple(
            ModemCoapContextState()
            for _ in range(self.COAP_MIN_CTX_ID, self.COAP_MAX_CTX_ID + 1)
        )
        """Index maps to the profile ID"""

    def _add_msg_to_mqtt_buffer(self, msg_id, topic, length, qos):
        # According to modem documentation;
        # A message with <qos>=0 doesn't have a <mid>,
        # as this type of message is overwritten every time a new message arrives.
        # No <mid> value is to be given to read a message with <qos>=0.
        if qos == 0:
            for msg in self._mqtt_msg_buffer:
                if msg.qos == 0:
                    msg.topic = topic
                    msg.length = length
                    msg.free = False
                    msg.payload = None
                    return

        if qos > 0:
            for msg in self._mqtt_msg_buffer:
                if msg.message_id == msg_id and msg.topic == topic:
                    return

        for msg in self._mqtt_msg_buffer:
            if msg.free:
                msg.topic = topic
                msg.length = length
                msg.qos = qos
                msg.message_id = msg_id
                msg.payload = None
                msg.free = False
                return
            
        log('WARNING',
            'Modem Library\'s MQTT Message Buffer is full, incoming message was dropped')

    async def _queue_rx_buffer(self):
        """
        Copy the currently received data buffer into the task queue.
        
        This function will copy the current modem receive buffer into the
        task queue. When the buffer could not be placed in the queue it will
        be silently dropped.
        
        :returns: None.
        """
        qitem = ModemTaskQueueItem()
        qitem.rsp = self._parser_data.line
        
        if self.debug_log:
            try:
                log('DEBUG, RX', qitem.rsp.decode())
            except:
                log('DEBUG, RX', qitem.rsp)
        await self._task_queue.put(qitem)

        self._parser_data.line = bytearray()

    def _add_at_byte_to_buffer(self, data, raw_mode_active):
        """
        Handle an AT data byte.
        
        This function is used by the AT data parser to add a databyte to 
        the buffer currently in use or to reserve a new buffer to add a byte
        to.
        
        :param data: The data byte to handle.
        
        :returns: None.
        """
        
        if not raw_mode_active and data == ModemCore.CR:
            self._parser_data.state = WalterModemRspParserState.END_LF
            return

        self._parser_data.line += bytes([data])

    async def _uart_reader(self):
        rx_stream = asyncio.StreamReader(self._uart, {})

        while True:
            incoming_uart_data = bytearray(256)
            size = await rx_stream.readinto(incoming_uart_data)

            for b in incoming_uart_data[:size]:
                if self._parser_data.state == WalterModemRspParserState.START_CR:
                    if b == ModemCore.CR:
                        self._parser_data.state = WalterModemRspParserState.START_LF
                    elif b == ModemCore.PLUS:
                        # This is the start of a new line in a multiline response
                        self._parser_data.state = WalterModemRspParserState.DATA
                        self._add_at_byte_to_buffer(b, False)
                    else:
                        self._parser_data.state = WalterModemRspParserState.DATA
                        self._add_at_byte_to_buffer(b, False)
                
                elif self._parser_data.state == WalterModemRspParserState.START_LF:
                    if b == ModemCore.LF:
                        self._parser_data.state = WalterModemRspParserState.DATA
                
                elif self._parser_data.state == WalterModemRspParserState.DATA:
                    if b == ModemCore.GREATER_THAN:
                        self._parser_data.state = WalterModemRspParserState.DATA_PROMPT
                    elif b == ModemCore.SMALLER_THAN:
                        self._parser_data.state = WalterModemRspParserState.DATA_HTTP_START1
                
                    self._add_at_byte_to_buffer(b, False)
                    
                elif self._parser_data.state == WalterModemRspParserState.DATA_PROMPT:
                    self._add_at_byte_to_buffer(b, False)
                    if b == ModemCore.SPACE:
                        self._parser_data.state = WalterModemRspParserState.START_CR
                        await self._queue_rx_buffer()
                    elif b == ModemCore.GREATER_THAN:
                        self._parser_data.state = WalterModemRspParserState.DATA_PROMPT_HTTP
                    else:
                        # state might have changed after detecting end \r
                        if self._parser_data.state == WalterModemRspParserState.DATA_PROMPT:
                            self._parser_data.state = WalterModemRspParserState.DATA
                
                elif self._parser_data.state == WalterModemRspParserState.DATA_PROMPT_HTTP:
                    self._add_at_byte_to_buffer(b, False)
                    if b == ModemCore.GREATER_THAN:
                        self._parser_data.state = WalterModemRspParserState.START_CR
                        await self._queue_rx_buffer()
                    else:
                        # state might have changed after detecting end \r
                        if self._parser_data.state == WalterModemRspParserState.DATA_PROMPT_HTTP:
                            self._parser_data.state = WalterModemRspParserState.DATA

                elif self._parser_data.state == WalterModemRspParserState.DATA_HTTP_START1:
                    if b == ModemCore.SMALLER_THAN:
                        self._parser_data.state = WalterModemRspParserState.DATA_HTTP_START2
                    else:
                        self._parser_data.state = WalterModemRspParserState.DATA

                    self._add_at_byte_to_buffer(b, False)

                elif self._parser_data.state == WalterModemRspParserState.DATA_HTTP_START2:
                    if b == ModemCore.SMALLER_THAN and self._http_current_profile < ModemCore.MAX_HTTP_PROFILES:
                        # FIXME: modem might block longer than cmd timeout,
                        # will lead to retry, error etc - fix properly
                        self._parser_data.raw_chunk_size = self._http_context_list[self._http_current_profile].content_length + len("\r\nOK\r\n")
                        self._parser_data.state = WalterModemRspParserState.RAW
                    else:
                        self._parser_data.state = WalterModemRspParserState.DATA

                    self._add_at_byte_to_buffer(b, False)

                elif self._parser_data.state == WalterModemRspParserState.END_LF:
                    if b == ModemCore.LF:
                        if b'+CME ERROR' in self._parser_data.line:
                            self._parser_data.raw_chunk_size = 0

                        if self._parser_data.raw_chunk_size:
                            self._parser_data.line += b'\r'
                            self._parser_data.state = WalterModemRspParserState.RAW
                        else:
                            self._parser_data.state = WalterModemRspParserState.START_CR
                            await self._queue_rx_buffer()
                    else:
                        # only now we know the \r was thrown away for no good reason
                        self._parser_data.line += b'\r'

                        # next byte gets the same treatment; since we really are
                        # back in semi DATA state, as we now know
                        # (but > will not lead to data prompt mode)
                        self._add_at_byte_to_buffer(b, False)
                        if b != ModemCore.CR:
                            self._parser_data.state = WalterModemRspParserState.DATA

                elif self._parser_data.state == WalterModemRspParserState.RAW:
                    self._add_at_byte_to_buffer(b, True)
                    self._parser_data.raw_chunk_size -= 1

                    if self._parser_data.raw_chunk_size == 0:
                        self._parser_data.state = WalterModemRspParserState.START_CR
                        await self._queue_rx_buffer()

    async def _dev_debug_uart_reader(self):
        rx_stream = asyncio.StreamReader(self._uart, {})

        while True:
            incoming_uart_data = bytearray(256)
            size = await rx_stream.readinto(incoming_uart_data)
            print(incoming_uart_data[:size].strip(b'\x00'))
            print(WalterModemRspParserState.get_value_name(self._parser_data.state))

            for b in incoming_uart_data[:size].strip(b'\x00'):
                if self._parser_data.state == WalterModemRspParserState.START_CR:
                    print('UART >>> START_CR')
                    if b == ModemCore.CR:
                        print('UART >>>   CR')
                        self._parser_data.state = WalterModemRspParserState.START_LF
                    elif b == ModemCore.PLUS:
                        print('UART >>>   PLUS')
                        # This is the start of a new line in a multiline response
                        self._parser_data.state = WalterModemRspParserState.DATA
                        self._add_at_byte_to_buffer(b, False)
                    else:
                        self._parser_data.state = WalterModemRspParserState.DATA
                        self._add_at_byte_to_buffer(b, False)
                
                elif self._parser_data.state == WalterModemRspParserState.START_LF:
                    print('UART >>> START_LF')
                    if b == ModemCore.LF:
                        print('UART >>>   LF')
                        self._parser_data.state = WalterModemRspParserState.DATA
                
                elif self._parser_data.state == WalterModemRspParserState.DATA:
                    print('UART >>> DATA')
                    if b == ModemCore.GREATER_THAN:
                        print('UART >>>   GREATER_THAN')
                        self._parser_data.state = WalterModemRspParserState.DATA_PROMPT
                    elif b == ModemCore.SMALLER_THAN:
                        print('UART >>>   SMALLER_THAN')
                        self._parser_data.state = WalterModemRspParserState.DATA_HTTP_START1
                
                    self._add_at_byte_to_buffer(b, False)
                    
                elif self._parser_data.state == WalterModemRspParserState.DATA_PROMPT:
                    print('UART >>> DATA_PROMPT')
                    self._add_at_byte_to_buffer(b, False)
                    if b == ModemCore.SPACE:
                        print('UART >>>   SPACE')
                        self._parser_data.state = WalterModemRspParserState.START_CR
                        await self._queue_rx_buffer()
                    elif b == ModemCore.GREATER_THAN:
                        print('UART >>>   GREATTER_THAN')
                        self._parser_data.state = WalterModemRspParserState.DATA_PROMPT_HTTP
                    else:
                        print('UART >>>   else...')
                        # state might have changed after detecting end \r
                        if self._parser_data.state == WalterModemRspParserState.DATA_PROMPT:
                            self._parser_data.state = WalterModemRspParserState.DATA
                
                elif self._parser_data.state == WalterModemRspParserState.DATA_PROMPT_HTTP:
                    print('UART >>> DATA_PROMPT_HTTP')
                    self._add_at_byte_to_buffer(b, False)
                    if b == ModemCore.GREATER_THAN:
                        print('UART >>>   GREATER_THAN')
                        self._parser_data.state = WalterModemRspParserState.START_CR
                        await self._queue_rx_buffer()
                    else:
                        print('UART >>>   else...')
                        # state might have changed after detecting end \r
                        if self._parser_data.state == WalterModemRspParserState.DATA_PROMPT_HTTP:
                            print('UART >>>     DATA_PROMPT_HTTP')
                            self._parser_data.state = WalterModemRspParserState.DATA

                elif self._parser_data.state == WalterModemRspParserState.DATA_HTTP_START1:
                    print('UART >>> DATA_HTTP_START1')
                    if b == ModemCore.SMALLER_THAN:
                        print('UART >>>   SMALLER_THAN')
                        self._parser_data.state = WalterModemRspParserState.DATA_HTTP_START2
                    else:
                        print('UART >>>   else...')
                        self._parser_data.state = WalterModemRspParserState.DATA

                    self._add_at_byte_to_buffer(b, False)

                elif self._parser_data.state == WalterModemRspParserState.DATA_HTTP_START2:
                    print('UART >>> DATA_HTTP_START2')
                    if b == ModemCore.SMALLER_THAN and self._http_current_profile < ModemCore.MAX_HTTP_PROFILES:
                        print('UART >>>   SMALLER_THAN')
                        # FIXME: modem might block longer than cmd timeout,
                        # will lead to retry, error etc - fix properly
                        self._parser_data.raw_chunk_size = self._http_context_list[self._http_current_profile].content_length + len("\r\nOK\r\n")
                        self._parser_data.state = WalterModemRspParserState.RAW
                    else:
                        print('UART >>>   else...')
                        self._parser_data.state = WalterModemRspParserState.DATA

                    self._add_at_byte_to_buffer(b, False)

                elif self._parser_data.state == WalterModemRspParserState.END_LF:
                    print('UART >>> END_LF')
                    if b == ModemCore.LF:
                        print('UART >>>   LF')
                        if b'+CME ERROR' in self._parser_data.line:
                            print('UART >>>     +CME ERROR detected')
                            self._parser_data.raw_chunk_size = 0

                        if self._parser_data.raw_chunk_size:
                            print('UART >>>     chunk size truthy')
                            self._parser_data.line += b'\r'
                            self._parser_data.state = WalterModemRspParserState.RAW
                        else:
                            print('UART >>>     else...')
                            self._parser_data.state = WalterModemRspParserState.START_CR
                            await self._queue_rx_buffer()
                    else:
                        print('UART >>>   else...')
                        # only now we know the \r was thrown away for no good reason
                        self._parser_data.line += b'\r'

                        # next byte gets the same treatment; since we really are
                        # back in semi DATA state, as we now know
                        # (but > will not lead to data prompt mode)
                        self._add_at_byte_to_buffer(b, False)
                        if b != ModemCore.CR:
                            print('UART >>>     CR')
                            self._parser_data.state = WalterModemRspParserState.DATA

                elif self._parser_data.state == WalterModemRspParserState.RAW:
                    print('UART >>> RAW')
                    self._add_at_byte_to_buffer(b, True)
                    self._parser_data.raw_chunk_size -= 1

                    if self._parser_data.raw_chunk_size == 0:
                        print('UART >>>   raw_chunk_size == 0')
                        self._parser_data.state = WalterModemRspParserState.START_CR
                        await self._queue_rx_buffer()

    async def _finish_queue_cmd(self, cmd, result):
        cmd.rsp.result = result

        if cmd.complete_handler:
            await cmd.complete_handler(result, cmd.rsp, cmd.complete_handler_arg)

        # we must unblock stuck cmd now
        cmd.state = WalterModemCmdState.COMPLETE
        cmd.event.set()

    async def _process_queue_cmd(self, tx_stream, cmd):
        if cmd.type == WalterModemCmdType.TX:
            if self.debug_log:
                log('DEBUG, TX', cmd.at_cmd)

            tx_stream.write(cmd.at_cmd)
            tx_stream.write(b'\r\n')
            await tx_stream.drain()
            await self._finish_queue_cmd(cmd, WalterModemState.OK)

        elif cmd.type == WalterModemCmdType.TX_WAIT \
        or cmd.type == WalterModemCmdType.DATA_TX_WAIT:
            if cmd.state == WalterModemCmdState.NEW:
                if self.debug_log:
                    log('DEBUG, TX', cmd.at_cmd)
                    
                tx_stream.write(cmd.at_cmd)
                if cmd.type == WalterModemCmdType.DATA_TX_WAIT:
                    tx_stream.write(b'\n')
                else:
                    tx_stream.write(b'\r\n')
                await tx_stream.drain()
                cmd.attempt = 1
                cmd.attempt_start = time.time()
                cmd.state = WalterModemCmdState.PENDING

            else:
                tick_diff = time.time() - cmd.attempt_start
                timed_out = tick_diff >= ModemCore.CMD_TIMEOUT
                if timed_out or cmd.state == WalterModemCmdState.RETRY_AFTER_ERROR:
                    if cmd.attempt >= cmd.max_attempts:
                        if timed_out:
                            await self._finish_queue_cmd(cmd, WalterModemState.TIMEOUT)
                        else:
                            await self._finish_queue_cmd(cmd, WalterModemState.ERROR)
                    else:
                        if self.debug_log:
                            log('DEBUG, TX', cmd.at_cmd)

                        tx_stream.write(cmd.at_cmd)
                        if cmd.type == WalterModemCmdType.DATA_TX_WAIT:
                            tx_stream.write(b'\n')
                        else:
                            tx_stream.write(b'\r\n')
                        await tx_stream.drain()
                        cmd.attempt += 1
                        cmd.attempt_start = time.time()
                        cmd.state = WalterModemCmdState.PENDING

                else:
                    return

        elif cmd.type == WalterModemCmdType.WAIT:
            if cmd.state == WalterModemCmdState.NEW:
                cmd.attempt_start = time.time()
                cmd.state = WalterModemCmdState.PENDING

            else:
                tick_diff = time.time() - cmd.attempt_start
                if tick_diff >= ModemCore.CMD_TIMEOUT:
                    await self._finish_queue_cmd(cmd, WalterModemState.TIMEOUT)
                else:
                    return

    async def _handle_data_tx_wait(self, tx_stream, cmd, at_rsp):
        if cmd and cmd.data and cmd.type == WalterModemCmdType.DATA_TX_WAIT:
            tx_stream.write(cmd.data)
            await tx_stream.drain()

        return WalterModemState.OK

    async def _handle_error(self, tx_stream, cmd, at_rsp):
        if cmd is not None:
            cmd.rsp.type = WalterModemRspType.NO_DATA
            cmd.state = WalterModemCmdState.RETRY_AFTER_ERROR
        return None
    
    async def _handle_cme_error(self, tx_stream, cmd, at_rsp):
        if cmd is not None:
            cme_error = int(at_rsp.decode().split(':')[1].split(',')[0])
            cmd.rsp.type = WalterModemRspType.CME_ERROR
            cmd.rsp.cme_error = cme_error
            cmd.state = WalterModemCmdState.RETRY_AFTER_ERROR
        return None

    async def _handle_sqn_mode_active(self, tx_stream, cmd, at_rsp):
        if cmd is None:
            return None
        
        cmd.rsp.type = WalterModemRspType.RAT
        cmd.rsp.rat = int(at_rsp.decode().split(':')[1])

        return WalterModemState.OK

    async def _handle_cclk(self, tx_stream, cmd, at_rsp):
        if not cmd:
            return None

        cmd.rsp.type = WalterModemRspType.CLOCK
        time_str = at_rsp[len('+CCLK: '):].decode()[1:-1] # strip double quotes
        cmd.rsp.clock = parse_cclk_time(time_str)

        return WalterModemState.OK

    async def _handle_sqn_coap_closed(self, tx_stream, cmd, at_rsp):
        ctx_id, cause = at_rsp.split(b': ')[1].split(b',')
        ctx_id = int(ctx_id)
        cause = cause.strip(b'"')

        self.coap_context_states[ctx_id].connected = False
        self.coap_context_states[ctx_id].cause = cause

        return WalterModemState.OK

    async def _handle_sqn_coap_error(self, tx_stream, cmd, at_rsp):
        return WalterModemState.ERROR
    
    async def _handle_sqn_coap_ring(self, tx_stream, cmd, at_rsp):
        parts = at_rsp.split(b': ')[1].split(b',')
        ctx_id, msg_id, req_resp, m_type, method_or_rsp_code, length = [int(p.decode()) for p in parts]

        self.coap_context_states[ctx_id].rings.append(ModemCoapRing(
            ctx_id=ctx_id,
            msg_id=msg_id,
            req_resp=req_resp,
            m_type=m_type,
            method=method_or_rsp_code if req_resp == WalterModemCoapReqResp.REQUEST else None,
            rsp_code=method_or_rsp_code if req_resp == WalterModemCoapReqResp.RESPONSE else None,
            length=length
        ))

        return WalterModemState.OK

    async def _handle_sqn_coap_rcv(self, tx_stream, cmd, at_rsp):
        header, payload = at_rsp.split(b': ')[1].split(b'\r')
        header = header.split(b',')

        ctx_id, msg_id = int(header[0].decode()), int(header[1].decode())
        token = header[2].decode()
        req_resp, m_type, method_or_rsp_code, length = [int(p.decode()) for p in header[3:]]

        cmd.rsp.type = WalterModemRspType.COAP
        cmd.rsp.coap_rcv_response = ModemCoapResponse(
            ctx_id=ctx_id,
            msg_id=msg_id,
            token=token,
            req_resp=req_resp,
            m_type=m_type,
            method=method_or_rsp_code if req_resp == WalterModemCoapReqResp.REQUEST else None,
            rsp_code=method_or_rsp_code if req_resp == WalterModemCoapReqResp.RESPONSE else None,
            length=length,
            payload=payload
        )

        return WalterModemState.OK

    async def _handle_sqn_coap_create(self, tx_stream, cmd, at_rsp):
        if (ctx_info := at_rsp.split(b': ')[1]) and b',' in ctx_info:
            ctx_id = int(ctx_info.split(b',')[0].decode())
            self.coap_context_states[ctx_id].connected = True
        else:
            ctx_id = int(ctx_info.decode())
            self.coap_context_states[ctx_id].connected = False
    
    async def _handle_sqn_coap_options(self, tx_stream, cmd, at_rsp):
        if cmd and cmd.at_cmd:
            if (cmd.at_cmd.startswith('AT+SQNCOAPOPT=')
            and cmd.at_cmd.split('=')[1].split(',')[1] == '2'):
                ctx_id_str, option_str, value = at_rsp[13:].decode().split(',', 2)
                cmd.rsp.coap_options = ModemCoapOption(
                    ctx_id=int(ctx_id_str),
                    option=int(option_str),
                    value=value
                )
    
    async def _handle_sqn_coap_rcvo(self, tx_stream, cmd, at_rsp):
        ctx_id_str, option_str, value = at_rsp[14:].decode().split(',', 2)
        coap_option = ModemCoapOption(
            ctx_id=int(ctx_id_str),
            option=int(option_str),
            value=value
        )
        if isinstance(cmd.rsp.coap_options, list):
            cmd.rsp.coap_options.append(coap_option)
        else:
            cmd.rsp.coap_options = [coap_option]

    async def _handle_sqn_http_rcv_answer_start(self, tx_stream, cmd, at_rsp):
        if self._http_current_profile >= ModemCore.MAX_HTTP_PROFILES or self._http_context_list[self._http_current_profile].state != WalterModemHttpContextState.GOT_RING:
            return WalterModemState.ERROR
        else:
            if not cmd:
                return

            cmd.rsp.type = WalterModemRspType.HTTP
            cmd.rsp.http_response = ModemHttpResponse()
            cmd.rsp.http_response.http_status = self._http_context_list[self._http_current_profile].http_status
            cmd.rsp.http_response.data = at_rsp[3:-len(b'\r\nOK\r\n')] # 3 skips: <<<
            cmd.rsp.http_response.content_type = self._http_context_list[self._http_current_profile].content_type
            cmd.rsp.http_response.content_length = self._http_context_list[self._http_current_profile].content_length

            # the complete handler will reset the state,
            # even if we never received <<< but got an error instead
            return WalterModemState.OK

    async def _handle_sqn_http_ring(self, tx_stream, cmd, at_rsp):
        profile_id_str, http_status_str, content_type, content_length_str = at_rsp[len("+SQNHTTPRING: "):].decode().split(',')
        profile_id = int(profile_id_str)
        http_status = int(http_status_str)
        content_length = int(content_length_str)

        if profile_id >= ModemCore.MAX_HTTP_PROFILES:
            # TODO: return error if modem returns invalid profile id.
            # problem: this message is an URC: the associated cmd
            # may be any random command currently executing */
            return

        # TODO: if not expecting a ring, it may be a bug in the modem
        # or at our side and we should report an error + read the
        # content to free the modem buffer
        # (knowing that this is a URC so there is no command
        # to give feedback to)
        if self._http_context_list[profile_id].state != WalterModemHttpContextState.EXPECT_RING:
            return

        # remember ring info
        self._http_context_list[profile_id].state = WalterModemHttpContextState.GOT_RING
        self._http_context_list[profile_id].http_status = http_status
        self._http_context_list[profile_id].content_type = content_type
        self._http_context_list[profile_id].content_length = content_length

        return WalterModemState.OK

    async def _handle_sqn_http_connect(self, tx_stream, cmd, at_rsp):
        profile_id_str, result_code_str = at_rsp[len("+SQNHTTPCONNECT: "):].decode().split(',')
        profile_id = int(profile_id_str)
        result_code = int(result_code_str)

        if profile_id < ModemCore.MAX_HTTP_PROFILES:
            if result_code == 0:
                self._http_context_list[profile_id].connected = True
            else:
                self._http_context_list[profile_id].connected = False
        
        return WalterModemState.OK

    async def _handle_sqn_http_disconnect(self, tx_stream, cmd, at_rsp):
        profile_id = int(at_rsp[len("+SQNHTTPDISCONNECT: "):].decode())

        if profile_id < ModemCore.MAX_HTTP_PROFILES:
            self._http_context_list[profile_id].connected = False
        
        return WalterModemState.OK

    async def _handle_sqn_http_sh(self, tx_stream, cmd, at_rsp):
        profile_id_str, _ = at_rsp[len('+SQNHTTPSH: '):].decode().split(',')
        profile_id = int(profile_id_str)

        if profile_id < ModemCore.MAX_HTTP_PROFILES:
            self._http_context_list[profile_id].connected = False

        return WalterModemState.OK

    async def _handle_sqns_mqtt_on_connect(self, tx_stream, cmd, at_rsp):
        _, result_code_str = at_rsp[len("+SQNSMQTTONCONNECT:"):].decode().split(',')
        result_code = int(result_code_str)

        if cmd and cmd.at_cmd:
            cmd.rsp.type = WalterModemRspType.MQTT
            cmd.rsp.mqtt_rc = result_code

        if result_code:
            self._mqtt_status = WalterModemMqttState.DISCONNECTED
        else:
            self._mqtt_status = WalterModemMqttState.CONNECTED

        if self._mqtt_status == WalterModemMqttState.CONNECTED:
            for (topic, qos) in self._mqtt_subscriptions:
                asyncio.create_task(self._run_cmd(
                    at_cmd=f'AT+SQNSMQTTSUBSCRIBE=0,{modem_string(topic)},{qos}',
                    at_rsp=b'+SQNSMQTTONSUBSCRIBE:0,{}'.format(modem_string(topic)),
                ))
        
        if cmd and cmd.at_cmd and cmd.at_cmd.startswith('AT+SQNSMQTTCONNECT=0'):
            if result_code != WalterModemMqttResultCode.SUCCESS:
                return WalterModemState.ERROR
        
        return WalterModemState.OK
    
    async def _handle_sqns_mqtt_on_publish(self, tx_stream, cmd, at_rsp):
        result_code = int(at_rsp[-2:].strip(b','))

        if cmd and cmd.at_cmd:
            cmd.rsp.type = WalterModemRspType.MQTT
            cmd.rsp.mqtt_rc = result_code

        if cmd and cmd.at_cmd and cmd.at_cmd.startswith('AT+SQNSMQTTPUBLISH=0'):
            if result_code != WalterModemMqttResultCode.SUCCESS:
                return WalterModemState.ERROR
        
        return WalterModemState.OK        

    async def _handle_sqns_mqtt_on_disconnect(self, tx_stream, cmd, at_rsp):
        _, result_code_str = at_rsp[len("+SQNSMQTTONDISCONNECT:"):].decode().split(',')
        result_code = int(result_code_str)

        if cmd and cmd.at_cmd:
            cmd.rsp.type = WalterModemRspType.MQTT
            cmd.rsp.mqtt_rc = result_code

        if result_code != 0:
            return WalterModemState.ERROR

        self._mqtt_status = WalterModemMqttState.DISCONNECTED
        self._mqtt_subscriptions = []
        for msg in self._mqtt_msg_buffer:
            msg.free = True
        
        if cmd and cmd.at_cmd and cmd.at_cmd.startswith('AT+SQNSMQTTDISCONNECT=0'):
            if result_code != WalterModemMqttResultCode.SUCCESS:
                return WalterModemState.ERROR

        return WalterModemState.OK

    async def _handle_sqns_mqtt_on_message(self, tx_stream, cmd, at_rsp):
        parts = at_rsp[len("+SQNSMQTTONMESSAGE:"):].decode().split(',')
        topic = parts[1].replace('"', '')
        length = int(parts[2])
        qos = int(parts[3])
        if qos != 0 and len(parts) > 4:
            message_id = parts[4]
        else:
            message_id = None

        self._add_msg_to_mqtt_buffer(message_id, topic, length, qos)
        return WalterModemState.OK

    async def _handle_sqns_mqtt_memory_full(self, tx_stream, cmd, at_rsp):
        log('WARNING',
            'Sequans Modem\'s MQTT Memory full')

        for msg in self._mqtt_msg_buffer:
            msg.free = True

        return WalterModemState.OK
    
    async def _handle_sqns_mqtt_subscribe(self, tx_stream, cmd, at_rsp):
        result_code = int(at_rsp[-2:].strip(b','))

        if cmd and cmd.at_cmd:
            cmd.rsp.type = WalterModemRspType.MQTT
            cmd.rsp.mqtt_rc = result_code

        if cmd and cmd.at_cmd and cmd.at_cmd.startswith('AT+SQNSMQTTSUBSCRIBE=0'):
            if result_code != WalterModemMqttResultCode.SUCCESS:
                return WalterModemState.ERROR
        
        return WalterModemState.OK    

    async def _handle_sqn_sh(self, tx_stream, cmd, at_rsp):
        socket_id = int(at_rsp[len('+SQNSH: '):].decode())
        try:
            _socket = self._socket_list[socket_id - 1]
        except Exception:
            return None

        self._socket = _socket
        _socket.state = WalterModemSocketState.FREE

        return WalterModemState.OK

    async def _handle_sqnscfg(self, tx_stream, cmd, at_rsp):
        conn_id, cid, pkt_sz, max_to, conn_to, tx_to = map(int, at_rsp.split(b': ')[1].split(b','))

        socket = self._socket_list[conn_id - 1]
        socket.id = conn_id
        socket.pdp_context_id = cid
        socket.mtu = pkt_sz
        socket.exchange_timeout = max_to
        socket.conn_timeout = conn_to / 10
        socket.send_delay_ms = tx_to * 100

    async def _handle_lp_gnss_fix_ready(self, tx_stream, cmd, at_rsp):
        data = at_rsp[len(b'+LPGNSSFIXREADY: '):]

        parenthesis_open = False
        part_no = 0
        start_pos = 0
        part = ''
        gnss_fix = ModemGNSSFix()

        for character_pos in range(len(data)):
            character = data[character_pos]
            part_complete = False

            if character == ord(',') and not parenthesis_open:
                part = data[start_pos:character_pos]
                part_complete = True
            elif character == ord('('):
                parenthesis_open = True
            elif character == ord(')'):
                parenthesis_open = False
            elif character_pos + 1 == len(data):
                part = data[start_pos:character_pos + 1]
                part_complete = True

            if part_complete:
                if part_no == 0:
                    gnss_fix.fix_id = int(part)
                elif part_no == 1:
                    part = part[1:-1]
                    gnss_fix.timestamp = parse_gnss_time(part)
                elif part_no == 2:
                    gnss_fix.time_to_fix = int(part)
                elif part_no == 3:
                    part = part[1:-1]
                    gnss_fix.estimated_confidence = float(part)
                elif part_no == 4:
                    part = part[1:-1]
                    gnss_fix.latitude = float(part)
                elif part_no == 5:
                    part = part[1:-1]
                    gnss_fix.longitude = float(part)
                elif part_no == 6:
                    part = part[1:-1]
                    gnss_fix.height = float(part)
                elif part_no == 7:
                    part = part[1:-1]
                    gnss_fix.north_speed = float(part)
                elif part_no == 8:
                    part = part[1:-1]
                    gnss_fix.east_speed = float(part)
                elif part_no == 9:
                    part = part[1:-1]
                    gnss_fix.down_speed = float(part)
                elif part_no == 10:
                     # Raw satellite signal sample is ignored
                    pass
                else:
                    satellite_data = part.decode().split(',')

                    # Iterate through the satellite_data list, taking every two elements as pairs
                    for i in range(0, len(satellite_data), 2):
                        sat_no_str = satellite_data[i]
                        sat_sig_str = satellite_data[i + 1]

                        gnss_fix.sats.append(ModemGNSSSat(int(sat_no_str[1:]), int(sat_sig_str[:-1])))

                # +1 for the comma
                part_no += 1
                start_pos = character_pos + 1
                part = ''

        # notify every coroutine that is waiting for a fix
        async with self._gnss_fix_lock:
            for gnss_fix_waiter in self._gnss_fix_waiters:
                gnss_fix_waiter.gnss_fix = gnss_fix
                gnss_fix_waiter.event.set()

            self._gnss_fix_waiters = []
        
        return WalterModemState.OK

    async def _handle_lp_gnss_assistance(self, tx_stream, cmd, at_rsp):
        if not cmd:
            return

        if cmd.rsp.type != WalterModemRspType.GNSS_ASSISTANCE_DATA:
            cmd.rsp.type = WalterModemRspType.GNSS_ASSISTANCE_DATA
            cmd.rsp.gnss_assistance = ModemGNSSAssistance()

        data = at_rsp[len("+LPGNSSASSISTANCE: "):]
        part_no = 0
        start_pos = 0
        part = ''
        gnss_details = None

        for character_pos in range(len(data)):
            character = data[character_pos]
            part_complete = False

            if character == ord(','):
                part = data[start_pos:character_pos]
                part_complete = True
            elif character_pos + 1 == len(data):
                part = data[start_pos:character_pos + 1]
                part_complete = True

            if part_complete:
                if part_no == 0:
                    if part[0] == ord('0'):
                        gnss_details = cmd.rsp.gnss_assistance.almanac
                    elif part[0] == ord('1'):
                        gnss_details = cmd.rsp.gnss_assistance.realtime_ephemeris
                    elif part[0] == ord('2'):
                        gnss_details = cmd.rsp.gnss_assistance.predicted_ephemeris
                elif part_no == 1:
                    if gnss_details:
                        gnss_details.available = int(part) == 1
                elif part_no == 2:
                    if gnss_details:
                        gnss_details.last_update = int(part)
                elif part_no == 3:
                    if gnss_details:
                        gnss_details.time_to_update = int(part)
                elif part_no == 4 and gnss_details:
                        gnss_details.time_to_expire = int(part)

                # +1 for the comma
                part_no += 1
                start_pos = character_pos + 1
                part = ''

        return WalterModemState.OK

    async def _handle_cesq(self, tx_stream, cmd, at_rsp):
        if not cmd:
            return None

        cmd.rsp.type = WalterModemRspType.SIGNAL_QUALITY

        parts = at_rsp.decode().split(',')
        cmd.rsp.signal_quality = ModemSignalQuality()
        cmd.rsp.signal_quality.rsrq = -195 + (int(parts[4]) * 5)
        cmd.rsp.signal_quality.rsrp = -140 + int(parts[5])

        return WalterModemState.OK

    async def _handle_cfun(self, tx_stream, cmd, at_rsp):
        op_state = int(at_rsp.decode().split(':')[1].split(',')[0])
        self._op_state = op_state

        if cmd is None:
            return None

        cmd.rsp.type = WalterModemRspType.OP_STATE
        cmd.rsp.op_state = self._op_state
        return WalterModemState.OK

    async def _handle_csq(self, tx_stream, cmd, at_rsp):
        if not cmd:
            return None

        parts = at_rsp.decode().split(',')
        raw_rssi = int(parts[0][len('+CSQ: '):])

        cmd.rsp.type = WalterModemRspType.RSSI
        cmd.rsp.rssi = -113 + (raw_rssi * 2)

        return WalterModemState.OK

    async def _handle_sqnmoni(self, tx_stream, cmd, at_rsp):
        if cmd is None:
            return

        cmd.rsp.type = WalterModemRspType.CELL_INFO

        data_str = at_rsp[len(b"+SQNMONI: "):].decode()

        cmd.rsp.cell_information = ModemCellInformation()
        first_key_parsed = False

        for part in data_str.split(' '):
            if ':' not in part:
                continue
                
            pattern, value = part.split(':', 1)
            pattern = pattern.strip()
            value = value.strip()

            if not first_key_parsed and len(pattern) > 2:
                operator_name = pattern[:-2]
                cmd.rsp.cell_information.net_name = operator_name[:ModemCore.OPERATOR_MAX_SIZE]
                pattern = pattern[-2:]
                first_key_parsed = True

            if pattern == "Cc":
                cmd.rsp.cell_information.cc = int(value, 10)
            elif pattern == "Nc":
                cmd.rsp.cell_information.nc = int(value, 10)
            elif pattern == "RSRP":
                cmd.rsp.cell_information.rsrp = float(value)
            elif pattern == "CINR":
                cmd.rsp.cell_information.cinr = float(value)
            elif pattern == "RSRQ":
                cmd.rsp.cell_information.rsrq = float(value)
            elif pattern == "TAC":
                cmd.rsp.cell_information.tac = int(value, 10)
            elif pattern == "Id":
                cmd.rsp.cell_information.pci = int(value, 10)
            elif pattern == "EARFCN":
                cmd.rsp.cell_information.earfcn = int(value, 10)
            elif pattern == "PWR":
                cmd.rsp.cell_information.rssi = float(value)
            elif pattern == "PAGING":
                cmd.rsp.cell_information.paging = int(value, 10)
            elif pattern == "CID":
                cmd.rsp.cell_information.cid = int(value, 16)
            elif pattern == "BAND":
                cmd.rsp.cell_information.band = int(value, 10)
            elif pattern == "BW":
                cmd.rsp.cell_information.bw = int(value, 10)
            elif pattern == "CE":
                cmd.rsp.cell_information.ce_level = int(value, 10)

        return WalterModemState.OK

    async def _handle_sqn_band_sel(self, tx_stream, cmd, at_rsp):
        data = at_rsp[len(b'+SQNBANDSEL: '):]

        # create the array and response type upon reception of the
        # first band selection
        if cmd.rsp.type != WalterModemRspType.BANDSET_CFG_SET:
            cmd.rsp.type = WalterModemRspType.BANDSET_CFG_SET
            cmd.rsp.band_sel_cfg_list = []

        bsel = ModemBandSelection()

        if data[0] == ord('0'):
            bsel.rat = WalterModemRat.LTEM
        else:
            bsel.rat = WalterModemRat.NBIOT

        # Parse operator name
        bsel.net_operator.format = WalterModemOperatorFormat.LONG_ALPHANUMERIC
        bsel_parts = data[2:].decode().split(',')
        bsel.net_operator.name = bsel_parts[0]

        # Parse configured bands
        bands_list = bsel_parts[1:]
        if len(bands_list) > 1:
            bands_list[0] = bands_list[0][1:]
            bands_list[-1] = bands_list[-1][:-1]
            bsel.bands = [ int(x) for x in bands_list ]
        elif bands_list[0] != '""':
            bsel.bands = [ int(bands_list[0][1:-1]) ]
        else:
            bsel.bands = []

        cmd.rsp.band_sel_cfg_list.append(bsel)
        return WalterModemState.OK

    async def _handle_cereg(self, tx_stream, cmd, at_rsp):
        parts = at_rsp.decode().split(':')[1].split(',')
        parts_len = len(parts)
        if parts_len == 1 or parts_len > 2:
            self._reg_state = int(parts[0])
        elif parts_len == 2:
            self._reg_state = int(parts[1])
    
    async def _handle_cgpaddr(self, tx_stream, cmd, at_rsp):
        if not cmd:
            return None

        cmd.rsp.type = WalterModemRspType.PDP_ADDR 
        cmd.rsp.pdp_address_list = []

        parts = at_rsp.decode().split(',')
            
        if len(parts) > 1 and parts[1]:
            cmd.rsp.pdp_address_list.append(parts[1][1:-1])
        if len(parts) > 2 and parts[2]:
            cmd.rsp.pdp_address_list.append(parts[2][1:-1])
        
        return WalterModemState.OK

    async def _handle_cpin(self, tx_stream, cmd, at_rsp):
        if cmd is None:
            return None

        cmd.rsp.type = WalterModemRspType.SIM_STATE
        if at_rsp[len('+CPIN: '):] == b'READY':
            cmd.rsp.sim_state = WalterModemSimState.READY
        elif at_rsp[len('+CPIN: '):] == b"SIM PIN":
            cmd.rsp.sim_state = WalterModemSimState.PIN_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"SIM PUK":
            cmd.rsp.sim_state = WalterModemSimState.PUK_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"PH-SIM PIN":
            cmd.rsp.sim_state = WalterModemSimState.PHONE_TO_SIM_PIN_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"PH-FSIM PIN":
            cmd.rsp.sim_state = WalterModemSimState.PHONE_TO_FIRST_SIM_PIN_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"PH-FSIM PUK":
            cmd.rsp.sim_state = WalterModemSimState.PHONE_TO_FIRST_SIM_PUK_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"SIM PIN2":
            cmd.rsp.sim_state = WalterModemSimState.PIN2_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"SIM PUK2":
            cmd.rsp.sim_state = WalterModemSimState.PUK2_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"PH-NET PIN":
            cmd.rsp.sim_state = WalterModemSimState.NETWORK_PIN_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"PH-NET PUK":
            cmd.rsp.sim_state = WalterModemSimState.NETWORK_PUK_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"PH-NETSUB PIN":
            cmd.rsp.sim_state = WalterModemSimState.NETWORK_SUBSET_PIN_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"PH-NETSUB PUK":
            cmd.rsp.sim_state = WalterModemSimState.NETWORK_SUBSET_PUK_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"PH-SP PIN":
            cmd.rsp.sim_state = WalterModemSimState.SERVICE_PROVIDER_PIN_REQUIRED
        elif at_rsp[len('+CPIN: '):] == b"PH-SP PUK":
            cmd.rsp.sim_state = WalterModemSimState.SERVICE_PROVIDER_PUK_REQUIRED 
        elif at_rsp[len('+CPIN: '):] == b"PH-CORP PIN":
            cmd.rsp.sim_state = WalterModemSimState.CORPORATE_SIM_REQUIRED 
        elif at_rsp[len('+CPIN: '):] == b"PH-CORP PUK":
            cmd.rsp.sim_state = WalterModemSimState.CORPORATE_PUK_REQUIRED 
        else:
            cmd.rsp.type = WalterModemRspType.NO_DATA

        return WalterModemState.OK
    
    async def _handle_sqns_mqtt_rcv_message(self, tx_stream, cmd, at_rsp):
        if cmd.rsp.type != WalterModemRspType.MQTT:
            cmd.rsp.type = WalterModemRspType.MQTT
            
        if isinstance(cmd.ring_return, list) and (at_rsp != b'OK' and at_rsp != b'ERROR'):
            cmd.ring_return.append(at_rsp.decode())
        
        return WalterModemState.OK

    async def _process_queue_rsp(self, tx_stream, cmd, at_rsp: bytes):
        """
        Process an AT response from the queue.

        This function is called in the queue processing task when an AT
        response is received from the modem. The function will process the
        response and notify blocked functions or call the correct callbacks.

        :param cmd: The pending command or None when no command is pending.
        :param at_rsp: The AT response.

        :return: None.
        """
        if self._proc_queue_rsp_rsp_handlers is None:
            # Using tuples reduces the memory overhead significantly (they are immutable).
            # Tuples are fixed in size and do not require hash tables like dictionaries do.
            self._proc_queue_rsp_rsp_handlers = (
                (b'>>>', self._handle_data_tx_wait),
                (b'>', self._handle_data_tx_wait),
                (b'ERROR', self._handle_error),
                (b'+CME ERROR: ', self._handle_cme_error),
                
                # 4. Device Configuration
                (b'+CCLK: ', self._handle_cclk),

                # 6. Dual Mode
                (b'+SQNMODEACTIVE: ', self._handle_sqn_mode_active),

                # 8. IP Data Services
                # - CoAP
                (b'+SQNCOAPCLOSED: ', self._handle_sqn_coap_closed),
                (b'+SQNCOAP: ERROR', self._handle_sqn_coap_error),
                (b'+SQNCOAPRING:', self._handle_sqn_coap_ring),
                (b'+SQNCOAPRCV: ', self._handle_sqn_coap_rcv),
                (b'+SQNCOAPCREATE: ', self._handle_sqn_coap_create),
                (b'+SQNCOAPOPT: ', self._handle_sqn_coap_options),
                (b'+SQNCOAPRCVO: ', self._handle_sqn_coap_rcvo),
                # - HTTP
                (b'<<<', self._handle_sqn_http_rcv_answer_start),
                (b'+SQNHTTPRING: ', self._handle_sqn_http_ring),
                (b'+SQNHTTPCONNECT: ', self._handle_sqn_http_connect),
                (b'+SQNHTTPDISCONNECT: ', self._handle_sqn_http_disconnect),
                (b'+SQNHTTPSH: ', self._handle_sqn_http_sh),
                # - MQTT
                (b'+SQNSMQTTONCONNECT:0,', self._handle_sqns_mqtt_on_connect),
                (b'+SQNSMQTTONPUBLISH:0', self._handle_sqns_mqtt_on_publish),
                (b'+SQNSMQTTONDISCONNECT:0,', self._handle_sqns_mqtt_on_disconnect),
                (b'+SQNSMQTTONMESSAGE:0,', self._handle_sqns_mqtt_on_message),
                (b'+SQNSMQTTMEMORYFULL', self._handle_sqns_mqtt_memory_full),
                (b'+SQNSMQTTONSUBSCRIBE:0', self._handle_sqns_mqtt_subscribe),
                # - Socket
                (b'+SQNSH: ', self._handle_sqn_sh),
                (b'+SQNSCFG: ', self._handle_sqnscfg),

                # 10. Location Services
                (b'+LPGNSSFIXREADY: ', self._handle_lp_gnss_fix_ready),
                (b'+LPGNSSASSISTANCE: ', self._handle_lp_gnss_assistance),

                # 12. Mobile Equipment Control and Status
                (b'+CESQ: ', self._handle_cesq),
                (b'+CFUN: ', self._handle_cfun),
                (b'+CSQ: ', self._handle_csq),
                (b'+SQNMONI', self._handle_sqnmoni),

                # 13. Network Service
                (b'+SQNBANDSEL: ', self._handle_sqn_band_sel),
                (b'+CEREG: ', self._handle_cereg),

                # 14. Packet Domain Related
                (b'+CGPADDR: ', self._handle_cgpaddr),

                # 15. SIM Management
                (b'+CPIN: ', self._handle_cpin),
            )

        if self._proc_queue_rsp_cmd_handlers is None:
            self._proc_queue_rsp_cmd_handlers = (
                ('AT+SQNSMQTTRCVMESSAGE=0', self._handle_sqns_mqtt_rcv_message),
            )

        result = WalterModemState.OK

        for pattern, handler in self._proc_queue_rsp_rsp_handlers:
            if at_rsp.startswith(pattern):
                result = await handler(tx_stream, cmd, at_rsp)
                break
        
        if cmd and cmd.at_cmd:
            for pattern, handler in self._proc_queue_rsp_cmd_handlers:
                if cmd.at_cmd.startswith(pattern):
                    result = await handler(tx_stream, cmd, at_rsp)
                    break
        
        if self._application_queue_rsp_handlers_set:
            for pattern, handler in self._application_queue_rsp_handlers:
                if at_rsp.startswith(pattern):
                    handler(cmd, at_rsp)
                    break
# FOR DEBUGGING:        
#        if cmd is not None and cmd.at_rsp is not None:
#            print('=====')
#            print('Full response:', at_rsp)
#            print('cmd.at_rsp:', cmd.at_rsp)
#            if isinstance(cmd.at_rsp, bytes):
#                print('Expected prefix (bytearray):', cmd.at_rsp)
#                print('Response start:', at_rsp[:len(cmd.at_rsp)])
#                print('Mismatch:', cmd.at_rsp != at_rsp[:len(cmd.at_rsp)])
#            elif isinstance(cmd.at_rsp, tuple):
#                print('Expected prefixes (tuple):', cmd.at_rsp)
#                for rsp in cmd.at_rsp:
#                    print(f'Checking prefix "{rsp}":', at_rsp.startswith(rsp))
        if (
            result is None or
            cmd is None or
            cmd.at_rsp is None or
            cmd.type == WalterModemCmdType.TX or
            (isinstance(cmd.at_rsp, bytes) and cmd.at_rsp != at_rsp[:len(cmd.at_rsp)]) or
            (isinstance(cmd.at_rsp, tuple) and not any(
                at_rsp.startswith(rsp) for rsp in cmd.at_rsp)
            )
        ):
            return

        await self._finish_queue_cmd(cmd, result)

    async def _queue_worker(self):
        tx_stream = asyncio.StreamWriter(self._uart, {})
        cur_cmd = None

        while True:
            if not cur_cmd and not self._command_queue.empty():
                qitem = ModemTaskQueueItem()
                qitem.cmd = await self._command_queue.get()
            else:
                qitem = await self._task_queue.get()
                if not isinstance(qitem, ModemTaskQueueItem):
                    log('ERROR',
                        f'Invalid task queue item: {type(qitem)}, {str(qitem)}')

            # process or enqueue new command or response
            if qitem.cmd:
                if not cur_cmd:
                    cur_cmd = qitem.cmd
                else:
                    await self._command_queue.put(qitem.cmd)
            elif qitem.rsp:
                await self._process_queue_rsp(tx_stream, cur_cmd, qitem.rsp)

            # initial transmit of cmd + retransmits after timeout
            if cur_cmd:
                if cur_cmd.state == WalterModemCmdState.RETRY_AFTER_ERROR \
                or cur_cmd.state == WalterModemCmdState.NEW \
                or cur_cmd.state == WalterModemCmdState.PENDING:
                    await self._process_queue_cmd(tx_stream, cur_cmd)

                if cur_cmd.state == WalterModemCmdState.COMPLETE:
                    cur_cmd = None

    async def _run_cmd(self,
        at_cmd: str,
        at_rsp: str | tuple[str], 
        rsp: ModemRsp | None = None,
        ring_return: list | None = None,
        cmd_type: int = WalterModemCmdType.TX_WAIT,
        data = None,
        complete_handler = None,
        complete_handler_arg = None,
        max_attempts = DEFAULT_CMD_ATTEMPTS
    ) -> bool:
        """
        Add a command to the command queue and await execution.
        
        This function add a command to the task queue. This function will 
        only fail when the command queue is full. The command which is put
        onto the queue will automatically get the CMD_STATE_NEW
        state. This function will never call any callbacks.
        
        :param rsp: the ModemRsp 
        :param cmd_type: The type of queue AT command.
        :param at_cmd: NULL terminated array of command elements. The elements
        must stay available until the command is complete. The array is only
        shallow copied.
        :param at_rsp: The expected AT response(s), when providing a tuple of multiple responses,
        they are to be seen as "OR", when either one of the responses are received,
        the cmd will be seen as complete.
        :param data: The extra data to be sent to the modem
        :param complete_handler: Optional complete handler function.
        :param complete_handler_arg: Optional argument for the complete handler.
        :param max_attempts: The maximum number of retries for this command.
        
        :returns: bool representing wether or not the command executed succesfully
        """
        cmd = ModemCmd()

        cmd.at_cmd = at_cmd
        cmd.at_rsp = at_rsp
        cmd.rsp = rsp if rsp else ModemRsp()
        cmd.ring_return = ring_return if ring_return is not None else None
        cmd.type = cmd_type
        cmd.data = data
        cmd.complete_handler = complete_handler
        cmd.complete_handler_arg = complete_handler_arg
        cmd.max_attempts = max_attempts
        cmd.state = WalterModemCmdState.NEW
        cmd.attempt = 0
        cmd.attempt_start = 0

        qitem = ModemTaskQueueItem()
        qitem.cmd = cmd
        await self._task_queue.put(qitem)

        # we expect the queue runner to release the (b)lock.
        await cmd.event.wait()

        return (
            cmd.rsp.result == WalterModemState.OK or
            (cmd.rsp.type == WalterModemRspType.HTTP and cmd.rsp.result == WalterModemState.NO_DATA)
        )

    async def _sleep_wakeup(self):
        await self._run_cmd(at_cmd='AT+CFUN?', at_rsp=b'OK')
        await self._run_cmd(at_cmd='AT+CEREG?', at_rsp=b'OK')
        await self._run_cmd(at_cmd='AT+SQNSCFG?', at_rsp=b'OK')
        await self._run_cmd(at_cmd='AT+SQNCOAPCREATE?', at_rsp=b'OK')

        rtc = RTC()
        packed_data = rtc.memory()

        mqtt_subs = packed_data[0]
        packed_data = packed_data[1:]
        if mqtt_subs == 1:
            buffer = io.BytesIO(packed_data)
            mqtt_subscriptions = self._mqtt_subscriptions
        
            while buffer.tell() < len(packed_data):
                topic_length = struct.unpack('I', buffer.read(4))[0]
                topic = struct.unpack(f'{topic_length}s', buffer.read(topic_length))[0].decode('utf-8')
                qos = struct.unpack('B', buffer.read(1))[0]

                mqtt_subscriptions.append((topic, qos))

    def _sleep_prepare(self, persist_mqtt_subs: bool):
        if persist_mqtt_subs:
            buffer = io.BytesIO()
            buffer.write(struct.pack('B', 1))

            for topic, qos in self._mqtt_subscriptions:
                encoded_topic = topic.encode('utf-8')
                buffer.write(struct.pack('I', len(encoded_topic)))
                buffer.write(struct.pack(f'{len(encoded_topic)}s', encoded_topic))
                buffer.write(struct.pack('B', qos))

            packed_data = buffer.getvalue()
        else:
            packed_data = struct.pack('B', 0)
        
        rtc = RTC()
        rtc.memory(packed_data)