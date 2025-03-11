from ..core import ModemCore
from ..enums import (
    ModemCmdType,
    ModemState
)
from ..structs import (
    ModemRsp,
    ModemMQTTResponse
)
from ..utils import (
    modem_string
)

class ModemMQTT(ModemCore):
    async def _mqtt_config(self,
        client_id: str,
        user_name: str,
        password: str,
        tls_profile_id: int = None,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Coroutine to configure a connection to an MQTT broker,
        called internally just before establishing the connection.
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNSMQTTCFG=0,{},{},{}{}'.format(
                modem_string(client_id),
                modem_string(user_name) if user_name else '""',
                modem_string(password) if user_name else '""',
                f',{tls_profile_id}' if tls_profile_id else ''
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
        tls_profile_id: int = None,
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
            at_rsp=b'+SQNSMQTTONCONNECT:0,'
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
    
    async def mqtt_did_ring(self,
        msg_list: list,
        topic: str = None,
        rsp: ModemRsp = None
        ) -> bool:
        """
        :param msg_list: Refence to a list where the received messages will be put.
        :param topic: The exact topic to filter on, leave as None for all topics
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        msg = None
        msg_index = -1

        for i in range(len(self._mqtt_msg_buffer)):
            _msg = self._mqtt_msg_buffer[i]
            if not _msg.free:
                if (topic and _msg.topic == topic) or topic is None:
                    msg = _msg
                    msg_index = i
                    break

        if msg is None:
            if rsp: rsp.result = ModemState.NO_DATA
            return False
        
        at_cmd = f'AT+SQNSMQTTRCVMESSAGE=0,{modem_string(msg.topic)}'
        if msg.message_id:
            at_cmd += f',{msg.message_id}'

        self._mqtt_msg_buffer[msg_index].free = True

        async def complete_handler(result, rsp, complete_handler_arg):
            rsp.mqtt_response = complete_handler_arg

        return await self._run_cmd(
            rsp=rsp,
            ring_return=msg_list,
            at_cmd=at_cmd,
            at_rsp=b'OK',
            complete_handler=complete_handler,
            complete_handler_arg=ModemMQTTResponse(msg.topic, msg.qos)
        )