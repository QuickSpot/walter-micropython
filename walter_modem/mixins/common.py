import time
from machine import Pin # type: ignore

from ..core import ModemCore
from ..enums import (
    WalterModemCmdType,
    WalterModemCMEErrorReportsType,
    WalterModemCEREGReportsType
)
from ..structs import (
    ModemRsp
)

class ModemCommon(ModemCore):
    async def reset(self, rsp: ModemRsp = None) -> bool:
        """
        Physically reset the modem and wait for it to start.
        All connections will be lost when this function is called.
        The function will fail when the modem doesn't start after the reset.

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
        """
        self._reset_pin.init(hold=False)
        self._reset_pin.off()
        time.sleep(0.3)
        self._reset_pin.on()
        self._reset_pin.init(hold=True)

        super().__init__() # Reset internal mirror state
        self._begun = True # Keep begin idempotent

        return await self._run_cmd(
            rsp=rsp,
            at_cmd='',
            at_rsp=b'+SYSSTART',
            cmd_type=WalterModemCmdType.WAIT
        )
    
    async def soft_reset(self) -> bool:
        """
        Perform a soft reset on the modem, wait for it to complete.
        The method will fail when the modem doesn't reset.
        """
        cmd_result = await self._run_cmd(
            at_cmd='AT^RESET',
            at_rsp=b'+SYSSTART'
        )

        if cmd_result:
            super().__init__() # Reset internal mirror state
            self._begun = True # Keep begin idempotent
        
        return cmd_result
    
    async def check_comm(self, rsp: ModemRsp = None) -> bool:
        """
        Sends the 'AT' command to check if the modem responds with 'OK',
        verifying communication between the ESP32 and the modem.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT',
            at_rsp=b'OK'
        )
    
    async def get_clock(self, rsp: ModemRsp = None
    ) -> bool:
        """
        Retrieves the current time and date from the modem.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CCLK?',
            at_rsp=b'OK'
        )

    async def config_cme_error_reports(self,
        reports_type: int = WalterModemCMEErrorReportsType.NUMERIC,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Configures the CME error report type.
        By default, errors are enabled and numeric.
        Changing this may affect error reporting.

        :param reports_type: The CME error report type.
        :type reports_type: WalterModemCMEErrorReportsType
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CMEE={reports_type}',
            at_rsp=b'OK'
        )
    
    async def config_cereg_reports(self,
        reports_type: int = WalterModemCEREGReportsType.ENABLED,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Configures the CEREG status report type.
        By default, reports are enabled with minimal operational info.
        Changing this may affect library functionality.

        :param reports_type: The CEREG status reports type.
        :type reports_type: WalterModemCEREGReportsType
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CEREG={reports_type}',
            at_rsp=b'OK'
        )