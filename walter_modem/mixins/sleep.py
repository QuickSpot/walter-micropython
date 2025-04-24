import time

from machine import Pin, lightsleep, deepsleep # type: ignore

from ..core import ModemCore
from ..enums import (
    WalterModemPSMMode,
    WalterModemEDRXMODE,
    WalterModemState
)
from ..structs import (
    ModemRsp
)
from ..utils import (
    log,
    modem_string
)

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

    def _convert_PSM_duration(self, value_s: int, unit_options: tuple) -> int | None:
        best_residual = None
        best_code = None

        for prefix_int, unit_seconds in unit_options:
            step_floor = value_s // unit_seconds
            step_ceil = step_floor + 1

            for step in (step_floor, step_ceil):
                if 1 <= step <= 31:
                    residual = abs(value_s - step * unit_seconds)

                    if residual == 0:
                        return (prefix_int << 5) | step
                    
                    if best_residual is None or residual < best_residual:
                        best_residual = residual
                        best_code = (prefix_int << 5) | step
            
        return best_code
    
    def _periodic_TAU_s_to_binary_str(self, periodic_TAU_s: int) -> str:
        """
        Convert periodic TAU in seconds into the 8-bit T3412 code:
          [3 bits unit prefix][5 bits value]
        where value ∈ [1..31].  
        Minimal fallback for <2 s is 2 s step.
        """
    
        if periodic_TAU_s < 2:
            log('WARNING', f'Requested TAU={periodic_TAU_s}s < 2, falling back to 2s')
            return '01100001'
        
        if periodic_TAU_s > 35712000:
            log('WARNING',
                f'Requested TAU={periodic_TAU_s}s > 35712000, falling back to 35 712 000s')
            return '11011111'
        
        if (code := self._convert_PSM_duration(periodic_TAU_s, _PSM_TAU_UNIT_OPTIONS)) is None:
            log('WARNING',
                f'No valid encoding for TAU={periodic_TAU_s}s found, skipping property.')
            return None

        return f'{code:08b}'
    
    def _active_time_s_to_binary_str(self, active_time_s: int) -> str | None:
        """
        Convert Active Time in seconds into the 8-bit T3324 code:
          [3 bits unit prefix][5 bits multiplier],
        where multiplier ∈ [1..31].
        Minimal fallback <2 s is 2 s step.
        """

        if active_time_s < 0:
            log('WARNING', f'Requested Active Time={active_time_s}s < 0, falling back to 0s')
            return '00000000'
        
        if active_time_s > 11160:
            log('WARNING'
                f'Requested Active Time={active_time_s}s > 11160, falling back to 11 160s')
            return '01011111'

        if (code := self._convert_PSM_duration(active_time_s, _PSM_ACTIVE_UNIT_OPTIONS)) is None:
            log('WARNING',
                f'No valid encoding for Active Time={active_time_s}s found, skipping property')
            return None
        
        return f'{code:08b}'
    
    async def config_PSM(self,
        mode: int,
        periodic_TAU_s: int = None,
        active_time_s: int = None,
        rsp: ModemRsp = None
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
                if (T3412 := self._periodic_TAU_s_to_binary_str(periodic_TAU_s)) is not None:
                    if self.debug_log: log('DEBUG', 
                                           f'PSM: T3412 (Periodic TAU), requesting: {T3412}')
                    cmd += f'"{T3412}"'

            if active_time_s is not None:
                if (T3324 := self._active_time_s_to_binary_str(active_time_s)) is not None:
                    if self.debug_log: log('DEBUG',
                                           f'PSM: T3324 (Active Time), requesting: {T3324}')
                    cmd += f',"{T3324}"'

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=cmd,
            at_rsp=b'OK'
        )

    async def config_EDRX(self,
        mode: int,
        req_edrx_val: str = None,
        req_ptw: str = None,
        rsp: ModemRsp = None
    ) -> bool:
        cmd = f'AT+SQNEDRX={mode}'

        if (mode == WalterModemEDRXMODE.ENABLE_EDRX or
        mode == WalterModemEDRXMODE.ENABLE_EDRX_AND_UNSOLICITED_RESULT_CODE):
            supported_act_type = None

            def cmd_handler(cmd, at_rsp):
                nonlocal supported_act_type
                supported_act_type = chr(at_rsp.split(b',')[1][1])

            self.register_application_queue_rsp_handler(
                b'+SQNEDRX:',
                cmd_handler
            )

            await self._run_cmd(at_cmd='AT+SQNEDRX=?', at_rsp=b'OK')

            for _ in range(5):
                if supported_act_type is not None: break
                time.sleep(1)
            self.unregister_application_queue_rsp_handler(cmd_handler)
            
            if supported_act_type is None:
                if rsp: rsp.result = WalterModemState.ERROR
                log('WARNING', 'Failed to set EDRX, could not verify current accept AcT-type.')
                return False

            cmd += f',{supported_act_type},{modem_string(req_edrx_val)},{modem_string(req_ptw)}'

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=cmd,
            at_rsp=b'OK'
        )