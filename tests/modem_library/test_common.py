import asyncio

from minimal_unittest import (
    AsyncTestCase,
    WalterModemAsserts
)

from walter_modem import Modem
from walter_modem.enums import (
    WalterModemOpState,
    WalterModemCEREGReportsType,
    WalterModemCMEErrorReportsType
)
from walter_modem.structs import (
    ModemRsp
)
from walter_modem.queue import (
    QueueFull
)

modem = Modem()

class TestBegin(
    AsyncTestCase
):
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

class TestReset(
    AsyncTestCase
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent

    async def test_returns_true(self):
        self.assert_true(await modem.reset())
    
    async def test_resets_mirror_state(self):
        # Only interested in changing mirror state for test,
        # not the actual modem's state
        modem._op_state = WalterModemOpState.MANUFACTURING
        mirror_op_state_before = modem._op_state

        await modem.reset()

        self.assert_not_equal(mirror_op_state_before, modem._op_state)        
    
    async def test_keeps_internal_begun_flag(self):
        await modem.reset()
        self.assert_true(modem._begun)

testcases = [testcase() for testcase in (
    TestBegin,
    TestReset,
)]

for testcase in testcases:
    testcase.run()