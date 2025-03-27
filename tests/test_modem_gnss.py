import asyncio
import minimal_unittest as unittest

from walter_modem import Modem
from walter_modem.enums import (
    WalterModemNetworkRegState,
    WalterModemRspType,
    WalterModemCMEError,
    WalterModemGNSSSensMode,
    WalterModemGNSSAcqMode,
    WalterModemGNSSLocMode
)
from walter_modem.structs import (
    ModemRsp,
    WalterModemOpState,
    ModemGNSSAssistance
)

modem = Modem()
modem_rsp = ModemRsp()

class TestModemGNSS(unittest.AsyncTestCase):
    async def async_setup(self):
        await modem.begin()

    async def async_teardown(self):
        # Restore back to library defaults
        await modem.config_gnss()

    async def test_config_gnss_runs(self):
        self.assert_true(await modem.config_gnss())
    
    async def test_config_gnss_correctly_sets_configuration_in_modem(self):
        if not await modem.config_gnss(
            sens_mode=WalterModemGNSSSensMode.MEDIUM,
            acq_mode=WalterModemGNSSAcqMode.COLD_WARM_START,
            loc_mode=WalterModemGNSSLocMode.ON_DEVICE_LOCATION
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
        await modem.get_gnss_assistance_status(rsp=modem_rsp)
        self.assert_is_instance(modem_rsp.gnss_assistance, ModemGNSSAssistance)
    
    async def test_get_gnss_assistance_status_sets_correct_response_type(self):
        self.assert_equal(WalterModemRspType.GNSS_ASSISTANCE_DATA ,modem_rsp.type)

test_modem_gnss = TestModemGNSS()
test_modem_gnss.run()