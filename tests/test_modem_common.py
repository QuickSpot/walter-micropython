import asyncio

import minimal_unittest as unittest
from walter_modem import Modem
from walter_modem.queue import QueueFull

modem = Modem()

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

test_modem_common = TestModemCommon()
test_modem_common.run()