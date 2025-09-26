from micropython import const # type: ignore

from ..core import ModemCore
from ..coreEnums import (
    Enum,
    WalterModemState,
    WalterModemRspType
)
from ..coreStructs import (
    WalterModemRsp
)
from ..utils import (
    mro_chain_init,
    modem_string,
    modem_bool
)

#region Enums

class WalterModemPDPType(Enum):
    X25 = '"X.25"'
    IP = '"IP"'
    IPV6 = '"IPV6"'
    IPV4V6 = '"IPV4V6"'
    OSPIH = '"OPSIH"'
    PPP = '"PPP"'
    NON_IP = '"Non-IP"'

class WalterModemPDPHeaderCompression(Enum):
    OFF = 0
    ON = 1
    RFC1144 = 2
    RFC2507 = 3
    RFC3095 = 4
    UNSPEC = 99

class WalterModemPDPDataCompression(Enum):
    OFF = 0
    ON = 1
    V42BIS = 2
    V44 = 3
    UNSPEC = 99

class WalterModemPDPIPv4AddrAllocMethod(Enum):
    NAS = 0
    DHCP = 1

class WalterModemPDPRequestType(Enum):
    NEW_OR_HANDOVER = 0
    EMERGENCY = 1
    NEW = 2
    HANDOVER = 3
    EMERGENCY_HANDOVER = 4

class WalterModemPDPPCSCFDiscoveryMethod(Enum):
    AUTO = 0
    NAS = 1

class WalterModemPDPAuthProtocol(Enum):
    NONE = 0
    PAP = 1
    CHAP = 2

#endregion
#region Constants

_PDP_MIN_CTX_ID = const(1)
_PDP_MAX_CTX_ID = const(8)
_PDP_DEFAULT_CTX_ID = const(1)

#endregion
#region MixinClass

class PDPMixin(ModemCore):
    MODEM_RSP_FIELDS = (
        ('pdp_address_list', None),
    )

    def __init__(self, *args, **kwargs):
        def init():
            self.__queue_rsp_rsp_handlers = (
                self.__queue_rsp_rsp_handlers + (
                    (b'+CGPADDR: ', self._handle_cgpaddr),
                )
            )

        mro_chain_init(self, super(), init, PDPMixin, *args, **kwargs)

    #region PublicMethods

    # Deprecated aliases, to be removed in a later release

    async def create_PDP_context(self, *args, **kwargs):
        return await self.pdp_context_create(*args, **kwargs)
    
    async def set_PDP_auth_params(self, *args, **kwargs):
        return await self.pdp_set_auth_params(*args, **kwargs)
    
    async def set_PDP_context_active(self, *args, **kwargs):
        return await self.pdp_context_set_active(*args, **kwargs)
    
    async def set_network_attachment_state(self, *args, **kwargs):
        return await self.pdp_set_attach_state(*args, **kwargs)
    
    async def get_PDP_address(self, *args, **kwargs):
        return await self.pdp_get_addressess(*args, **kwargs)

    # ---

    async def pdp_context_create(self,
        context_id: int = _PDP_DEFAULT_CTX_ID,
        apn: str = '',
        pdp_type: str = WalterModemPDPType.IP,
        pdp_address: str = None,
        header_comp: int = WalterModemPDPHeaderCompression.OFF,
        data_comp: int = WalterModemPDPDataCompression.OFF,
        ipv4_alloc_method: int = WalterModemPDPIPv4AddrAllocMethod.DHCP,
        request_type: int = WalterModemPDPRequestType.NEW_OR_HANDOVER,
        pcscf_method: int = WalterModemPDPPCSCFDiscoveryMethod.AUTO,
        for_IMCN: bool = False,
        use_NSLPI: bool  = False,
        use_secure_PCO: bool = False,
        use_NAS_ipv4_MTU_discovery: bool = False,
        use_local_addr_ind: bool = False,
        use_NAS_on_IPMTU_discovery: bool = False,
        rsp: WalterModemRsp | None = None
    ) -> bool:
        if context_id < _PDP_MIN_CTX_ID or context_id > _PDP_MAX_CTX_ID:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PDP_CONTEXT
            return False

        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CGDCONT={},{},{},{},{},{},{},{},{},{},{},{},{},{},{}'.format(
                context_id, pdp_type, modem_string(apn),
                modem_string(pdp_address), data_comp,
                header_comp, ipv4_alloc_method, request_type,
                pcscf_method, modem_bool(for_IMCN),
                modem_bool(use_NSLPI), modem_bool(use_secure_PCO),
                modem_bool(use_NAS_ipv4_MTU_discovery),
                modem_bool(use_local_addr_ind),
                modem_bool(use_NAS_on_IPMTU_discovery)
            ),
            at_rsp=b'OK'
        )
    
    async def pdp_set_auth_params(self,
        context_id: int = _PDP_DEFAULT_CTX_ID,
        protocol: int = WalterModemPDPAuthProtocol.NONE,
        user_id: str = None,
        password: str = None,
        rsp: WalterModemRsp = None
    ) -> bool:
        if context_id < _PDP_MIN_CTX_ID or context_id > _PDP_MAX_CTX_ID:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PDP_CONTEXT
            return False
        
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CGAUTH={},{},{},{}'.format(
                context_id, protocol,
                modem_string(user_id),
                modem_string(password)
            ),
            at_rsp=b'OK'
        )
    
    async def pdp_context_set_active(self,
        active: bool = True,
        context_id: int = _PDP_DEFAULT_CTX_ID,
        rsp: WalterModemRsp = None
    ) -> bool:
        if context_id < _PDP_MIN_CTX_ID or context_id > _PDP_MAX_CTX_ID:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PDP_CONTEXT
            return False
                
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CGACT={modem_bool(active)},{context_id}',
            at_rsp=b'OK'
        )
        
    async def pdp_set_attach_state(self,
        attach: bool = True,
        rsp: WalterModemRsp = None
    ) -> bool:
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CGATT={modem_bool(attach)}',
            at_rsp=b'OK'
        )
    
    async def pdp_get_addressess(self,
        context_id: int = _PDP_DEFAULT_CTX_ID,
        rsp: WalterModemRsp = None
    ) -> bool:
        if context_id < _PDP_MIN_CTX_ID or context_id > _PDP_MAX_CTX_ID:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PDP_CONTEXT
            return False

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CGPADDR={context_id}',
            at_rsp=b'OK'
        )

    #endregion
    #region QueueResponseHandlers

    async def _handle_cgpaddr(self, tx_stream, cmd, at_rsp):
        if not cmd:
            return None

        cmd.rsp.type = WalterModemRspType.PDP_ADDR 
        cmd.rsp.pdp_address_list = []

        parts = at_rsp.decode().split(',')
            
        if len(parts) > 1 and parts[1]:
            cmd.rsp.pdp_address_list.append(parts[1][1:-1])
        if len(parts) > 2 and parts[2]:
            cmd.rsp.pdp_address_list.append(parts[2][1:-1])
        
        return WalterModemState.OK

    #endregion
#endregion
