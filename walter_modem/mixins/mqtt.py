import asyncio
import io
import struct

from machine import RTC # type: ignore
from micropython import const # type: ignore

from ..core import ModemCore
from ..coreEnums import (
    Enum,
    WalterModemState,
    WalterModemRspType,
    WalterModemCmdType
)
from ..coreStructs import (
    WalterModemRsp
)
from ..utils import (
    mro_chain_init,
    modem_string,
    get_mac,
    log
)

#region Enums

class WalterModemMqttState(Enum):
    CONNECTED = 0
    DISCONNECTED = 1

class WalterModemMqttResultCode(Enum):
    SUCCESS = 0
    ERR_NOMEM = -1
    ERR_PROTOCOL = -2
    ERR_INVAL = -3
    ERR_NO_CONN = -4
    ERR_CONN_REFUSED = -5
    ERR_NOT_FOUND = -6
    ERR_CONN_LOST = -7
    ERR_TLS = -8
    ERR_PAYLOAD_SIZE = -9
    ERR_NOT_SUPPORTED = -10
    ERR_AUTH = -11
    ERR_ACL_DENIED = -12
    ERR_UNKOWN = -13
    ERR_ERRNO = -14
    ERR_EAI = -15
    ERR_PROXY = -16
    ERR_UNAVAILABLE = -17

#endregion
#region Structs

class WalterModemMQTTResponse:
    def __init__(self, topic, qos):
        self.topic = topic
        self.qos = qos

class WalterModemMqttMessage:
    def __init__(self, topic, length, qos, message_id = None, payload = None):
        self.topic = topic
        self.length = length
        self.qos = qos
        self.message_id = message_id
        self.payload = payload
        self.free = True

#endregion
#region Constants

_MQTT_TOPIC_MAX_SIZE = const(127)
_MQTT_MAX_PENDING_RINGS = const(8)
_MQTT_MAX_TOPICS = const(4)
_MQTT_MIN_KEEP_ALIVE = const(20)
_MQTT_MAX_MESSAGE_LEN = const(4096)

#endregion
#region MixinClass

