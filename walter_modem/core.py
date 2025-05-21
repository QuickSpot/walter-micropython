import asyncio
import gc
import time

from machine import ( # type: ignore
    UART,
    Pin,
    lightsleep,
    deepsleep,
    reset_cause,
    DEEPSLEEP_RESET
)
from micropython import const # type: ignore
from esp32 import gpio_deep_sleep_hold # type: ignore
from .queue import Queue

from .coreEnums import (
    WalterModemOpState,
    WalterModemNetworkRegState,
    WalterModemRspParserState,
    WalterModemCmdState,
    WalterModemState,
    WalterModemCmdType,
    WalterModemRspType,
    WalterModemCMEErrorReportsType,
    WalterModemCEREGReportsType
)
from .coreStructs import (
    ModemTaskQueueItem,
    ModemCmd,
    ModemRsp,
    ModemATParserData
)
from .utils import (
    parse_cclk_time,
    log
)

_UNICODE_CR = const(13)
_UNICODE_LF = const(10)
_UNICODE_PLUS = const(43)
_UNICODE_GREATER_THAN = const(62)
_UNICODE_SMALLER_THAN = const(60)
_UNICODE_SPACE = const(32)

_CMD_DEFAULT_ATTEMPTS = const(3)
"""The default number of attempts to execute a command."""
_CMD_TIMEOUT = const(5)
"""The maximum number of seconds to wait."""

_PIN_RX = const(14)
"""The RX pin on which modem data is received."""
_PIN_TX = const(48)
"""The TX to which modem data must be transmitted."""
_PIN_RTS = const(21)
"""The RTS pin on the ESP32 side."""
_PIN_CTS = const(47)
"""The CTS pin on the ESP32 size."""
_PIN_RESET = const(45)
"""The active low modem reset pin."""

_BAUD = const(115200)
"""The baud rate used to talk to the modem."""

class ModemCore:
    def __init__(self):
        gpio_deep_sleep_hold(True)

        self.__initialised_mixins = []
        """
        Internal book-keeping during initialisation, tracking which mixin's init has ran.
        Deleted after initialisation.
        """

        self.__queue_rsp_rsp_handlers: tuple[tuple[bytes, callable]] = (
            (b'>>>', self.__handle_data_tx_wait),
            (b'>', self.__handle_data_tx_wait),
            (b'ERROR', self.__handle_error),
            (b'+CME ERROR: ', self.__handle_cme_error),
            (b'+CCLK: ', self.__handle__cclk),
            (b'+CFUN: ', self.__handle_cfun),
            (b'+CEREG: ', self.__handle_cereg),
        )
        """The mapping of rsp patterns to handler methods for processing the rsp queue"""

        self.__queue_rsp_cmd_handlers: tuple[tuple[bytes, callable]] = ()
        """The mapping of cmd patterns to handler methods for processing the rsp queue"""

        self.__application_queue_rsp_handlers: list[tuple[bytes, callable]] = None
        """The mapping of rsp patterns to handler methods defined by the application code"""

        self.__application_queue_rsp_handlers_set: bool = False
        """
        Whether or not the application has defined/set queue rsp handlers
        Set as seperate bool for faster lookup.
        """

        self.__deep_sleep_prepare_callables = ()
        """Methods called on deepsleep prepare"""

        self.__deep_sleep_wakeup_callables = ()
        """Methods called on deepsleep wakeup"""

        self.__mirror_state_reset_callables = ()
        """Methods called on mirror-state reset"""

        self.__reset_pin = None
        """Reset pin (high indicates the modem to stay on)"""

        self.__begun = False
        """Whether or not the begin method has already been run."""

        self._op_state = WalterModemOpState.MINIMUM
        """The current operational state of the modem."""

        self._reg_state = WalterModemNetworkRegState.NOT_SEARCHING
        """The current network registration state of the modem."""

        self.default_modem_rsp = ModemRsp()
        """ModemRsp used when none is provided by the user."""

        gc.collect()
        if __debug__:
            log('DEBUG', 'Core loaded')

