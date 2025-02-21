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

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT',
            at_rsp=b'OK'
        )
    
    async def get_clock(self, rsp: ModemRsp = None
    ) -> bool:
        """
        This function retrieves the current time and date from the modem.

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
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
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
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
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CEREG={reports_type}',
            at_rsp=b'OK'
        )
    
    async def get_rssi(self, rsp: ModemRsp = None) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CSQ',
            at_rsp=b'OK'
        )
    
    async def get_signal_quality(self, rsp: ModemRsp = None) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
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
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNMONI={reports_type}',
            at_rsp=b'OK'
        )
    
    async def get_op_state(self, rsp: ModemRsp = None) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CFUN?',
            at_rsp=b'OK'
        )
    
    async def set_op_state(self, op_state: int, rsp: ModemRsp = None) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CFUN={op_state}',
            at_rsp=b'OK'
        )
    
    async def get_rat(self, rsp: ModemRsp = None) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNMODEACTIVE?',
            at_rsp=b'OK'
        )
    
    async def set_rat(self, rat: int, rsp: ModemRsp = None) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+SQNMODEACTIVE={rat + 1}',
            at_rsp=b'OK'
        )

    async def get_radio_bands(self, rsp: ModemRsp = None) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+SQNBANDSEL?',
            at_rsp=b'OK'
        )
    
    async def get_sim_state(self, rsp: ModemRsp = None) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+CPIN?',
            at_rsp=b'OK'
        )

    async def unlock_sim(self, pin: str = None, rsp: ModemRsp = None) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
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
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
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
        
    async def create_PDP_context(self, apn: str = '',
        auth_proto: int = enums.ModemPDPAuthProtocol.NONE,
        auth_user: str = None,
        auth_pass: str = None,
        auth_type: int = enums.ModemPDPType.IP,
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
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
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
        
        ctx.type = auth_type
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
    
    async def authenticate_PDP_context(self, context_id: int = None,
        rsp: ModemRsp = None
    ) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
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
    
    async def set_PDP_context_active(self, active: bool = True, context_id = -1,
        rsp: ModemRsp = None
    ) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
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
        
    async def attach_PDP_context(self, attached: bool = True, rsp: ModemRsp = None) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
        """
        async def complete_handler(result, rsp, complete_handler_arg):
            if result == enums.ModemState.OK and self._pdp_ctx:
                self._pdp_ctx.state = enums.ModemPDPContextState.ATTACHED

        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+CGATT={modem_bool(attached)}',
            at_rsp=b'OK',
            complete_handler=complete_handler
        )
    
    async def get_PDP_address(self, context_id: int = -1, rsp: ModemRsp = None) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
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
    
    async def create_socket(self, pdp_context_id: int = -1, mtu: int = 300,
        exchange_timeout = 90, conn_timeout = 60, send_delay_ms = 5000, rsp: ModemRsp = None
    ) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
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
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
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
    
    async def connect_socket(self, remote_host: str, remote_port: int,
        local_port: int = 0, protocol: int = enums.ModemSocketProto.UDP,
        accept_any_remote: int = enums.ModemSocketAcceptAnyRemote.DISABLED,
        socket_id: int = -1, rsp: ModemRsp = None
    ) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
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
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
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
        data: bytes,
        rai: int = enums.ModemRai.NO_INFO,
        socket_id: int = -1,
        rsp: ModemRsp = None
    ) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
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

        :param sens_mode: ModemGNSSSensMode
        :param acq_mode: ModemGNSSAcqMode
        :param loc_mode: ModemGNSSLocMode
        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+LPGNSSCFG={loc_mode},{sens_mode},2,,1,{acq_mode}',
            at_rsp=b'OK'
        )

    async def get_gnss_assistance_status(self, rsp: ModemRsp = None) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd='AT+LPGNSSASSISTANCE?',
            at_rsp=b'OK'
        )
    
    async def update_gnss_assistance(self,
        ass_type: int = enums.ModemGNSSAssistanceType.REALTIME_EPHEMERIS, 
        rsp: ModemRsp = None
    ) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
        """
        return await self._run_cmd(
            rsp=rsp,
            at_cmd=f'AT+LPGNSSASSISTANCE={ass_type}',
            at_rsp=b'+LPGNSSASSISTANCE:'
        )
    
    async def perform_gnss_action(self,
        action: int = enums.ModemGNSSAction.GET_SINGLE_FIX,
        rsp: ModemRsp = None
    ) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
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
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
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

    async def http_config_profile(self, profile_id: int, server_address: str,
        port: int = 80, use_basic_auth: bool = False, auth_user: str = '',
        auth_pass: str = '', tls_profile_id: int = None, rsp: ModemRsp = None
    ) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
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
    
    async def tls_config_profile(self, profile_id: int, tls_version: int, tls_validation: int,
        ca_certificate_id: int = None, client_certificate_id: int = None,
        client_private_key: int = None, rsp: ModemRsp = None
    ) -> bool:
        """
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
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
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
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
        

        :param rsp: reference to a modem response instance

        :return bool: true on success, false on failure
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
        

        :param rsp: reference to a modem response instance

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
    
    async def http_query(self, profile_id: int, uri: str,
        query_cmd: int = enums.ModemHttpQueryCmd.GET, extra_header_line: str = None,
        rsp: ModemRsp = None
    ) -> bool:
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
    
    async def http_send(self, profile_id: int, uri: str, data,
        send_cmd = enums.ModemHttpSendCmd.POST,
        post_param = enums.ModemHttpPostParam.UNSPECIFIED,
        rsp: ModemRsp = None
    ) -> bool:
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