import asyncio
import micropython # type: ignore
micropython.opt_level(0)

import minimal_unittest as unittest
from walter_modem import Modem
from walter_modem.mixins.default_sim_network import (
    WalterModemRat,
    WalterModemNetworkSelMode,
    ModemSignalQuality,
    ModemCellInformation,
    ModemBandSelection
)
from walter_modem.coreEnums import (
    WalterModemOpState,
    WalterModemNetworkRegState,
    WalterModemRspType
)
from walter_modem.coreStructs import (
    WalterModemRsp
)

modem = Modem()

async def await_connection():
        print('\nShowing uart debug logs:')
        modem.uart_debug = True

        for _ in range(600):
            if modem.get_network_reg_state() in (
                WalterModemNetworkRegState.REGISTERED_HOME,
                WalterModemNetworkRegState.REGISTERED_ROAMING
            ):
                modem.uart_debug = False
                return
            await asyncio.sleep(1)
        modem.uart_debug = False
        raise OSError('Connection Timed-out')

class TestSIMAndNetworkPreConnection(unittest.AsyncTestCase, unittest.WalterModemAsserts):
    """SIM & Network method tests for commands that require CFUN=0"""
    async def async_setup(self):
        await modem.begin()

    async def test_set_rat_runs(self):
        self.assert_true(await modem.set_rat(WalterModemRat.LTEM))
    
    async def test_set_rat_sends_correct_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT+SQNMODEACTIVE=1',
            lambda: modem.set_rat(WalterModemRat.LTEM)
        )

class EstablishLTEConnection(unittest.AsyncTestCase, unittest.WalterModemAsserts):
    async def async_setup(self):
        await modem.begin()
        await modem.set_op_state(WalterModemOpState.FULL)
    
    async def test_get_network_reg_state_returns(self):
        reg_state = modem.get_network_reg_state()
        self.assert_is_not_none(reg_state)
    
    async def test_set_network_selection_mode_runs(self):
        self.assert_true(await modem.set_network_selection_mode(WalterModemNetworkSelMode.AUTOMATIC))
    
    async def test_set_network_selection_mode_sends_correct_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT+COPS=0',
            lambda: modem.set_network_selection_mode(WalterModemNetworkSelMode.AUTOMATIC)
        )

    async def test_connection_is_made(self):
        await self.assert_does_not_throw(await_connection, OSError)

