from micropython import const # type: ignore

from ..core import ModemCore
from ..coreEnums import (
    Enum,
    WalterModemRspType,
    WalterModemCmdType,
    WalterModemState
)
from ..coreStructs import (
    ModemRsp
)
from ..utils import (
    mro_chain_init,
    modem_bool,
    modem_string
)

#region Enums

class WalterModemHttpContextState(Enum):
    IDLE = 0
    EXPECT_RING = 1
    GOT_RING = 2

class WalterModemHttpQueryCmd(Enum):
    GET = 0
    HEAD = 1
    DELETE = 2

class WalterModemHttpSendCmd(Enum):
    POST = 0
    PUT = 1

class WalterModemHttpPostParam(Enum):
    URL_ENCODED = 0
    TEXT_PLAIN = 1
    OCTET_STREAM = 2
    FORM_DATA = 3
    JSON = 4
    UNSPECIFIED = 99

#endregion
#region Structs

class ModemHttpResponse:
    def __init__(self):
        self.http_status = 0
        self.content_length = 0
        self.data = b''
        self.content_type = ''

class ModemHttpContext:
    def __init__(self):
        self.connected = False
        self.state = WalterModemHttpContextState.IDLE
        self.http_status = 0
        self.content_length = 0
        self.content_type = ''

#endregion
#region Constants

_HTTP_MIN_CTX_ID = const(0)
_HTTP_MAX_CTX_ID = const(2)
_TLS_MIN_CTX_ID = const(1)
_TLS_MAX_CTX_ID = const(6)

#endregion
#region MixinClass

