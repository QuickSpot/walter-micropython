import asyncio

import minimal_unittest as unittest
from walter_modem import Modem
from walter_modem.enums import WalterModemOpState
from walter_modem.structs import ModemRsp
from walter_modem.queue import QueueFull

modem = Modem()
modem_rsp = ModemRsp()

class TestModemCommon(unittest.AsyncTestCase):
    async def test_begin_runs(self):
        await self.assert_does_not_throw(modem.begin, (
            ValueError,
            OSError,
            RuntimeError,
            QueueFull,
            TypeError,
            asyncio.TimeoutError,
            asyncio.CancelledError
        ))

    async def test_reset_runs(self):
        self.assert_true(modem.reset())

    async def test_check_comm_runs(self):
        self.assert_true(modem.check_comm())

    async def test_get_clock_runs(self):
        self.assert_true(modem.get_clock())
    
    async def test_config_cme_error_reports_runs(self):
        self.assert_true(modem.config_cme_error_reports())

    async def test_config_cereg_reports_runs(self):
        self.assert_true(modem.config_cereg_reports())
    
    async def test_get_op_state_runs(self):
        self.assert_true(modem.get_op_state())
    
    async def test_set_op_state_runs(self):
        self.assert_true(modem.set_op_state(WalterModemOpState.MINIMUM))
    

test_modem_common = TestModemCommon()
test_modem_common.run()