class MQTTMixin(ModemCore):
    MODEM_RSP_FIELDS = (
        ('mqtt_response', None),
        ('mqtt_rc', None),
    )

    def __init__(self, *args, **kwargs):
        def init():
            self.mqtt_status = WalterModemMqttState.DISCONNECTED
            """Status of the MQTT connection"""

            self.__mqtt_msg_buffer: list[WalterModemMqttMessage] = [] # type: ignore
            """Inbox for MQTT messages"""

            self.__mqtt_subscriptions: list[tuple[str, int]] = [] # type: ignore

            self.__queue_rsp_rsp_handlers = (
                self.__queue_rsp_rsp_handlers + (
                    (b'+SQNSMQTTONCONNECT:0,', self.__handle_mqtt_on_connect),
                    (b'+SQNSMQTTONPUBLISH:0', self.__handle_mqtt_on_publish),
                    (b'+SQNSMQTTONDISCONNECT:0,', self.__handle_mqtt_on_disconnect),
                    (b'+SQNSMQTTONMESSAGE:0,', self.__handle_mqtt_on_message),
                    (b'+SQNSMQTTMEMORYFULL', self.__handle_mqtt_memory_full),
                    (b'+SQNSMQTTONSUBSCRIBE:0', self.__handle_mqtt_subscribe),
                ) 
            )

            self.__queue_rsp_cmd_handlers = (
                self.__queue_rsp_cmd_handlers + (
                    ('AT+SQNSMQTTRCVMESSAGE=0', self._handle_sqns_mqtt_rcv_message),
                )
            )

            self.__deep_sleep_prepare_callables = (
                self.__deep_sleep_prepare_callables + (self.__mqtt_deep_sleep_prepare,)
            )

            self.__deep_sleep_wakeup_callables = (
                self.__deep_sleep_wakeup_callables + (self.__mqtt_deep_sleep_wake,)
            )

            self.__mirror_state_reset_callables = (
                self.__mirror_state_reset_callables + (self._mqtt_mirror_state_reset,)
            )
    
        mro_chain_init(self, super(), init, MQTTMixin, *args, **kwargs)

    #region PublicMethods

    async def mqtt_config(self,
        client_id: str = get_mac(),
        user_name: str = '',
        password: str = '',
        tls_profile_id: int = None,
        library_message_buffer: int = 16,
        rsp: WalterModemRsp = None
    ) -> bool:
        if library_message_buffer >= 50:
            log('WARNING',
                'High lib message buffer '
                'Setting the MQTT Message Buffer too high may consume excessive memory')

        for _ in range(library_message_buffer):
            self.__mqtt_msg_buffer.append(WalterModemMqttMessage('', 0, 0, None))

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
        rsp: WalterModemRsp = None
    ) -> bool:
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSMQTTCONNECT=0,{modem_string(server_name)},{port},{keep_alive}',
            at_rsp=b'+SQNSMQTTONCONNECT:0,'
        )
    
    async def mqtt_disconnect(self, rsp: WalterModemRsp = None) -> bool:
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNSMQTTDISCONNECT=0',
            at_rsp=b'+SQNSMQTTONDISCONNECT:0,'
        )

    async def mqtt_publish(self,
        topic: str,
        data,
        qos: int,
        rsp: WalterModemRsp = None
    ) -> bool:
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
        rsp: WalterModemRsp = None
    ) -> bool:
        async def complete_handler(result, rsp, complete_handler_arg):
            if result == WalterModemState.OK:
                if complete_handler not in self.__mqtt_subscriptions:
                    self.__mqtt_subscriptions.append(complete_handler_arg)

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
        rsp: WalterModemRsp = None
    ) -> bool:
        msg = None
        msg_index = -1

        for i in range(len(self.__mqtt_msg_buffer)):
            _msg = self.__mqtt_msg_buffer[i]
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

        self.__mqtt_msg_buffer[msg_index].free = True

        async def complete_handler(result, rsp, complete_handler_arg):
            if result == WalterModemState.OK:
                rsp.mqtt_response = complete_handler_arg

        return await self._run_cmd(
            rsp=rsp,
            ring_return=msg_list,
            at_cmd=at_cmd,
            at_rsp=b'OK',
            complete_handler=complete_handler,
            complete_handler_arg=WalterModemMQTTResponse(msg.topic, msg.qos)
        )

    #region PrivateMethods

    def _add_msg_to_mqtt_buffer(self, msg_id, topic, length, qos):
        # According to modem documentation;
        # A message with <qos>=0 doesn't have a <mid>,
        # as this type of message is overwritten every time a new message arrives.
        # No <mid> value is to be given to read a message with <qos>=0.
        if qos == 0:
            for msg in self.__mqtt_msg_buffer:
                if msg.qos == 0:
                    msg.topic = topic
                    msg.length = length
                    msg.free = False
                    msg.payload = None
                    return

        if qos > 0:
            for msg in self.__mqtt_msg_buffer:
                if msg.message_id == msg_id and msg.topic == topic:
                    return

        for msg in self.__mqtt_msg_buffer:
            if msg.free:
                msg.topic = topic
                msg.length = length
                msg.qos = qos
                msg.message_id = msg_id
                msg.payload = None
                msg.free = False
                return
            
        log('WARN', 'Modem Library\'s MQTT Message Buffer is full, incoming message was dropped')
    
    def _mqtt_mirror_state_reset(self):
        self.mqtt_status = WalterModemMqttState.DISCONNECTED
        self.__mqtt_msg_buffer: list[WalterModemMqttMessage] = []
        self.__mqtt_subscriptions: list[tuple[str, int]] = []

    #endregion
    #region QueueResponseHandlers

    async def __handle_mqtt_on_connect(self, tx_stream, cmd, at_rsp):
        _, result_code_str = at_rsp[len("+SQNSMQTTONCONNECT:"):].decode().split(',')
        result_code = int(result_code_str)

        if cmd and cmd.at_cmd:
            cmd.rsp.type = WalterModemRspType.MQTT
            cmd.rsp.mqtt_rc = result_code

        if result_code:
            self.mqtt_status = WalterModemMqttState.DISCONNECTED
        else:
            self.mqtt_status = WalterModemMqttState.CONNECTED

        if self.mqtt_status == WalterModemMqttState.CONNECTED:
            for (topic, qos) in self.__mqtt_subscriptions:
                asyncio.create_task(self._run_cmd(
                    at_cmd=f'AT+SQNSMQTTSUBSCRIBE=0,{modem_string(topic)},{qos}',
                    at_rsp=b'+SQNSMQTTONSUBSCRIBE:0,{}'.format(modem_string(topic)),
                ))
        
        if cmd and cmd.at_cmd and cmd.at_cmd.startswith('AT+SQNSMQTTCONNECT=0'):
            if result_code != WalterModemMqttResultCode.SUCCESS:
                return WalterModemState.ERROR
        
        return WalterModemState.OK
    
    async def __handle_mqtt_on_publish(self, tx_stream, cmd, at_rsp):
        result_code = int(at_rsp[-2:].strip(b','))

        if cmd and cmd.at_cmd:
            cmd.rsp.type = WalterModemRspType.MQTT
            cmd.rsp.mqtt_rc = result_code

        if cmd and cmd.at_cmd and cmd.at_cmd.startswith('AT+SQNSMQTTPUBLISH=0'):
            if result_code != WalterModemMqttResultCode.SUCCESS:
                return WalterModemState.ERROR
        
        return WalterModemState.OK        

    async def __handle_mqtt_on_disconnect(self, tx_stream, cmd, at_rsp):
        _, result_code_str = at_rsp[len("+SQNSMQTTONDISCONNECT:"):].decode().split(',')
        result_code = int(result_code_str)

        if cmd and cmd.at_cmd:
            cmd.rsp.type = WalterModemRspType.MQTT
            cmd.rsp.mqtt_rc = result_code

        if result_code != 0:
            return WalterModemState.ERROR

        self.mqtt_status = WalterModemMqttState.DISCONNECTED
        self.__mqtt_subscriptions = []
        for msg in self.__mqtt_msg_buffer:
            msg.free = True
        
        if cmd and cmd.at_cmd and cmd.at_cmd.startswith('AT+SQNSMQTTDISCONNECT=0'):
            if result_code != WalterModemMqttResultCode.SUCCESS:
                return WalterModemState.ERROR

        return WalterModemState.OK

    async def __handle_mqtt_on_message(self, tx_stream, cmd, at_rsp):
        parts = at_rsp[len("+SQNSMQTTONMESSAGE:"):].decode().split(',')
        topic = parts[1].replace('"', '')
        length = int(parts[2])
        qos = int(parts[3])
        if qos != 0 and len(parts) > 4:
            message_id = parts[4]
        else:
            message_id = None

        self._add_msg_to_mqtt_buffer(message_id, topic, length, qos)
        return WalterModemState.OK

    async def __handle_mqtt_memory_full(self, tx_stream, cmd, at_rsp):
        log('WARNING',
            'Sequans Modem\'s MQTT Memory full')

        for msg in self.__mqtt_msg_buffer:
            msg.free = True

        return WalterModemState.OK
    
    async def __handle_mqtt_subscribe(self, tx_stream, cmd, at_rsp):
        result_code = int(at_rsp[-2:].strip(b',').decode())

        if cmd and cmd.at_cmd:
            cmd.rsp.type = WalterModemRspType.MQTT
            cmd.rsp.mqtt_rc = result_code

        if cmd and cmd.at_cmd and cmd.at_cmd.startswith('AT+SQNSMQTTSUBSCRIBE=0'):
            if result_code != WalterModemMqttResultCode.SUCCESS:
                return WalterModemState.ERROR
        
        return WalterModemState.OK

    async def _handle_sqns_mqtt_rcv_message(self, tx_stream, cmd, at_rsp):
        if cmd.rsp.type != WalterModemRspType.MQTT:
            cmd.rsp.type = WalterModemRspType.MQTT
            
        if isinstance(cmd.ring_return, list) and (at_rsp != b'OK' and at_rsp != b'ERROR'):
            cmd.ring_return.append(at_rsp.decode())
        
        return WalterModemState.OK

    #endregion
    #region Sleep

    def __mqtt_deep_sleep_prepare(self, persist_mqtt_subs: bool, *args):
        if persist_mqtt_subs:
            buffer = io.BytesIO()
            buffer.write(struct.pack('B', 1))

            for topic, qos in self.__mqtt_subscriptions:
                encoded_topic = topic.encode('utf-8')
                buffer.write(struct.pack('I', len(encoded_topic)))
                buffer.write(struct.pack(f'{len(encoded_topic)}s', encoded_topic))
                buffer.write(struct.pack('B', qos))

            packed_data = buffer.getvalue()
        else:
            packed_data = struct.pack('B', 0)
        
        rtc = RTC()
        rtc.memory(packed_data)
    
    async def __mqtt_deep_sleep_wake(self):
        rtc = RTC()
        packed_data = rtc.memory()

        if len(packed_data) > 0:
            mqtt_subs = packed_data[0]
            packed_data = packed_data[1:]
            if mqtt_subs == 1:
                buffer = io.BytesIO(packed_data)
                mqtt_subscriptions = self.__mqtt_subscriptions

                while buffer.tell() < len(packed_data):
                    topic_length = struct.unpack('I', buffer.read(4))[0]
                    topic = struct.unpack(
                        f'{topic_length}s',
                        buffer.read(topic_length)
                    )[0].decode('utf-8')
                    qos = struct.unpack('B', buffer.read(1))[0]

                    mqtt_subscriptions.append((topic, qos))

    #endregion
#endregion
