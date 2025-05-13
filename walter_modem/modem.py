import asyncio

from machine import ( # type: ignore
    UART,
    Pin,
    reset_cause,
    DEEPSLEEP_RESET,
)
from .queue import Queue
from .core import ModemCore
import walter_modem.mixins as mixins
from .enums import (
    WalterModemCMEErrorReportsType,
    WalterModemCEREGReportsType,
)
from .structs import (
    ModemATParserData,
)
from .utils import (
    log
)

class Modem(
    mixins.ModemCommon,
    mixins.ModemSimNetwork,
    mixins.ModemTLSCerts,
    mixins.ModemPDP,
    mixins.ModemGNSS,
    mixins.ModemSocket,
    mixins.ModemMQTT,
    mixins.ModemHTTP,
    mixins.ModemCoap,
    mixins.ModemSleep
):
    def __init__(self):
        ModemCore.__init__(self)

    async def begin(self,
        debug_log: bool = False,
        _dev_debug_uart_reader = False
    ):
        if not self._begun:
            self.debug_log = debug_log
            self._uart = UART(2,
                baudrate=ModemCore.BAUD,
                bits=8,
                parity=None,
                stop=1,
                flow=UART.RTS|UART.CTS,
                tx=ModemCore.PIN_TX,
                rx=ModemCore.PIN_RX,
                cts=ModemCore.PIN_CTS,
                rts=ModemCore.PIN_RTS,
                timeout=0,
                timeout_char=0,
                txbuf=2048,
                rxbuf=2048
            )

            self._reset_pin = Pin(ModemCore.PIN_RESET, Pin.OUT, value=1, hold=True)

            self._task_queue = Queue()
            self._command_queue = Queue()
            self._parser_data = ModemATParserData()

            if _dev_debug_uart_reader:
                self._uart_reader_task = asyncio.create_task(self._dev_debug_uart_reader())
            else:
                self._uart_reader_task = asyncio.create_task(self._uart_reader())
            self._queue_worker_task = asyncio.create_task(self._queue_worker())

            
            if reset_cause() == DEEPSLEEP_RESET:
                await self._sleep_wakeup()
            else:
                if not await self.reset():
                    raise RuntimeError('Failed to reset modem')
                
            if not await self.config_cme_error_reports(WalterModemCMEErrorReportsType.NUMERIC):
                raise RuntimeError('Failed to configure CME error reports')
            if not await self.config_cereg_reports(WalterModemCEREGReportsType.ENABLED_UE_PSM_WITH_LOCATION_EMM_CAUSE):
                raise RuntimeError('Failed to configure cereg reports')
        
        self._begun = True

    def register_application_queue_rsp_handler(self, start_pattern: bytes, handler: callable):
        if isinstance(start_pattern, bytes) and callable(handler):
            if not self._application_queue_rsp_handlers_set:
                self._application_queue_rsp_handlers_set = True
                self._application_queue_rsp_handlers = [(start_pattern, handler)]
            else:
                self._application_queue_rsp_handlers.append((start_pattern, handler))
        else:
            log('WARNING', 'Invalid parameters, not registering application queue rsp handler')
    
    def unregister_application_queue_rsp_handler(self, handler: callable):
        if callable(handler):
            if self._application_queue_rsp_handlers_set:
                for i in range(len(self._application_queue_rsp_handlers) - 1, -1, -1):
                    if self._application_queue_rsp_handlers[i][1] is handler:
                        self._application_queue_rsp_handlers.pop(i)
                if not self._application_queue_rsp_handlers:
                    self._application_queue_rsp_handlers_set = False
        else:
            log('WARNING', f'Invalid paramater, cannot unregister: {type(handler)}, must be a callable')