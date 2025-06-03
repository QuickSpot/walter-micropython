from walter_modem.structs import *
from walter_modem.enums import *
from walter_modem.utils import *

class Modem():

# ---
# CORE
# ---

    async def begin(self, uart_debug: bool = False):
        """
        Begin the modem library's processes.

        :param uart_debug: include the UART TX & RX in the debug logs
        """
    async def reset(self) -> bool:
        """
        Physically reset the modem and wait for it to start.
        All connections will be lost when this function is called.
        The function will fail when the modem doesn't start after the reset.

        :return bool: True on success, False on failure
        """
    async def soft_reset(self) -> bool:
        """
        Perform a soft reset on the modem, wait for it to complete.
        The method will fail when the modem doesn't reset.

        :return bool: True on success, False on failure
        """
    async def check_comm(self) -> bool:
        """
        Sends the 'AT' command to check if the modem responds with 'OK',
        verifying communication between the ESP32 and the modem.

        :return bool: True on success, False on failure
        """
    
    async def get_clock(self, rsp: ModemRsp | None = None) -> bool:
        """
        Retrieves the current time and date from the modem.

        :param rsp: Reference to a modem response instance
        :type rsp: ModemRsp

        :return bool: True on success, False on failure
        """
    
    async def config_cme_error_reports(self,
        reports_type: WalterModemCMEErrorReportsType = WalterModemCMEErrorReportsType.NUMERIC,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Configures the CME error report type.
        By default, errors are enabled and numeric.
        Changing this may affect error reporting.

        :param reports_type: The CME error report type.
        :type reports_type: WalterModemCMEErrorReportsType
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
    
    async def config_cereg_reports(self,
        reports_type: WalterModemCEREGReportsType = WalterModemCEREGReportsType.ENABLED,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Configures the CEREG status report type.
        By default, reports are enabled with minimal operational info.
        Changing this may affect library functionality.

        :param reports_type: The CEREG status reports type.
        :type reports_type: WalterModemCEREGReportsType
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def get_op_state(self, rsp: ModemRsp | None = None) -> bool:
        """
        Retrieves the modem's current operational state.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def set_op_state(self,
        op_state: WalterModemOpState,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Sets the operational state of the modem.

        :param op_state: The new operational state of the modem.
        :type op_state: WalterModemOpState
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    def get_network_reg_state(self) -> int:
        """
        Get the network registration state.
        This is buffered by the library and thus instantly available.

        :return int: The current modem registration state
        """

    def sleep(self,
        sleep_time_ms: int,
        light_sleep: bool = False,
        persist_mqtt_subs: bool = False
    ):
        """
        Put the esp32s3 to light or deepsleep.
        Using this method ensures the modem library is aware of the sleep,
        optionally allowing it to persist certain information.

        :param sleep_time_ms: The time to sleep for in ms.
        :param light_sleep: True for lightsleep, False for deepsleep
        :param persist_mqtt_subs: Whether or not to persist the MQTT subscriptions in RTC
        """

    def register_application_queue_rsp_handler(self, start_pattern: bytes, handler: callable):
        """
        IMPORTANT: DO NOT USE, unless you know what you're doing
        
        Register your own queue response handler.

        :param start_pattern: the start pattern to call your handler on if matched
        :param handler: a synchornous method to ba called, signature: handler(cmd, at_rsp)
        """
    
    def unregister_application_queue_rsp_handler(self, handler: callable):
        """
        IMPORTANT: DO NOT USE, unless you know what you're doing

        Unregister previously registered queue response handler(s) based on method reference.

        :param handler: the handler to unregister
        """

# ---
# PDPMixin
# ---

    async def create_PDP_context(self, *args, **kwargs):
        """DEPRECATED; use `pdp_context_create()` instead"""

    async def set_PDP_auth_params(self, *args, **kwargs):
        """DEPRECATED; use `pdp_set_auth_params()` instead"""
    
    async def set_PDP_context_active(self, *args, **kwargs):
        """DEPRECATED; use `pdp_context_set_active()` instead"""
    
    async def set_network_attachment_state(self, *args, **kwargs):
        """DEPRECATED; use `pdp_set_attach_state()` instead"""
    
    async def get_PDP_address(self, *args, **kwargs):
        """DEPRECATED; use `pdp_get_addressess()` instead"""

    async def pdp_context_create(self,
        context_id: int = 1,
        apn: str = '',
        pdp_type: WalterModemPDPType = WalterModemPDPType.IP,
        pdp_address: str | None = None,
        header_comp: WalterModemPDPHeaderCompression = WalterModemPDPHeaderCompression.OFF,
        data_comp: WalterModemPDPDataCompression = WalterModemPDPDataCompression.OFF,
        ipv4_alloc_method: WalterModemPDPIPv4AddrAllocMethod = WalterModemPDPIPv4AddrAllocMethod.DHCP,
        request_type: WalterModemPDPRequestType = WalterModemPDPRequestType.NEW_OR_HANDOVER,
        pcscf_method: WalterModemPDPPCSCFDiscoveryMethod = WalterModemPDPPCSCFDiscoveryMethod.AUTO,
        for_IMCN: bool = False,
        use_NSLPI: bool  = False,
        use_secure_PCO: bool = False,
        use_NAS_ipv4_MTU_discovery: bool = False,
        use_local_addr_ind: bool = False,
        use_NAS_on_IPMTU_discovery: bool = False,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the PDPMixin (loaded by default)

        ---

        Creates a new packet data protocol (PDP).

        :param context_id: The PDP context ID (default 0)
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

    async def pdp_set_auth_params(self,
        context_id: int = 0,
        protocol: WalterModemPDPAuthProtocol = WalterModemPDPAuthProtocol.NONE,
        user_id: str | None = None,
        password: str | None = None,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Provided by the PDPMixin (loaded by default)

        ---

        Specify authentication parameters for the PDP.

        :param context_id: The PDP context ID (default 0)
        :protocol: The used authentication protocol.
        :type protocol: WalterModemPDPAuthProtocol
        :param username: Optional user to use for authentication.
        :param password: Optional password to use for authentication.
        :param rsp: Reference to a modem response instance.

        :return bool: True on success, False on failure
        """

    async def pdp_context_set_active(self,
        active: bool = True,
        context_id: int = 0,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the PDPMixin (loaded by default)

        ---

        Activates or deactivates a given PDP context.

        :param active: True to activate the PDP context, False to deactivate.
        :param context_id: The PDP context ID (default 0)
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def pdp_set_attach_state(self,
        attach: bool = True,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the PDPMixin (loaded by default)

        ---

        Attaches to or detaches from the currently active PDP context for packet domain service.

        :param attach: True to attach, False to detach.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def pdp_get_addressess(self,
        context_id: int = 0,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the PDPMixin (loaded by default)

        ---

        Retrieves the list of PDP addresses for the specified PDP context ID.

        :param context_id: The PDP context ID (default 0)
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

# ---
# SimNetworkMixin
# ---

    async def get_rssi(self, rsp: ModemRsp | None = None) -> bool:
        """
        Provided by the SimNetworkMixin (loaded by default)

        ---

        Retrieves the RSSI information.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def get_signal_quality(self, rsp: ModemRsp | None = None) -> bool:
        """
        Provided by the SimNetworkMixin (loaded by default)

        ---

        Retrieves information about the serving and neighbouring cells,
        including operator, cell ID, RSSI, and RSRP.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def get_cell_information(self,
        reports_type: WalterModemSQNMONIReportsType = WalterModemSQNMONIReportsType.SERVING_CELL,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the SimNetworkMixin (loaded by default)

        ---

        Retrieves the modem's identity details, including IMEI, IMEISV, and SVN.

        :param reports_type: The type of cell information to retreive,
        defaults to the cell which is currently serving the connection.
        :type reports_type: WalterModemSQNMONIReportsType
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def get_rat(self, rsp: ModemRsp | None = None) -> bool:
        """
        Provided by the SimNetworkMixin (loaded by default)

        ---

        Retrieves the Radio Access Technology (RAT) for the modem.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def set_rat(self, rat: int, rsp: ModemRsp | None = None) -> bool:
        """
        Provided by the SimNetworkMixin (loaded by default)

        ---

        Sets the Radio Access Technology (RAT) for the modem.

        :param rat: The new RAT
        :type rat: WalterModemRat
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def get_radio_bands(self, rsp: ModemRsp | None = None) -> bool:
        """
        Provided by the SimNetworkMixin (loaded by default)

        ---

        Retrieves the radio bands the modem is configured to use for network connection.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def get_sim_state(self, rsp: ModemRsp | None = None) -> bool:
        """
        Provided by the SimNetworkMixin (loaded by default)

        ---

        Retrieves the state of the SIM card.

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def unlock_sim(self, pin: str | None = None, rsp: ModemRsp | None = None) -> bool:
        """
        Provided by the SimNetworkMixin (loaded by default)

        ---

        Sets the SIM card's PIN code.
        The modem must be in FULL or NO_RF operational state.

        :param pin: The PIN code of the SIM card or NULL for no pin.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def set_network_selection_mode(self,
        mode: WalterModemNetworkSelMode = WalterModemNetworkSelMode.AUTOMATIC,
        operator_name: str = '',
        operator_format: WalterModemOperatorFormat = WalterModemOperatorFormat.LONG_ALPHANUMERIC,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the SimNetworkMixin (loaded by default)

        ---

        Sets the network selection mode for Walter.
        This command is only available when the modem is in the fully operational state.

        :param mode: The network selection mode.
        :type mode: WalterModemNetworkSelMode
        :param operator_name: The network operator name in case manual selection has been chosen.
        :param operator_format: The format in which the network operator name is passed.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

# ---
# SleepMixin
# ---

    async def config_PSM(self, *args, **kwargs):
        """DEPRECATED; use `config_psm()` instead"""
    
    async def config_EDRX(self, *args, **kwargs):
        """DEPRECATED; use `config_edrx()` instead"""

    async def config_psm(self,
        mode: int,
        periodic_TAU_s: int | None = None,
        active_time_s: int | None = None,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the SleepMixin (loaded by default)

        ---

        Configure PSM on the modem; enable, disable or reset PSM.

        "DISABLE_AND_DISCARD_ALL_PARAMS", sets manufacturer specific defaults if available.

        :param mode: Enable, Disable or Disable & Reset.
        :type mode: WalterModemPSMMode
        :param periodic_TAU_s: Optional; specify the Periodic TAU in seconds
        :param active_time_s: Optional; specify the Active Time in seconds

        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure 
        """

    async def config_edrx(self,
        mode: int,
        req_edrx_val: str | None = None,
        req_ptw: str | None = None,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the SleepMixin (loaded by default)

        ---

        Configure eDRX on the modem.

        "DISABLE_AND_DISCARD_ALL_PARAMS", sets manufacturer specific defaults if available.

        :param mode: Enable, Enable Unsocilited, Disable or Disable & Reset
        :type mode: WalterModemEDRXMode
        :param req_edrx_val: requested eDRX value
        :param req_ptw: requested ptw value
        :param rsp: Reference to a modem response instance
        """

# ---
# COAPMixin
# ---

    coap_context_states: tuple[ModemCoapContextState]
    """
    Provided by the CoapMixin

    ---

    State information about the CoAP contexts.
    The tuple index maps to the context ID.
    """

    async def coap_context_create(self,
        ctx_id: int,
        server_address: str | None = None,
        server_port: int | None = None,
        local_port: int | None = None,
        timeout: int = 20,
        dtls: bool = False,
        secure_profile_id: int | None = None,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the CoapMixin

        ---

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

    async def coap_context_close(self,
        ctx_id: int,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the CoapMixin

        ---

        Close a CoAP context.

        :param ctx_id: Context profile identifier (0, 1, 2)
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def coap_set_options(self,
        ctx_id: int,
        action: WalterModemCoapOptionAction,
        option: WalterModemCoapOption,
        value: str | WalterModemCoapContentType | tuple[str] | None = None,
        rsp: ModemRsp | None = None,
    ) -> bool:
        """
        Provided by the CoapMixin

        ---

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

    async def coap_set_header(self,
        ctx_id: int,
        msg_id: int | None = None,
        token: str | None = None,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the CoapMixin

        ---

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

    async def coap_send(self,
        ctx_id: int,
        m_type: WalterModemCoapType,
        method: WalterModemCoapMethod,
        data: bytes | bytearray | str | None = None,
        length: int | None = None,
        path: str | None = None,
        content_type: WalterModemCoapContentType | None = None,
        rsp: ModemRsp | None = None,
    ) -> bool:
        """
        Provided by the CoapMixin

        ---

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

    async def coap_receive_data(self,
        ctx_id: int,
        msg_id: int,
        length: int,
        max_bytes: int = 1024,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Provided by the CoapMixin

        ---

        Read the contents of a CoAP message after it's ring has been received.

        :param ctx_id: Context profile identifier (0, 1, 2)
        :param msg_id: CoAP message id
        :param length: The length of the payload to receive (the length of the ring)
        :param max_bytes: How many bytes of the message to payload to read at once
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def coap_receive_options(self,
        ctx_id: int,
        msg_id: int,
        max_options: int = 32,
        rsp: ModemRsp = None
    ) -> bool:
        """
        Provided by the CoapMixin

        ---

        Read the options of a CoAP message after it's ring has been received.

        :param ctx_id: Context profile identifier (0, 1, 2)
        :param msg_id: CoAP message id
        :param max_options: The maximum options that can be shown in the response (0-32)
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure     
        """

# ---
# GNSSMixin
# ---

    async def config_gnss(self, *args, **kwargs):
        """DEPRECATED; use `gnss_config()` instead."""
    
    async def get_gnss_assistance_status(self, *args, **kwargs):
        """DEPRECATED; use `gnss_assistance_get_status()` instead"""
    
    async def update_gnss_assistance(self, *args, **kwargs):
        """DEPRECATED; use `gnss_assistance_update()` instead"""
    
    async def perform_gnss_action(self, *args, **kwargs):
        """DEPRECATED; use `gnss_perform_action()` instead"""
    
    async def wait_for_gnss_fix(self):
        """DEPRECATED; use `gnss_wait_for_fix()` instead"""

    async def gnss_config(self,
        sens_mode: WalterModemGNSSSensMode = WalterModemGNSSSensMode.HIGH,
        acq_mode: WalterModemGNSSAcqMode = WalterModemGNSSAcqMode.COLD_WARM_START,
        loc_mode: WalterModemGNSSLocMode = WalterModemGNSSLocMode.ON_DEVICE_LOCATION,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the GNSSMixin

        ---

        Configures Walter's GNSS receiver with persistent settings that
        may need to be reset after a modem firmware upgrade.
        Can also adjust sensitivity mode between fixes.
        Recommended to run at least once before using GNSS.

        :param sens_mode: The sensitivity mode.
        :type sens_mode: WalterModemGNSSSensMode
        :param acq_mode: The acquisition mode.
        :type acq_mode: WalterModemGNSSAcqMode
        :param loc_mode: The GNSS location mode.
        :type loc_mode: WalterModemGNSSLocMode
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def gnss_assistance_get_status(self,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the GNSSMixin

        ---

        Retrieves the status of the assistance data currently loaded in the GNSS subsystem.

        :param rsp: reference to a modem response instance

        :return bool: true on success, False on failure
        """

    async def gnss_assistance_update(self,
        type: WalterModemGNSSAssistanceType = WalterModemGNSSAssistanceType.REALTIME_EPHEMERIS, 
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the GNSSMixin

        ---

        Connects to the cloud to download and update the GNSS subsystem
        with the requested assistance data.
        Real-time ephemeris being the most efficient type.

        :param type: The type of GNSS assistance data to update.
        :type type: WalterModemGNSSAssistanceType
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def gnss_perform_action(self,
        action: WalterModemGNSSAction = WalterModemGNSSAction.GET_SINGLE_FIX,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the GNSSMixin

        ---

        Programs the GNSS subsystem to perform a specified action.

        :param action: The action for the GNSS subsystem to perform.
        :type action: WalterModemGNSSAction
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def gnss_wait_for_fix(self) -> ModemGNSSFix:
        """
        Provided by the GNSSMixin

        ---

        Waits for a gnss fix before then returning it.

        :return ModemGNSSFix:
        """

# ---
# HTTPMixin
# ---

    async def http_did_ring(self, profile_id: int, rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the HTTPMixin

        ---

        Fetch http response to earlier http request, if any.

        :param profile_id: Profile for which to get response
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def http_config_profile(self,
        profile_id: int,
        server_address: str,
        port: int = 80,
        use_basic_auth: bool = False,
        auth_user: str = '',
        auth_pass: str = '',
        tls_profile_id: int | None = None,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the HTTPMixin

        ---

        Configures an HTTP profile. The profile is stored persistently in the modem, 
        allowing reuse without needing to reset parameters in future sketches. 
        TLS and file uploads/downloads are not supported.

        :param profile_id: HTTP profile id (0, 1 or 2)
        :param server_address: The server name to connect to.
        :param port: The port of the server to connect to.
        :param use_basic_auth: Set true to use basic auth and send username/pw.
        :param auth_user: Username.
        :param auth_pass: Password.
        :param tls_profile_id: If provided, TLS is used with the given profile.
        :type tls_profile_id: WalterModemTlsValidation
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def http_connect(self, profile_id: int, rsp: ModemRsp | None = None) -> bool:
        """
        Provided by the HTTPMixin

        ---

        Makes an HTTP connection using a predefined profile.
        This command is buggy and returns OK  while the connection is being 
        established in the background. 
        Poll http_get_context_status to check when the connection is ready.

        :param profile_id: HTTP profile id (0, 1 or 2)
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def http_close(self, profile_id: int, rsp: ModemRsp | None = None) -> bool:
        """
        Provided by the HTTPMixin

        ---

        Closes the HTTP connection for the given context.

        :param profile_id: HTTP profile id (0, 1 or 2)
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    def http_get_context_status(self, profile_id: int, rsp: ModemRsp | None = None) -> bool:
        """
        Provided by the HTTPMixin

        ---

        Gets the connection status of an HTTP context.
        Avoid connect and disconnect operations if possible (see implementation comments).

        :param profile_id: HTTP profile id (0, 1 or 2)
        :param rsp: Reference to a modem response instance

        :return bool:
        """

    async def http_query(self,
        profile_id: int,
        uri: str,
        query_cmd: WalterModemHttpQueryCmd = WalterModemHttpQueryCmd.GET,
        extra_header_line: str | None = None,
        rsp: ModemRsp  | None = None
    ) -> bool:
        """
        Provided by the HTTPMixin

        ---

        Performs an HTTP GET, DELETE, or HEAD request.
        No need to open the connection with the buggy `http_connect` command
        unless TLS and a private key are required.

        :param profile_id: HTTP profile id (0, 1 or 2)
        :param uri: The URI
        :param query_cmd: The http request method (get, delete or head)
        :type query_cmd: WalterModemHttpQueryCmd
        :extra_header_line: additional lines to be placed in the request's header
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def http_send(self,
        profile_id: int,
        uri: str,
        data,
        send_cmd: WalterModemHttpSendCmd = WalterModemHttpSendCmd.POST,
        post_param: WalterModemHttpPostParam = WalterModemHttpPostParam.UNSPECIFIED,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the HTTPMixin

        ---

        Performs an HTTP POST or PUT request.
        No need to open the connection with the buggy `http_connect` command
        unless TLS and a private key are required.

        :param profile_id: HTTP profile id (0, 1 or 2)
        :param uri: The URI
        :param data: Data to be sent to the server
        :param send_cmd: The http request method (post, put)
        :type send_cmd: WalterModemHttpSendCmd
        :param post_param: content type
        :type post_param: WalterModemHttpPostParam
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

# ---
# MQTT
# ---

    mqtt_status: WalterModemMqttState
    """Status of the MQTT connection"""

    async def mqtt_config(self,
        client_id: str = get_mac(),
        user_name: str = '',
        password: str = '',
        tls_profile_id: int | None = None,
        library_message_buffer: int = 16,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the MQTTMixin

        ---

        Configure the MQTT client without connecting.

        :param client_id: MQTT client ID to use (defaults to the device MAC).
        :param user_name: Optional username for authentication.
        :param password: Optional password for authentication.
        :param tls_profile_id: Optional TLS profile ID to use.
        :param library_message_buffer: Size of the library's internal MQTT message buffer 
            (defaults to 16).
            This buffer stores metadata for received messages but does not hold their payloads.
            The modem itself supports up to 100 messages, but increasing this buffer significantly
            may consume excessive memory and is not recommended.
        :param rsp: Reference to a modem response instance.

        :return: True on success, False on failure.
        """

    async def mqtt_connect(self,
        server_name: str,
        port: int,
        keep_alive: int = 60,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the MQTTMixin

        ---

        Initialize MQTT and establish a connection.

        :param server_name: MQTT broker hostname
        :param port: Port to connect to
        :param keep_alive: Maximum keepalive time (in seconds), defaults to 60
        :param rsp: Reference to a modem response instance

        :return: True on success, False on failure
        """

    async def mqtt_disconnect(self, rsp: ModemRsp | None = None) -> bool:
        """
        Disconnect from an MQTT broker

        :param rsp: Reference to a modem response instance

        :return: True on success, False on failure
        """

    async def mqtt_publish(self,
        topic: str,
        data,
        qos: int,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the MQTTMixin

        ---

        Publish the passed data on the given MQTT topic using the earlier eastablished connection.

        :param topic: The topic to publish on
        :param data: The data to publish
        :param qos: Quality of Service (0: at least once, 1: at least once, 2: exactly once)
        :param rsp: Reference to a modem response instance

        :return: True on success, False on failure
        """

    async def mqtt_subscribe(self,
        topic: str,
        qos: int = 1,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Provided by the MQTTMixin

        ---

        Subscribe to a given MQTT topic using the earlier established connection.

        :param topic: The topic to subscribe to
        :param qos: Quality of Service (0: at least once, 1: at least once, 2: exactly once)
        :param rsp: Reference to a modem response instance

        :return: True on success, False on failure
        """

    async def mqtt_did_ring(self,
        msg_list: list,
        topic: str | None = None,
        rsp: ModemRsp | None = None
        ) -> bool:
        """
        Provided by the MQTTMixin

        ---

        Poll if the modem has reported any incoming MQTT messages received on topics
        that we are subscribed on.

        WARNING: No more than 1 message with QoS 0 are stored in the buffer,
        every new message with QoS 0 overwrites the previous
        (this only applies to messages with QoS 0)

        :param msg_list: Refence to a list where the received messages will be put.
        :param topic: The exact topic to filter on, leave as None for all topics
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

# ---
# SocketMixin
# ---

    async def create_socket(self, *args, **kwargs):
        """DEPRECATED; use `socket_create()` instead"""
    
    async def connect_socket(self, *args, **kwargs):
        """DEPRECATED; use `socket_connect()` instead"""
    
    async def close_socket(self, *args, **kwargs):
        """DEPRECATED; use `socket_close()` instead"""

    async def socket_create(self,
        pdp_context_id: int = 1,
        mtu: int = 300,
        exchange_timeout: int = 90,
        conn_timeout: int = 60,
        send_delay_ms: int = 5000,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Creates a new socket in a specified PDP context.
        Additional socket settings can be applied.
        The socket can be used for communication.

        :param pdp_context_id: The PDP context id.
        :param: mtu: The Maximum Transmission Unit used by the socket.
        :param exchange_timeout: The maximum number of seconds this socket can be inactive.
        :param conn_timeout: The maximum number of seconds this socket is allowed to try to connect.
        :param send_delay_ms: The number of milliseconds send delay.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def socket_connect(self,
        remote_host: str,
        remote_port: int,
        local_port: int = 0,
        socket_id: int = -1,
        protocol: int = WalterModemSocketProto.UDP,
        accept_any_remote: WalterModemSocketAcceptAnyRemote = WalterModemSocketAcceptAnyRemote.DISABLED,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Connects a socket to a remote host,
        allowing data exchange once the connection is successful.

        :param remote_host: The remote IPv4/IPv6 or hostname to connect to.
        :param remote_port: The remote port to connect on.
        :param local_port: The local port in case of an UDP socket.
        :param socket_id: The id of the socket to connect or -1 to re-use the last one.
        :param protocol: The protocol to use, UDP by default.
        :type protocol: WalterModemSocketProto
        :param accept_any_remote: How to accept remote UDP packets.
        :type accept_any_remote: WalterModemSocketAcceptAnyRemote
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def socket_close(self,
        socket_id: int = -1,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Closes a socket. Sockets can only be closed when suspended; 
        active connections cannot be closed.        

        :param socket_id: The id of the socket to close or -1 to re-use the last one.
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def socket_send(self,
        data,
        socket_id: int = -1,
        rai: WalterModemRai = WalterModemRai.NO_INFO,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Sends data over a socket.

        :param data: The data to send.
        :param socket_id: The id of the socket to close or -1 to re-use the last one.
        :param rai: The release assistance information.
        :type rai: WalterModemRai
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
# ---
# TLSCertsMixin
# ---

    async def tls_config_profile(self,
        profile_id: int,
        tls_version: int,
        tls_validation: int,
        ca_certificate_id: int | None = None,
        client_certificate_id: int | None = None,
        client_private_key: int | None = None,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Configures TLS profiles in the modem,
        including optional client authentication certificates, validation levels, and TLS version. 
        This should be done in an initializer sketch, 
        allowing later HTTP, MQTT, CoAP, or socket sessions to use the preconfigured profile IDs.

        :param profile_id: Security profile id (1-6)
        :param tls_version: TLS version
        :type tls_version: WalterModemTlsVersion
        :param tls_validation: TLS validation level: nothing, URL, CA+period or all
        :type tls_validation: WalterModemTlsValidation
        :param ca_certificate_id: CA certificate for certificate validation (0-19)
        :param client_certificate_id: Client TLS certificate index (0-19)
        :param client_private_key: Client TLS private key index (0-19)
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """

    async def tls_write_credential(self,
        is_private_key: bool,
        slot_idx: int,
        credential,
        rsp: ModemRsp | None = None
    ) -> bool:
        """
        Upload key or certificate to modem NVRAM.

        It is recommended to save credentials in index 10-19 to avoid overwriting preinstalled
        certificates and (if applicable) BlueCherry cloud platform credentials.

        :param is_private_key: True if it's a private key, False if it's a certificate
        :param slot_idx: Slot index within the modem NVRAM keystore
        :param credential: NULL-terminated string containing the PEM key/cert data
        :param rsp: Reference to a modem response instance

        :return bool: True on success, False on failure
        """
