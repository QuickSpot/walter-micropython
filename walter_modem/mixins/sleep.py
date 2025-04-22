import time

from machine import Pin, lightsleep, deepsleep # type: ignore

from ..core import ModemCore
from ..enums import (
    WalterModemPSMMode,
)
from ..structs import (
    ModemRsp
)
from ..utils import log

_PSM_TAU_UNIT_OPTIONS = (
    (0b110, 320 * 3600),  # 320 h
    (0b010, 10  * 3600),  # 10 h
    (0b001, 1   * 3600),  # 1 h
    (0b000, 10  *  60),   # 10 m
    (0b101, 1   *  60),   # 1 m
    (0b100,      30),     # 30 s
    (0b011,       2),     # 2 s
)

_PSM_ACTIVE_UNIT_OPTIONS = (
    (0b010,  6 * 60),   # 6 min
    (0b001,      60),   # 1 min
    (0b000,       2),   # 2 s
)

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
    
    def _periodic_TAU_s_to_binary_str(periodic_TAU_s: int) -> str:
        """
        Convert periodic TAU in seconds into the 7-bit T3412 code:
          [3 bits unit prefix][5 bits value]
        where value ∈ [1..31].  
        Minimal fallback for <2 s is 2 s step.
        """
    
        if periodic_TAU_s < 2:
            log('WARNING', f'Requested TAU={periodic_TAU_s}s < 2, defaulting to 2s')
            return '01100001'
        
        best_residual = None
        best_code = None

        for prefix_int, unit_seconds in _PSM_TAU_UNIT_OPTIONS:
            floor_multiplier = periodic_TAU_s // unit_seconds
            ceil_multiplier = floor_multiplier + 1

            for multiplier in (floor_multiplier, ceil_multiplier):
                if 1 <= multiplier <= 31:
                    residual = abs(periodic_TAU_s - multiplier * unit_seconds)

                    if residual == 0:
                        return f'{((prefix_int << 5) | multiplier):07b}'

                    if best_residual is None or residual < best_residual:
                        best_residual = residual
                        best_code = (prefix_int << 5) | multiplier
        
        # Fallback, should there be a logical mistake; catch none found and default
        if best_code is None:
            log('WARNING', f'No valid encoding for TAU={periodic_TAU_s}s found, defaulting to 2s')
            return '01100001'

        return f'{best_code:07b}'
    
    def _active_time_s_to_binary_str(active_time_s: int) -> str:
        """
        Convert Active Time in seconds into the 7-bit T3324 code:
          [3 bits unit prefix][5 bits multiplier],
        where multiplier ∈ [1..31].
        Minimal fallback <2 s is 2 s step.
        """

        if active_time_s < 2:
            log('WARNING', f'Requested Active Time={active_time_s}s < 2, defaulting to 2s')
            return '00000001'
        
        best_residual = None
        best_code = None

        for prefix_int, unit_seconds in _PSM_ACTIVE_UNIT_OPTIONS:
            floor_multiplier = active_time_s // unit_seconds
            ceil_multiplier = floor_multiplier + 1

            for multiplier in (floor_multiplier, ceil_multiplier):
                if 1 <= multiplier <= 31:
                    residual = abs(active_time_s - multiplier * unit_seconds)

                    if residual == 0:
                        return f'{((prefix_int << 5) | multiplier):07b}'
                    
                    if best_residual is None or residual < best_residual:
                        best_residual = residual
                        best_code = (prefix_int << 5) | multiplier
        
        # Fallback, should there be a logical mistake; catch none found and default
        if best_code is None:
            log('WARNING', f'No valid encoding for Active Time={active_time_s}s found, defaulting to 2s')
            return '00000001'
        
        return f'{best_code:07b}'
    
    async def config_PSM(self,
        mode: int,
        periodic_TAU_s: int = None,
        active_time_s: int = None,
        rsp= ModemRsp
    ) -> bool:
        """
        Configure PSM on the modem; enable, disable or reset PSM.

        "DISABLE_AND_DISCARD_ALL_PARAMS", sets manufacturer specific defaults if available.

        :param mode: Enable, Disable or Disable & Reset.
        :type mode: WalterModemPSMMode
        :param periodic_TAU_s: Optional; specify the Periodic TAU in seconds
        :param active_time_s: Optional; specify the Active Time in seconds

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure 
        """
        T3412 = None
        T3324 = None

        cmd = f'AT+CPSMS={mode}'

        if (mode == WalterModemPSMMode.ENABLE_PSM and (
            periodic_TAU_s is not None or active_time_s is not None
        )):
            cmd += ',,,'
            if periodic_TAU_s is not None:
                T3412 = self._periodic_TAU_s_to_binary_str(periodic_TAU_s)
                if self.debug_log: log('DEBUG', f'PSM: T3412 (Periodic TAU), requesting: {T3412}')
                cmd += f'"{T3412}"'
            else:
                cmd += f'","'

            if active_time_s is not None:
                T3324 = self._active_time_s_to_binary_str(active_time_s)
                if self.debug_log: log('DEBUG', f'PSM: T3324 (Active Time), requesting: {T3324}')
                cmd += f'"{T3324}"'

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=cmd,
            at_rsp=b'OK'
        )
