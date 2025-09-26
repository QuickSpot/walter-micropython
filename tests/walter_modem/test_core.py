import asyncio
import micropython # type: ignore
micropython.opt_level(1)

from minimal_unittest import (
    AsyncTestCase,
    WalterModemAsserts,
    NetworkConnectivity
)

from walter_modem import Modem
from walter_modem.coreEnums import (
    WalterModemState,
    WalterModemOpState,
    WalterModemCEREGReportsType,
    WalterModemCMEErrorReportsType
)
from walter_modem.coreStructs import (
    WalterModemRsp
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
        self.assert_true(modem.__begun)

class TestSoftReset(
    AsyncTestCase,
    WalterModemAsserts
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent
    
    async def test_returns_true(self):
        self.assert_true(await modem.soft_reset())
    
    async def test_sends_expected_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT^RESET',
            lambda: modem.soft_reset(),
            b'+SYSSTART'
        )
    
    async def test_resets_mirror_state(self):
        # Only interested in changing mirror state for test,
        # not the actual modem's state
        modem._op_state = WalterModemOpState.MANUFACTURING
        mirror_op_state_before = modem._op_state

        await modem.soft_reset()

        self.assert_not_equal(mirror_op_state_before, modem._op_state)
    
    async def test_keeps_internal_begun_flag(self):
        await modem.soft_reset()
        self.assert_true(modem.__begun)

class TestCheckComm(
    AsyncTestCase,
    WalterModemAsserts
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent

    async def test_returns_true(self):
        self.assert_true(await modem.check_comm())

    async def test_sends_expected_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT',
            lambda: modem.check_comm()
        )

class TestGetClock(
    AsyncTestCase,
    WalterModemAsserts,
    NetworkConnectivity
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent
        await self.ensure_network_connection(modem) # Clock sync
    
    async def test_returns_true(self):
        self.assert_true(await modem.get_clock())
    
    async def test_sends_expected_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT+CCLK?',
            lambda: modem.get_clock()
        )
    
    async def test_clock_is_set_in_modem_rsp(self):
        modem_rsp = WalterModemRsp()
        await modem.get_clock(rsp=modem_rsp)

        self.assert_is_not_none(modem_rsp.clock)

class TestConfigCMEErrorReports(
    AsyncTestCase,
    WalterModemAsserts
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent

    # Test fail on invalid params
    
    async def test_fails_on_invalid_reports_type(self):
        self.assert_false(await modem.config_cme_error_reports(reports_type=70))
    
    async def test_result_error_set_in_modem_rsp_on_invalid_reports_type(self):
        modem_rsp = WalterModemRsp()
        await modem.config_cme_error_reports(reports_type=-10, rsp=modem_rsp)

        self.assert_equal(WalterModemState.ERROR, modem_rsp.result)
    
    # Test normal run
    
    async def test_returns_true_on_no_param(self):
        self.assert_true(await modem.config_cme_error_reports())
    
    async def test_returns_true_on_valid_param(self):
        self.assert_true(await modem.config_cme_error_reports(
            reports_type=WalterModemCMEErrorReportsType.OFF
            ))
    
    async def test_sends_expected_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT+CMEE=1',
            lambda: modem.config_cme_error_reports(
                reports_type=WalterModemCMEErrorReportsType.NUMERIC
            )
        )

class TestConfigCeregReports(
    AsyncTestCase,
    WalterModemAsserts
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent
    
    # Test fail on invalid params
    
    async def test_fails_on_invalid_reports_type(self):
        self.assert_false(await modem.config_cereg_reports(reports_type=70))
    
    async def test_result_error_set_in_modem_rsp_on_invalid_reports_type(self):
        modem_rsp = WalterModemRsp()
        await modem.config_cereg_reports(reports_type=-10, rsp=modem_rsp)

        self.assert_equal(WalterModemState.ERROR, modem_rsp.result)
    
    # Test normal run

    async def test_returns_true_on_no_param(self):
        self.assert_true(await modem.config_cereg_reports())
    
    async def test_returns_true_on_valid_param(self):
        self.assert_true(await modem.config_cereg_reports(
            reports_type=WalterModemCEREGReportsType.ENABLED
        ))
    
    async def test_sends_expected_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT+CEREG=5',
            lambda: modem.config_cereg_reports(
                reports_type=WalterModemCEREGReportsType.ENABLED_UE_PSM_WITH_LOCATION_EMM_CAUSE
            )
        )

testcases = [testcase() for testcase in (
    TestBegin,
    TestReset,
    TestSoftReset,
    TestCheckComm,
    TestGetClock,
    TestConfigCMEErrorReports,
    TestConfigCeregReports,
)]

for testcase in testcases:
    testcase.run()
