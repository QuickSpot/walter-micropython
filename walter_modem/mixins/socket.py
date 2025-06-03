import gc
from micropython import const # type: ignore

from ..core import ModemCore
from ..enums import (
    WalterModemState,
    WalterModemRspType,
    WalterModemSocketState,
    WalterModemSocketProto,
    WalterModemSocketAcceptAnyRemote,
    WalterModemRai,
    WalterModemCmdType
)
from ..structs import (
    ModemRsp,
    ModemSocket
)
from ..utils import (
    modem_string,
    log
)

_SOCKET_MIN_CTX_ID = const(1)
_SOCKET_MAX_CTX_ID = const(6)
_PDP_DEFAULT_CTX_ID = const(1)
_PDP_MIN_CTX_ID = const(1)
_PDP_MAX_CTX_ID = const(8)

class SocketMixin(ModemCore):
    def __init__(self, *args, **kwargs):
        if not hasattr(self, '__initialised_mixins'):
            super().__init__(*args, **kwargs)

        self._socket_list = [ModemSocket(idx + 1) for idx in range(_SOCKET_MAX_CTX_ID + 1)]
        """The list of sockets"""

        self._socket = None
        """The socket which is currently in use by the library or None when no socket is in use."""

        self.__queue_rsp_rsp_handlers = (
            self.__queue_rsp_rsp_handlers + (
                (b'+SQNSH: ', self.__handle_sh),
                (b'+SQNSCFG: ', self.__handle_sqnscfg),
            )
        )

        self.__mirror_state_reset_callables = (
            self.__mirror_state_reset_callables + (self._socket_mirror_state_reset,)
        )

        self.__initialised_mixins.append(SocketMixin)
        if len(self.__initialised_mixins) == len(self.__class__.__bases__):
            del self.__initialised_mixins
            next_base = None
        else:
            next_base: callable
            for base in self.__class__.__bases__:
                if base not in self.__initialised_mixins:
                    next_base = base
                    break

        gc.collect()
        log('INFO', 'Socket mixin loaded')
        if next_base is not None: next_base.__init__(self, *args, **kwargs)

