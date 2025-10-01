from micropython import const # type: ignore

from ..core import *
from ..coreEnums import *
from ..coreStructs import *
from ..utils import *

#region Enums

class WalterModemSocketProtocol(Enum):
    TCP = 0
    UDP = 1

class WalterModemSocketAcceptAnyRemote(Enum):
    DISABLED = 0
    REMOTE_RX_ONLY = 1
    REMOTE_RX_AND_TX = 2

class WalterModemRai(Enum):
    NO_INFO = 0
    NO_FURTHER_RXTX_EXPECTED = 1
    ONLY_SINGLE_RXTX_EXPECTED = 2

class WalterModemSocketRingMode(Enum):
    NORMAL = 0
    """Only ctx_id"""
    DATA_AMOUNT = 1
    """ctx_id & data length"""
    DATA_VIEW = 2
    """ctx_id, data length & data"""

class WalterModemSocketRecvMode(Enum):
    TEXT_OR_RAW = 0
    HEX_BYTES_SEQUENCE = 1

class WalterModemSocketSendMode(Enum):
    TEXT_OR_RAW = 0
    HEX_BYTES_SEQUENCE = 1

class WalterModemSocketListenState(Enum):
    CLOSE = 0
    IPV4 = 1
    IPV6 = 2

class WalterModemSocketState(Enum):
    CLOSED = 0
    ACTIVE_DATA = 1
    SUSPENDED = 2
    SUSPENDED_PENDING_DATA = 3
    LISTENING = 4
    INCOMING_CONNECTION = 5
    OPENING = 6

#endregion
#region Structs

class ModemSocketContextState:
    def __init__(self):
        self.connected = False
        self.rings: list[ModemSocketRing] = []
        self.accept_any_remote = WalterModemSocketAcceptAnyRemote.DISABLED
        self.listen_auto_rsp: bool = False

class ModemSocketRing:
    def __init__(self, ctx_id, length = None, data = None):
        self.ctx_id: int = ctx_id
        self.length: int | None = length
        self.data = data

class ModemSocketResponse:
    def __init__(self, ctx_id, max_bytes, payload, addr = None, port = None):
        self.ctx_id: int = ctx_id
        self.max_bytes: int = max_bytes
        self.addr: str | None = addr
        self.port: int | None = port
        self.payload: bytearray = payload

class ModemSocketInformation:
    def __init__(self, ctx_id, sent, received, buff_in, ack_waiting):
        self.ctx_id: int = ctx_id
        self.sent: int = sent
        self.received: int = received
        self.buff_in: int = buff_in
        self.ack_waiting: int = ack_waiting

class ModemSocketStatus:
    def __init__(self, ctx_id, state, local_addr, local_port, remote_addr, remote_port, protocol):
        self.ctx_id: int = ctx_id
        self.state: WalterModemSocketState = state,
        self.local_addr: str = local_addr,
        self.local_port: int = local_port,
        self.remote_addr: str = remote_addr,
        self.remote_port: int = remote_port,
        self.protocol: WalterModemSocketProtocol = protocol

#endregion
#region Constants

_SOCKET_MIN_CTX_ID = const(1)
_SOCKET_MAX_CTX_ID = const(6)
_SOCKET_SEND_MIN_BYTES_LEN = const(1)
_SOCKET_SEND_MAX_BYTES_LEN = const(16777216)
_SOCKET_RECV_MIN_BYTES_LEN = const(1)
_SOCKET_RECV_MAX_BYTES_LEN = const(1500)

_TLS_MIN_CTX_ID = const(1)
_TLS_MAX_CTX_ID = const(6)

_PDP_MIN_CTX_ID = const(0)
_PDP_MAC_CTX_ID = const(6)

#endregion
#region MixinClass

