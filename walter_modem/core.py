import asyncio
import time

from machine import UART
from .queue import Queue

from .enums import (
    ModemNetworkRegState,
    ModemNetworkSelMode,
    ModemOpState,
    ModemRspParserState,
    ModemCmdState,
    ModemState,
    ModemCmdType,
    ModemRspType,
    ModemRat,
    ModemOperatorFormat,
    ModemSimState,
    ModemHttpContextState,
    ModemSocketState,
    ModemCMEErrorReportsType,
    ModemCEREGReportsType
)

from .structs import (
    ModemOperator,
    ModemPDPContext,
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
    ModemATParserData
)

from .utils import (
    bytes_to_str,
    parse_cclk_time,
    parse_gnss_time
)

class ModemCore:
    CR = 13
    LF = 10
    PLUS = ord('+')
    GREATER_THAN = ord('>')
    SMALLER_THAN = ord('<')
    SPACE = ord(' ')

    WALTER_MODEM_DEFAULT_CMD_ATTEMPTS = 3
    """The default number of attempts to execute a command."""

    WALTER_MODEM_PIN_RX = 14
    """The RX pin on which modem data is received."""

    WALTER_MODEM_PIN_TX = 48
    """The TX to which modem data must be transmitted."""

    WALTER_MODEM_PIN_RTS = 21
    """The RTS pin on the ESP32 side."""

    WALTER_MODEM_PIN_CTS = 47
    """The CTS pin on the ESP32 size."""

    WALTER_MODEM_PIN_RESET = 45
    """The active low modem reset pin."""

    WALTER_MODEM_BAUD = 115200
    """The baud rate used to talk to the modem."""

    WALTER_MODEM_CMD_TIMEOUT = 5
    """The maximum number of seconds to wait."""

    WALTER_MODEM_MIN_VALID_TIMESTAMP = 1672531200
    """Any modem time below 1 Jan 2023 00:00:00 UTC is considered an invalid time."""

    WALTER_MODEM_MAX_PDP_CTXTS = 8
    """The maximum number of PDP contexts that the library can support."""

    WALTER_MODEM_MAX_SOCKETS = 6
    """The maximum number of sockets that the library can support."""

    WALTER_MODEM_MAX_HTTP_PROFILES = 3
    """The max nr of http profiles"""

    WALTER_MODEM_MAX_TLS_PROFILES = 6
    """The maximum number of TLS profiles that the library can support"""

    WALTER_MODEM_OPERATOR_MAX_SIZE = 16
    """The maximum number of characters of an operator name"""

    def __init__(self):
        self._op_state = ModemOpState.MINIMUM
        """The current operational state of the modem."""

        self._reg_state = ModemNetworkRegState.NOT_SEARCHING
        """The current network registration state of the modem."""

        self._sim_PIN = None
        """The PIN code when required for the installed SIM."""

        self._network_sel_mode = ModemNetworkSelMode.AUTOMATIC
        """The chosen network selection mode."""

        self._operator = ModemOperator()
        """An operator to use, this is ignored when automatic operator selectionis used."""

        self._pdp_ctx = None
        """
        The PDP context which is currently in use by the library or None when
        no PDP context is in use. In use doesn't mean that the 
        context is activated yet it is just a pointer to the PDP context
        which was last used by any of the functions that work with a PDPcontext.
        """
        
        self._pdp_ctx_list = [ModemPDPContext(idx + 1) for idx in range(ModemCore.WALTER_MODEM_MAX_PDP_CTXTS)]
        """The list of PDP contexts."""

        self._socket_list = [ModemSocket(idx + 1) for idx in range(ModemCore.WALTER_MODEM_MAX_SOCKETS) ]
        """The list of sockets"""

        self._socket = None
        """The socket which is currently in use by the library or None when no socket is in use."""

        self._http_context_list = [ModemHttpContext() for _ in range(ModemCore.WALTER_MODEM_MAX_HTTP_PROFILES) ]
        """The list of http contexts in the modem"""

        self._http_current_profile = 0xff
        """Current http profile in use in the modem"""

        self._gnss_fix_lock = asyncio.Lock()
        self._gnss_fix_waiters = []
        """GNSS fix waiters"""

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
            self._parser_data.state = ModemRspParserState.END_LF
            return

        self._parser_data.line += bytes([data])

    async def _uart_reader(self):
        rx_stream = asyncio.StreamReader(self._uart, {})

        while True:
            incoming_uart_data = bytearray(256)
            size = await rx_stream.readinto(incoming_uart_data)
            if self.debug_log:
                for line in incoming_uart_data[:size].splitlines():
                    print(
                        'WalterModem (core, _uart_reader) - DEBUG: RX: '
                        f'"{bytes_to_str(line)}"'
                    )
            for b in incoming_uart_data[:size]:
                if self._parser_data.state == ModemRspParserState.START_CR:
                    if b == ModemCore.CR:
                        self._parser_data.state = ModemRspParserState.START_LF
                    elif b == ModemCore.PLUS:
                        # This is the start of a new line in a multiline response
                        self._parser_data.state = ModemRspParserState.DATA
                        self._add_at_byte_to_buffer(b, False)
                
                elif self._parser_data.state == ModemRspParserState.START_LF:
                    if b == ModemCore.LF:
                        self._parser_data.state = ModemRspParserState.DATA
                
                elif self._parser_data.state == ModemRspParserState.DATA:
                    if b == ModemCore.GREATER_THAN:
                        self._parser_data.state = ModemRspParserState.DATA_PROMPT
                    elif b == ModemCore.SMALLER_THAN:
                        self._parser_data.state = ModemRspParserState.DATA_HTTP_START1
                
                    self._add_at_byte_to_buffer(b, False)
                    
                elif self._parser_data.state == ModemRspParserState.DATA_PROMPT:
                    self._add_at_byte_to_buffer(b, False)
                    if b == ModemCore.SPACE:
                        self._parser_data.state = ModemRspParserState.START_CR
                        await self._queue_rx_buffer()
                    elif b == ModemCore.GREATER_THAN:
                        self._parser_data.state = ModemRspParserState.DATA_PROMPT_HTTP
                    else:
                        # state might have changed after detecting end \r
                        if self._parser_data.state == ModemRspParserState.DATA_PROMPT:
                            self._parser_data.state = ModemRspParserState.DATA
                
                elif self._parser_data.state == ModemRspParserState.DATA_PROMPT_HTTP:
                    self._add_at_byte_to_buffer(b, False)
                    if b == ModemCore.GREATER_THAN:
                        self._parser_data.state = ModemRspParserState.START_CR
                        await self._queue_rx_buffer()
                    else:
                        # state might have changed after detecting end \r
                        if self._parser_data.state == ModemRspParserState.DATA_PROMPT_HTTP:
                            self._parser_data.state = ModemRspParserState.DATA

                elif self._parser_data.state == ModemRspParserState.DATA_HTTP_START1:
                    if b == ModemCore.SMALLER_THAN:
                        self._parser_data.state = ModemRspParserState.DATA_HTTP_START2
                    else:
                        self._parser_data.state = ModemRspParserState.DATA

                    self._add_at_byte_to_buffer(b, False)

                elif self._parser_data.state == ModemRspParserState.DATA_HTTP_START2:
                    if b == ModemCore.SMALLER_THAN and self._http_current_profile < ModemCore.WALTER_MODEM_MAX_HTTP_PROFILES:
                        # FIXME: modem might block longer than cmd timeout,
                        # will lead to retry, error etc - fix properly
                        self._parser_data.raw_chunk_size = self._http_context_list[self._http_current_profile].content_length + len("\r\nOK\r\n")
                        self._parser_data.state = ModemRspParserState.RAW
                    else:
                        self._parser_data.state = ModemRspParserState.DATA

                    self._add_at_byte_to_buffer(b, False)

                elif self._parser_data.state == ModemRspParserState.END_LF:
                    if b == ModemCore.LF:
                        chunk_size = 0 # FIXME
                        #uint16_t chunkSize = _extractRawBufferChunkSize();
                        if chunk_size:
                            self._parser_data.raw_chunk_size = chunk_size
                            self._parser_data.line += b'\r'
                            self._parser_data.state = ModemRspParserState.RAW
                        else:
                            self._parser_data.state = ModemRspParserState.START_CR
                            await self._queue_rx_buffer()
                    else:
                        # only now we know the \r was thrown away for no good reason
                        self._parser_data.line += b'\r'

                        # next byte gets the same treatment; since we really are
                        # back in semi DATA state, as we now know
                        # (but > will not lead to data prompt mode)
                        self._add_at_byte_to_buffer(b, False)
                        if b != ModemCore.CR:
                            self._parser_data.state = ModemRspParserState.DATA

                elif self._parser_data.state == ModemRspParserState.RAW:
                    self._add_at_byte_to_buffer(b, True)
                    self._parser_data.raw_chunk_size -= 1

                    if self._parser_data.raw_chunk_size == 0:
                        self._parser_data.state = ModemRspParserState.START_CR
                        await self._queue_rx_buffer()

    async def _finish_queue_cmd(self, cmd, result):
        cmd.rsp.result = result

        if cmd.complete_handler:
            await cmd.complete_handler(result, cmd.rsp, cmd.complete_handler_arg)

        # we must unblock stuck cmd now
        cmd.state = ModemCmdState.COMPLETE
        cmd.event.set()

    async def _process_queue_cmd(self, tx_stream, cmd):
        if cmd.type == ModemCmdType.TX:
            if self.debug_log:
                print(
                    f'WalterModem (core, _process_queue_cmd) - DEBUG: TX:'
                    f'"{bytes_to_str(cmd.at_cmd)}"'
                )
            tx_stream.write(cmd.at_cmd)
            tx_stream.write(b'\r\n')
            await tx_stream.drain()
            await self._finish_queue_cmd(cmd, ModemState.OK)

        elif cmd.type == ModemCmdType.TX_WAIT \
        or cmd.type == ModemCmdType.DATA_TX_WAIT:
            if cmd.state == ModemCmdState.NEW:
                if self.debug_log:
                    print(
                        'WalterModem (core, _process_queue_cmd) - DEBUG: TX: '
                        f'"{bytes_to_str(cmd.at_cmd)}"'
                    )
                tx_stream.write(cmd.at_cmd)
                if cmd.type == ModemCmdType.DATA_TX_WAIT:
                    tx_stream.write(b'\n')
                else:
                    tx_stream.write(b'\r\n')
                await tx_stream.drain()
                cmd.attempt = 1
                cmd.attempt_start = time.time()
                cmd.state = ModemCmdState.PENDING

            else:
                tick_diff = time.time() - cmd.attempt_start
                timed_out = tick_diff >= ModemCore.WALTER_MODEM_CMD_TIMEOUT
                if timed_out or cmd.state == ModemCmdState.RETRY_AFTER_ERROR:
                    if cmd.attempt >= cmd.max_attempts:
                        if timed_out:
                            await self._finish_queue_cmd(cmd, ModemState.TIMEOUT)
                        else:
                            await self._finish_queue_cmd(cmd, ModemState.ERROR)
                    else:
                        if self.debug_log:
                            print(
                                'WalterModem (core, _process_queue_cmd) - DEBUG: TX: '
                                f'"{bytes_to_str(cmd.at_cmd)}"'
                            )
                        tx_stream.write(cmd.at_cmd)
                        if cmd.type == ModemCmdType.DATA_TX_WAIT:
                            tx_stream.write(b'\n')
                        else:
                            tx_stream.write(b'\r\n')
                        await tx_stream.drain()
                        cmd.attempt += 1
                        cmd.attempt_start = time.time()
                        cmd.state = ModemCmdState.PENDING

                else:
                    return

        elif cmd.type == ModemCmdType.WAIT:
            if cmd.state == ModemCmdState.NEW:
                cmd.attempt_start = time.time()
                cmd.state = ModemCmdState.PENDING

            else:
                tick_diff = time.time() - cmd.attempt_start
                if tick_diff >= ModemCore.WALTER_MODEM_CMD_TIMEOUT:
                    await self._finish_queue_cmd(cmd, ModemState.TIMEOUT)
                else:
                    return
                
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
        
        result = ModemState.OK

        if at_rsp.startswith(b'+CEREG: '):
            ce_reg = int(at_rsp.decode().split(':')[1].split(',')[0])
            self._reg_state = ce_reg
            # TODO: call correct handlers (also still todo in arduino version)

        elif at_rsp.startswith(b'>') or at_rsp.startswith(b'>>>'):
            if cmd and cmd.data and cmd.type == ModemCmdType.DATA_TX_WAIT:
                if self.debug_log:
                    print(
                        'WalterModem (core, _process_queue_rsp) - DEBUG: TX: '
                        f'"{bytes_to_str(cmd.data)}"'
                    )
                tx_stream.write(cmd.data)
                await tx_stream.drain()

        elif at_rsp.startswith(b'ERROR'):
            if cmd is not None:
                cmd.rsp.type = ModemRspType.NO_DATA
                cmd.state = ModemCmdState.RETRY_AFTER_ERROR
            return

        elif at_rsp.startswith(b'+CME ERROR: '):
            if cmd is not None:
                cme_error = int(at_rsp.decode().split(':')[1].split(',')[0])
                cmd.rsp.type = ModemRspType.CME_ERROR
                cmd.rsp.cme_error = cme_error
                cmd.state = ModemCmdState.RETRY_AFTER_ERROR
            return

        elif at_rsp.startswith(b'+CFUN: '):
            op_state = int(at_rsp.decode().split(':')[1].split(',')[0])
            self._op_state = op_state

            if cmd is None:
                return

            cmd.rsp.type = ModemRspType.OP_STATE
            cmd.rsp.op_state = self._op_state

        elif at_rsp.startswith(b'+SQNMODEACTIVE: '):
            if cmd is None:
                return

            cmd.rsp.type = ModemRspType.RAT
            cmd.rsp.rat = int(at_rsp.decode().split(':')[1]) - 1

        elif at_rsp.startswith(b'+SQNBANDSEL: '):
            data = at_rsp[len(b'+SQNBANDSEL: '):]

            # create the array and response type upon reception of the
            # first band selection
            if cmd.rsp.type != ModemRspType.BANDSET_CFG_SET:
                cmd.rsp.type = ModemRspType.BANDSET_CFG_SET
                cmd.rsp.band_sel_cfg_list = []

            bsel = ModemBandSelection()

            if data[0] == ord('0'):
                bsel.rat = ModemRat.LTEM
            else:
                bsel.rat = ModemRat.NBIOT

            # Parse operator name
            bsel.net_operator.format = ModemOperatorFormat.LONG_ALPHANUMERIC
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

        elif at_rsp.startswith(b'+CPIN: '):
            if cmd is None:
                return

            cmd.rsp.type = ModemRspType.SIM_STATE
            if at_rsp[len('+CPIN: '):] == b'READY':
                cmd.rsp.sim_state = ModemSimState.READY
            elif at_rsp[len('+CPIN: '):] == b"SIM PIN":
                cmd.rsp.sim_state = ModemSimState.PIN_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"SIM PUK":
                cmd.rsp.sim_state = ModemSimState.PUK_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"PH-SIM PIN":
                cmd.rsp.sim_state = ModemSimState.PHONE_TO_SIM_PIN_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"PH-FSIM PIN":
                cmd.rsp.sim_state = ModemSimState.PHONE_TO_FIRST_SIM_PIN_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"PH-FSIM PUK":
                cmd.rsp.sim_state = ModemSimState.PHONE_TO_FIRST_SIM_PUK_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"SIM PIN2":
                cmd.rsp.sim_state = ModemSimState.PIN2_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"SIM PUK2":
                cmd.rsp.sim_state = ModemSimState.PUK2_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"PH-NET PIN":
                cmd.rsp.sim_state = ModemSimState.NETWORK_PIN_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"PH-NET PUK":
                cmd.rsp.sim_state = ModemSimState.NETWORK_PUK_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"PH-NETSUB PIN":
                cmd.rsp.sim_state = ModemSimState.NETWORK_SUBSET_PIN_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"PH-NETSUB PUK":
                cmd.rsp.sim_state = ModemSimState.NETWORK_SUBSET_PUK_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"PH-SP PIN":
                cmd.rsp.sim_state = ModemSimState.SERVICE_PROVIDER_PIN_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"PH-SP PUK":
                cmd.rsp.sim_state = ModemSimState.SERVICE_PROVIDER_PUK_REQUIRED 
            elif at_rsp[len('+CPIN: '):] == b"PH-CORP PIN":
                cmd.rsp.sim_state = ModemSimState.CORPORATE_SIM_REQUIRED 
            elif at_rsp[len('+CPIN: '):] == b"PH-CORP PUK":
                cmd.rsp.sim_state = ModemSimState.CORPORATE_PUK_REQUIRED 
            else:
                cmd.rsp.type = ModemRspType.NO_DATA

        elif at_rsp.startswith(b'+CGPADDR: '):
            if not cmd:
                return

            cmd.rsp.type = ModemRspType.PDP_ADDR 
            cmd.rsp.pdp_address_list = []

            parts = at_rsp.decode().split(',')
            
            if len(parts) > 1 and parts[1]:
                cmd.rsp.pdp_address_list.append(parts[1][1:-1])
            if len(parts) > 2 and parts[2]:
                cmd.rsp.pdp_address_list.append(parts[2][1:-1])

        elif at_rsp.startswith(b'+CSQ: '):
            if not cmd:
                return

            parts = at_rsp.decode().split(',')
            raw_rssi = int(parts[0][len('+CSQ: '):])

            cmd.rsp.type = ModemRspType.RSSI
            cmd.rsp.rssi = -113 + (raw_rssi * 2)

        elif at_rsp.startswith(b'+CESQ: '):
            if not cmd:
                return

            cmd.rsp.type = ModemRspType.SIGNAL_QUALITY

            parts = at_rsp.decode().split(',')
            cmd.rsp.signal_quality = ModemSignalQuality()
            cmd.rsp.signal_quality.rsrq = -195 + (int(parts[4]) * 5)
            cmd.rsp.signal_quality.rsrp = -140 + int(parts[5])

        elif at_rsp.startswith(b'+CCLK: '):
            if not cmd:
                return

            cmd.rsp.type = ModemRspType.CLOCK
            time_str = at_rsp[len('+CCLK: '):].decode()[1:-1]   # strip double quotes
            cmd.rsp.clock = parse_cclk_time(time_str)

        elif at_rsp.startswith(b'<<<'):      # <<< is start of SQNHTTPRCV answer
            if self._http_current_profile >= ModemCore.WALTER_MODEM_MAX_HTTP_PROFILES or self._http_context_list[self._http_current_profile].state != ModemHttpContextState.GOT_RING:
                result = ModemState.ERROR
            else:
                if not cmd:
                    return

                cmd.rsp.type = ModemRspType.HTTP_RESPONSE
                cmd.rsp.http_response = ModemHttpResponse()
                cmd.rsp.http_response.http_status = self._http_context_list[self._http_current_profile].http_status
                cmd.rsp.http_response.data = at_rsp[3:-len(b'\r\nOK\r\n')] # 3 skips: <<<
                cmd.rsp.http_response.content_type = self._http_context_list[self._http_current_profile].content_type
                cmd.rsp.http_response.content_length = self._http_context_list[self._http_current_profile].content_length

                # the complete handler will reset the state,
                # even if we never received <<< but got an error instead

        elif at_rsp.startswith(b'+SQNHTTPRING: '):
            profile_id_str, http_status_str, content_type, content_length_str = at_rsp[len("+SQNHTTPRING: "):].decode().split(',')
            profile_id = int(profile_id_str)
            http_status = int(http_status_str)
            content_length = int(content_length_str)

            if profile_id >= ModemCore.WALTER_MODEM_MAX_HTTP_PROFILES:
                # TODO: return error if modem returns invalid profile id.
                # problem: this message is an URC: the associated cmd
                # may be any random command currently executing */
                return

            # TODO: if not expecting a ring, it may be a bug in the modem
            # or at our side and we should report an error + read the
            # content to free the modem buffer
            # (knowing that this is a URC so there is no command
            # to give feedback to)
            if self._http_context_list[profile_id].state != ModemHttpContextState.EXPECT_RING:
                return

            # remember ring info
            self._http_context_list[profile_id].state = ModemHttpContextState.GOT_RING
            self._http_context_list[profile_id].http_status = http_status
            self._http_context_list[profile_id].content_type = content_type
            self._http_context_list[profile_id].content_length = content_length

        elif at_rsp.startswith(b'+SQNHTTPCONNECT: '):
            profile_id_str, result_code_str = at_rsp[len("+SQNHTTPCONNECT: "):].decode().split(',')
            profile_id = int(profile_id_str)
            result_code = int(result_code_str)

            if profile_id < ModemCore.WALTER_MODEM_MAX_HTTP_PROFILES:
                if result_code == 0:
                    self._http_context_list[profile_id].connected = True
                else:
                    self._http_context_list[profile_id].connected = False

        elif at_rsp.startswith(b'+SQNHTTPDISCONNECT: '):
            profile_id = int(at_rsp[len("+SQNHTTPDISCONNECT: "):].decode())

            if profile_id < ModemCore.WALTER_MODEM_MAX_HTTP_PROFILES:
                self._http_context_list[profile_id].connected = False

        elif at_rsp.startswith(b'+SQNHTTPSH: '):
            profile_id_str, _ = at_rsp[len('+SQNHTTPSH: '):].decode().split(',')
            profile_id = int(profile_id_str)

            if profile_id < ModemCore.WALTER_MODEM_MAX_HTTP_PROFILES:
                self._http_context_list[profile_id].connected = False

        elif at_rsp.startswith(b'+SQNSH: '):
            socket_id = int(at_rsp[len('+SQNSH: '):].decode())
            try:
                _socket = self._socket_list[socket_id - 1]
            except Exception:
                return

            self._socket = _socket
            _socket.state = ModemSocketState.FREE

        elif at_rsp.startswith(b'+LPGNSSFIXREADY: '):
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

        elif at_rsp.startswith(b'+LPGNSSASSISTANCE: '):
            if not cmd:
                return

            if cmd.rsp.type != ModemRspType.GNSS_ASSISTANCE_DATA:
                cmd.rsp.type = ModemRspType.GNSS_ASSISTANCE_DATA
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

        elif at_rsp.startswith(b"+SQNMONI"):
            if cmd is None:
                return

            cmd.rsp.type = ModemRspType.CELL_INFO

            data_str = at_rsp[len(b"+SQNMONI: "):].decode()

            cmd.rsp.cell_information = ModemCellInformation()
            first_key_parsed = False

            for part in data_str.split(' '):
                if ':' not in part:
                    continue
                
                key, value = part.split(':', 1)
                key = key.strip()
                value = value.strip()

                if not first_key_parsed and len(key) > 2:
                    operator_name = key[:-2]
                    cmd.rsp.cell_information.net_name = operator_name[:ModemCore.WALTER_MODEM_OPERATOR_MAX_SIZE]
                    key = key[-2:]
                    first_key_parsed = True

                if key == "Cc":
                    cmd.rsp.cell_information.cc = int(value, 10)
                elif key == "Nc":
                    cmd.rsp.cell_information.nc = int(value, 10)
                elif key == "RSRP":
                    cmd.rsp.cell_information.rsrp = float(value)
                elif key == "CINR":
                    cmd.rsp.cell_information.cinr = float(value)
                elif key == "RSRQ":
                    cmd.rsp.cell_information.rsrq = float(value)
                elif key == "TAC":
                    cmd.rsp.cell_information.tac = int(value, 10)
                elif key == "Id":
                    cmd.rsp.cell_information.pci = int(value, 10)
                elif key == "EARFCN":
                    cmd.rsp.cell_information.earfcn = int(value, 10)
                elif key == "PWR":
                    cmd.rsp.cell_information.rssi = float(value)
                elif key == "PAGING":
                    cmd.rsp.cell_information.paging = int(value, 10)
                elif key == "CID":
                    cmd.rsp.cell_information.cid = int(value, 16)
                elif key == "BAND":
                    cmd.rsp.cell_information.band = int(value, 10)
                elif key == "BW":
                    cmd.rsp.cell_information.bw = int(value, 10)
                elif key == "CE":
                    cmd.rsp.cell_information.ce_level = int(value, 10)



