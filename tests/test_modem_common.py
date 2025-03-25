import asyncio

import minimal_unittest as unittest
from walter_modem import Modem
from walter_modem.structs import ModemRsp
from walter_modem.queue import QueueFull

modem = Modem()
modem_rsp = ModemRsp()

class TestModemCommon(unittest.AsyncTestCase):
    async def test_modem_begin_runs(self):
        await self.assert_does_not_throw(modem.begin, (
            ValueError,
            OSError,
            RuntimeError,
            QueueFull,
            TypeError,
            asyncio.TimeoutError,
            asyncio.CancelledError
        ))

    async def test_modem_reset_runs(self):
        self.assert_true(modem.reset())

    async def test_modem_check_comm_runs(self):
        self.assert_true(modem.check_comm())

    async def test_modem_get_clock_runs(self):
        self.assert_true(modem.get_clock())
    

test_modem_common = TestModemCommon()
test_modem_common.run()