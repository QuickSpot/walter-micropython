import time
from machine import Pin

from .core import ModemCore

from .. import enums

from ..structs import (
    ModemRsp,
    ModemGnssFixWaiter,
    ModemGNSSFix
)

from ..utils import (
    pdp_type_as_string,
    modem_string,
    modem_bool
)

class Modem(ModemCore):
    def __init__(self):
        super().__init__()

    def get_network_reg_state(self) -> int:
        return self._reg_state

    async def reset(self, rsp: ModemRsp = None) -> bool:
        """
        Physically reset the modem and wait for it to start.
        All connections will be lost when this function is called.
        The function will fail when the modem doesn't start after the reset.

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
        """
        reset_pin = Pin(ModemCore.WALTER_MODEM_PIN_RESET, Pin.OUT)
        reset_pin.off()
        time.sleep(0.1)
        reset_pin.on()

        # Also reset internal "modem mirror" state
        super().__init__()

        return await self._run_cmd(
            rsp=rsp,
            at_cmd='',
            at_rsp=b'+SYSSTART',
            cmd_type=enums.ModemCmdType.WAIT
        )
    
    async def check_comm(self, rsp: ModemRsp = None) -> bool:
        """
        Sends the 'AT' command to check if the modem responds with 'OK',
        verifying communication between the ESP32 and the modem.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT',
            at_rsp=b'OK'
        )
    
    async def get_clock(self, rsp: ModemRsp = None
    ) -> bool:
        """
        Retrieves the current time and date from the modem.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CCLK?',
            at_rsp=b'OK'
        )

    
    async def config_cme_error_reports(self,
        reports_type: int = enums.ModemCMEErrorReportsType.NUMERIC,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Configures the CME error report type.
        By default, errors are enabled and numeric.
        Changing this may affect error reporting.

        :param reports_type: The CME error report type.
        :type reports_type: ModemCMEErrorReportsType
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CMEE={reports_type}',
            at_rsp=b'OK'
        )
    
    async def config_cereg_error_reports(self,
        reports_type: int = enums.ModemCEREGReportsType.ENABLED,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Configures the CEREG status report type.
        By default, reports are enabled with minimal operational info.
        Changing this may affect library functionality.

        :param reports_type: The CEREG status reports type.
        :type reports_type: ModemCEREGReportsType
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CEREG={reports_type}',
            at_rsp=b'OK'
        )
    
    async def get_rssi(self, rsp: ModemRsp = None) -> bool:
        """
        Retrieves the RSRQ and RSRP signal quality indicators.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CSQ',
            at_rsp=b'OK'
        )
    
    async def get_signal_quality(self, rsp: ModemRsp = None) -> bool:
        """
        Retrieves information about the serving and neighbouring cells,
        including operator, cell ID, RSSI, and RSRP.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CESQ',
            at_rsp=b'OK'
        )
    
    async def get_cell_information(self,
        reports_type: int = enums.ModemSQNMONIReportsType.SERVING_CELL,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Retrieves the modem's identity details, including IMEI, IMEISV, and SVN.

        :param reports_type: The type of cell information to retreive,
        defaults to the cell which is currently serving the connection.
        :type reports_type: ModemSQNMONIReportsType
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNMONI={reports_type}',
            at_rsp=b'OK'
        )
    
    async def get_op_state(self, rsp: ModemRsp = None) -> bool:
        """
        Retrieves the modem's current operational state.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CFUN?',
            at_rsp=b'OK'
        )
    
    async def set_op_state(self, op_state: int, rsp: ModemRsp = None) -> bool:
        """
        Sets the operational state of the modem.

        :param op_state: The new operational state of the modem.
        :type op_state: ModemOpState
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CFUN={op_state}',
            at_rsp=b'OK'
        )
    
    async def get_rat(self, rsp: ModemRsp = None) -> bool:
        """
        Retrieves the Radio Access Technology (RAT) for the modem.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNMODEACTIVE?',
            at_rsp=b'OK'
        )
    
    async def set_rat(self, rat: int, rsp: ModemRsp = None) -> bool:
        """
        Sets the Radio Access Technology (RAT) for the modem.

        :param rat: The new RAT
        :type rat: ModemRat
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNMODEACTIVE={rat + 1}',
            at_rsp=b'OK'
        )

    async def get_radio_bands(self, rsp: ModemRsp = None) -> bool:
        """
        Retrieves the radio bands the modem is configured to use for network connection.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNBANDSEL?',
            at_rsp=b'OK'
        )
    
    async def get_sim_state(self, rsp: ModemRsp = None) -> bool:
        """
        Retrieves the state of the SIM card.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CPIN?',
            at_rsp=b'OK'
        )

    async def unlock_sim(self, pin: str = None, rsp: ModemRsp = None) -> bool:
        """
        Sets the SIM card's PIN code.
        The modem must be in FULL or NO_RF operational state.

        :param pin: The PIN code of the SIM card or NULL for no pin.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        self._sim_PIN = pin
        if self._sim_PIN is None:
            return await self.get_sim_state()

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CPIN={pin}',
            at_rsp=b'OK'
        )

    async def set_network_selection_mode(self,
        mode: int = enums.ModemNetworkSelMode.AUTOMATIC,
        operator_name: str = '',
        operator_format: int = enums.ModemOperatorFormat.LONG_ALPHANUMERIC,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Sets the network selection mode for Walter.
        This command is only available when the modem is in the fully operational state.

        :param mode: The network selection mode.
        :type mode: ModemNetworkSelMode
        :param operator_name: The network operator name in case manual selection has been chosen.
        :param operator_format: The format in which the network operator name is passed.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        self._network_sel_mode = mode
        self._operator.format = operator_format
        self._operator.name = operator_name

        if mode == enums.ModemNetworkSelMode.AUTOMATIC:
            return await self._run_cmd(
                rsp=rsp,
                at_cmd=f'AT+COPS={mode}',
                at_rsp=b'OK'
            )
        else:
            return await self._run_cmd(
                rsp=rsp,
                at_cmd='AT+COPS={},{},{}'.format(
                    self._network_sel_mode, self._operator.format,
                    modem_string(self._operator.name)
                ),
                at_rsp=b'OK'
            )
        
    async def create_PDP_context(self,
        apn: str = '',
        auth_proto: int = enums.ModemPDPAuthProtocol.NONE,
        auth_user: str = None,
        auth_pass: str = None,
        type: int = enums.ModemPDPType.IP,
        pdp_address: str = None,
        header_comp: int = enums.ModemPDPHeaderCompression.OFF,
        data_comp: int = enums.ModemPDPDataCompression.OFF,
        ipv4_alloc_method: int = enums.ModemPDPIPv4AddrAllocMethod.DHCP,
        request_type: int = enums.ModemPDPRequestType.NEW_OR_HANDOVER,
        pcscf_method: int = enums.ModemPDPPCSCFDiscoveryMethod.AUTO,
        for_IMCN: bool = False,
        use_NSLPI: bool  = True,
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
            if pdp_ctx.state == enums.ModemPDPContextState.FREE:
                pdp_ctx.state = enums.ModemPDPContextState.RESERVED
                ctx = pdp_ctx
                break

        if ctx == None:
            if rsp: rsp.result = enums.ModemState.NO_FREE_PDP_CONTEXT
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
            rsp.type = enums.ModemRspType.PDP_CTX_ID
            rsp.pdp_ctx_id = ctx.id

            if result == enums.ModemState.OK:
                ctx.state = enums.ModemPDPContextState.INACTIVE

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

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        try:
            ctx = self._pdp_ctx_list[context_id - 1]
        except Exception:
            if rsp: rsp.result = enums.ModemState.NO_SUCH_PDP_CONTEXT
            return False
        
        self._pdp_ctx = ctx

        if ctx.auth_proto == enums.ModemPDPAuthProtocol.NONE:
            if rsp: rsp.result = enums.ModemState.OK
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
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        try:
            if context_id == -1:
                ctx = self._pdp_ctx
            else:
                ctx = self._pdp_ctx_list[context_id - 1]
        except Exception:
            if rsp: rsp.result = enums.ModemState.NO_SUCH_PDP_CONTEXT
            return False
        
        self._pdp_ctx = ctx

        async def complete_handler(result, rsp, complete_handler_arg):
            ctx = complete_handler_arg
            if result == enums.ModemState.OK:
                ctx.state = enums.ModemPDPContextState.ACTIVE

                for pdp_ctx in self._pdp_ctx_list:
                    pdp_ctx.state = enums.ModemPDPContextState.INACTIVE
                
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
            if result == enums.ModemState.OK and self._pdp_ctx:
                self._pdp_ctx.state = enums.ModemPDPContextState.ATTACHED

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
            if rsp: rsp.result = enums.ModemState.NO_SUCH_PDP_CONTEXT
            return False
        
        self._pdp_ctx = ctx

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CGPADDR={ctx.id}',
            at_rsp=b'OK'
        )
    
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
            if rsp: rsp.result = enums.ModemState.NO_SUCH_PDP_CONTEXT
            return False
        
        self._pdp_ctx = ctx

        socket = None
        for _socket in self._socket_list:
            if _socket.state == enums.ModemSocketState.FREE:
                _socket.state = enums.ModemSocketState.RESERVED
                socket = _socket
                break

        if socket == None:
            if rsp: rsp.result = enums.ModemState.NO_FREE_SOCKET
            return False

        self._socket = socket

        socket.pdp_context_id = ctx.id
        socket.mtu = mtu
        socket.exchange_timeout = exchange_timeout
        socket.conn_timeout = conn_timeout
        socket.send_delay_ms = send_delay_ms

        async def complete_handler(result, rsp, complete_handler_arg):
            sock = complete_handler_arg
            rsp.type = enums.ModemRspType.SOCKET_ID
            rsp.socket_id = sock.id

            if result == enums.ModemState.OK:
                sock.state = enums.ModemSocketState.CREATED
        
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
            if rsp: rsp.result = enums.ModemState.NO_SUCH_SOCKET
            return False
        
        self._socket = socket

        async def complete_handler(result, rsp, complete_handler_arg):
            sock = complete_handler_arg

            if result == enums.ModemState.OK:
                sock.state = enums.ModemSocketState.CONFIGURED

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
        socket_id: int = -1,
        local_port: int = 0,
        protocol: int = enums.ModemSocketProto.UDP,
        accept_any_remote: int = enums.ModemSocketAcceptAnyRemote.DISABLED,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Connects a socket to a remote host,
        allowing data exchange once the connection is successful.

        :param remote_host: The remote IPv4/IPv6 or hostname to connect to.
        :param remote_port: The remote port to connect on.
        :param socket_id: The id of the socket to connect or -1 to re-use the last one.
        :param local_port: The local port in case of an UDP socket.
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
            if rsp: rsp.result = enums.ModemState.NO_SUCH_SOCKET
            return False
        
        self._socket = socket

        socket.protocol = protocol
        socket.accept_any_remote = accept_any_remote
        socket.remote_host = remote_host
        socket.remote_port = remote_port
        socket.local_port = local_port

        async def complete_handler(result, rsp, complete_handler_arg):
            sock = complete_handler_arg
            if result == enums.ModemState.OK:
                sock.state = enums.ModemSocketState.OPENED

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
            if rsp: rsp.result = enums.ModemState.NO_SUCH_SOCKET
            return False
        
        self._socket = socket

        async def complete_handler(result, rsp, complete_handler_arg):
            sock = complete_handler_arg
            if result == enums.ModemState.OK:
                sock.state = enums.ModemSocketState.FREE

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
        rai: int = enums.ModemRai.NO_INFO,
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
            if rsp: rsp.result = enums.ModemState.NO_SUCH_SOCKET
            return False
        
        self._socket = _socket

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNSSENDEXT={_socket.id},{len(data)},{rai}',
            at_rsp=b'OK',
            at_data=data
        )

    async def config_gnss(
        self,
        sens_mode: int = enums.ModemGNSSSensMode.HIGH,
        acq_mode: int = enums.ModemGNSSAcqMode.COLD_WARM_START,
        loc_mode: int = enums.ModemGNSSLocMode.ON_DEVICE_LOCATION,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Configures Walter's GNSS receiver with persistent settings that
        may need to be reset after a modem firmware upgrade.
        Can also adjust sensitivity mode between fixes.
        Recommended to run at least once before using GNSS.

        :param sens_mode: The sensitivity mode.
        :type sens_mode: ModemGNSSSensMode
        :param acq_mode: The acquisition mode.
        :type acq_mode: ModemGNSSAcqMode
        :param loc_mode: The GNSS location mode.
        :type loc_mode: ModemGNSSLocMode
        :type rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+LPGNSSCFG={loc_mode},{sens_mode},2,,1,{acq_mode}',
            at_rsp=b'OK'
        )

    async def get_gnss_assistance_status(self, rsp: ModemRsp = None) -> bool:
        """
        Retrieves the status of the assistance data currently loaded in the GNSS subsystem.

        :param rsp: reference to a modem response instance

        :return bool: true on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+LPGNSSASSISTANCE?',
            at_rsp=b'OK'
        )
    
    async def update_gnss_assistance(self,
        type: int = enums.ModemGNSSAssistanceType.REALTIME_EPHEMERIS, 
        rsp: ModemRsp = None
    ) -> bool:
        """
        Connects to the cloud to download and update the GNSS subsystem
        with the requested assistance data.
        Real-time ephemeris being the most efficient type.

        :param type: The type of GNSS assistance data to update.
        :type type: ModemGNSSAssistanceType
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+LPGNSSASSISTANCE={type}',
            at_rsp=b'+LPGNSSASSISTANCE:'
        )
    
    async def perform_gnss_action(self,
        action: int = enums.ModemGNSSAction.GET_SINGLE_FIX,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Programs the GNSS subsystem to perform a specified action.

        :param action: The action for the GNSS subsystem to perform.
        :type action: ModemGNSSAction
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        if action == enums.ModemGNSSAction.GET_SINGLE_FIX:
            action_str = 'single'
        elif action == enums.ModemGNSSAction.CANCEL:
            action_str = 'stop'
        else:
            action_str = ''

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+LPGNSSFIXPROG="{action_str}"',
            at_rsp=b'OK'
        )

    async def wait_for_gnss_fix(self) -> ModemGNSSFix:
        """
        Waits for a gnss fix before then returning it.

        :return ModemGNSSFix:
        """
        gnss_fix_waiter = ModemGnssFixWaiter()

        async with self._gnss_fix_lock:
            self._gnss_fix_waiters.append(gnss_fix_waiter)

        await gnss_fix_waiter.event.wait()

        return gnss_fix_waiter.gnss_fix
    
    async def http_did_ring(self, profile_id: int, rsp: ModemRsp = None
    ) -> bool:
        """
        Fetch http response to earlier http request, if any.

        :param profile_id: Profile for which to get response
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        if self._http_current_profile != 0xff:
            if rsp: rsp.result = enums.ModemState.ERROR
            return False

        if profile_id >= ModemCore.WALTER_MODEM_MAX_HTTP_PROFILES:
            if rsp: rsp.result = enums.ModemState.NO_SUCH_PROFILE
            return False

        if self._http_context_list[profile_id].state == enums.ModemHttpContextState.IDLE:
            if rsp: rsp.result = enums.ModemState.NOT_EXPECTING_RING
            return False

        if self._http_context_list[profile_id].state == enums.ModemHttpContextState.EXPECT_RING:
            if rsp: rsp.result = enums.ModemState.AWAITING_RING
            return False

        if self._http_context_list[profile_id].state != enums.ModemHttpContextState.GOT_RING:
            if rsp: rsp.result = enums.ModemState.ERROR
            return False

        # ok, got ring. http context fields have been filled.
        # http status 0 means: timeout (or also disconnected apparently)
        if self._http_context_list[profile_id].http_status == 0:
            self._http_context_list[profile_id].state = enums.ModemHttpContextState.IDLE
            if rsp: rsp.result = enums.ModemState.ERROR
            return False

        self._http_current_profile = profile_id

        async def complete_handler(result, rsp, complete_handler_arg):
            modem = complete_handler_arg
            modem._http_context_list[modem._http_current_profile].state = enums.ModemHttpContextState.IDLE
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
            if rsp: rsp.result = enums.ModemState.NO_SUCH_PROFILE
            return False

        if tls_profile_id and tls_profile_id > ModemCore.WALTER_MODEM_MAX_TLS_PROFILES:
            if rsp: rsp.result = enums.ModemState.NO_SUCH_PROFILE
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
    
    async def tls_config_profile(self,
        profile_id: int,
        tls_version: int,
        tls_validation: int,
        ca_certificate_id: int = None,
        client_certificate_id: int = None,
        client_private_key: int = None,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Configures TLS profiles in the modem,
        including optional client authentication certificates, validation levels, and TLS version. 
        This should be done in an initializer sketch, 
        allowing later HTTP, MQTT, CoAP, or socket sessions to use the preconfigured profile IDs.

        :param profile_id: Security profile id (1-6)
        :param tls_version: TLS version
        :type tls_version: ModemTlsVersion
        :param tls_validation: TLS validation level: nothing, URL, CA+period or all
        :type tls_validation: ModemTlsValidation
        :param ca_certificate_id: CA certificate for certificate validation (0-19)
        :param client_certificate_id: Client TLS certificate index (0-19)
        :param client_private_key: Client TLS private key index (0-19)
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
        if profile_id > ModemCore.WALTER_MODEM_MAX_TLS_PROFILES or profile_id <= 0:
            if rsp: rsp.result = enums.ModemState.NO_SUCH_PROFILE
            return False
        
        cmd = 'AT+SQNSPCFG={},{},"",{}'.format(
                profile_id, tls_version, tls_validation, 
        )

        cmd += ','
        if ca_certificate_id is not None:
            cmd += f'{ca_certificate_id}'

        cmd += ','
        if client_certificate_id is not None:
            cmd += f',{client_certificate_id}'
        
        cmd += ','
        if client_private_key is not None:
            cmd += f',{client_private_key}'

        cmd += ',"","",0'
        
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=cmd,
            at_rsp=b'OK',
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
            if rsp: rsp.result = enums.ModemState.NO_SUCH_PROFILE
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
            if rsp: rsp.result = enums.ModemState.NO_SUCH_PROFILE
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
            if rsp: rsp.result = enums.ModemState.NO_SUCH_PROFILE
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
        query_cmd: int = enums.ModemHttpQueryCmd.GET,
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
            if rsp: rsp.result = enums.ModemState.NO_SUCH_PROFILE
            return False

        if self._http_context_list[profile_id].state != enums.ModemHttpContextState.IDLE:
            if rsp: rsp.result = enums.ModemState.BUSY
            return False

        async def complete_handler(result, rsp, complete_handler_arg):
            ctx = complete_handler_arg

            if result == enums.ModemState.OK:
                ctx.state = enums.ModemHttpContextState.EXPECT_RING

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
        send_cmd = enums.ModemHttpSendCmd.POST,
        post_param = enums.ModemHttpPostParam.UNSPECIFIED,
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
            if rsp: rsp.result = enums.ModemState.NO_SUCH_PROFILE
            return False

        if self._http_context_list[profile_id].state != enums.ModemHttpContextState.IDLE:
            if rsp: rsp.result = enums.ModemState.BUSY
            return False

        async def complete_handler(result, rsp, complete_handler_arg):
            ctx = complete_handler_arg

            if result == enums.ModemState.OK:
                ctx.state = enums.ModemHttpContextState.EXPECT_RING

        if post_param == enums.ModemHttpPostParam.UNSPECIFIED:
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