#region PublicMethods

    async def begin(self,
        uart_debug: bool = False
    ):
        if not self.__begun:
            if __debug__:
                self.uart_debug = uart_debug
            self.__uart = UART(2,
                baudrate=_BAUD,
                bits=8,
                parity=None,
                stop=1,
                flow=UART.RTS|UART.CTS,
                tx=_PIN_TX,
                rx=_PIN_RX,
                cts=_PIN_CTS,
                rts=_PIN_RTS,
                timeout=0,
                timeout_char=0,
                txbuf=2048,
                rxbuf=2048
            )

            self.__reset_pin = Pin(_PIN_RESET, Pin.OUT, value=1, hold=True)

            self.__task_queue = Queue()
            self.__command_queue = Queue()
            self.__parser_data = ModemATParserData()

            self.__uart_reader_task = asyncio.create_task(self._uart_reader())
            self.__queue_worker_task = asyncio.create_task(self._queue_worker())

            
            if reset_cause() == DEEPSLEEP_RESET:
                await self._deep_sleep_wakeup()
            else:
                if not await self.reset():
                    raise RuntimeError('Failed to reset modem')
                
            if not await self.config_cme_error_reports(
                WalterModemCMEErrorReportsType.NUMERIC):
                raise RuntimeError('Failed to configure CME error reports')
            if not await self.config_cereg_reports(
                WalterModemCEREGReportsType.ENABLED_UE_PSM_WITH_LOCATION_EMM_CAUSE):
                raise RuntimeError('Failed to configure cereg reports')
        
        self.__begun = True

    async def reset(self) -> bool:
        self.__reset_pin.init(hold=False)
        self.__reset_pin.off()
        time.sleep(0.3)
        self.__reset_pin.on()
        self.__reset_pin.init(hold=True)

        self._reset_mirror_state()

        return await self._run_cmd(
            at_cmd='',
            at_rsp=b'+SYSSTART',
            cmd_type=WalterModemCmdType.WAIT
        )
    
    async def soft_reset(self) -> bool:
        cmd_result = await self._run_cmd(
            at_cmd='AT^RESET',
            at_rsp=b'+SYSSTART'
        )

        if cmd_result: self._reset_mirror_state()
        return cmd_result

    async def check_comm(self) -> bool:
        return await self._run_cmd(
            at_cmd='AT',
            at_rsp=b'OK'
        )
    
    async def get_clock(self, rsp: ModemRsp = None
    ) -> bool:
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CCLK?',
            at_rsp=b'OK'
        )

    async def config_cme_error_reports(self,
        reports_type: int = WalterModemCMEErrorReportsType.NUMERIC,
        rsp: ModemRsp = None
    ) -> bool:
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CMEE={reports_type}',
            at_rsp=b'OK'
        )
    
    async def config_cereg_reports(self,
        reports_type: int = WalterModemCEREGReportsType.ENABLED,
        rsp: ModemRsp = None
    ) -> bool:
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CEREG={reports_type}',
            at_rsp=b'OK'
        )

    async def get_op_state(self, rsp: ModemRsp = None) -> bool:
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CFUN?',
            at_rsp=b'OK'
        )
    
    async def set_op_state(self, op_state: int, rsp: ModemRsp = None) -> bool:
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CFUN={op_state}',
            at_rsp=b'OK'
        )

    def get_network_reg_state(self) -> int:
        return self._reg_state

    def sleep(self,
        sleep_time_ms: int,
        light_sleep: bool = False,
        persist_mqtt_subs: bool = False
    ):
        if light_sleep:
            self.__uart.init(flow=0)
            rts_pin = Pin(_PIN_RTS, value=1, hold=True)
            lightsleep(sleep_time_ms)
            rts_pin.init(hold=False)
        else:
            self.__uart_reader_task.cancel()
            self.__queue_worker_task.cancel()
            self.__uart.deinit()

            self._deep_sleep_prepare(persist_mqtt_subs=persist_mqtt_subs)
            time.sleep(1)
            deepsleep(sleep_time_ms)

    def register_application_queue_rsp_handler(self, start_pattern: bytes, handler: callable):
        if isinstance(start_pattern, bytes) and callable(handler):
            if not self.__application_queue_rsp_handlers_set:
                self.__application_queue_rsp_handlers_set = True
                self.__application_queue_rsp_handlers = [(start_pattern, handler)]
            else:
                self.__application_queue_rsp_handlers.append((start_pattern, handler))
        else:
            log('WARNING', 'Invalid parameters, not registering application queue rsp handler')
    
    def unregister_application_queue_rsp_handler(self, handler: callable):
        if callable(handler):
            if self.__application_queue_rsp_handlers_set:
                for i in range(len(self.__application_queue_rsp_handlers) - 1, -1, -1):
                    if self.__application_queue_rsp_handlers[i][1] is handler:
                        self.__application_queue_rsp_handlers.pop(i)
                if not self.__application_queue_rsp_handlers:
                    self.__application_queue_rsp_handlers_set = False
        else:
            log('WARNING',
            f'Invalid paramater, cannot unregister: {type(handler)}, must be a callable')

