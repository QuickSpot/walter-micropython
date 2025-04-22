from ..core import ModemCore
from ..enums import (
    WalterModemCmdType,
    WalterModemState
)
from ..structs import (
    ModemRsp,
    ModemMQTTResponse,
    ModemMqttMessage
)
from ..utils import (
    modem_string,
    get_mac,
    log
)

class ModemMQTT(ModemCore):
    async def mqtt_config(self,
        client_id: str = get_mac(),
        user_name: str = '',
        password: str = '',
        tls_profile_id: int = None,
        library_message_buffer: int = 16,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Configure the MQTT client without connecting.

        :param client_id: MQTT client ID to use (defaults to the device MAC).
        :param user_name: Optional username for authentication.
        :param password: Optional password for authentication.
        :param tls_profile_id: Optional TLS profile ID to use.
        :param library_message_buffer: Size of the library's internal MQTT message buffer 
            (defaults to 16).
            This buffer stores metadata for received messages but does not hold their payloads.
            The modem itself supports up to 100 messages, but increasing this buffer significantly
            may consume excessive memory and is not recommended.
        :param rsp: Reference to a modem response instance.

        :return: True on success, False on failure.
        """

        if library_message_buffer >= 50:
            log('WARNING',
                'High lib message buffer '
                'Setting the MQTT Message Buffer too high may consume excessive memory')

        for _ in range(library_message_buffer):
            self._mqtt_msg_buffer.append(ModemMqttMessage('', 0, 0, None))

        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNSMQTTCFG=0,{},{},{}{}'.format(
                modem_string(client_id),
                modem_string(user_name),
                modem_string(password),
                f',{tls_profile_id}' if tls_profile_id else ''
            ),
            at_rsp=b'OK'
        )

    async def mqtt_connect(self,
        server_name: str,
        port: int,
        keep_alive: int = 60,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Initialize MQTT and establish a connection.

        :param server_name: MQTT broker hostname
        :param port: Port to connect to
        :param keep_alive: Maximum keepalive time (in seconds), defaults to 60
        :param rsp: Reference to a modem response instance

        :return: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSMQTTCONNECT=0,{modem_string(server_name)},{port},{keep_alive}',
            at_rsp=b'+SQNSMQTTONCONNECT:0,'
        )
    
    async def mqtt_disconnect(self, rsp: ModemRsp = None) -> bool:
        """
        Disconnect from an MQTT broker

        :param rsp: Reference to a modem response instance

        :return: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNSMQTTDISCONNECT=0',
            at_rsp=b'+SQNSMQTTONDISCONNECT:0,'
        )

    async def mqtt_publish(self,
        topic: str,
        data,
        qos: int,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Publish the passed data on the given MQTT topic using the earlier eastablished connection.

        :param topic: The topic to publish on
        :param payload: The data to publish
        :param qos: Quality of Service (0: at least once, 1: at least once, 2: exactly once)
        :param rsp: Reference to a modem response instance

        :return: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSMQTTPUBLISH=0,{modem_string(topic)},{qos},{len(data)}',
            at_rsp=b'+SQNSMQTTONPUBLISH:0,',
            data=data,
            cmd_type=WalterModemCmdType.DATA_TX_WAIT
        )

    async def mqtt_subscribe(self,
        topic: str,
        qos: int = 1,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Subscribe to a given MQTT topic using the earlier established connection.

        :param topic: The topic to subscribe to
        :param qos: Quality of Service (0: at least once, 1: at least once, 2: exactly once)
        :param rsp: Reference to a modem response instance

        :return: True on success, False on failure
        """
        async def complete_handler(result, rsp, complete_handler_arg):
            if result == WalterModemState.OK:
                if complete_handler not in self._mqtt_subscriptions:
                    self._mqtt_subscriptions.append(complete_handler_arg)

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSMQTTSUBSCRIBE=0,{modem_string(topic)},{qos}',
            at_rsp=b'+SQNSMQTTONSUBSCRIBE:0,{}'.format(modem_string(topic)),
            complete_handler=complete_handler,
            complete_handler_arg=(topic, qos)
        )
    
    async def mqtt_did_ring(self,
        msg_list: list,
        topic: str = None,
        rsp: ModemRsp = None
        ) -> bool:
        """
        Poll if the modem has reported any incoming MQTT messages received on topics
        that we are subscribed on.

        WARNING: No more than 1 message with QoS 0 are stored in the buffer,
        every new message with QoS 0 overwrites the previous
        (this only applies to messages with QoS 0)

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
            if rsp: rsp.result = WalterModemState.NO_DATA
            return False
        
        at_cmd = f'AT+SQNSMQTTRCVMESSAGE=0,{modem_string(msg.topic)}'
        if msg.message_id:
            at_cmd += f',{msg.message_id}'

        self._mqtt_msg_buffer[msg_index].free = True

        async def complete_handler(result, rsp, complete_handler_arg):
            if result == WalterModemState.OK:
                rsp.mqtt_response = complete_handler_arg

        return await self._run_cmd(
            rsp=rsp,
            ring_return=msg_list,
            at_cmd=at_cmd,
            at_rsp=b'OK',
            complete_handler=complete_handler,
            complete_handler_arg=ModemMQTTResponse(msg.topic, msg.qos)
        )