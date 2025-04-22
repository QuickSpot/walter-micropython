import time

from machine import Pin, lightsleep, deepsleep # type: ignore

from ..core import ModemCore

class ModemSleep(ModemCore):
    def sleep(self,
        sleep_time_ms: int,
        light_sleep: bool = False,
        persist_mqtt_subs: bool = False
    ):
        if light_sleep:
            self._uart.init(flow=0)
            rts_pin = Pin(ModemCore.PIN_RTS, value=1, hold=True)
            lightsleep(sleep_time_ms)
            rts_pin.init(hold=False)
        else:
            self._uart_reader_task.cancel()
            self._queue_worker_task.cancel()
            self._uart.deinit()

            self._sleep_prepare(persist_mqtt_subs)
            time.sleep(1)
            deepsleep(sleep_time_ms)