#endregion

#region QueueResponseHandler

    async def __handle__cclk(self, tx_stream, cmd, at_rsp):
        if not cmd:
            return None

        cmd.rsp.type = WalterModemRspType.CLOCK
        time_str = at_rsp[len('+CCLK: '):].decode()[1:-1] # strip double quotes
        cmd.rsp.clock = parse_cclk_time(time_str)

        return WalterModemState.OK

    async def __handle_data_tx_wait(self, tx_stream, cmd, at_rsp):
        if cmd and cmd.data and cmd.type == WalterModemCmdType.DATA_TX_WAIT:
            tx_stream.write(cmd.data)
            await tx_stream.drain()

        return WalterModemState.OK

    async def __handle_error(self, tx_stream, cmd, at_rsp):
        if cmd is not None:
            cmd.rsp.type = WalterModemRspType.NO_DATA
            cmd.state = WalterModemCmdState.RETRY_AFTER_ERROR
        return None
    
    async def __handle_cme_error(self, tx_stream, cmd, at_rsp):
        if cmd is not None:
            cme_error = int(at_rsp.decode().split(':')[1].split(',')[0])
            cmd.rsp.type = WalterModemRspType.CME_ERROR
            cmd.rsp.cme_error = cme_error
            cmd.state = WalterModemCmdState.RETRY_AFTER_ERROR
        return None

    async def __handle_cfun(self, tx_stream, cmd, at_rsp):
        op_state = int(at_rsp.decode().split(':')[1].split(',')[0])
        self._op_state = op_state

        if cmd is None:
            return None

        cmd.rsp.type = WalterModemRspType.OP_STATE
        cmd.rsp.op_state = self._op_state
        return WalterModemState.OK

    async def __handle_cereg(self, tx_stream, cmd, at_rsp):
        parts = at_rsp.decode().split(':')[1].split(',')
        parts_len = len(parts)
        if parts_len == 1 or parts_len > 2:
            self._reg_state = int(parts[0])
        elif parts_len == 2:
            self._reg_state = int(parts[1])

#endregion

