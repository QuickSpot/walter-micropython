import minimal_unittest as unittest

from walter_modem import Modem
from walter_modem.enums import (
    WalterModemPSMMode,
    WalterModemEDRXMODE
)
from walter_modem.structs import (
    ModemRsp
)

modem = Modem()

class TestSleepMethods(unittest.AsyncTestCase, unittest.WalterModemAsserts):
    async def async_setup(self):
        await modem.begin()

    async def async_teardown(self):
        await modem.config_PSM(WalterModemPSMMode.DISABLE_AND_DISCARD_ALL_PARAMS)
        await modem.config_EDRX(WalterModemEDRXMODE.DISABLE_AND_DISCARD_ALL_PARAMS)

    async def test_config_PSM_sends_correct_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            f'AT+CPSMS=0',
            lambda: modem.config_PSM(WalterModemPSMMode.DISABLE_PSM)
        )
    
    async def test_config_PSM_sends_correct_at_cmd_with_tau(self):
        await self.assert_sends_at_command(
            modem,
            f'AT+CPSMS=1,,,"10010111"',
            lambda: modem.config_PSM(
                mode=WalterModemPSMMode.ENABLE_PSM,
                periodic_TAU_s=678
            )
        )
    
    async def test_config_PSM_sends_correct_at_cmd_with_active_time(self):
        await self.assert_sends_at_command(
            modem,
            f'AT+CPSMS=1,,,,"00000010"',
            lambda: modem.config_PSM(
                mode=WalterModemPSMMode.ENABLE_PSM,
                active_time_s=5
            )
        )

    async def test_config_PSM_sends_correct_at_cmd_with_tau_and_active_time(self):
        await self.assert_sends_at_command(
            modem,
            f'AT+CPSMS=1,,,"10010111","00000010"',
            lambda: modem.config_PSM(
                mode=WalterModemPSMMode.ENABLE_PSM,
                periodic_TAU_s=678,
                active_time_s=5
            )
        )
    
    async def test_config_EDRX_sends_correct_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            f'AT+SQNEDRX=0',
            lambda: modem.config_EDRX(WalterModemEDRXMODE.DISABLE_EDRX)
        )

    async def test_config_EDRX_sends_correct_at_cmd_with_req_edrx_val_and_req_ptw(self):
        modem_rsp = ModemRsp()
        await modem.get_rat(modem_rsp)
        rat = modem_rsp.rat

        await self.assert_sends_at_command(
            modem,
            f'AT+SQNEDRX=1,{rat + 3},"0101","0001"',
            lambda: modem.config_EDRX(
                mode=WalterModemEDRXMODE.ENABLE_EDRX,
                req_edrx_val='0101',
                req_ptw='0001'
            )
        )

test_sleep_methods = TestSleepMethods()
test_sleep_methods.run()
