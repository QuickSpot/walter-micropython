from ..core import ModemCore
from ..enums import (
    ModemRspType,
    ModemCmdType
)
from ..structs import (
    ModemRsp
)
from ..utils import (
    modem_string
)

class ModemMQTT(ModemCore):
    async def _mqtt_config(self,
        client_id: str,
        user_name: str,
        password: str,
        tls_profile_id: int,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Coroutine to configure a connection to an MQTT broker,
        called internally just before establishing the connection.
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNSMQTTCFG=0,{},{},{},{}'.format(
                modem_string(client_id), modem_string(user_name),
                modem_string(password), tls_profile_id
            ),
            at_rsp=b'OK'
        )

    async def mqtt_disconnect(self, rsp: ModemRsp = None) -> bool:
        """
        Disconnect from an MQTT broker
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNSMQTTDISCONNECT=0',
            at_rsp=b'+SQNSMQTTONDISCONNECT:0,0'
        )

    async def mqtt_connect(self,
        server_name: str,
        port: int,
        client_id: str,
        user_name: str,
        password: str,
        tls_profile_id: int,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Coroutine to establish a connection to an MQTT broker,
        also wrapping the configuration of the connection.
        This follows the logic of the Arduino example.
        """
        if not await self._mqtt_config(client_id, user_name, password, tls_profile_id, rsp):
            print('Failed to configure mqtt client.')
            return rsp

        print('MQTT client configured.')
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSMQTTCONNECT=0,{modem_string(server_name)},{port}',
            at_rsp=b'+SQNSMQTTONCONNECT:0,0'
        )

    async def mqtt_publish(self,
        topic: str,
        payload,
        qos,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Coroutine to publish a new MQTT message to a given topic
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSMQTTPUBLISH=0,{modem_string(topic)},{qos},{len(payload)}',
            at_rsp=b'+SQNSMQTTONPUBLISH:0,',
            data=payload,
            cmd_type=ModemCmdType.DATA_TX_WAIT
        )

    async def mqtt_subscribe(self,
        topic: str,
        qos,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Coroutine to subscribe to an MQTT topic
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSMQTTSUBSCRIBE=0,{modem_string(topic)},{qos}',
            at_rsp=b'+SQNSMQTTONSUBSCRIBE:0,{}'.format(modem_string(topic))
        )

    async def _mqtt_receive_message(self,
        topic: str,
        message_id = None,
        max_length = None,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Coroutine to initiate delivery of an MQTT message by the modem
        The payload of the MQTT message will be stored in the 'payload' property
        of the corresponding ModemMqttMessage instance within the
        _mqtt_messages list
        """
        at_cmd = "AT+SQNSMQTTRCVMESSAGE=0,{}".format(modem_string(topic))
        if message_id:
            at_cmd += ",{}".format(message_id)
        if max_length:
            at_cmd += ",{}".format(max_length)

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=at_cmd,
            at_rsp=b'OK'
        )

    async def mqtt_receive(self):
        """
        Coroutine to 'download' the payloads of all MQTT messages that are stored
        in the buffer of the modem and have not yet been downloaded from the modem
        into the controller.
        The return value is the number of all downloaded messages.
        """
        n = 0 
        for msg in self._mqtt_messages:
            if not msg.received:
                rsp = ModemRsp()
                if not await self._mqtt_receive_message(msg.topic, msg.message_id, rsp=rsp):
                    print('Failed to receive MQTT message')
                elif rsp.type == ModemRspType.MQTT:
                    msg.payload = rsp.mqtt_data
                    msg.received = True
                    n += 1
            else:
                # include messages in the count that have already been downloaded previously
                n += 1
        return n
    def get_mqtt_message(self):
        """
        Function to get the first of the 'received' messages in the list, 
        'received' meaning the payload has been downloaded from the buffer
        of the modem.
        Return value is a ModemMqttMessage
        """
        for msg in self._mqtt_messages:
            if msg.received:
                self._mqtt_messages.remove(msg)
                return msg