#region UARTReading

    async def _queue_rx_buffer(self):
        """
        Copy the currently received data buffer into the task queue.
        
        This function will copy the current modem receive buffer into the
        task queue. When the buffer could not be placed in the queue it will
        be silently dropped.
        
        :returns: None.
        """
        qitem = ModemTaskQueueItem()
        qitem.rsp = self.__parser_data.line
        
        if __debug__:
            if self.uart_debug:
                try:
                    log('DEBUG, RX', qitem.rsp.decode())
                except:
                    log('DEBUG, RX', qitem.rsp)
        await self.__task_queue.put(qitem)

        self.__parser_data.line = bytearray()

    def _add_at_byte_to_buffer(self, data, raw_mode_active):
        """
        Handle an AT data byte.
        
        This function is used by the AT data parser to add a databyte to 
        the buffer currently in use or to reserve a new buffer to add a byte
        to.
        
        :param data: The data byte to handle.
        
        :returns: None.
        """
        
        if not raw_mode_active and data == _UNICODE_CR:
            self.__parser_data.state = WalterModemRspParserState.END_LF
            return

        self.__parser_data.line += bytes([data])

    async def _uart_reader(self):
        rx_stream = asyncio.StreamReader(self.__uart, {})

        while True:
            incoming_uart_data = bytearray(256)
            size = await rx_stream.readinto(incoming_uart_data)

            for b in incoming_uart_data[:size]:
                if self.__parser_data.state == WalterModemRspParserState.START_CR:
                    if b == _UNICODE_CR:
                        self.__parser_data.state = WalterModemRspParserState.START_LF
                    elif b == _UNICODE_PLUS:
                        # This is the start of a new line in a multiline response
                        self.__parser_data.state = WalterModemRspParserState.DATA
                        self._add_at_byte_to_buffer(b, False)
                    else:
                        self.__parser_data.state = WalterModemRspParserState.DATA
                        self._add_at_byte_to_buffer(b, False)
                
                elif self.__parser_data.state == WalterModemRspParserState.START_LF:
                    if b == _UNICODE_LF:
                        self.__parser_data.state = WalterModemRspParserState.DATA
                
                elif self.__parser_data.state == WalterModemRspParserState.DATA:
                    if b == _UNICODE_GREATER_THAN:
                        self.__parser_data.state = WalterModemRspParserState.DATA_PROMPT
                    elif b == _UNICODE_SMALLER_THAN:
                        self.__parser_data.state = WalterModemRspParserState.DATA_HTTP_START1
                
                    self._add_at_byte_to_buffer(b, False)
                    
                elif self.__parser_data.state == WalterModemRspParserState.DATA_PROMPT:
                    self._add_at_byte_to_buffer(b, False)
                    if b == _UNICODE_SPACE:
                        self.__parser_data.state = WalterModemRspParserState.START_CR
                        await self._queue_rx_buffer()
                    elif b == _UNICODE_GREATER_THAN:
                        self.__parser_data.state = WalterModemRspParserState.DATA_PROMPT_HTTP
                    else:
                        # state might have changed after detecting end \r
                        if self.__parser_data.state == WalterModemRspParserState.DATA_PROMPT:
                            self.__parser_data.state = WalterModemRspParserState.DATA
                
                elif self.__parser_data.state == WalterModemRspParserState.DATA_PROMPT_HTTP:
                    self._add_at_byte_to_buffer(b, False)
                    if b == _UNICODE_GREATER_THAN:
                        self.__parser_data.state = WalterModemRspParserState.START_CR
                        await self._queue_rx_buffer()
                    else:
                        # state might have changed after detecting end \r
                        if self.__parser_data.state == WalterModemRspParserState.DATA_PROMPT_HTTP:
                            self.__parser_data.state = WalterModemRspParserState.DATA

                elif self.__parser_data.state == WalterModemRspParserState.DATA_HTTP_START1:
                    if b == _UNICODE_SMALLER_THAN:
                        self.__parser_data.state = WalterModemRspParserState.DATA_HTTP_START2
                    else:
                        self.__parser_data.state = WalterModemRspParserState.DATA

                    self._add_at_byte_to_buffer(b, False)

                elif self.__parser_data.state == WalterModemRspParserState.DATA_HTTP_START2:
                    if b == _UNICODE_SMALLER_THAN and self._http_current_profile < 3: #Max http ctx ids
                        # FIXME: modem might block longer than cmd timeout,
                        # will lead to retry, error etc - fix properly
                        self.__parser_data.raw_chunk_size = self._http_context_list[self._http_current_profile].content_length + len("\r\nOK\r\n")
                        self.__parser_data.state = WalterModemRspParserState.RAW
                    else:
                        self.__parser_data.state = WalterModemRspParserState.DATA

                    self._add_at_byte_to_buffer(b, False)

                elif self.__parser_data.state == WalterModemRspParserState.END_LF:
                    if b == _UNICODE_LF:
                        if b'+CME ERROR' in self.__parser_data.line:
                            self.__parser_data.raw_chunk_size = 0

                        if self.__parser_data.raw_chunk_size:
                            self.__parser_data.line += b'\r'
                            self.__parser_data.state = WalterModemRspParserState.RAW
                        else:
                            self.__parser_data.state = WalterModemRspParserState.START_CR
                            await self._queue_rx_buffer()
                    else:
                        # only now we know the \r was thrown away for no good reason
                        self.__parser_data.line += b'\r'

                        # next byte gets the same treatment; since we really are
                        # back in semi DATA state, as we now know
                        # (but > will not lead to data prompt mode)
                        self._add_at_byte_to_buffer(b, False)
                        if b != _UNICODE_CR:
                            self.__parser_data.state = WalterModemRspParserState.DATA

                elif self.__parser_data.state == WalterModemRspParserState.RAW:
                    self._add_at_byte_to_buffer(b, True)
                    self.__parser_data.raw_chunk_size -= 1

                    if self.__parser_data.raw_chunk_size == 0:
                        self.__parser_data.state = WalterModemRspParserState.START_CR
                        await self._queue_rx_buffer()


#endregion

