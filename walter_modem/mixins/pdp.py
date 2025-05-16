from ..core import ModemCore
from ..enums import (
    WalterModemPDPAuthProtocol,
    WalterModemPDPType,
    WalterModemPDPHeaderCompression,
    WalterModemPDPDataCompression,
    WalterModemPDPIPv4AddrAllocMethod,
    WalterModemPDPRequestType,
    WalterModemPDPPCSCFDiscoveryMethod,
    WalterModemState
)
from ..structs import (
    ModemRsp,
)
from ..utils import (
    modem_string,
    modem_bool
)

class ModemPDP(ModemCore):

    # Deprecated aliases, to be removed in a later release

    async def create_PDP_context(self, *args, **kwargs):
        """DEPRECATED; use `pdp_context_create()` instead"""
        return await self.pdp_context_create(*args, **kwargs)
    
    async def set_PDP_auth_params(self, *args, **kwargs):
        """DEPRECATED; use `pdp_set_auth_params()` instead"""
        return await self.pdp_set_auth_params(*args, **kwargs)
    
    async def set_PDP_context_active(self, *args, **kwargs):
        """DEPRECATED; use `pdp_context_set_active()` instead"""
        return await self.pdp_context_set_active(*args, **kwargs)
    
    async def set_network_attachment_state(self, *args, **kwargs):
        """DEPRECATED; use `pdp_set_attach_state()` instead"""
        return await self.pdp_set_attach_state(*args, **kwargs)
    
    async def get_PDP_address(self, *args, **kwargs):
        """DEPRECATED; use `pdp_get_addressess()` instead"""
        return await self.pdp_get_addressess(*args, **kwargs)

    # ---

    async def pdp_context_create(self,
        context_id: int = ModemCore.DEFAULT_PDP_CTX_ID,
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
        """
        Creates a new packet data protocol (PDP).

        :param context_id: The PDP context ID
        :param apn: The access point name.
        :param type: The type of PDP context to create.
        :type type: WalterModemPDPType
        :param pdp_address: Optional PDP address.
        :param header_comp: The type of header compression to use.
        :type header_comp: WalterModemPDPHeaderCompression
        :param data_comp: The type of data compression to use.
        :type data_comp: WalterModemPDPDataCompression
        :param ipv4_alloc_method: The IPv4 alloction method.
        :type ipv4_alloc_method: WalterModemPDPIPv4AddrAllocMethod
        :param request_type: The type of PDP requests.
        :type request_type: WalterModemPDPRequestType
        :param pcscf_method: The method to use for P-CSCF discovery.
        :type pcscf_method: WalterModemPDPPCSCFDiscoveryMethod
        :param for_IMCN: Set when this PDP ctx is used for IM CN signalling.
        :param use_NSLPI: Set when NSLPI is used.
        :param use_secure_PCO: Set to use secure protocol config options. 
        :param use_NAS_ipv4_MTU_discovery: Set to use NAS for IPv4 MTU discovery.
        :param use_local_addr_ind: Set when local IPs are supported in the TFT.
        :param use_NAS_on_IPMTU_discovery: Set for NAS based no-IP MTU discovery.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        if context_id < ModemCore.MIN_PDP_CTX_ID or context_id > ModemCore.MAX_PDP_CTX_ID:
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
        context_id: int = ModemCore.DEFAULT_PDP_CTX_ID,
        protocol: int = WalterModemPDPAuthProtocol.NONE,
        user_id: str = None,
        password: str = None,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Specify authentication parameters for the PDP.

        :param context_id: The PDP context id or -1 to re-use the last one.
        :protocol: The used authentication protocol.
        :type protocol: WalterModemPDPAuthProtocol
        :param username: Optional user to use for authentication.
        :param password: Optional password to use for authentication.
        :param rsp: Reference to a modem response instance.

        :return bool: True on success, False on failure
        """
        if context_id < ModemCore.MIN_PDP_CTX_ID or context_id > ModemCore.MAX_PDP_CTX_ID:
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
        context_id: int = ModemCore.DEFAULT_PDP_CTX_ID,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Activates or deactivates a given PDP context.

        :param active: True to activate the PDP context, False to deactivate.
        :param context_id: The PDP context id or -1 to re-use the last one.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        if context_id < ModemCore.MIN_PDP_CTX_ID or context_id > ModemCore.MAX_PDP_CTX_ID:
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
        """
        Attaches to or detaches from the currently active PDP context for packet domain service.

        :param attach: True to attach, False to detach.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CGATT={modem_bool(attach)}',
            at_rsp=b'OK'
        )
    
    async def pdp_get_addressess(self,
        context_id: int = ModemCore.DEFAULT_PDP_CTX_ID,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Retrieves the list of PDP addresses for the specified PDP context ID.

        :param context_id: The PDP context id or -1 to re-use the last one.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        if context_id < ModemCore.MIN_PDP_CTX_ID or context_id > ModemCore.MAX_PDP_CTX_ID:
            if rsp: rsp.result = WalterModemState.NO_SUCH_PDP_CONTEXT
            return False

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CGPADDR={context_id}',
            at_rsp=b'OK'
        )