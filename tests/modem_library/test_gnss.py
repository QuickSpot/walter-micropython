from minimal_unittest import (
    AsyncTestCase,
    WalterModemAsserts,
)

from walter_modem import Modem
from walter_modem.enums import (
    WalterModemRspType,
    WalterModemGNSSSensMode,
    WalterModemGNSSAcqMode,
    WalterModemGNSSLocMode,
    WalterModemCMEError
)
from walter_modem.structs import (
    ModemRsp,
    ModemGNSSAssistance,
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

class TestGetGNNSAssistanceStatus(
    AsyncTestCase,
    WalterModemAsserts
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent
        self.register_fail_on_cme_error(modem)
    
    async def async_teardown(self):
        self.unregister_fail_on_cme_error(modem)
    
    async def test_returns_true(self):
        self.assert_true(await modem.get_gnss_assistance_status())
    
    async def test_sends_expected_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT+LPGNSSASSISTANCE?',
            lambda: modem.get_gnss_assistance_status()
        )

    async def test_gnss_assistance_set_in_modem_rsp(self):
        modem_rsp = ModemRsp()
        await modem.get_gnss_assistance_status(rsp=modem_rsp)
        
        self.assert_is_instance(modem_rsp.gnss_assistance, ModemGNSSAssistance)
    
    async def test_type_set_to_gnss_assistance_data_in_modem_rsp(self):
        modem_rsp = ModemRsp()
        await modem.get_gnss_assistance_status(rsp=modem_rsp)

        self.assert_equal(WalterModemRspType.GNSS_ASSISTANCE_DATA, modem_rsp.type)

testcases = [testcase() for testcase in (
    TestConfigGNNS,
    TestGetGNNSAssistanceStatus,
)]

for testcase in testcases:
    testcase.run()