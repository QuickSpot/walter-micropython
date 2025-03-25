import asyncio
import minimal_unittest as unittest

from walter_modem import Modem
from walter_modem.enums import (
    WalterModemOpState,
    WalterModemNetworkRegState,
    WalterModemRat,
    WalterModemNetworkSelMode
)
from walter_modem.structs import ModemRsp

modem = Modem()
modem_rsp = ModemRsp()

class TestModemEstablishLTEConnection(unittest.AsyncTestCase):
    async def await_connection(self):
        print('\nShowing modem debug logs:')
        modem.set_debug(True)
        for _ in range(600):
            if modem.get_network_reg_state() in (
                WalterModemNetworkRegState.REGISTERED_HOME,
                WalterModemNetworkRegState.REGISTERED_ROAMING
            ):
                modem.set_debug(False)
                return
            await asyncio.sleep(1)
        modem.set_debug(False)
        raise OSError('Connection Timed-out')
    
    async def async_setup(self):
        await modem.begin()
        await modem.set_op_state(WalterModemOpState.FULL)
    
    async def test_get_network_reg_state_returns(self):
        reg_state = modem.get_network_reg_state()
        self.assert_is_not_none(reg_state)
    
    async def test_set_network_selection_mode_runs(self):
        self.assert_true(await modem.set_network_selection_mode(WalterModemNetworkSelMode.AUTOMATIC))

    async def test_connection_is_made(self):
        await self.assert_does_not_throw(self.await_connection, OSError)

class TestModemSimAndNetwork(unittest.AsyncTestCase):
    async def async_setup(self):
        if not modem.get_network_reg_state() in (
            WalterModemNetworkRegState.REGISTERED_HOME,
            WalterModemNetworkRegState.REGISTERED_ROAMING
        ):
            raise AssertionError('Modem not connected to LTE')

    async def test_get_rssi_runs(self):
        self.assert_true(await modem.get_rssi())
    
    async def test_get_signal_quality_runs(self):
        self.assert_true(await modem.get_signal_quality())
    
    async def test_get_cell_information_runs(self):
        self.assert_true(await modem.get_cell_information())
    
    async def test_get_rat_runs(self):
        self.assert_true(await modem.get_rat())
    
    async def test_set_rat_runs(self):
        self.assert_true(await modem.set_rat(WalterModemRat.AUTO))
    
    async def test_get_radio_bands_runs(self):
        self.assert_true(await modem.get_radio_bands())
    
    async def test_get_sim_state_runs(self):
        self.assert_true(await modem.get_sim_state())

test_modem_essential_methods_for_connection = TestModemEstablishLTEConnection()
test_modem_sim_and_network = TestModemSimAndNetwork()
test_modem_essential_methods_for_connection.run()
test_modem_sim_and_network.run()