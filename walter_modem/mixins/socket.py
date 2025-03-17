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
)
from ..utils import (
    modem_string
)

class ModemSocket(ModemCore):
    async def create_socket(self,
        pdp_context_id: int = -1,
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

        :param pdp_context_id: The PDP context id or -1 to re-use the last one.
        :param: mtu: The Maximum Transmission Unit used by the socket.
        :param exchange_timeout: The maximum number of seconds this socket can be inactive.
        :param conn_timeout: The maximum number of seconds this socket is allowed to try to connect.
        :param send_delay_ms: The number of milliseconds send delay.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        try:
            if pdp_context_id == -1:
                ctx = self._pdp_ctx
            else:
                ctx = self._pdp_ctx_list[pdp_context_id - 1]
        except Exception:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PDP_CONTEXT
            return False
        
        self._pdp_ctx = ctx

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

        socket.pdp_context_id = ctx.id
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
                socket.id, ctx.id, socket.mtu, socket.exchange_timeout,
                socket.conn_timeout * 10, socket.send_delay_ms // 100
            ),
            at_rsp=b'OK',
            complete_handler=complete_handler,
            complete_handler_arg=socket
        )

    async def config_socket(self, socket_id = -1, rsp: ModemRsp = None) -> bool:
        """
        Configures a newly created socket to ensure the modem is correctly set up to use it.

        :param socket_id: The id of the socket to connect or -1 to re-use the last one.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        try:
            if socket_id == -1:
                socket = self._socket
            else:
                socket = self._socket_list[socket_id - 1]
        except Exception:
            if rsp: rsp.result = WalterModemState.NO_SUCH_SOCKET
            return False
        
        self._socket = socket

        async def complete_handler(result, rsp, complete_handler_arg):
            sock = complete_handler_arg

            if result == WalterModemState.OK:
                sock.state = WalterModemSocketState.CONFIGURED

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSCFGEXT={socket_id},2,0,0,0,0,0',
            at_rsp=b'OK',
            complete_handler=complete_handler,
            complete_handler_arg=socket
        )
    
    async def connect_socket(self,
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
        :type protocol: ModemSocketProto
        :param accept_any_remote: How to accept remote UDP packets.
        :type accept_any_remote: ModemSocketAcceptAnyRemote
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

    
    async def close_socket(self, socket_id: int = -1, rsp: ModemRsp = None) -> bool:
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
        :type rai: ModemRai
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