class HTTPMixin(ModemCore):
    MODEM_RSP_FIELDS = (
        ('http_response', None),
    )

    def __init__(self, *args, **kwargs):
        def init():
            self._http_context_list = [ModemHttpContext() for _ in range(_HTTP_MAX_CTX_ID + 1)]
            """The list of http contexts in the modem"""

            self._http_current_profile = 0xff
            """Current http profile in use in the modem"""

            self.__queue_rsp_rsp_handlers = (
                self.__queue_rsp_rsp_handlers + (
                    (b'<<<', self.__handle_http_rcv_answer_start),
                    (b'+SQNHTTPRING: ', self.__handle_http_ring),
                    (b'+SQNHTTPCONNECT: ', self.__handle_http_connect),
                    (b'+SQNHTTPDISCONNECT: ', self.__handle_http_disconnect),
                    (b'+SQNHTTPSH: ', self.__handle_http_sh),
                )
            )

            self.__mirror_state_reset_callables = (
                self.__mirror_state_reset_callables + (self._http_mirror_state_reset,)
            )
        
        mro_chain_init(self, super(), init, HTTPMixin, *args, **kwargs)
    
    #region PublicMethods

    async def http_did_ring(self, profile_id: int, rsp: ModemRsp = None
    ) -> bool:
        if self._http_current_profile != 0xff:
            if rsp: rsp.result = WalterModemState.ERROR
            return False

        if profile_id > _HTTP_MAX_CTX_ID:
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

            rsp.type = WalterModemRspType.HTTP
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
        if profile_id > _HTTP_MAX_CTX_ID or profile_id < 0:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False

        if tls_profile_id and tls_profile_id > _TLS_MAX_CTX_ID:
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
        if profile_id > _HTTP_MAX_CTX_ID:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNHTTPCONNECT={profile_id}',
            at_rsp=b'OK'
        )

    async def http_close(self, profile_id: int, rsp: ModemRsp = None) -> bool:
        if profile_id > _HTTP_MAX_CTX_ID:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PROFILE
            return False

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'T+SQNHTTPDISCONNECT={profile_id}',
            at_rsp=b'OK'
        )

    def http_get_context_status(self, profile_id: int, rsp: ModemRsp = None) -> bool:
        if profile_id > _HTTP_MAX_CTX_ID:
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
        if profile_id > _HTTP_MAX_CTX_ID:
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
        if profile_id > _HTTP_MAX_CTX_ID:
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
                cmd_type=WalterModemCmdType.DATA_TX_WAIT,
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
                cmd_type=WalterModemCmdType.DATA_TX_WAIT,
                complete_handler=complete_handler,
                complete_handler_arg=self._http_context_list[profile_id]
            )

    #endregion
    #region PrivateMethods

    def _http_mirror_state_reset(self):
        self._http_context_list = [ModemHttpContext() for _ in range(_HTTP_MAX_CTX_ID + 1)]
        self._http_current_profile = 0xff

    #endregion
    #region QueueResponseHandlers

    async def __handle_http_rcv_answer_start(self, tx_stream, cmd, at_rsp):
        if self._http_current_profile > _HTTP_MAX_CTX_ID or self._http_context_list[self._http_current_profile].state != WalterModemHttpContextState.GOT_RING:
            return WalterModemState.ERROR
        else:
            if not cmd:
                return

            cmd.rsp.type = WalterModemRspType.HTTP
            cmd.rsp.http_response = ModemHttpResponse()
            cmd.rsp.http_response.http_status = self._http_context_list[self._http_current_profile].http_status
            cmd.rsp.http_response.data = at_rsp[3:-len(b'\r\nOK\r\n')] # 3 skips: <<<
            cmd.rsp.http_response.content_type = self._http_context_list[self._http_current_profile].content_type
            cmd.rsp.http_response.content_length = self._http_context_list[self._http_current_profile].content_length

            # the complete handler will reset the state,
            # even if we never received <<< but got an error instead
            return WalterModemState.OK

    async def __handle_http_ring(self, tx_stream, cmd, at_rsp):
        profile_id_str, http_status_str, content_type, content_length_str = at_rsp[len("+SQNHTTPRING: "):].decode().split(',')
        profile_id = int(profile_id_str)
        http_status = int(http_status_str)
        content_length = int(content_length_str)

        if profile_id > _HTTP_MAX_CTX_ID:
            # TODO: return error if modem returns invalid profile id.
            # problem: this message is an URC: the associated cmd
            # may be any random command currently executing */
            return

        # TODO: if not expecting a ring, it may be a bug in the modem
        # or at our side and we should report an error + read the
        # content to free the modem buffer
        # (knowing that this is a URC so there is no command
        # to give feedback to)
        if self._http_context_list[profile_id].state != WalterModemHttpContextState.EXPECT_RING:
            return

        # remember ring info
        self._http_context_list[profile_id].state = WalterModemHttpContextState.GOT_RING
        self._http_context_list[profile_id].http_status = http_status
        self._http_context_list[profile_id].content_type = content_type
        self._http_context_list[profile_id].content_length = content_length

        return WalterModemState.OK

    async def __handle_http_connect(self, tx_stream, cmd, at_rsp):
        profile_id_str, result_code_str = at_rsp[len("+SQNHTTPCONNECT: "):].decode().split(',')
        profile_id = int(profile_id_str)
        result_code = int(result_code_str)

        if profile_id <= _HTTP_MAX_CTX_ID:
            if result_code == 0:
                self._http_context_list[profile_id].connected = True
            else:
                self._http_context_list[profile_id].connected = False
        
        return WalterModemState.OK

    async def __handle_http_disconnect(self, tx_stream, cmd, at_rsp):
        profile_id = int(at_rsp[len("+SQNHTTPDISCONNECT: "):].decode())

        if profile_id <= _HTTP_MAX_CTX_ID:
            self._http_context_list[profile_id].connected = False
        
        return WalterModemState.OK

    async def __handle_http_sh(self, tx_stream, cmd, at_rsp):
        profile_id_str, _ = at_rsp[len('+SQNHTTPSH: '):].decode().split(',')
        profile_id = int(profile_id_str)

        if profile_id <= _HTTP_MAX_CTX_ID:
            self._http_context_list[profile_id].connected = False

        return WalterModemState.OK

    #endregion
#endregion
