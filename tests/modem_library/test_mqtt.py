import asyncio
import minimal_unittest as unittest

from walter_modem import Modem
from walter_modem.enums import (
    WalterModemNetworkRegState,
    WalterModemRspType
)
from walter_modem.structs import (
    ModemRsp,
    WalterModemOpState
)

modem = Modem()

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

class TestMQTT(unittest.AsyncTestCase, unittest.WalterModemAsserts):
    async def async_setup(self):
        modem_rsp = ModemRsp()
        await modem.begin()

        await modem.create_PDP_context()

        await modem.get_op_state(rsp=modem_rsp)
        if modem_rsp.op_state is not WalterModemOpState.FULL:
            await modem.set_op_state(WalterModemOpState.FULL)

        await await_connection()
    
    # ---
    # mqtt_config()

    async def test_mqtt_config_sends_correct_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            f'AT+SQNSMQTTCFG=0,"mqtt-test","test-username","test-pwd",1',
            lambda: modem.mqtt_config(
                client_id='mqtt-test',
                user_name='test-username',
                password='test-pwd',
                tls_profile_id=1
            )
        )
    
    async def test_mqtt_config_runs(self):
        self.assert_true(await modem.mqtt_config())
    
    # ---
    # mqtt_connect()

    async def test_mqtt_connect_to_invalid_server_fails(self):
        self.assert_false(await modem.mqtt_connect(server_name='totally.valid.server', port=1234))
    
    async def test_mqtt_connect_to_invalid_server_sets_mqtt_rc_in_response(self):
        modem_rsp = ModemRsp()
        await modem.mqtt_connect(server_name='totally.valid.server', port=1234, rsp=modem_rsp)
        self.assert_is_instance(modem_rsp.mqtt_rc, int)
    
    async def test_mqtt_connect_sets_correct_modem_response_type(self):
        modem_rsp = ModemRsp()
        await modem.mqtt_connect(server_name='totally.valid.server', port=1234, rsp=modem_rsp)
        self.assert_equal(WalterModemRspType.MQTT, modem_rsp.type)
    
    async def test_mqtt_connect_to_valid_server_runs(self):
        self.assert_true(await modem.mqtt_connect(server_name='test.mosquitto.org', port=1883))

    # ---
    # mqtt_publish()

    async def test_mqtt_publish_runs(self):
        self.assert_true(await modem.mqtt_publish(
                topic='/walter/mqtt-test',
                data='Hello from the walter test',
                qos=0
            )
        )
    
    # ---
    # mqtt_disconnect()

    async def test_mqtt_disconnect_runs(self):
        self.assert_true(await modem.mqtt_disconnect())
    
    # TODO: See if there is a way to get an error rc wihtout just getting ERROR
    # Whilst the modem library should be able to handle that, it remains untested.


test_mqtt = TestMQTT()
test_mqtt.run()