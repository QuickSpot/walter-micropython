import asyncio

import minimal_unittest as unittest

from walter_modem import Modem
from walter_modem.enums import (
    WalterModemOpState,
    WalterModemCEREGReportsType,
    WalterModemCMEErrorReportsType
)
from walter_modem.structs import ModemRsp
from walter_modem.queue import QueueFull

modem = Modem()

class TestCommon(unittest.AsyncTestCase, unittest.WalterModemAsserts):
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
        self.assert_true(await modem.reset())

    async def test_check_comm_runs(self):
        self.assert_true(await modem.check_comm())

    async def test_get_clock_runs(self):
        self.assert_true(await modem.get_clock())
    
    async def test_config_cme_error_reports_runs(self):
        self.assert_true(await modem.config_cme_error_reports())
    
    async def test_config_cme_error_reports_sends_correct_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT+CMEE=1',
            lambda: modem.config_cme_error_reports(WalterModemCMEErrorReportsType.NUMERIC)
        )

    async def test_config_cereg_reports_runs(self):
        self.assert_true(await modem.config_cereg_reports())

    async def test_config_cereg_reports_sends_correct_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT+CEREG=1',
            lambda: modem.config_cereg_reports(WalterModemCEREGReportsType.ENABLED)
        )
    
    async def test_get_op_state_runs(self):
        self.assert_true(await modem.get_op_state())

    async def test_get_op_state_sets_op_state_in_response(self):
        modem_rsp = ModemRsp()
        await modem.get_op_state(rsp=modem_rsp)
        self.assert_is_not_none(modem_rsp.op_state)
    
    async def test_set_op_state_runs(self):
        self.assert_true(await modem.set_op_state(WalterModemOpState.MINIMUM))
    
    async def test_set_op_state_sends_correct_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT+CFUN=4',
            lambda: modem.set_op_state(WalterModemOpState.NO_RF)
        )

test_common = TestCommon()
test_common.run()