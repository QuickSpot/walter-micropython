import asyncio
import minimal_unittest as unittest
import machine # type: ignore

from walter_modem import Modem

from walter_modem.enums import (
    WalterModemNetworkRegState
)

from walter_modem.structs import (
    ModemRsp,
    WalterModemOpState,
)

modem = Modem()
modem_rsp = ModemRsp()

async def await_connection():
        print('\nShowing modem debug logs:')
        modem.debug_log = True

        for _ in range(600):
            if modem.get_network_reg_state() in (
                WalterModemNetworkRegState.REGISTERED_HOME,
                WalterModemNetworkRegState.REGISTERED_ROAMING
            ):
                modem.debug_log = False
                return
            await asyncio.sleep(1)
        modem.debug_log = False
        raise OSError('Connection Timed-out')

class TestDeepSleepMqttPersist(unittest.AsyncTestCase):
    async def async_setup(self):
        print(f'Started, reason: {machine.reset_cause()}')
        await asyncio.sleep(3)
        print('Second startup notice (3s after startup)')
        await modem.begin()
        
        if machine.reset_cause() != machine.DEEPSLEEP_RESET:
            await modem.create_PDP_context()
            await modem.get_op_state(rsp=modem_rsp)
            if modem_rsp.op_state is not WalterModemOpState.FULL:
                await modem.set_op_state(WalterModemOpState.FULL)

            await await_connection()
            print('Network Connection established')
            await modem.mqtt_config()
            print('connecting to MQTT')
            await modem.mqtt_connect(server_name='test.mosquitto.org', port=1883)
            print('setting MQTT subscriptions')
            await modem.mqtt_subscribe(topic='short', qos=1)
            await modem.mqtt_subscribe(topic='long-topic-test', qos=0)
            print(modem._mqtt_subscriptions)
            print('Waiting 5sec before entering deepsleep')
            await asyncio.sleep(5)
            print('Starting 20s deepsleep')
            modem.sleep(sleep_time_ms=20000, persist_mqtt_subs=True)
        
    async def test_mqtt_subscriptions_persist_after_deepsleep(self):
        self.assert_equal([('short', 1), ('long-topic-test', 0)], modem._mqtt_subscriptions)

test_deep_sleep_mqtt_persist = TestDeepSleepMqttPersist()
test_deep_sleep_mqtt_persist.run()