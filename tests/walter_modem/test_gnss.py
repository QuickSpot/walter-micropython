import asyncio
import micropython # type: ignore
micropython.opt_level(1)

from minimal_unittest import (
    AsyncTestCase,
    WalterModemAsserts,
    NetworkConnectivity
)

from walter_modem import Modem
from walter_modem.mixins.gnss import (
    GNSSMixin,
    WalterModemGNSSSensMode,
    WalterModemGNSSAcqMode,
    WalterModemGNSSLocMode,
    WalterModemGNSSAssistanceType,
    WalterModemGNSSAction,
    ModemGNSSAssistance,
    ModemGNSSFix
)
from walter_modem.coreEnums import (
    WalterModemRspType,
    WalterModemCMEError
)
from walter_modem.coreStructs import (
    ModemRsp,
)

modem = Modem(GNSSMixin)

class TestGNSSConfig(
    AsyncTestCase,
    WalterModemAsserts
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent
    
    async def async_teardown(self):
        await modem.gnss_config() # Restore back to library defaults
    
    # Test fail on invalid param

    async def test_fails_on_invalid_sens_mode(self):
        self.assert_false(await modem.gnss_config(sens_mode=-70))

    async def test_fails_on_invalid_acq_mode(self):
        self.assert_false(await modem.gnss_config(acq_mode=-70))

    async def test_fails_on_invalid_loc_mode(self):
        self.assert_false(await modem.gnss_config(acq_mode=-70))
    
    async def test_cme_50_set_in_modem_rsp_on_invalid_param(self):
        modem_rsp = ModemRsp()
        await modem.gnss_config(-70, -60, -50, modem_rsp)

        self.assert_equal(WalterModemCMEError.INCORRECT_PARAMETERS, modem_rsp.cme_error)

    # Test normal run

    async def test_returns_true_on_no_params(self):
        self.assert_true(await modem.gnss_config())

    async def test_returns_true_on_valid_params(self):
        self.assert_true(await modem.gnss_config(
            sens_mode=WalterModemGNSSSensMode.LOW,
            acq_mode=WalterModemGNSSAcqMode.HOT_START,
            loc_mode=WalterModemGNSSLocMode.ON_DEVICE_LOCATION
        ))
    
    async def test_sends_correct_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT+LPGNSSCFG=0,2,2,,1,0',
            lambda: modem.gnss_config(
                sens_mode=WalterModemGNSSSensMode.MEDIUM,
                acq_mode=WalterModemGNSSAcqMode.COLD_WARM_START,
                loc_mode=WalterModemGNSSLocMode.ON_DEVICE_LOCATION
            )
        )

class TestGNSSAssistanceGetStatus(
    AsyncTestCase,
    WalterModemAsserts
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent
        self.register_fail_on_cme_error(modem)
    
    async def async_teardown(self):
        self.unregister_fail_on_cme_error(modem)
    
    async def test_returns_true(self):
        self.assert_true(await modem.gnss_assistance_get_status())
    
    async def test_sends_expected_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT+LPGNSSASSISTANCE?',
            lambda: modem.gnss_assistance_get_status()
        )

    async def test_gnss_assistance_set_in_modem_rsp(self):
        modem_rsp = ModemRsp()
        await modem.gnss_assistance_get_status(rsp=modem_rsp)
        
        self.assert_is_instance(modem_rsp.gnss_assistance, ModemGNSSAssistance)
    
    async def test_type_set_to_gnss_assistance_data_in_modem_rsp(self):
        modem_rsp = ModemRsp()
        await modem.gnss_assistance_get_status(rsp=modem_rsp)

        self.assert_equal(WalterModemRspType.GNSS_ASSISTANCE_DATA, modem_rsp.type)

class TestGNSSAssistanceUpdate(
    AsyncTestCase,
    WalterModemAsserts,
    NetworkConnectivity
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent
        await self.ensure_network_connection(modem)
    
    # Test fail on invalid param

    async def test_fails_on_invalid_type(self):
        self.assert_false(await modem.gnss_assistance_update(type=-3))

    async def test_cme_50_set_in_modem_rsp_on_invalid_param(self):
        modem_rsp = ModemRsp()
        await modem.gnss_assistance_update(type=-3, rsp=modem_rsp)

        self.assert_equal(WalterModemCMEError.INCORRECT_PARAMETERS, modem_rsp.cme_error)

    # Test normal run

    async def test_returns_true_on_no_param(self):
        self.assert_true(await modem.gnss_assistance_update())

    async def test_returns_true_on_valid_param(self):
        self.assert_true(await modem.gnss_assistance_update(
            type=WalterModemGNSSAssistanceType.REALTIME_EPHEMERIS
        ))

    async def test_sends_correct_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT+LPGNSSASSISTANCE=1',
            lambda: modem.gnss_assistance_update(
                type=WalterModemGNSSAssistanceType.REALTIME_EPHEMERIS
            )
        )

class TestGNSSPerformAction(
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
        # Ensure no gnss action is still running
        await modem._run_cmd(
            at_cmd='AT+LPGNSSFIXPROG="stop"',
            at_rsp=b'OK'
        )

    # Test fail on invalid param

    async def test_fails_on_invalid_param(self):
        self.assert_false(await modem.gnss_perform_action(action=-10))
    
    async def test_cme_4_set_in_modem_rsp_on_invalid_param(self):
        modem_rsp = ModemRsp()
        await modem.gnss_perform_action(action=-10, rsp=modem_rsp)

        self.assert_equal(WalterModemCMEError.OPERATION_NOT_SUPPORTED, modem_rsp.cme_error)
    
    # Test normal run

    async def test_returns_true_on_no_param(self):
        self.assert_true(await modem.gnss_perform_action())
        await asyncio.sleep(1)
        await modem._run_cmd('AT+LPGNSSFIXPROG="stop"', b'OK')

    async def test_gnss_perform_action_single_fix_runs(self):
        self.assert_true(await modem.gnss_perform_action(action=WalterModemGNSSAction.GET_SINGLE_FIX))
        await asyncio.sleep(1)
        await modem._run_cmd('AT+LPGNSSFIXPROG="stop"', b'OK')
    
    async def test_gnss_perform_action_cancel_runs(self):
        await modem._run_cmd('AT+LPGNSSFIXPROG="single"', b'OK')
        await asyncio.sleep(1)
        self.assert_true(await modem.gnss_perform_action(action=WalterModemGNSSAction.CANCEL))

class TestGNSSWaitForFix(
    AsyncTestCase,
    WalterModemAsserts
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent

    async def test_returns_gnss_fix(self):
        await modem._run_cmd('AT+LPGNSSFIXPROG="single"', b'OK')
        try:
            result = await asyncio.wait_for(modem.gnss_wait_for_fix(), timeout=180)
            self.assert_is_instance(result, ModemGNSSFix)
        except asyncio.TimeoutError:
            raise OSError('Runtime Error, timeout whilst waiting for "gnss_wait_for_fix"')

testcases = [testcase() for testcase in (
    TestGNSSConfig,
    TestGNSSAssistanceGetStatus,
    TestGNSSAssistanceUpdate,
    TestGNSSPerformAction,
    TestGNSSWaitForFix,
)]

for testcase in testcases:
    testcase.run()