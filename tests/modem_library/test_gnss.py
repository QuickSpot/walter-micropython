from minimal_unittest import (
    AsyncTestCase,
    WalterModemAsserts
)

from walter_modem import Modem
from walter_modem.enums import (
    WalterModemGNSSSensMode,
    WalterModemGNSSAcqMode,
    WalterModemGNSSLocMode,
    WalterModemCMEError
)
from walter_modem.structs import (
    ModemRsp
)

modem = Modem()

class TestConfigGNNS(
    AsyncTestCase,
    WalterModemAsserts
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent
    
    async def async_teardown(self):
        await modem.config_gnss() # Restore back to library defaults
    
    # Test fail on invalid param

    async def test_fails_on_invalid_sens_mode(self):
        self.assert_false(await modem.config_gnss(sens_mode=-70))

    async def test_fails_on_invalid_acq_mode(self):
        self.assert_false(await modem.config_gnss(acq_mode=-70))

    async def test_fails_on_invalid_loc_mode(self):
        self.assert_false(await modem.config_gnss(acq_mode=-70))
    
    async def test_cme_50_set_in_modem_rsp_on_invalid_param(self):
        modem_rsp = ModemRsp()
        await modem.config_gnss(-70, -60, -50, modem_rsp)

        self.assert_equal(WalterModemCMEError.INCORRECT_PARAMETERS, modem_rsp.cme_error)

    # Test normal run

    async def test_returns_true_on_no_params(self):
        self.assert_true(await modem.config_gnss())

    async def test_returns_true_on_valid_params(self):
        self.assert_true(await modem.config_gnss(
            sens_mode=WalterModemGNSSSensMode.LOW,
            acq_mode=WalterModemGNSSAcqMode.HOT_START,
            loc_mode=WalterModemGNSSLocMode.ON_DEVICE_LOCATION
        ))
    
    async def test_sends_correct_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT+LPGNSSCFG=0,2,2,,1,0',
            lambda: modem.config_gnss(
                sens_mode=WalterModemGNSSSensMode.MEDIUM,
                acq_mode=WalterModemGNSSAcqMode.COLD_WARM_START,
                loc_mode=WalterModemGNSSLocMode.ON_DEVICE_LOCATION
            )
        )

testcases = [testcase() for testcase in (
    TestConfigGNNS,
)]

for testcase in testcases:
    testcase.run()