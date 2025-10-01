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
                    (b'+SQNSH: ', self.__handle_socket_closed),
                    (b'+SQNSRING: ', self.__handle_socket_ring),
                    (b'+SQNSRECV: ', self.__handle_socket_rcv),
                    (b'+SQNSI: ', self.__handle_socket_information),
                    (b'+SQNSO: ', self.__handle_scoket_status)
                )
            )

            self.__deep_sleep_wakeup_callables = (
                self.__deep_sleep_prepare_callables + (self.__socket_deep_sleep_wake,)
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

    async def socket_accept(self,
        ctx_id: int,
        command_mode: bool = True,
        rsp: WalterModemRsp = None
    ) -> bool:
        if ctx_id < _SOCKET_MIN_CTX_ID or _SOCKET_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False
        
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSA={ctx_id},{modem_bool(command_mode)}',
            at_rsp=b'OK',
            cmd_type=WalterModemCmdType.DATA_TX_WAIT
        )

    async def socket_listen(self,
        ctx_id: int,
        protocol: int = WalterModemSocketProtocol.TCP,
        listen_state: int = WalterModemSocketListenState.IPV4,
        listen_port: int = 0,
        rsp: WalterModemRsp = None
    ) -> bool:
        if ctx_id < _SOCKET_MIN_CTX_ID or _SOCKET_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False
        
        if protocol == WalterModemSocketProtocol.TCP:
            return await self._run_cmd(
                rsp=rsp,
                at_cmd=f'AT+SQNSL={ctx_id},{listen_state},{listen_port}',
                at_rsp=b'OK',
                cmd_type=WalterModemCmdType.DATA_TX_WAIT
            )
        elif protocol == WalterModemSocketProtocol.UDP:
            return await self._run_cmd(
                rsp=rsp,
                at_cmd=f'AT+SQNSLUDP={ctx_id},{listen_state},{listen_port}',
                at_rsp=b'OK',
                cmd_type=WalterModemCmdType.DATA_TX_WAIT
            )
        else:
            if rsp: rsp.result = WalterModemState.ERROR
            return False

    async def socket_receive_data(self,
        ctx_id: int,
        length: int,
        max_bytes: int,
        rsp: WalterModemRsp = None
    ) -> bool:
        if ctx_id < _SOCKET_MIN_CTX_ID or _SOCKET_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False
        
        if max_bytes < _SOCKET_RECV_MIN_BYTES_LEN or _SOCKET_RECV_MAX_BYTES_LEN < max_bytes:
            if rsp: rsp.result = WalterModemState.ERROR
            return False
        
        if length < 0:
            if rsp: rsp.result = WalterModemState.ERROR
            return False
        
        self.__parser_data.raw_chunk_size = min(length, max_bytes)

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSRECV={ctx_id},{max_bytes}',
            at_rsp=b'OK'
        )

    async def socket_restore(self,
        ctx_id: int,
        rsp: WalterModemRsp = None
    ) -> bool:
        if ctx_id < _SOCKET_MIN_CTX_ID or _SOCKET_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False
        
        async def complete_handler(result, rsp, complete_handler_arg):
            if result == WalterModemState.OK:
                self.socket_context_states[ctx_id].connected = True
        
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSO={ctx_id}',
            at_rsp=b'OK',
            complete_handler=complete_handler
        )
    
    async def socket_information(self,
        ctx_id: int,
        rsp: WalterModemRsp = None
    ) -> bool:
        if ctx_id < _SOCKET_MIN_CTX_ID or _SOCKET_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False
        
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSI={ctx_id}',
            at_rsp=(b'OK', b'CONNECT')
        )
    
    async def socket_status(self,
        ctx_id: int,
        rsp: WalterModemRsp = None
    ) -> bool:
        if ctx_id < _SOCKET_MIN_CTX_ID or _SOCKET_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False
        
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSS={ctx_id}',
            at_rsp=b'OK'
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

    async def __handle_socket_closed(self, tx_stream, cmd, at_rsp):
        ctx_id = int(at_rsp.split(b':').decode())
        self.socket_context_states[ctx_id].connected = False

        return WalterModemState.OK
    
    async def __handle_socket_ring(self, tx_stream, cmd, at_rsp):
        parts = at_rsp.split(b': ', 1)[1].split(b',')
        ctx_id = int(parts[0].decode())

        self.socket_context_states[ctx_id].rings.append(ModemSocketRing(
            ctx_id=ctx_id,
            length=int(parts[1].decode()) if len(parts) >= 2 else None,
            data=parts[2] if len(parts) == 3 else None
        ))

        return WalterModemState.OK
    
    async def __handle_socket_rcv(self, tx_stream, cmd, at_rsp):
        header, payload = at_rsp.split(b': ', 1)[1].split(b'\r')
        header = header.split(b',')

        ctx_id, max_bytes = int(header[0].decode()), int(header[1].decode())
        addr = None
        port = None
        if len(header) == 4:
            addr = header[2].decode()
            port = int(header[3].decode())
        
        cmd.rsp.type = WalterModemRspType.SOCKET
        cmd.rsp.socket_rcv_response = ModemSocketResponse(
            ctx_id=ctx_id,
            max_bytes=max_bytes,
            payload=payload,
            addr=addr,
            port=port
        )

        return WalterModemState.OK
    
    async def __handle_socket_information(self, tx_stream, cmd, at_rsp):
        parts = at_rsp.split(b': ')[1].split(b',')
        ctx_id, sent, received, buff_in, ack_waiting = [int(p.decode()) for p in parts]

        cmd.rsp.tye = WalterModemRspType.SOCKET
        cmd.rsp.socket_information = ModemSocketInformation(
            ctx_id=ctx_id,
            sent=sent,
            received=received,
            buff_in=buff_in,
            ack_waiting=ack_waiting
        )
    
    async def __handle_scoket_status(self, tx_stream, cmd, at_rsp):
        parts = at_rsp.split(b': ', 1)[1].split(b',')
        ctx_id, state, locIP, locPort, remIP, remPort, txProt = [p.decode() for p in parts]

        self.socket_context_states[int(ctx_id)].connected = (
            state == '1' or state == '4' or state == '5'
        )

        cmd.rsp.typ = WalterModemRspType.SOCKET
        cmd.response.socket_status = ModemSocketStatus(
            ctx_id=int(ctx_id),
            state=int(state),
            local_addr=locIP,
            local_port=int(locPort),
            remote_addr=remIP,
            remote_port=int(remPort),
            protocol=int(txProt)
        )

    #endregion
    #region Sleep

    async def __socket_deep_sleep_wake(self):
        await self._run_cmd(at_cmd='AT+SQNSS', at_rsp=b'OK')

    #endregion
#endregion
