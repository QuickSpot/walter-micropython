import gc
from micropython import const # type: ignore

from ..core import ModemCore
from ..enums import (
    WalterModemState,
    WalterModemCmdType,
    WalterModemCoapType,
    WalterModemCoapMethod,
    WalterModemCoapOption,
    WalterModemCoapOptionAction,
    WalterModemCoapContentType,
    WalterModemCoapReqResp,
    WalterModemRspType
)
from ..structs import (
    ModemRsp,
    ModemCoapContextState,
    ModemCoapRing,
    ModemCoapResponse,
    ModemCoapOption
)
from ..utils import (
    modem_bool,
    modem_string,
    log
)

_COAP_MIN_CTX_ID = const(0)
_COAP_MAX_CTX_ID = const(2)
_COAP_MIN_MSG_ID = const(0)
_COAP_MAX_MSG_ID = const(65535)
_COAP_MIN_TIMEOUT = const(1)
_COAP_MAX_TIMEOUT = const(120)
_COAP_MIN_BYTES_LEN = const(0)
_COAP_MAX_BYTES_LEN = const(1024)
_COAP_RECV_OPT_MIN_OPTS = const(0)
_COAP_RECV_OPT_MAX_OPTS = const(32)
_COAP_HEADER_MAX_TOKEN_STR_LEN = const(16)

_COAP_REPEATABLE_OPTIONS = (
    WalterModemCoapOption.IF_MATCH,
    WalterModemCoapOption.ETAG,
    WalterModemCoapOption.LOCATION_PATH,
    WalterModemCoapOption.URI_PATH,
    WalterModemCoapOption.URI_QUERY,
    WalterModemCoapOption.LOCATION_QUERY
)

class ModemCoap(ModemCore):
    def __init__(self, *args, **kwargs):
        if not hasattr(self, '__initialised_mixins'):
            super().__init__(*args, **kwargs)

        self.coap_context_states = tuple(
            ModemCoapContextState()
            for _ in range(_COAP_MIN_CTX_ID, _COAP_MAX_CTX_ID + 1)
        )
        """
        State information about the CoAP contexts.
        The tuple index maps to the context ID.
        """

        self.__queue_rsp_rsp_handlers = (
            self.__queue_rsp_rsp_handlers + (
                (b'+SQNCOAPCLOSED: ', self.__handle_coap_closed),
                (b'+SQNCOAP: ERROR', self.__handle_coap_error),
                (b'+SQNCOAPRING:', self.__handle_coap_ring),
                (b'+SQNCOAPRCV: ', self.__handle_coap_rcv),
                (b'+SQNCOAPCREATE: ', self.__handle_coap_create),
                (b'+SQNCOAPOPT: ', self.__handle_coap_options),
                (b'+SQNCOAPRCVO: ', self.__handle_coap_rcvo),
            )
        )

        self.__deep_sleep_wakeup_callables = (
            self.__deep_sleep_wakeup_callables + (self.__coap_deep_sleep_wakeup,)
        )

        self.__mirror_state_reset_callables = (
            self.__mirror_state_reset_callables + (self._coap_mirror_state_reset,)
        )

        self.__initialised_mixins.append(ModemCoap)
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
        log('INFO', 'Coap mixin loaded')
        if next_base is not None: next_base.__init__(self, *args, **kwargs)