class SocketMixin(ModemCore):
    MODEM_RSP_FIELDS = (
        ('socket_rcv_response', None),
        ('socket_information', None),
        ('socket_status', None)
    )

    def __init__(self, *args, **kwargs):
        def init():
            self.socket_context_states = tuple(
                ModemSocketContextState()
                for _ in range(_SOCKET_MIN_CTX_ID, _SOCKET_MAX_CTX_ID + 1)
            )

            self.__queue_rsp_rsp_handlers = (
                self.__queue_rsp_rsp_handlers + (
                    (b'+SQNSH: ', self.__handle_sh),
                    (b'+SQNSCFG: ', self.__handle_sqnscfg),
                )
            )

            self.__mirror_state_reset_callables = (
                self.__mirror_state_reset_callables + (self._socket_mirror_state_reset,)
            )
        
        mro_chain_init(self, super(), init, SocketMixin, *args, **kwargs)

    #region PublicMethods

    async def socket_config(self,
        ctx_id: int,
        pdp_ctx_id: int,
        mtu: int = 300,
        exchange_timeout: int = 90,
        connection_timeout: int = 60,
        send_delay_ms: int = 5000,
        rsp: WalterModemRsp = None
    ) -> bool:
        if ctx_id < _SOCKET_MIN_CTX_ID or _SOCKET_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False

        if pdp_ctx_id < _PDP_MIN_CTX_ID or _PDP_MAC_CTX_ID < pdp_ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PDP_CONTEXT
            return False
        
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNSCFG={},{},{},{},{},{}'.format(
                ctx_id, pdp_ctx_id, mtu, exchange_timeout,
                connection_timeout * 10, send_delay_ms // 100
            ),
            at_rsp=b'OK'
        )

    async def socket_config_extended(self,
        ctx_id: int,
        ring_mode: int = WalterModemSocketRingMode.DATA_AMOUNT,
        recv_mode: int = WalterModemSocketRecvMode.TEXT_OR_RAW,
        keepalive: int = 60,
        listen_auto_resp: bool = False,
        send_mode: int = WalterModemSocketSendMode.TEXT_OR_RAW,
        rsp: WalterModemRsp = None
    ) -> bool:
        if ctx_id < _SOCKET_MIN_CTX_ID or _SOCKET_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False
        
        async def complete_handler(result, rsp, complete_handler_arg):
            if result == WalterModemState.OK:
                self.socket_context_states[ctx_id].listen_auto_rsp = listen_auto_resp
        
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNSCFGEXT={},{},{},{},{},{}'.format(
                ctx_id, ring_mode, recv_mode, keepalive, modem_bool(listen_auto_resp), send_mode
            ),
            at_rsp=b'OK',
            complete_handler=complete_handler
        )

    async def socket_config_secure(self,
        ctx_id: int,
        enable: bool,
        secure_profile_id: int,
        rsp: WalterModemRsp = None
    ) -> bool:
        if ctx_id < _SOCKET_MIN_CTX_ID or _SOCKET_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False
        
        if secure_profile_id < _TLS_MIN_CTX_ID or _TLS_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.ERROR
            return False
        
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSSCFG={ctx_id},{modem_bool(enable)},{secure_profile_id}',
            at_rsp=b'OK'
        )

    async def socket_dial(self,
        ctx_id: int,
        remote_addr: str,
        remote_port: int,
        local_port: int = 0,
        protocol: int = WalterModemSocketProtocol.UDP,
        accept_any_remote: int = WalterModemSocketAcceptAnyRemote.DISABLED,
        rsp: WalterModemRsp = None
    ) -> bool:
        if ctx_id < _SOCKET_MIN_CTX_ID or _SOCKET_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False

        async def complete_handler(result, rsp, complete_handler_arg):
            if result == WalterModemState.OK:
                self.socket_context_states[ctx_id].connected = True
                self.socket_context_states[ctx_id].accept_any_remote = accept_any_remote
        
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNSD={},{},{},{},0,{},1,{},0'.format(
                ctx_id, protocol, remote_port, modem_string(remote_addr),
                local_port, accept_any_remote
            ),
            at_rsp=b'OK', # TODO: test if I always get okay, or if I get an URC, ... ... 
            complete_handler=complete_handler
        )

    async def socket_close(self,
        ctx_id: int,
        rsp: WalterModemRsp = None
    ) -> bool:
        if ctx_id < _SOCKET_MIN_CTX_ID or _SOCKET_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False

        async def complete_handler(result, rsp, complete_handler_arg):
            if result == WalterModemState.OK:
                self.socket_context_states[ctx_id].connected = False

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSH={ctx_id}',
            at_rsp=b'OK',
            complete_handler=complete_handler
        )

    async def socket_send(self,
        ctx_id: int,
        data: bytes | bytearray | str | None,
        length: int = None,
        rai: int = WalterModemRai.NO_INFO,
        remote_addr: str = None,
        remote_port: int = None,
        rsp: WalterModemRsp = None
    ) -> bool:
        if ctx_id < _SOCKET_MIN_CTX_ID or _SOCKET_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False
        
        if self.socket_context_states[ctx_id].accept_any_remote != WalterModemSocketAcceptAnyRemote.REMOTE_RX_AND_TX:
            if remote_addr is not None or remote_port is not None:
                if rsp: rsp.result = WalterModemState.ERROR
                return False
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        elif data is not None and not isinstance(data, (bytes, bytearray)):
            if rsp: rsp.result = WalterModemState.ERROR
            return False
        
        if length is None:
            length = 0 if data is None else len(data)
        
        if length < _SOCKET_SEND_MIN_BYTES_LEN or _SOCKET_SEND_MAX_BYTES_LEN < length:
            if rsp: rsp.result = WalterModemState.ERROR
            return False

        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNSSENDEXT={},{},{}{}'.format(
                ctx_id, length, rai,
                f',{remote_addr},{remote_port}' if remote_addr is not None and remote_port is not None else ''
            ),
            at_rsp=b'OK',
            cmd_type=WalterModemCmdType.DATA_TX_WAIT,
            data=data
        )

    #endregion
    #region PrivateMethods

    def _socket_mirror_state_reset(self):
        self.socket_context_states = tuple(
            ModemSocketContextState()
            for _ in range(_SOCKET_MIN_CTX_ID, _SOCKET_MAX_CTX_ID + 1)
        )

    #endregion
    #region QueueResponseHandlers

    async def __handle_sh(self, tx_stream, cmd, at_rsp):
        socket_id = int(at_rsp[len('+SQNSH: '):].decode())
        try:
            _socket = self._socket_list[socket_id - 1]
        except Exception:
            return None

        self._socket = _socket
        _socket.state = WalterModemSocketState.FREE

        return WalterModemState.OK

    async def __handle_sqnscfg(self, tx_stream, cmd, at_rsp):
        conn_id, cid, pkt_sz, max_to, conn_to, tx_to = map(int, at_rsp.split(b': ')[1].split(b','))

        socket = self._socket_list[conn_id - 1]
        socket.id = conn_id
        socket.pdp_context_id = cid
        socket.mtu = pkt_sz
        socket.exchange_timeout = max_to
        socket.conn_timeout = conn_to / 10
        socket.send_delay_ms = tx_to * 100

    #endregion
#endregion
