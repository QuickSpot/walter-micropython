import asyncio

from minimal_unittest import (
    AsyncTestCase,
    WalterModemAsserts,
    NetworkConnectivity
)

from walter_modem import Modem
from walter_modem.enums import (
    WalterModemRspType,
    WalterModemGNSSSensMode,
    WalterModemGNSSAcqMode,
    WalterModemGNSSLocMode,
    WalterModemGNSSAssistanceType,
    WalterModemGNSSAction,
    WalterModemCMEError
)
from walter_modem.structs import (
    ModemRsp,
    ModemGNSSAssistance,
    ModemGNSSFix
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

class TestUpdateGNNSAssistance(
    AsyncTestCase,
    WalterModemAsserts,
    NetworkConnectivity
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent
        await self.ensure_network_connection(modem)
    
    # Test fail on invalid param

    async def test_fails_on_invalid_type(self):
        self.assert_false(await modem.update_gnss_assistance(type=-3))

    async def test_cme_50_set_in_modem_rsp_on_invalid_param(self):
        modem_rsp = ModemRsp()
        await modem.update_gnss_assistance(type=-3, rsp=modem_rsp)

        self.assert_equal(WalterModemCMEError.INCORRECT_PARAMETERS, modem_rsp.cme_error)

    # Test normal run

    async def test_returns_true_on_no_param(self):
        self.assert_true(await modem.update_gnss_assistance())

    async def test_returns_true_on_valid_param(self):
        self.assert_true(await modem.update_gnss_assistance(
            type=WalterModemGNSSAssistanceType.REALTIME_EPHEMERIS
        ))

    async def test_sends_correct_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT+LPGNSSASSISTANCE=1',
            lambda: modem.update_gnss_assistance(
                type=WalterModemGNSSAssistanceType.REALTIME_EPHEMERIS
            )
        )

class TestPerformGNSSAction(
    AsyncTestCase,
    WalterModemAsserts,
    NetworkConnectivity
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent

        print('NOTE: This TestCase uses get_clock() and might fail if get_clock() is broken.')

        modem_rsp = ModemRsp()
        await modem.get_clock(rsp=modem_rsp)

        if not modem_rsp.clock:
            print('No RTC (clock time), briefly connecting to LTE to retrieve time')
            await self.ensure_network_connection(modem)
            await asyncio.sleep(3)
        # Time synced, LTE connection & GNSS cannot work simultaniously
        await modem._run_cmd('AT+CFUN=0', b'OK')

    async def async_teardown(self):
        # Ensure no gnns action is still running
        await modem._run_cmd(
            at_cmd='AT+LPGNSSFIXPROG="stop"',
            at_rsp=b'OK'
        )

    # Test fail on invalid param

    async def test_fails_on_invalid_param(self):
        self.assert_false(await modem.perform_gnss_action(action=-10))
    
    async def test_cme_4_set_in_modem_rsp_on_invalid_param(self):
        modem_rsp = ModemRsp()
        await modem.perform_gnss_action(action=-10, rsp=modem_rsp)

        self.assert_equal(WalterModemCMEError.OPERATION_NOT_SUPPORTED, modem_rsp.cme_error)
    
    # Test normal run

    async def test_returns_true_on_no_param(self):
        self.assert_true(await modem.perform_gnss_action())
        await asyncio.sleep(1)
        await modem._run_cmd('AT+LPGNSSFIXPROG="stop"', b'OK')

    async def test_perform_gnss_action_single_fix_runs(self):
        self.assert_true(await modem.perform_gnss_action(action=WalterModemGNSSAction.GET_SINGLE_FIX))
        await asyncio.sleep(1)
        await modem._run_cmd('AT+LPGNSSFIXPROG="stop"', b'OK')
    
    async def test_perform_gnss_action_cancel_runs(self):
        await modem._run_cmd('AT+LPGNSSFIXPROG="single"', b'OK')
        await asyncio.sleep(1)
        self.assert_true(await modem.perform_gnss_action(action=WalterModemGNSSAction.CANCEL))

class TestWaitForGNSSFix(
    AsyncTestCase,
    WalterModemAsserts
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent

    async def test_wait_for_gnss_fix_returns_gnss_fix(self):
        await modem._run_cmd('AT+LPGNSSFIXPROG="single"', b'OK')
        try:
            result = await asyncio.wait_for(modem.wait_for_gnss_fix(), timeout=180)
            self.assert_is_instance(result, ModemGNSSFix)
        except asyncio.TimeoutError:
            raise OSError('Runtime Error, timeout whilst waiting for "wait_for_gnss_fix"')

testcases = [testcase() for testcase in (
    TestConfigGNNS,
    TestGetGNNSAssistanceStatus,
    TestUpdateGNNSAssistance,
    TestPerformGNSSAction,
    TestWaitForGNSSFix,
)]

for testcase in testcases:
    testcase.run()