import time

from ..core import ModemCore
from ..coreEnums import (
    Enum,
    WalterModemState
)
from ..coreStructs import (
    WalterModemRsp
)
from ..utils import (
    mro_chain_init,
    modem_string,
    log
)

#region Enums

class WalterModemPSMMode(Enum):
    DISABLE_PSM = 0
    ENABLE_PSM = 1
    DISABLE_AND_DISCARD_ALL_PARAMS = 2

class WalterModemEDRXMode(Enum):
    DISABLE_EDRX = 0
    ENABLE_EDRX = 1
    ENABLE_EDRX_AND_UNSOLICITED_RESULT_CODE = 2
    DISABLE_AND_DISCARD_ALL_PARAMS = 3

#endregion
#region Constants

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

#endregion
#region MixinClass

class PowerSavingMixin(ModemCore):
    def __init__(self, *args, **kwargs):
        mro_chain_init(self, super(), lambda: None, PowerSavingMixin, *args, **kwargs)

    #region PublicMethods

    # Deprecated aliases, to be removed in a later release

    async def config_PSM(self, *args, **kwargs):
        return await self.config_psm(*args, **kwargs)
    
    async def config_EDRX(self, *args, **kwargs):
        return await self.config_edrx(*args, **kwargs)

    # ---  
    
    async def config_psm(self,
        mode: int,
        periodic_TAU_s: int = None,
        active_time_s: int = None,
        rsp: WalterModemRsp = None
    ) -> bool:
        T3412 = None
        T3324 = None

        cmd = f'AT+CPSMS={mode}'

        if (mode == WalterModemPSMMode.ENABLE_PSM and (
            periodic_TAU_s is not None or active_time_s is not None
        )):
            cmd += ',,,'
            if periodic_TAU_s is not None:
                if (T3412 := self._periodic_tau_s_to_binary_str(periodic_TAU_s)) is not None:
                    if __debug__:
                        log('DEBUG', f'PSM: T3412 (Periodic TAU), requesting: {T3412}')
                    cmd += f'"{T3412}"'

            if active_time_s is not None:
                if (T3324 := self._active_time_s_to_binary_str(active_time_s)) is not None:
                    if __debug__:
                        log('DEBUG', f'PSM: T3324 (Active Time), requesting: {T3324}')
                    cmd += f',"{T3324}"'

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=cmd,
            at_rsp=b'OK'
        )

    async def config_edrx(self,
        mode: int,
        req_edrx_val: str = None,
        req_ptw: str = None,
        rsp: WalterModemRsp = None
    ) -> bool:
        cmd = f'AT+SQNEDRX={mode}'

        if (mode == WalterModemEDRXMode.ENABLE_EDRX or
        mode == WalterModemEDRXMode.ENABLE_EDRX_AND_UNSOLICITED_RESULT_CODE):
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

    #endregion
    #region PrivateMethods

    def _convert_psm_duration(self, value_s: int, unit_options: tuple) -> int | None:
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
    
    def _periodic_tau_s_to_binary_str(self, periodic_TAU_s: int) -> str:
        if periodic_TAU_s < 2:
            log('WARNING', f'Requested TAU={periodic_TAU_s}s < 2, falling back to 2s')
            return '01100001'
        
        if periodic_TAU_s > 35712000:
            log('WARNING',
                f'Requested TAU={periodic_TAU_s}s > 35712000, falling back to 35 712 000s')
            return '11011111'
        
        if (code := self._convert_psm_duration(periodic_TAU_s, _PSM_TAU_UNIT_OPTIONS)) is None:
            log('WARNING',
                f'No valid encoding for TAU={periodic_TAU_s}s found, skipping property.')
            return None

        return f'{code:08b}'
    
    def _active_time_s_to_binary_str(self, active_time_s: int) -> str | None:
        if active_time_s < 0:
            log('WARNING', f'Requested Active Time={active_time_s}s < 0, falling back to 0s')
            return '00000000'
        
        if active_time_s > 11160:
            log('WARNING'
                f'Requested Active Time={active_time_s}s > 11160, falling back to 11 160s')
            return '01011111'

        if (code := self._convert_psm_duration(active_time_s, _PSM_ACTIVE_UNIT_OPTIONS)) is None:
            log('WARNING',
                f'No valid encoding for Active Time={active_time_s}s found, skipping property')
            return None
        
        return f'{code:08b}'  

    #endregion
#endregion
