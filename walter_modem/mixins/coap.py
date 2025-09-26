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
    modem_bool,
    modem_string,
)

#region Enums

class WalterModemCoapCloseCause(Enum):
    USER = b'USER'
    SERVER = b'SERVER'
    NAT_TIMEOUT = b'NAT_TIMEOUT'
    NETWORK = b'NETWORK'

class WalterModemCoapReqResp(Enum):
    REQUEST = 0
    RESPONSE = 1

class WalterModemCoapType(Enum):
    CON = 0
    NON = 1
    ACK = 2
    RST = 3

class WalterModemCoapMethod(Enum):
    GET = 1
    POST = 2
    PUT = 3
    DELETE = 4

class WalterModemCoapResponseCode(Enum):
    CREATED = 201
    DELETED = 202
    VALID = 203
    CHANGED = 204
    CONTENT = 205
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    BAD_OPTION = 402
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    NOT_ACCEPTABLE = 406
    PRECONDITION_FAILED = 412
    REQUEST_ENTITY_TOO_LARGE = 413
    UNSUPPORTED_MEDIA_TYPE = 415
    INERNAL_SERVER_ERROR = 500
    NOT_IMPLIMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 501
    PROXYING_NOT_SUPPORTED = 505

class WalterModemCoapOptionAction(Enum):
    SET = 0
    DELETE = 1
    READ = 2
    EXTEND = 3

class WalterModemCoapOption(Enum):
    IF_MATCH = 1
    URI_HOST = 3
    ETAG = 4
    IF_NONE_MATCH = 5
    OBSERVE = 6
    URI_PORT = 7
    LOCATION_PATH = 8
    URI_PATH = 11
    CONTENT_TYPE = 12
    MAX_AGE = 14
    URI_QUERY = 15
    ACCEPT = 17
    TOKEN = 19
    LOCATION_QUERY = 20
    BLOCK2 = 23
    BLOCK1 = 27
    SIZE2 = 28
    PROXY_URI = 35
    SIZE1 = 60

class WalterModemCoapContentType(Enum):
    TEXT_PLAIN = '0'
    TEXT_XML = '1'
    TEXT_CSV = '2'
    TEXT_HTML = '3'
    IMAGE_GIF = '21'
    IMAGE_JPEG = '22'
    IMAGE_PNG = '23'
    IMAGE_TIFF = '24'
    AUDIO_RAW = '25'
    VIDEO_RAW = '26'
    APPLICATION_LINK_FORMAT = '40'
    APPLICATION_XML = '41'
    APPLICATION_OCTET_STREAM = '42'
    APPLICATION_RDF_XML = '43'
    APPLICATION_SOAP_XML = '44'
    APPLICATION_ATOM_XML = '45'
    APPLICATION_XMPP_XML = '46'
    APPLICATION_EXI = '47'
    APPLICATION_FASTINFOSET = '48'
    APPLICATION_SOAP_FASTINFOSET = '49'
    APPLICATION_JSON = '50'
    APPLICATION_X_OBIX_BINARY = '51'
    APPLICATION_CBOR = '60'

#endregion
#region Structs

class WalterModemCoapContextState:
    def __init__(self):
        self.connected: bool = False
        self.cause: None | WalterModemCoapCloseCause = None
        self.rings: list[WalterModemCoapRing] = []

    @property
    def configured(self):
        return self.connected

class WalterModemCoapRing:
    def __init__(self, ctx_id, msg_id, req_resp, m_type, method, rsp_code, length):
        self.ctx_id: int = ctx_id
        self.msg_id: int = msg_id
        self.req_resp: WalterModemCoapReqResp = req_resp
        self.type: WalterModemCoapType = m_type
        self.method: WalterModemCoapMethod | None = method
        self.rsp_code: WalterModemCoapResponseCode | None = rsp_code
        self.length: int = length

class WalterModemCoapResponse:
    def __init__(self, ctx_id, msg_id, token, req_resp, m_type, method, rsp_code, length, payload):
        self.ctx_id: int = ctx_id
        self.msg_id: int = msg_id
        self.token: str = token
        self.req_resp: int = req_resp
        self.type: WalterModemCoapType = m_type
        self.method: WalterModemCoapMethod | None = method
        self.rsp_code: WalterModemCoapResponseCode | None = rsp_code
        self.length: int = length
        self.payload: bytearray = payload

class WalterModemCoapOption:
    def __init__(self, ctx_id, option, value):
        self.ctx_id: int = ctx_id,
        self.option: WalterModemCoapOption = option,
        self.value: str = value

#endregion
#region Constants

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

#endregion
#region MixinClass

class CoapMixin(ModemCore):
    MODEM_RSP_FIELDS = (
        ('coap_rcv_response', None),
        ('coap_options', None),
    )

    def __init__(self, *args, **kwargs):
        def init():
            self.coap_context_states = tuple(
                WalterModemCoapContextState()
                for _ in range(_COAP_MIN_CTX_ID, _COAP_MAX_CTX_ID + 1)
            )

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

        mro_chain_init(self, super(), init, CoapMixin, *args, **kwargs)

    #region PublicMethods

    async def coap_context_create(self,
        ctx_id: int,
        server_address: str = None,
        server_port: int = None,
        local_port: int = None,
        timeout: int = 20,
        dtls: bool = False,
        secure_profile_id: int = None,
        rsp: WalterModemRsp = None
    ) -> bool:
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
        rsp: WalterModemRsp = None
    ) -> bool:
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
        rsp: WalterModemRsp = None,
    ) -> bool:
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
        rsp: WalterModemRsp = None
    ) -> bool:
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
        rsp: WalterModemRsp = None,
    ) -> bool:
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
        rsp: WalterModemRsp = None
    ) -> bool:
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
        rsp: WalterModemRsp = None
    ) -> bool:
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
            WalterModemCoapContextState()
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

        self.coap_context_states[ctx_id].rings.append(WalterModemCoapRing(
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
        cmd.rsp.coap_rcv_response = WalterModemCoapResponse(
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
                cmd.rsp.coap_options = WalterModemCoapOption(
                    ctx_id=int(ctx_id_str),
                    option=int(option_str),
                    value=value
                )
    
    async def __handle_coap_rcvo(self, tx_stream, cmd, at_rsp):
        ctx_id_str, option_str, value = at_rsp[14:].decode().split(',', 2)
        coap_option = WalterModemCoapOption(
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
#endregion
