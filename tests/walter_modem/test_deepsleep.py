import asyncio
import minimal_unittest as unittest
import machine # type: ignore

from walter_modem import Modem

from walter_modem.coreEnums import (
    WalterModemNetworkRegState
)

from walter_modem.coreStructs import (
    ModemRsp,
    WalterModemOpState,
)

modem = Modem()
modem_rsp = ModemRsp()

# NOTE: Minimal deepsleep testing
# ===============================
# Most of the deepsleep testing has to be done manually
# Measuring power, expected modem behaviour, ...
# That said, this testfile aids in that testing,
# as it only runs again after pressing the reset button.

async def await_connection():
        print('\nShowing modem uart debug logs:')
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

class TestDeepSleep(unittest.AsyncTestCase):
    async def async_setup(self):
        print(f'Started, reason: {machine.reset_cause()}')
        await asyncio.sleep(3)
        print('Second startup notice (3s after startup)')

        if machine.reset_cause() != machine.DEEPSLEEP_RESET:
            await modem.begin()
            await modem.pdp_context_create()
            await modem.get_op_state(rsp=modem_rsp)
            if modem_rsp.op_state is not WalterModemOpState.FULL:
                await modem.set_op_state(WalterModemOpState.FULL)

            await await_connection()
            print('Network Connection established')
            print('Waiting 5sec before entering deepsleep')
            await asyncio.sleep(5)
            print('Starting 20s deepsleep')
            modem.sleep(sleep_time_ms=20000)

    async def test_modem_begins_after_deepsleep(self):
        await self.assert_does_not_throw(modem.begin, Exception)
    
    async def test_modem_retained_connection_during_sleep(self):
        self.assert_equal(WalterModemOpState.FULL, modem._op_state)

test_deep_sleep = TestDeepSleep()
test_deep_sleep.run()