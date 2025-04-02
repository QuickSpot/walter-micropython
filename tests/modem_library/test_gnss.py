import asyncio
import minimal_unittest as unittest

from walter_modem import Modem
from walter_modem.enums import (
    WalterModemNetworkRegState,
    WalterModemRspType,
    WalterModemCMEError,
    WalterModemGNSSSensMode,
    WalterModemGNSSAcqMode,
    WalterModemGNSSLocMode,
    WalterModemGNSSAction
)
from walter_modem.structs import (
    ModemRsp,
    WalterModemOpState,
    ModemGNSSAssistance,
    ModemGNSSFix
)

modem = Modem()

async def await_connection():
        print('\nShowing modem debug logs:')
        modem.debug_log = True

        for _ in range(600):
            if modem.get_network_reg_state() in (
                WalterModemNetworkRegState.REGISTERED_HOME,
                WalterModemNetworkRegState.REGISTERED_ROAMING
            ):
                modem.debug_log = False
                return
            await asyncio.sleep(1)
        modem.debug_log = False
        raise OSError('Connection Timed-out')

class TestGNSSPreConnection(unittest.AsyncTestCase):
    async def async_setup(self):
        modem_rsp = ModemRsp()
        await modem.begin()

        # GNSS action requires available RTC (clock)
        await modem.get_clock(rsp=modem_rsp)

        if not modem_rsp.clock:
            print('No RTC (clock time), briefly connecting to LTE to retrieve time')
            await modem.get_op_state(rsp=modem_rsp)
            if modem_rsp.op_state is not WalterModemOpState.FULL:
                await modem.create_PDP_context()
                await modem.set_op_state(WalterModemOpState.FULL)

            await await_connection()

            for _ in range(5):
                await modem.get_clock(rsp=modem_rsp)
                if modem_rsp.clock:
                    break
                await asyncio.sleep(0.5)
        
        # Time synced with network, LTE connection not needed for these tests
        # These tests should work without LTE
        await modem.set_op_state(WalterModemOpState.MINIMUM)

    async def async_teardown(self):
        # Restore back to library defaults
        await modem.config_gnss()

        # Ensure no gnns action is still running
        await modem._run_cmd(
            at_cmd='AT+LPGNSSFIXPROG="stop"',
            at_rsp=b'OK'
        )

    async def test_config_gnss_runs(self):
        self.assert_true(await modem.config_gnss())
    
    async def test_config_gnss_correctly_sets_configuration_in_modem(self):
        modem_rsp = ModemRsp()

        if not await modem.config_gnss(
            sens_mode=WalterModemGNSSSensMode.MEDIUM,
            acq_mode=WalterModemGNSSAcqMode.COLD_WARM_START,
            loc_mode=WalterModemGNSSLocMode.ON_DEVICE_LOCATION,
            rsp=modem_rsp
        ):
            raise RuntimeError(
                'Failed to config GNSS',
                WalterModemCMEError.get_value_name(modem_rsp.cme_error)
            )
    
        gnss_config_str_from_modem = None

        def lpgnsscfg_handler(cmd, at_rsp):
            nonlocal gnss_config_str_from_modem
            gnss_config_str_from_modem = at_rsp
        
        modem._register_application_queue_rsp_handler(b'+LPGNSSCFG: ', lpgnsscfg_handler)
        await modem._run_cmd(at_cmd='AT+LPGNSSCFG?', at_rsp=b'OK')

        for _ in range(100):
            if gnss_config_str_from_modem is not None: break
            await asyncio.sleep(0.1)
        
        self.assert_equal(b'+LPGNSSCFG: 0,2,2,,1,0,0', gnss_config_str_from_modem)
    
    async def test_get_gnss_assistance_status_runs(self):
        self.assert_true(await modem.get_gnss_assistance_status())
    
    async def test_get_gnss_assistance_status_sets_gnss_assistance_in_response(self):
        modem_rsp = ModemRsp()
        await modem.get_gnss_assistance_status(rsp=modem_rsp)
        
        self.assert_is_instance(modem_rsp.gnss_assistance, ModemGNSSAssistance)
    
    async def test_get_gnss_assistance_status_sets_correct_response_type(self):
        modem_rsp = ModemRsp()
        await modem.get_gnss_assistance_status(rsp=modem_rsp)

        self.assert_equal(WalterModemRspType.GNSS_ASSISTANCE_DATA, modem_rsp.type)

    async def test_perform_gnss_action_single_fix_runs(self):
        self.assert_true(await modem.perform_gnss_action(action=WalterModemGNSSAction.GET_SINGLE_FIX))
    
    async def test_perform_gnss_action_cancel_runs(self):
        self.assert_true(await modem.perform_gnss_action(action=WalterModemGNSSAction.CANCEL))

    async def test_wait_for_gnss_fix_returns(self):
        await modem.perform_gnss_action(WalterModemGNSSAction.GET_SINGLE_FIX)
        try:
            result = await asyncio.wait_for(modem.wait_for_gnss_fix(), timeout=180)
            self.assert_is_instance(result, ModemGNSSFix)
        except asyncio.TimeoutError:
            raise OSError('Runtime Error, timeout whilst waiting for "wait_for_gnss_fix"')

class TestGNSSPostConnection(unittest.AsyncTestCase):
    async def async_setup(self):
        modem_rsp = ModemRsp()

        await modem.begin()

        await modem.get_op_state(rsp=modem_rsp)
        if modem_rsp.op_state is not WalterModemOpState.FULL:
            await modem.create_PDP_context()
            await modem.set_op_state(WalterModemOpState.FULL)

        await await_connection()
    
    async def test_update_gnss_assistance_runs(self):
        self.assert_true(await modem.update_gnss_assistance())
    
    async def test_update_gnss_assistance_sets_gnss_assistance_in_response(self):
        modem_rsp = ModemRsp()
        await modem.update_gnss_assistance(rsp=modem_rsp)

        self.assert_is_instance(modem_rsp.gnss_assistance, ModemGNSSAssistance)
    
    async def test_update_gnss_assistance_sets_correct_response_type(self):
        modem_rsp = ModemRsp()
        await modem.update_gnss_assistance(rsp=modem_rsp)

        self.assert_equal(WalterModemRspType.GNSS_ASSISTANCE_DATA, modem_rsp.type)


test_gnss_pre_connection = TestGNSSPreConnection()
test_gnss_post_connection = TestGNSSPostConnection()

test_gnss_pre_connection.run()
test_gnss_post_connection.run()