from ..core import ModemCore
from ..enums import (
    WalterModemGNSSSensMode,
    WalterModemGNSSAcqMode,
    WalterModemGNSSLocMode,
    WalterModemGNSSAssistanceType,
    WalterModemGNSSAction
)
from ..structs import (
    ModemRsp,
    ModemGNSSFix,
    ModemGnssFixWaiter
)
from ..utils import (
    modem_string
)

class ModemGNSS(ModemCore):
    async def config_gnss(
        self,
        sens_mode: int = WalterModemGNSSSensMode.HIGH,
        acq_mode: int = WalterModemGNSSAcqMode.COLD_WARM_START,
        loc_mode: int = WalterModemGNSSLocMode.ON_DEVICE_LOCATION,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Configures Walter's GNSS receiver with persistent settings that
        may need to be reset after a modem firmware upgrade.
        Can also adjust sensitivity mode between fixes.
        Recommended to run at least once before using GNSS.

        :param sens_mode: The sensitivity mode.
        :type sens_mode: ModemGNSSSensMode
        :param acq_mode: The acquisition mode.
        :type acq_mode: ModemGNSSAcqMode
        :param loc_mode: The GNSS location mode.
        :type loc_mode: ModemGNSSLocMode
        :type rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+LPGNSSCFG={loc_mode},{sens_mode},2,,1,{acq_mode}',
            at_rsp=b'OK'
        )

    async def get_gnss_assistance_status(self, rsp: ModemRsp = None) -> bool:
        """
        Retrieves the status of the assistance data currently loaded in the GNSS subsystem.

        :param rsp: reference to a modem response instance

        :return bool: true on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+LPGNSSASSISTANCE?',
            at_rsp=b'OK'
        )
    
    async def update_gnss_assistance(self,
        type: int = WalterModemGNSSAssistanceType.REALTIME_EPHEMERIS, 
        rsp: ModemRsp = None
    ) -> bool:
        """
        Connects to the cloud to download and update the GNSS subsystem
        with the requested assistance data.
        Real-time ephemeris being the most efficient type.

        :param type: The type of GNSS assistance data to update.
        :type type: ModemGNSSAssistanceType
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+LPGNSSASSISTANCE={type}',
            at_rsp=b'+LPGNSSASSISTANCE:'
        )
    
    async def perform_gnss_action(self,
        action: int = WalterModemGNSSAction.GET_SINGLE_FIX,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Programs the GNSS subsystem to perform a specified action.

        :param action: The action for the GNSS subsystem to perform.
        :type action: ModemGNSSAction
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        if action == WalterModemGNSSAction.GET_SINGLE_FIX:
            action_str = 'single'
        elif action == WalterModemGNSSAction.CANCEL:
            action_str = 'stop'
        else:
            action_str = ''

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+LPGNSSFIXPROG="{action_str}"',
            at_rsp=b'OK'
        )

    async def wait_for_gnss_fix(self) -> ModemGNSSFix:
        """
        Waits for a gnss fix before then returning it.

        :return ModemGNSSFix:
        """
        gnss_fix_waiter = ModemGnssFixWaiter()

        async with self._gnss_fix_lock:
            self._gnss_fix_waiters.append(gnss_fix_waiter)

        await gnss_fix_waiter.event.wait()

        return gnss_fix_waiter.gnss_fix