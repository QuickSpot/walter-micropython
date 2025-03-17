from ..core import ModemCore
from ..enums import (
    WalterModemPDPAuthProtocol,
    WalterModemPDPType,
    WalterModemPDPHeaderCompression,
    WalterModemPDPDataCompression,
    WalterModemPDPIPv4AddrAllocMethod,
    WalterModemPDPRequestType,
    WalterModemPDPPCSCFDiscoveryMethod,
    WalterModemPDPContextState,
    WalterModemState,
    WalterModemRspType
)
from ..structs import (
    ModemRsp,
)
from ..utils import (
    pdp_type_as_string,
    modem_string,
    modem_bool
)

class ModemPDP(ModemCore):
    async def create_PDP_context(self,
        apn: str = '',
        auth_proto: int = WalterModemPDPAuthProtocol.NONE,
        auth_user: str = None,
        auth_pass: str = None,
        type: int = WalterModemPDPType.IP,
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
        """
        Creates a new packet data protocol (PDP) context with the lowest available context ID.

        :param apn: The access point name.
        :param auth_proto: The used authentication protocol.
        :type auth_proto: ModemPDPAuthProtocol
        :param auth_user: Optional user to use for authentication.
        :param auth_pass: Optional password to use for authentication.
        :param type: The type of PDP context to create.
        :type type: ModemPDPType
        :param pdp_address: Optional PDP address.
        :param header_comp: The type of header compression to use.
        :type header_comp: ModemPDPHeaderCompression
        :param data_comp: The type of data compression to use.
        :type data_comp: ModemPDPDataCompression
        :param ipv4_alloc_method: The IPv4 alloction method.
        :type ipv4_alloc_method: ModemPDPIPv4AddrAllocMethod
        :param request_type: The type of PDP requests.
        :type request_type: ModemPDPRequestType
        :param pcscf_method: The method to use for P-CSCF discovery.
        :type pcscf_method: ModemPDPPCSCFDiscoveryMethod
        :param for_IMCN: Set when this PDP ctx is used for IM CN signalling.
        :param use_NSLPI: Set when NSLPI is used.
        :param use_secure_PCO: Set to use secure protocol config options. 
        :param use_NAS_ipv4_MTU_discovery: Set to use NAS for IPv4 MTU discovery.
        :param use_local_addr_ind: Set when local IPs are supported in the TFT.
        :param use_NAS_on_IPMTU_discovery: Set for NAS based no-IP MTU discovery.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        ctx = None
        for pdp_ctx in self._pdp_ctx_list:
            if pdp_ctx.state == WalterModemPDPContextState.FREE:
                pdp_ctx.state = WalterModemPDPContextState.RESERVED
                ctx = pdp_ctx
                break

        if ctx == None:
            if rsp: rsp.result = WalterModemState.NO_FREE_PDP_CONTEXT
            return False
        
        self._pdp_ctx = ctx
        
        ctx.type = type
        ctx.apn = apn
        ctx.pdp_address = pdp_address
        ctx.header_comp = header_comp
        ctx.data_comp = data_comp
        ctx.ipv4_alloc_method = ipv4_alloc_method
        ctx.request_type = request_type
        ctx.pcscf_method = pcscf_method
        ctx.for_IMCN = for_IMCN
        ctx.use_NSLPI = use_NSLPI
        ctx.use_secure_PCO  = use_secure_PCO
        ctx.use_NAS_ipv4_MTU_discovery = use_NAS_ipv4_MTU_discovery
        ctx.use_local_addr_ind = use_local_addr_ind
        ctx.use_NAS_non_IPMTU_discovery = use_NAS_on_IPMTU_discovery
        ctx.auth_proto = auth_proto
        ctx.auth_user = auth_user
        ctx.auth_pass = auth_pass

        async def complete_handler(result, rsp, complete_handler_arg):
            ctx = complete_handler_arg
            rsp.type = WalterModemRspType.PDP_CTX_ID
            rsp.pdp_ctx_id = ctx.id

            if result == WalterModemState.OK:
                ctx.state = WalterModemPDPContextState.INACTIVE

        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CGDCONT={},{},{},{},{},{},{},{},{},{},{},{},{},{},{}'.format(
                ctx.id, pdp_type_as_string(ctx.type), modem_string(ctx.apn),
                modem_string(ctx.pdp_address), ctx.data_comp,
                ctx.header_comp, ctx.ipv4_alloc_method, ctx.request_type,
                ctx.pcscf_method, modem_bool(ctx.for_IMCN),
                modem_bool(ctx.use_NSLPI), modem_bool(ctx.use_secure_PCO),
                modem_bool(ctx.use_NAS_ipv4_MTU_discovery),
                modem_bool(ctx.use_local_addr_ind),
                modem_bool(ctx.use_NAS_non_IPMTU_discovery)
            ),
            at_rsp=b'OK',
            complete_handler=complete_handler,
            complete_handler_arg=ctx
        )
    
    async def authenticate_PDP_context(self,
        context_id: int = None,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Authenticates a PDP context if its APN requires authentication.
        Has no effect if 'NONE' is selected as the authentication method.

        :param context_id: The PDP context id or -1 to re-use the last one.
        :param rsp: Reference to a modem response instance.

        :return bool: True on success, False on failure
        """
        try:
            ctx = self._pdp_ctx_list[context_id - 1]
        except Exception:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PDP_CONTEXT
            return False
        
        self._pdp_ctx = ctx

        if ctx.auth_proto == WalterModemPDPAuthProtocol.NONE:
            if rsp: rsp.result = WalterModemState.OK
            return True
        
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CGAUTH={},{},{},{}'.format(
                ctx.id, ctx.auth_proto, modem_string(ctx.auth_user),
                modem_string(ctx.auth_pass)
            ),
            at_rsp=b'OK'
        )
    
    async def set_PDP_context_active(self,
        active: bool = True,
        context_id = -1,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Activates or deactivates a given PDP context.
        The context must be activated before it can be attached to.

        :param active: True to activate the PDP context, False to deactivate.
        :param context_id: The PDP context id or -1 to re-use the last one.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        try:
            if context_id == -1:
                ctx = self._pdp_ctx
            else:
                ctx = self._pdp_ctx_list[context_id - 1]
        except Exception:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PDP_CONTEXT
            return False
        
        self._pdp_ctx = ctx

        async def complete_handler(result, rsp, complete_handler_arg):
            ctx = complete_handler_arg
            if result == WalterModemState.OK:
                ctx.state = WalterModemPDPContextState.ACTIVE

                for pdp_ctx in self._pdp_ctx_list:
                    pdp_ctx.state = WalterModemPDPContextState.INACTIVE
                
            return await self._run_cmd(
                rsp=rsp,
                at_cmd=f'AT+CGACT={ctx.id, modem_bool(active)}',
                at_rsp=b'OK',
                complete_handler=complete_handler,
                complete_handler_arg=ctx
            )
        
    async def attach_PDP_context(self,
        attach: bool = True,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Attaches to or detaches from the currently active PDP context for packet domain service.

        :param attach: True to attach, False to detach.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        async def complete_handler(result, rsp, complete_handler_arg):
            if result == WalterModemState.OK and self._pdp_ctx:
                self._pdp_ctx.state = WalterModemPDPContextState.ATTACHED

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CGATT={modem_bool(attach)}',
            at_rsp=b'OK',
            complete_handler=complete_handler
        )
    
    async def get_PDP_address(self, context_id: int = -1, rsp: ModemRsp = None) -> bool:
        """
        Retrieves the list of PDP addresses for the specified PDP context ID.

        :param context_id: The PDP context id or -1 to re-use the last one.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        try:
            if context_id == -1:
                ctx = self._pdp_ctx
            else:
                ctx = self._pdp_ctx_list[context_id - 1]
        except Exception:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PDP_CONTEXT
            return False
        
        self._pdp_ctx = ctx

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CGPADDR={ctx.id}',
            at_rsp=b'OK'
        )