class TestSIMAndNetworkPostConnection(unittest.AsyncTestCase):
    async def async_setup(self):
        modem_rsp = WalterModemRsp()
        await modem.begin()

        await modem.get_op_state(rsp=modem_rsp)
        if modem_rsp.op_state is not WalterModemOpState.FULL:
            await modem.set_op_state(WalterModemOpState.FULL)

        await await_connection()

    # ---
    # get_rssi()

    async def test_get_rssi_runs(self):
        self.assert_true(await modem.get_rssi())
    
    async def test_get_rssi_sets_rssi_in_modem_rsp(self):
        modem_rsp = WalterModemRsp()
        await modem.get_rssi(rsp=modem_rsp)
        self.assert_is_not_none(modem_rsp.rssi)

    async def test_get_rssi_sets_correct_response_type(self):
        modem_rsp = WalterModemRsp()
        await modem.get_rssi(rsp=modem_rsp)
        self.assert_equal(WalterModemRspType.RSSI, modem_rsp.type)

    # ---
    # get_signal_quality()
    
    async def test_get_signal_quality_runs(self):
        self.assert_true(await modem.get_signal_quality())

    async def test_get_signal_quality_sets_signal_quality_in_modem_rsp(self):
        modem_rsp = WalterModemRsp()
        await modem.get_signal_quality(rsp=modem_rsp)
        self.assert_is_instance(modem_rsp.signal_quality, ModemSignalQuality)

    async def test_get_signal_quality_sets_correct_response_type(self):
        modem_rsp = WalterModemRsp()
        await modem.get_signal_quality(rsp=modem_rsp)
        self.assert_equal(WalterModemRspType.SIGNAL_QUALITY, modem_rsp.type)

    async def test_signal_quality_response_includes_rsrq(self):
        modem_rsp = WalterModemRsp()
        await modem.get_signal_quality(rsp=modem_rsp)
        self.assert_is_not_none(modem_rsp.signal_quality.rsrq)

    async def test_signal_quality_response_includes_rsrp(self):
        modem_rsp = WalterModemRsp()
        await modem.get_signal_quality(rsp=modem_rsp)
        self.assert_is_not_none(modem_rsp.signal_quality.rsrp)
    
    # ---
    # get_cell_information()
    
    async def test_get_cell_information_runs(self):
        self.assert_true(await modem.get_cell_information())

    async def test_get_cell_info_sets_correct_response_type(self):
        modem_rsp = WalterModemRsp()
        await modem.get_cell_information(rsp=modem_rsp)
        self.assert_equal(WalterModemRspType.CELL_INFO, modem_rsp.type)

    async def test_get_cell_info_sets_cell_information_in_response(self):
        modem_rsp = WalterModemRsp()
        await modem.get_cell_information(rsp=modem_rsp)
        self.assert_is_instance(modem_rsp.cell_information, ModemCellInformation)
    
    # ---
    # get_rat()
    
    async def test_get_rat_runs(self):
        self.assert_true(await modem.get_rat())

    async def test_get_rat_sets_correct_response_type(self):
        modem_rsp = WalterModemRsp()
        await modem.get_rat(rsp=modem_rsp)
        self.assert_equal(WalterModemRspType.RAT, modem_rsp.type)
    
    async def test_get_rat_sets_rat_in_response(self):
        modem_rsp = WalterModemRsp()
        await modem.get_rat(rsp=modem_rsp)
        self.assert_is_not_none(modem_rsp.rat)
    
    # ---
    # get_radio_bands()
    
    async def test_get_radio_bands_runs(self):
        self.assert_true(await modem.get_radio_bands())

    async def test_get_radio_bands_sets_band_sel_cfg_list_in_response(self):
        modem_rsp = WalterModemRsp()
        await modem.get_radio_bands(rsp=modem_rsp)
        self.assert_is_not_none(modem_rsp.band_sel_cfg_list)

    async def test_get_radio_bands_sets_correct_response_type(self):
        modem_rsp = WalterModemRsp()
        await modem.get_radio_bands(rsp=modem_rsp)
        self.assert_equal(WalterModemRspType.BANDSET_CFG_SET, modem_rsp.type)
    
    async def test_radio_bands_response_contains_valid_modem_band_selections(self):
        modem_rsp = WalterModemRsp()
        await modem.get_radio_bands(rsp=modem_rsp)
        self.assert_is_instance(modem_rsp.band_sel_cfg_list[0], ModemBandSelection)
    
    # ---
    # get_sim_state()
    
    async def test_get_sim_state_runs(self):
        self.assert_true(await modem.get_sim_state())

    async def test_get_sim_state_sets_sim_state_in_response(self):
        modem_rsp = WalterModemRsp()
        await modem.get_sim_state(modem_rsp)
        self.assert_is_not_none(modem_rsp.sim_state)
    
    async def test_get_sim_state_sets_correct_response_type(self):
        modem_rsp = WalterModemRsp()
        await modem.get_sim_state(modem_rsp)
        self.assert_equal(WalterModemRspType.SIM_STATE, modem_rsp.type)


test_sim_and_network_pre_connection = TestSIMAndNetworkPreConnection()
establish_lte_connection = EstablishLTEConnection()
test_sim_and_network_post_connection = TestSIMAndNetworkPostConnection()

test_sim_and_network_pre_connection.run()
establish_lte_connection.run()
test_sim_and_network_post_connection.run()