#region PublicMethods

    async def coap_context_create(self,
        ctx_id: int,
        server_address: str = None,
        server_port: int = None,
        local_port: int = None,
        timeout: int = 20,
        dtls: bool = False,
        secure_profile_id: int = None,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Create a CoAP context, required to send, receive & set CoAP options.

        If the server_address & server_port are provided, a connection attempt is made.

        If server_address & server_port are omitted and only local_port is provided,
        the context is created in listen mode, waiting for an incoming connection.

        :param ctx_id: Context profile identifier (0, 1, 2)
        :param server_address: IP addr/hostname of the CoAP server.
        :param server_port: The UDP remote port of the CoAP server;
        :param local_port: The UDP local port, if omitted, a randomly available port is assigned
        (recommended)
        :param timeout: The time (in seconds) to wait for a response from the CoAP server
        before aborting: 1-120. (independent of the ACK_TIMEOUT used for retransmission)
        :param dtls: Whether or not to use DTLS encryption
        :param secure_profile_id: The SSL/TLS security profile configuration (ID) to use.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

        if ctx_id < _COAP_MIN_CTX_ID or _COAP_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False

        if timeout < _COAP_MIN_TIMEOUT or _COAP_MAX_TIMEOUT < timeout:
            if rsp: rsp.result = WalterModemState.ERROR
            return False

        async def complete_handler(result, rsp, complete_handler_arg):
            if result == WalterModemState.OK:
                self.coap_context_states[complete_handler_arg].connected = True

        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNCOAPCREATE={},{},{},{},{},{}{}'.format(
                ctx_id,
                modem_string(server_address) if server_address else '',
                server_port if server_port else '',
                local_port if local_port else '',
                modem_bool(dtls),
                timeout,
                f',,{secure_profile_id}' if secure_profile_id else ''
            ),
            at_rsp=(b'+SQNCOAPCONNECTED:', b'+SQNCOAP: ERROR'),
            complete_handler=complete_handler,
            complete_handler_arg=ctx_id
        )

    async def coap_context_close(self,
        ctx_id: int,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Close a CoAP context.

        :param ctx_id: Context profile identifier (0, 1, 2)
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

        if ctx_id < _COAP_MIN_CTX_ID or _COAP_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNCOAPCLOSE={ctx_id}',
            at_rsp=b'OK'
        )

    async def coap_set_options(self,
        ctx_id: int,
        action: WalterModemCoapOptionAction,
        option: WalterModemCoapOption,
        value: str | WalterModemCoapContentType | tuple[str] = None,
        rsp: ModemRsp = None,
    ) -> bool:
        """
        Configure CoAP options for the next message to be sent.
        Options are to be configured one at a time.
        For repeatable options, up to 6 values can be provided (the order is respected).
        The repeatable options are:
        IF_MATCH, ETAG, LOCATION_PATH, LOCATION_PATH, URI_PATH, URI_QUERY, LOCATION_QUERY

        The values are to be passed along as extra params.

        :param ctx_id: Context profile identifier (0, 1, 2)
        :param action: Action to perform
        :type action: WalterModemCoapOptionAction
        :param option: The option to perform the action on
        :type option: WalterModemCoapOption
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

        if ctx_id < _COAP_MIN_CTX_ID or _COAP_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False
        
        if isinstance(value, tuple):
            if len(value) > 0 and option not in _COAP_REPEATABLE_OPTIONS:
                if rsp: rsp.result = WalterModemState.ERROR
                return False

            if len(value) > 6:
                if rsp: rsp.result = WalterModemState.ERROR
                return False

            value = ','.join(modem_string(v) for v in value)
        else:
            value = modem_string(value)
        
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNCOAPOPT={},{},{}{}'.format(
                ctx_id, action, option,
                f',{value}' if value != None else ''
            ),
            at_rsp=b'OK'
        )
    
    async def coap_set_header(self,
        ctx_id: int,
        msg_id: int = None,
        token: str = None,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Configure the coap header for the next message to be sent

        If only msg_id is set, the CoAP client sets a random token value.
        If only token is set, the CoAP client sets a random msg_id value.

        :param ctx_id: Context profile identifier (0, 1, 2)
        :param msg_id: Message ID of the CoAP header (0-65535)
        :param token: hexidecimal format, token to be used in the CoAP header,
        specify: "NO_TOKEN" for a header without token.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

        if ctx_id < _COAP_MIN_CTX_ID or _COAP_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False
        
        if msg_id != None and (msg_id < _COAP_MIN_MSG_ID or _COAP_MAX_MSG_ID < msg_id):
            if rsp: rsp.result = WalterModemState.ERROR
            return False
        
        if token != None:
            if _COAP_HEADER_MAX_TOKEN_STR_LEN < len(token):
                if rsp: rsp.result = WalterModemState.ERROR
                return False
            
            if token != 'NO_TOKEN':
                try:
                    int(token, 16)
                except ValueError:
                    if rsp: rsp.result = WalterModemState.ERROR
                    return False
        
        await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNCOAPHDR={ctx_id},{msg_id},{modem_string(token) if token != None else ''}',
            at_rsp=b'OK'
        )
    
    async def coap_send(self,
        ctx_id: int,
        m_type: WalterModemCoapType,
        method: WalterModemCoapMethod,
        data: bytes | bytearray | str | None = None,
        length: int = None,
        path: str = None,
        content_type: WalterModemCoapContentType = None,
        rsp: ModemRsp = None,
    ) -> bool:
        """
        Send data over CoAP, if no data is sent, length must be set to zero.

        :param ctx_id: Context profile identifier (0, 1, 2)
        :param m_type: CoAP message type
        :type m_type: WalterModemCoapType
        :param method: method (GET, POST, PUT, DELETE)
        :type method: WalterModemCoapMethod
        :param data: Binary data to send (bytes, bytearray) or string (will be UTF-8 encoded)
        :param length: Length of the payload (optional, auto-calculated if not provided)
        :param path: Optional, the URI_PATH to send on,
        this will set the path in the CoAP options before sending
        :param content_type: Optional, the content_type,
        this will set the content type in the CoAP options before sending
        :type content_type: WalterModemCoapContentType
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

        if ctx_id < _COAP_MIN_CTX_ID or _COAP_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        elif data is not None and not isinstance(data, (bytes, bytearray)):
            if rsp: rsp.result = WalterModemState.ERROR
            return False
        
        if length is None:
            length = 0 if data is None else len(data)
        
        if length < _COAP_MIN_BYTES_LEN or _COAP_MAX_BYTES_LEN < length:
            if rsp: rsp.result = WalterModemState.ERROR
            return False
        
        if path is not None:
            path_parts = path.strip('/').split('/')

            while len(path_parts) > 0:
                if not await self.coap_set_options(
                    ctx_id=ctx_id,
                    action=WalterModemCoapOptionAction.SET,
                    option=WalterModemCoapOption.URI_PATH,
                    value=tuple(path_parts[:6]),
                    rsp=rsp
                ):
                    return False
                path_parts[:6] = []
        
        if isinstance(content_type, WalterModemCoapContentType):
            if not await self.coap_set_options(
                ctx_id=ctx_id,
                action=WalterModemCoapOptionAction.SET,
                option=WalterModemCoapOption.CONTENT_TYPE,
                value=content_type,
                rsp=rsp
            ):
                return False
        
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNCOAPSEND={ctx_id},{m_type},{method},{length}',
            at_rsp=b'OK',
            data=data,
            cmd_type=WalterModemCmdType.DATA_TX_WAIT
        )
    
    async def coap_receive_data(self,
        ctx_id: int,
        msg_id: int,
        length: int,
        max_bytes = 1024,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Read the contents of a CoAP message after it's ring has been received.

        :param ctx_id: Context profile identifier (0, 1, 2)
        :param msg_id: CoAP message id
        :param length: The length of the payload to receive (the length of the ring)
        :param max_bytes: How many bytes of the message to payload to read at once
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

        if ctx_id < _COAP_MIN_CTX_ID or _COAP_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False

        if max_bytes < _COAP_MIN_BYTES_LEN or _COAP_MAX_BYTES_LEN < max_bytes:
            if rsp: rsp.result = WalterModemState.ERROR
            return False
        
        if length < 0:
            if rsp: rsp.result = WalterModemState.ERROR
            return False
        
        self.__parser_data.raw_chunk_size = min(length, max_bytes)
        
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNCOAPRCV={ctx_id},{msg_id},{max_bytes}',
            at_rsp=b'OK'
        )
    
    async def coap_receive_options(self,
        ctx_id: int,
        msg_id: int,
        max_options = 32,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Read the options of a CoAP message after it's ring has been received.

        :param ctx_id: Context profile identifier (0, 1, 2)
        :param msg_id: CoAP message id
        :param max_options: The maximum options that can be shown in the response (0-32)
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure     
        """

        if ctx_id < _COAP_MIN_CTX_ID or _COAP_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False
        
        if max_options < _COAP_RECV_OPT_MIN_OPTS or _COAP_RECV_OPT_MAX_OPTS < max_options:
            if rsp: rsp.result = WalterModemState.ERROR
            return False
        
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNCOAPRCVO={ctx_id},{msg_id},{max_options}',
            at_rsp=b'OK'
        )
#endregion

#region PrivateMethods

    def _coap_mirror_state_reset(self):
        self.coap_context_states = tuple(
            ModemCoapContextState()
            for _ in range(_COAP_MIN_CTX_ID, _COAP_MAX_CTX_ID + 1)
        )

#endregion

#region QueueResponseHandlers

    async def __handle_coap_closed(self, tx_stream, cmd, at_rsp):
        ctx_id, cause = at_rsp.split(b': ')[1].split(b',')
        ctx_id = int(ctx_id.decode())
        
        self.coap_context_states[ctx_id].connected = False
        self.coap_context_states[ctx_id].cause = bytes(cause).strip(b'"')

        return WalterModemState.OK
    
    async def __handle_coap_error(self, tx_stream, cmd, at_rsp):
        return WalterModemState.ERROR
    
    async def __handle_coap_ring(self, tx_stream, cmd, at_rsp):
        parts = at_rsp.split(b': ')[1].split(b',')
        ctx_id, msg_id, req_resp, m_type, method_or_rsp_code, length = [int(p.decode()) for p in parts]

        self.coap_context_states[ctx_id].rings.append(ModemCoapRing(
            ctx_id=ctx_id,
            msg_id=msg_id,
            req_resp=req_resp,
            m_type=m_type,
            method=method_or_rsp_code if req_resp == WalterModemCoapReqResp.REQUEST else None,
            rsp_code=method_or_rsp_code if req_resp == WalterModemCoapReqResp.RESPONSE else None,
            length=length
        ))

        return WalterModemState.OK
    
    async def __handle_coap_rcv(self, tx_stream, cmd, at_rsp):
        header, payload = at_rsp.split(b': ')[1].split(b'\r')
        header = header.split(b',')

        ctx_id, msg_id = int(header[0].decode()), int(header[1].decode())
        token = header[2].decode()
        req_resp, m_type, method_or_rsp_code, length = [int(p.decode()) for p in header[3:]]

        cmd.rsp.type = WalterModemRspType.COAP
        cmd.rsp.coap_rcv_response = ModemCoapResponse(
            ctx_id=ctx_id,
            msg_id=msg_id,
            token=token,
            req_resp=req_resp,
            m_type=m_type,
            method=method_or_rsp_code if req_resp == WalterModemCoapReqResp.REQUEST else None,
            rsp_code=method_or_rsp_code if req_resp == WalterModemCoapReqResp.RESPONSE else None,
            length=length,
            payload=payload
        )

        return WalterModemState.OK
    
    async def __handle_coap_create(self, tx_stream, cmd, at_rsp):
        if (ctx_info := at_rsp.split(b': ')[1]) and b',' in ctx_info:
            ctx_id = int(ctx_info.split(b',')[0].decode())
            self.coap_context_states[ctx_id].connected = True
        else:
            ctx_id = int(ctx_info.decode())
            self.coap_context_states[ctx_id].connected = False

    async def __handle_coap_options(self, tx_stream, cmd, at_rsp):
        if cmd and cmd.at_cmd:
            if (cmd.at_cmd.startswith('AT+SQNCOAPOPT=')
            and cmd.at_cmd.split('=')[1].split(',')[1] == '2'):
                ctx_id_str, option_str, value = at_rsp[13:].decode().split(',', 2)
                cmd.rsp.coap_options = ModemCoapOption(
                    ctx_id=int(ctx_id_str),
                    option=int(option_str),
                    value=value
                )
    
    async def __handle_coap_rcvo(self, tx_stream, cmd, at_rsp):
        ctx_id_str, option_str, value = at_rsp[14:].decode().split(',', 2)
        coap_option = ModemCoapOption(
            ctx_id=int(ctx_id_str),
            option=int(option_str),
            value=value
        )
        if isinstance(cmd.rsp.coap_options, list):
            cmd.rsp.coap_options.append(coap_option)
        else:
            cmd.rsp.coap_options = [coap_option]

#endregion

#region Sleep

    async def __coap_deep_sleep_wakeup(self):
        await self._run_cmd(at_cmd='AT+SQNCOAPCREATE?', at_rsp=b'OK')

#endregion