#region QueueProcessing

    async def _queue_worker(self):
        tx_stream = asyncio.StreamWriter(self.__uart, {})
        cur_cmd = None

        while True:
            if not cur_cmd and not self.__command_queue.empty():
                qitem = ModemTaskQueueItem()
                qitem.cmd = await self.__command_queue.get()
            else:
                qitem = await self.__task_queue.get()
                if not isinstance(qitem, ModemTaskQueueItem):
                    log('ERROR',
                        f'Invalid task queue item: {type(qitem)}, {str(qitem)}')

            # process or enqueue new command or response
            if qitem.cmd:
                if not cur_cmd:
                    cur_cmd = qitem.cmd
                else:
                    await self.__command_queue.put(qitem.cmd)
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

    async def _process_queue_cmd(self, tx_stream, cmd):
        if cmd.type == WalterModemCmdType.TX:
            if __debug__: 
                if self.uart_debug: log('DEBUG, TX', cmd.at_cmd)

            tx_stream.write(cmd.at_cmd)
            tx_stream.write(b'\r\n')
            await tx_stream.drain()
            await self._finish_queue_cmd(cmd, WalterModemState.OK)

        elif cmd.type == WalterModemCmdType.TX_WAIT \
        or cmd.type == WalterModemCmdType.DATA_TX_WAIT:
            if cmd.state == WalterModemCmdState.NEW:
                if __debug__:
                    if self.uart_debug: log('DEBUG, TX', cmd.at_cmd)
                    
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
                timed_out = tick_diff >= _CMD_TIMEOUT
                if timed_out or cmd.state == WalterModemCmdState.RETRY_AFTER_ERROR:
                    if cmd.attempt >= cmd.max_attempts:
                        if timed_out:
                            await self._finish_queue_cmd(cmd, WalterModemState.TIMEOUT)
                        else:
                            await self._finish_queue_cmd(cmd, WalterModemState.ERROR)
                    else:
                        if __debug__:
                            if self.uart_debug: log('DEBUG, TX', cmd.at_cmd)

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
                if tick_diff >= _CMD_TIMEOUT:
                    await self._finish_queue_cmd(cmd, WalterModemState.TIMEOUT)
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
        result = WalterModemState.OK 
        # Gets overwriten with the handler return value.
        # OK is set in case no handlers were called, state is OK.
        # Handlers returning None cause _finish_queue_cmd to no longer be called.

        for pattern, handler in self.__queue_rsp_rsp_handlers:
            if at_rsp.startswith(pattern):
                result = await handler(tx_stream, cmd, at_rsp)
                break
        
        if cmd and cmd.at_cmd:
            for pattern, handler in self.__queue_rsp_cmd_handlers:
                if cmd.at_cmd.startswith(pattern):
                    result = await handler(tx_stream, cmd, at_rsp)
                    break
        
        if self.__application_queue_rsp_handlers_set:
            for pattern, handler in self.__application_queue_rsp_handlers:
                if at_rsp.startswith(pattern):
                    handler(cmd, at_rsp)
                    break

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

    async def _finish_queue_cmd(self, cmd, result):
        cmd.rsp.result = result

        if cmd.complete_handler:
            await cmd.complete_handler(result, cmd.rsp, cmd.complete_handler_arg)

        # we must unblock stuck cmd now
        cmd.state = WalterModemCmdState.COMPLETE
        cmd.event.set()

#endregion
#region RunCommand

    async def _run_cmd(self,
        at_cmd: str,
        at_rsp: str | tuple[str], 
        rsp: ModemRsp | None = None,
        ring_return: list | None = None,
        cmd_type: int = WalterModemCmdType.TX_WAIT,
        data = None,
        complete_handler = None,
        complete_handler_arg = None,
        max_attempts = _CMD_DEFAULT_ATTEMPTS
    ) -> bool:
        cmd = ModemCmd()

        cmd.at_cmd = at_cmd
        cmd.at_rsp = at_rsp
        cmd.rsp = rsp if rsp else self.default_modem_rsp
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
        await self.__task_queue.put(qitem)

        # we expect the queue runner to release the (b)lock.
        await cmd.event.wait()

        return_value = (
            cmd.rsp.result == WalterModemState.OK or
            (cmd.rsp.type == WalterModemRspType.HTTP and cmd.rsp.result == WalterModemState.NO_DATA)
        )

        del cmd
        del qitem

        return return_value

#endregion
#region Sleep

    async def _deep_sleep_wakeup(self):
        await self._run_cmd(at_cmd='AT+CFUN?', at_rsp=b'OK')
        await self._run_cmd(at_cmd='AT+CEREG?', at_rsp=b'OK')
        await self._run_cmd(at_cmd='AT+SQNSCFG?', at_rsp=b'OK')

        for method in self.__deep_sleep_wakeup_callables:
            await method()

    def _deep_sleep_prepare(self, *args, **kwargs):
        for method in self.__deep_sleep_prepare_callables:
            method(*args, **kwargs)

#region MirrorState
    
    def _reset_mirror_state(self):
        self._op_state = WalterModemOpState.MINIMUM
        self._reg_state = WalterModemNetworkRegState.NOT_SEARCHING

        for method in self.__mirror_state_reset_callables:
            method()
        
        gc.collect()

#endregion