#        if cmd:
#            print('process rsp to cmd:' + str(cmd) + ' ' + str(cmd.at_cmd) + ' ' + str(at_rsp) + ' expecting ' + str(cmd.at_rsp))
#        else:
#            print('process rsp without preceding cmd: ' + str(at_rsp))

        if not cmd or not cmd.at_rsp or cmd.type == ModemCmdType.TX or cmd.at_rsp != at_rsp[:len(cmd.at_rsp)]:
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
                    if self.debug_log:
                        print(
                            'WalterModem (core, _queue_worker) - ERROR: '
                            f'Invalid task queue item: {type(qitem)}, {str(qitem)}'
                        )
                    continue

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
                if cur_cmd.state == ModemCmdState.RETRY_AFTER_ERROR \
                or cur_cmd.state == ModemCmdState.NEW \
                or cur_cmd.state == ModemCmdState.PENDING:
                    await self._process_queue_cmd(tx_stream, cur_cmd)

                if cur_cmd.state == ModemCmdState.COMPLETE:
                    cur_cmd = None

    async def _run_cmd(self,
        rsp: ModemRsp | None,
        at_cmd: str,
        at_rsp: str, 
        cmd_type: int = ModemCmdType.TX_WAIT,
        data = None,
        complete_handler = None,
        complete_handler_arg = None,
        max_attempts = WALTER_MODEM_DEFAULT_CMD_ATTEMPTS
    ) -> bool:
        """
        Add a command to the command queue and await execution.
        
        This function add a command to the task queue. This function will 
        only fail when the command queue is full. The command which is put
        onto the queue will automatically get the WALTER_MODEM_CMD_STATE_NEW
        state. This function will never call any callbacks.
        
        :param rsp: the ModemRsp 
        :param cmd_type: The type of queue AT command.
        :param at_cmd: NULL terminated array of command elements. The elements
        must stay available until the command is complete. The array is only
        shallow copied.
        :param at_rsp: The expected AT response.
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
        cmd.type = cmd_type
        cmd.data = data
        cmd.complete_handler = complete_handler
        cmd.complete_handler_arg = complete_handler_arg
        cmd.max_attempts = max_attempts
        cmd.state = ModemCmdState.NEW
        cmd.attempt = 0
        cmd.attempt_start = 0

        qitem = ModemTaskQueueItem()
        qitem.cmd = cmd
        await self._task_queue.put(qitem)

        # we expect the queue runner to release the (b)lock.
        await cmd.event.wait()

        return (
            cmd.rsp.result == ModemState.OK or
            (cmd.rsp.type == ModemRspType.HTTP_RESPONSE and cmd.rsp.result == ModemState.NO_DATA)
        )

    async def begin(self, debug_log: bool = False):
        self.debug_log = debug_log
        self._uart = UART(2,
            baudrate=ModemCore.WALTER_MODEM_BAUD,
            bits=8,
            parity=None,
            stop=1,
            flow=UART.RTS|UART.CTS,
            tx=ModemCore.WALTER_MODEM_PIN_TX,
            rx=ModemCore.WALTER_MODEM_PIN_RX,
            cts=ModemCore.WALTER_MODEM_PIN_CTS,
            rts=ModemCore.WALTER_MODEM_PIN_RTS,
            timeout=0,
            timeout_char=0,
            txbuf=2048,
            rxbuf=2048
        )

        self._task_queue = Queue()
        self._command_queue = Queue()
        self._parser_data = ModemATParserData()

        asyncio.create_task(self._uart_reader())
        asyncio.create_task(self._queue_worker())

        await self.reset()
        await self.config_cme_error_reports(ModemCMEErrorReportsType.NUMERIC)
        await self.config_cereg_reports(ModemCEREGReportsType.ENABLED)