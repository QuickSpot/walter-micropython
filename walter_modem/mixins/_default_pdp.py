import gc

from micropython import const # type: ignore

from ..core import ModemCore
from ..enums import (
    WalterModemPDPAuthProtocol,
    WalterModemPDPType,
    WalterModemPDPHeaderCompression,
    WalterModemPDPDataCompression,
    WalterModemPDPIPv4AddrAllocMethod,
    WalterModemPDPRequestType,
    WalterModemPDPPCSCFDiscoveryMethod,
    WalterModemState,
    WalterModemRspType
)
from ..structs import (
    ModemRsp,
)
from ..utils import (
    modem_string,
    modem_bool,
    log
)

_PDP_MIN_CTX_ID = const(1)
_PDP_MAX_CTX_ID = const(8)
_PDP_DEFAULT_CTX_ID = const(1)

class PDPMixin(ModemCore):
    def __init__(self, *args, **kwargs):
        if not hasattr(self, '__initialised_mixins'):
            super().__init__(*args, **kwargs)

        self.__queue_rsp_rsp_handlers = (
            self.__queue_rsp_rsp_handlers + (
                (b'+CGPADDR: ', self._handle_cgpaddr),
            )
        )

        self.__initialised_mixins.append(PDPMixin)
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
        log('INFO', '(default) PDP mixin loaded')
        if next_base is not None: next_base.__init__(self, *args, **kwargs)

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
        rsp: ModemRsp | None = None
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
        rsp: ModemRsp = None
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
        rsp: ModemRsp = None
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
        rsp: ModemRsp = None
    ) -> bool:
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CGATT={modem_bool(attach)}',
            at_rsp=b'OK'
        )
    
    async def pdp_get_addressess(self,
        context_id: int = _PDP_DEFAULT_CTX_ID,
        rsp: ModemRsp = None
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
