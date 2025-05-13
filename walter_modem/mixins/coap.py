from ..core import ModemCore
from ..enums import (
    WalterModemState,
    WalterModemCmdType,
    WalterModemCoapType,
    WalterModemCoapMethod,
    WalterModemCoapOption,
    WalterModemCoapOptionAction,
    WalterModemCoapContentType
)
from ..structs import (
    ModemRsp,
)
from ..utils import (
    modem_bool,
    modem_string
)

COAP_REPEATABLE_OPTIONS = (
    WalterModemCoapOption.IF_MATCH,
    WalterModemCoapOption.ETAG,
    WalterModemCoapOption.LOCATION_PATH,
    WalterModemCoapOption.URI_PATH,
    WalterModemCoapOption.URI_QUERY,
    WalterModemCoapOption.LOCATION_QUERY
)

COAP_HEADER_MAX_TOKEN_STR_LEN = 16
COAP_MIN_MSG_ID = 0
COAP_MAX_MSG_ID = 65535
COAP_RECVO_MAX_OPTS = 32
COAP_RECVO_MIN_OPTS = 0


class ModemCoap(ModemCore):
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

        if ctx_id < ModemCore.COAP_MIN_CTX_ID or ModemCore.COAP_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False

        if timeout < ModemCore.COAP_MIN_TIMEOUT or ModemCore.COAP_MAX_TIMEOUT < timeout:
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

        if ctx_id < ModemCore.COAP_MIN_CTX_ID or ModemCore.COAP_MAX_CTX_ID < ctx_id:
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

        if ctx_id < ModemCore.COAP_MIN_CTX_ID or ModemCore.COAP_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False
        
        if isinstance(value, tuple):
            if len(value) > 0 and option not in COAP_REPEATABLE_OPTIONS:
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

        if ctx_id < ModemCore.COAP_MIN_CTX_ID or ModemCore.COAP_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False
        
        if msg_id != None and (msg_id < COAP_MIN_MSG_ID or COAP_MAX_MSG_ID < msg_id):
            if rsp: rsp.result = WalterModemState.ERROR
            return False
        
        if token != None:
            if COAP_HEADER_MAX_TOKEN_STR_LEN < len(token):
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

        if ctx_id < ModemCore.COAP_MIN_CTX_ID or ModemCore.COAP_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        elif data is not None and not isinstance(data, (bytes, bytearray)):
            if rsp: rsp.result = WalterModemState.ERROR
            return False
        
        if length is None:
            length = 0 if data is None else len(data)
        
        if length < ModemCore.COAP_MIN_BYTES_LENGTH or ModemCore.COAP_MAX_BYTES_LENGTH < length:
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

        if ctx_id < ModemCore.COAP_MIN_CTX_ID or ModemCore.COAP_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False

        if max_bytes < ModemCore.COAP_MIN_BYTES_LENGTH or ModemCore.COAP_MAX_BYTES_LENGTH < max_bytes:
            if rsp: rsp.result = WalterModemState.ERROR
            return False
        
        if length < 0:
            if rsp: rsp.result = WalterModemState.ERROR
            return False
        
        self._parser_data.raw_chunk_size = min(length, max_bytes)
        
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

        if ctx_id < ModemCore.COAP_MIN_CTX_ID or ModemCore.COAP_MAX_CTX_ID < ctx_id:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False
        
        if max_options < COAP_RECVO_MIN_OPTS or COAP_RECVO_MAX_OPTS < max_options:
            if rsp: rsp.result = WalterModemState.ERROR
            return False
        
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNCOAPRCVO={ctx_id},{msg_id},{max_options}',
            at_rsp=b'OK'
        )
