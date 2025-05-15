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