#region PublicMethods

    # Deprecated aliases, to be removed in a later release

    async def create_socket(self, *args, **kwargs):
        """DEPRECATED; use `socket_create()` instead"""
        return await self.socket_create(*args, **kwargs)
    
    async def connect_socket(self, *args, **kwargs):
        """DEPRECATED; use `socket_connect()` instead"""
        return await self.socket_connect(*args, **kwargs)
    
    async def close_socket(self, *args, **kwargs):
        """DEPRECATED; use `socket_close()` instead"""
        return await self.socket_close(*args, **kwargs)

    # ---

    async def socket_create(self,
        pdp_context_id: int = _PDP_DEFAULT_CTX_ID,
        mtu: int = 300,
        exchange_timeout: int = 90,
        conn_timeout: int = 60,
        send_delay_ms: int = 5000,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Creates a new socket in a specified PDP context.
        Additional socket settings can be applied.
        The socket can be used for communication.

        :param pdp_context_id: The PDP context id.
        :param: mtu: The Maximum Transmission Unit used by the socket.
        :param exchange_timeout: The maximum number of seconds this socket can be inactive.
        :param conn_timeout: The maximum number of seconds this socket is allowed to try to connect.
        :param send_delay_ms: The number of milliseconds send delay.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        if pdp_context_id < _PDP_MIN_CTX_ID or pdp_context_id > _PDP_MAX_CTX_ID:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PDP_CONTEXT
            return False

        socket = None
        for _socket in self._socket_list:
            if _socket.state == WalterModemSocketState.FREE:
                _socket.state = WalterModemSocketState.RESERVED
                socket = _socket
                break

        if socket == None:
            if rsp: rsp.result = WalterModemState.NO_FREE_SOCKET
            return False

        self._socket = socket

        socket.pdp_context_id = pdp_context_id
        socket.mtu = mtu
        socket.exchange_timeout = exchange_timeout
        socket.conn_timeout = conn_timeout
        socket.send_delay_ms = send_delay_ms

        async def complete_handler(result, rsp, complete_handler_arg):
            sock = complete_handler_arg
            rsp.type = WalterModemRspType.SOCKET_ID
            rsp.socket_id = sock.id

            if result == WalterModemState.OK:
                sock.state = WalterModemSocketState.CREATED
        
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNSCFG={},{},{},{},{},{}'.format(
                socket.id, socket.pdp_context_id, socket.mtu, socket.exchange_timeout,
                socket.conn_timeout * 10, socket.send_delay_ms // 100
            ),
            at_rsp=b'OK',
            complete_handler=complete_handler,
            complete_handler_arg=socket
        )
    
    async def socket_connect(self,
        remote_host: str,
        remote_port: int,
        local_port: int = 0,
        socket_id: int = -1,
        protocol: int = WalterModemSocketProto.UDP,
        accept_any_remote: int = WalterModemSocketAcceptAnyRemote.DISABLED,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Connects a socket to a remote host,
        allowing data exchange once the connection is successful.

        :param remote_host: The remote IPv4/IPv6 or hostname to connect to.
        :param remote_port: The remote port to connect on.
        :param local_port: The local port in case of an UDP socket.
        :param socket_id: The id of the socket to connect or -1 to re-use the last one.
        :param protocol: The protocol to use, UDP by default.
        :type protocol: WalterModemSocketProto
        :param accept_any_remote: How to accept remote UDP packets.
        :type accept_any_remote: WalterModemSocketAcceptAnyRemote
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        try:
            socket = self._socket if socket_id == -1 else self._socket_list[socket_id - 1]
        except Exception:
            if rsp: rsp.result = WalterModemState.NO_SUCH_SOCKET
            return False
        
        self._socket = socket

        socket.protocol = protocol
        socket.accept_any_remote = accept_any_remote
        socket.remote_host = remote_host
        socket.remote_port = remote_port
        socket.local_port = local_port

        async def complete_handler(result, rsp, complete_handler_arg):
            sock = complete_handler_arg
            if result == WalterModemState.OK:
                sock.state = WalterModemSocketState.OPENED

        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNSD={},{},{},{},0,{},1,{},0'.format(
                socket.id, socket.protocol, socket.remote_port,
                modem_string(socket.remote_host), socket.local_port,
                socket.accept_any_remote
            ),
            at_rsp=b'OK',
            complete_handler=complete_handler,
            complete_handler_arg=socket
        )
    
    async def socket_close(self,
        socket_id: int = -1,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Closes a socket. Sockets can only be closed when suspended; 
        active connections cannot be closed.        

        :param socket_id: The id of the socket to close or -1 to re-use the last one.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        try:
            socket = self._socket if socket_id == -1 else self._socket_list[socket_id - 1]
        except Exception:
            if rsp: rsp.result = WalterModemState.NO_SUCH_SOCKET
            return False
        
        self._socket = socket

        async def complete_handler(result, rsp, complete_handler_arg):
            sock = complete_handler_arg
            if result == WalterModemState.OK:
                sock.state = WalterModemSocketState.FREE

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSH={socket.id}',
            at_rsp=b'OK',
            complete_handler=complete_handler,
            complete_handler_arg=socket
        )
    
    async def socket_send(self,
        data,
        socket_id: int = -1,
        rai: int = WalterModemRai.NO_INFO,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Sends data over a socket.

        :param data: The data to send.
        :param socket_id: The id of the socket to close or -1 to re-use the last one.
        :param rai: The release assistance information.
        :type rai: WalterModemRai
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        try:
            _socket = self._socket if socket_id == -1 else self._socket_list[socket_id - 1]
        except Exception:
            if rsp: rsp.result = WalterModemState.NO_SUCH_SOCKET
            return False
        
        self._socket = _socket

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSSENDEXT={_socket.id},{len(data)},{rai}',
            at_rsp=b'OK',
            cmd_type=WalterModemCmdType.DATA_TX_WAIT,
            data=data
        )

#endregion

#region PrivateMethods

    def _socket_mirror_state_reset(self):
        self._socket_list = [sModemSocket(idx + 1) for idx in range(_SOCKET_MAX_CTX_ID + 1)]
        self._socket = None

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
