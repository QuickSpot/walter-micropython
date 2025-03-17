from ..core import ModemCore
from ..enums import (
    WalterModemState,
    WalterModemHttpContextState,
    WalterModemHttpQueryCmd,
    WalterModemHttpSendCmd,
    WalterModemHttpPostParam,
    WalterModemRspType
)
from ..structs import (
    ModemRsp,
    ModemHttpResponse
)
from ..utils import (
    modem_bool,
    modem_string
)

class ModemHTTP(ModemCore):
    async def http_did_ring(self, profile_id: int, rsp: ModemRsp = None
    ) -> bool:
        """
        Fetch http response to earlier http request, if any.

        :param profile_id: Profile for which to get response
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        if self._http_current_profile != 0xff:
            if rsp: rsp.result = WalterModemState.ERROR
            return False

        if profile_id >= ModemCore.WALTER_MODEM_MAX_HTTP_PROFILES:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False

        if self._http_context_list[profile_id].state == WalterModemHttpContextState.IDLE:
            if rsp: rsp.result = WalterModemState.NOT_EXPECTING_RING
            return False

        if self._http_context_list[profile_id].state == WalterModemHttpContextState.EXPECT_RING:
            if rsp: rsp.result = WalterModemState.AWAITING_RING
            return False

        if self._http_context_list[profile_id].state != WalterModemHttpContextState.GOT_RING:
            if rsp: rsp.result = WalterModemState.ERROR
            return False

        # ok, got ring. http context fields have been filled.
        # http status 0 means: timeout (or also disconnected apparently)
        if self._http_context_list[profile_id].http_status == 0:
            self._http_context_list[profile_id].state = WalterModemHttpContextState.IDLE
            if rsp: rsp.result = WalterModemState.ERROR
            return False
        
        if self._http_context_list[profile_id].content_length == 0:
            self._http_context_list[profile_id].state = WalterModemHttpContextState.IDLE

            rsp.type = WalterModemRspType.HTTP_RESPONSE
            rsp.http_response = ModemHttpResponse()
            rsp.http_response.http_status = self._http_context_list[profile_id].http_status
            rsp.http_response.content_length = 0
            rsp.result = WalterModemState.NO_DATA
            return True

        self._http_current_profile = profile_id

        async def complete_handler(result, rsp, complete_handler_arg):
            modem = complete_handler_arg
            modem._http_context_list[modem._http_current_profile].state = WalterModemHttpContextState.IDLE
            modem._http_current_profile = 0xff

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f"AT+SQNHTTPRCV={profile_id}",
            at_rsp=b"<<<",
            complete_handler=complete_handler,
            complete_handler_arg=self
        )

    async def http_config_profile(self,
        profile_id: int,
        server_address: str,
        port: int = 80,
        use_basic_auth: bool = False,
        auth_user: str = '',
        auth_pass: str = '',
        tls_profile_id: int = None,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Configures an HTTP profile. The profile is stored persistently in the modem, 
        allowing reuse without needing to reset parameters in future sketches. 
        TLS and file uploads/downloads are not supported.

        :param profile_id: HTTP profile id (0, 1 or 2)
        :param server_address: The server name to connect to.
        :param port: The port of the server to connect to.
        :param use_basic_auth: Set true to use basic auth and send username/pw.
        :param auth_user: Username.
        :param auth_pass: Password.
        :param tls_profile_id: If not 0, TLS is used with the given profile.
        :type tls_profile_id: ModemTlsValidation
        :PARAM
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        if profile_id >= ModemCore.WALTER_MODEM_MAX_HTTP_PROFILES or profile_id < 0:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False

        if tls_profile_id and tls_profile_id > ModemCore.WALTER_MODEM_MAX_TLS_PROFILES:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False

        cmd = 'AT+SQNHTTPCFG={},"{}",{},{},"{}","{}"'.format(
            profile_id, server_address, port, modem_bool(use_basic_auth),
            auth_user, auth_pass
        )

        if tls_profile_id:
            cmd += ',1,,,{}'.format(tls_profile_id)

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=cmd,
            at_rsp=b'OK'
        )
    
    async def http_connect(self, profile_id: int, rsp: ModemRsp = None) -> bool:
        """
        Makes an HTTP connection using a predefined profile.
        This command is buggy and returns OK  while the connection is being 
        established in the background. 
        Poll http_get_context_status to check when the connection is ready.

        :param profile_id: HTTP profile id (0, 1 or 2)
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        if profile_id >= ModemCore.WALTER_MODEM_MAX_HTTP_PROFILES:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNHTTPCONNECT={profile_id}',
            at_rsp=b'OK'
        )

    async def http_close(self, profile_id: int, rsp: ModemRsp = None) -> bool:
        """
        Closes the HTTP connection for the given context.

        :param profile_id: HTTP profile id (0, 1 or 2)
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        if profile_id >= ModemCore.WALTER_MODEM_MAX_HTTP_PROFILES:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'T+SQNHTTPDISCONNECT={profile_id}',
            at_rsp=b'OK'
        )

    def http_get_context_status(self, profile_id: int, rsp: ModemRsp = None) -> bool:
        """
        Gets the connection status of an HTTP context.
        Avoid connect and disconnect operations if possible (see implementation comments).

        :param profile_id: HTTP profile id (0, 1 or 2)
        :param rsp: Reference to a modem response instance

        :return bool:
        """
        if profile_id >= ModemCore.WALTER_MODEM_MAX_HTTP_PROFILES:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False

        # note: in my observation the SQNHTTPCONNECT command is to be avoided.
        # if the connection is closed by the server, you will not even
        # receive a +SQNHTTPSH disconnected message (you will on the next
        # connect attempt). reconnect will be impossible even if you try
        # to manually disconnect.
        # and a SQNHTTPQRY will still work and create its own implicit connection.
        #
        # (too bad: according to the docs SQNHTTPCONNECT is mandatory for
        # TLS connections)

        return self._http_context_list[profile_id].connected
    
    async def http_query(self,
        profile_id: int,
        uri: str,
        query_cmd: int = WalterModemHttpQueryCmd.GET,
        extra_header_line: str = None,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Performs an HTTP GET, DELETE, or HEAD request.
        No need to open the connection with the buggy `http_connect` command
        unless TLS and a private key are required.

        :param profile_id: HTTP profile id (0, 1 or 2)
        :param uri: The URI
        :param query_cmd: The http request method (get, delete or head)
        :type query_cmd: ModemHttpQueryCmd
        :extra_header_line: additional lines to be placed in the request's header
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        if profile_id >= ModemCore.WALTER_MODEM_MAX_HTTP_PROFILES:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False

        if self._http_context_list[profile_id].state != WalterModemHttpContextState.IDLE:
            if rsp: rsp.result = WalterModemState.BUSY
            return False

        async def complete_handler(result, rsp, complete_handler_arg):
            ctx = complete_handler_arg

            if result == WalterModemState.OK:
                ctx.state = WalterModemHttpContextState.EXPECT_RING

        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNHTTPQRY={},{},{}{}'.format(
                profile_id, query_cmd, modem_string(uri),
                f',"{extra_header_line}"' if extra_header_line else ''
            ),
            at_rsp=b'OK',
            complete_handler=complete_handler,
            complete_handler_arg=self._http_context_list[profile_id]
        )
    
    async def http_send(self,
        profile_id: int,
        uri: str,
        data,
        send_cmd = WalterModemHttpSendCmd.POST,
        post_param = WalterModemHttpPostParam.UNSPECIFIED,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Performs an HTTP POST or PUT request.
        No need to open the connection with the buggy `http_connect` command
        unless TLS and a private key are required.

        :param profile_id: HTTP profile id (0, 1 or 2)
        :param uri: The URI
        :param data: Data to be sent to the server
        :param send_cmd: The http request method (post, put)
        :type send_cmd: ModemHttpSendCmd
        :param post_param: content type
        :type post_param: ModemHttpPostParam
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        if profile_id >= ModemCore.WALTER_MODEM_MAX_HTTP_PROFILES:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False

        if self._http_context_list[profile_id].state != WalterModemHttpContextState.IDLE:
            if rsp: rsp.result = WalterModemState.BUSY
            return False

        async def complete_handler(result, rsp, complete_handler_arg):
            ctx = complete_handler_arg

            if result == WalterModemState.OK:
                ctx.state = WalterModemHttpContextState.EXPECT_RING

        if post_param == WalterModemHttpPostParam.UNSPECIFIED:
            return await self._run_cmd(
                rsp=rsp,
                at_cmd='AT+SQNHTTPSND={},{},{},{}'.format(
                    profile_id, send_cmd, modem_string(uri), len(data)
                ),
                at_rsp=b'OK',
                data=data,
                complete_handler=complete_handler,
                complete_handler_arg=self._http_context_list[profile_id]
            )
        else:
            return await self._run_cmd(
                rsp=rsp,
                at_cmd='AT+SQNHTTPSND={},{},{},{},\"{}\"'.format(
                    profile_id, send_cmd, modem_string(uri), len(data), post_param
                ),
                at_rsp=b'OK',
                data=data,
                complete_handler=complete_handler,
                complete_handler_arg=self._http_context_list[profile_id]
            )