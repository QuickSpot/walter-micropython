import asyncio

import minimal_unittest as unittest
from walter_modem import Modem
from walter_modem.enums import WalterModemNetworkRegState
from walter_modem.structs import ModemRsp
from walter_modem.queue import QueueFull

modem = Modem()
modem_rsp = ModemRsp()

class TestModemSimAndNetwork(unittest.AsyncTestCase):
    async def async_setup(self):
        await modem.begin()
    
    async def test_get_network_reg_state_returns_not_searching_default(self):
        reg_state = modem.get_network_reg_state()
        self.assert_equal(WalterModemNetworkRegState.NOT_SEARCHING, reg_state)

test_modem_common = TestModemSimAndNetwork()
test_modem_common.run()