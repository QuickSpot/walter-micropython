from walter_modem.coreStructs import *
from walter_modem.coreEnums import *
from walter_modem.utils import *

from walter_modem.mixins._default_pdp import *
from walter_modem.mixins._default_sim_network import *
from walter_modem.mixins._default_power_saving import *
from walter_modem.mixins.coap import *
from walter_modem.mixins.gnss import *
from walter_modem.mixins.http import *
from walter_modem.mixins.mqtt import *
from walter_modem.mixins.socket import *
from walter_modem.mixins.tls_certs import *

class Modem():
    """
    Singleton factory for constructing a modem instance with the given mixins.

    This class enforces the singleton pattern, ensuring that only one modem instance
    can exist at any time. Attempts to create additional instances will always return
    the original instance.

    The library comes with a variety of mixins (e.g. SocketMixin, HTTPMixin, CoapMixin, ...)
    that can be inlcuded when constructing the modem-instance. By only loading the mixins you need,
    the library's memory footprint is kept small.

    For detailed information information on creating custom mixins,
    refer to the developer documentation on the GitHub wiki.

    PDP context, SIM & network and power saving mixins are included by default but can be turned of
    individually, see params.
    """

    def __new__(cls,
    *mixins,
    load_default_pdp_mixin=True,
    load_default_sim_network_mixin=True,
    load_default_power_saving_mixin=True
    ) -> Modem:
        """
        Usage:
        >>> # Initialise with default mixins:
        >>> from walter_modem import Modem
        >>> modem = Modem()
        >>> 
        >>> # Initialise with default + CoAP Mixin
        >>> from walter_modem import Modem
        >>> from walter_modem.mixins.coap import *
        >>> modem = Modem(CoapMixin)

        Args:
            *mixins:
                Mixin classes to load into the modem library.
            load_default_pdp_mixin (bool, optional):
                If True, includes the default PDP mixin.
                Defaults to True.
            load_default_sim_network_mixin (bool, optional):
                If True, includes the default SIM/network mixin.
                Defaults to True.
            load_default_sleep_mixin (bool, optional):
                If True, includes the default sleep mixin.
                Defaults to True.

        Raises:
            TypeError: If any provided mixin does not inherit from ModemCore.
        """

# ---
# CORE
# ---

    async def begin(self, uart_debug: bool = False):
        """Inlcuded in Core

        ---

        Begin the modem library's processes.

        This method is idempotent as the lirary should only have at most 1 running instance.

        Args:
            uart_debug (bool, optional):
                include the UART TX & RX in the debug logs.
                Defaults to False.

        Raises:
            RuntimeError: If modem reset fails
            RuntimeError: If configuring CME error reports fails
            RuntimeError: If configuring cereg reports fails
        """

    async def reset(self) -> bool:
        """Inlcuded in Core

        ---

        Physically reset the modem and wait for it to start.

        All connections will be lost when this function is called.

        The function will fail when the modem doesn't start after the reset.

        Returns:
            bool: True on success, False on failure
        """

    async def soft_reset(self) -> bool:
        """Inlcuded in Core

        ---

        Perform a soft reset on the modem, wait for it to complete.

        The method will fail when the modem doesn't reset.

        Returns:
            bool: True on success, False on failure
        """

    async def check_comm(self) -> bool:
        """Inlcuded in Core

        ---

        Sends the 'AT' command to check if the modem responds with 'OK',
        verifying communication between the ESP32 and the modem.

        Returns:
            bool: True on success, False on failure
        """

    async def get_clock(self, rsp: ModemRsp | None = None) -> bool:
        """Inlcuded in Core

        ---

        Retrieves the current time and date from the modem.

        Args:
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """
    
    async def config_cme_error_reports(self,
        reports_type: WalterModemCMEErrorReportsType = WalterModemCMEErrorReportsType.NUMERIC,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Inlcuded in Core

        ---

        Configures the CME error report type.

        By default, errors are enabled and numeric.
        Changing this may affect error reporting.

        Args:
            reports_type (int, optional):
                The CME error report type.
                Defaults to WalterModemCMEErrorReportsType.NUMERIC.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """
    
    async def config_cereg_reports(self,
        reports_type: WalterModemCEREGReportsType = WalterModemCEREGReportsType.ENABLED,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Inlcuded in Core

        ---

        Configures the CEREG status report type.

        By default, reports are enabled with minimal operational info.
        Changing this may affect library functionality.

        Args:
            reports_type (int, optional):
                The CEREG status reports type.
                Defaults to WalterModemCEREGReportsType.ENABLED.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def get_op_state(self, rsp: ModemRsp | None = None) -> bool:
        """Inlcuded in Core

        ---

        Retrieves the modem's current operational state.

        Args:
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def set_op_state(self,
        op_state: WalterModemOpState,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Inlcuded in Core

        ---

        Sets the operational state of the modem.

        Args:
            op_state (WalterModemOpState):
                The new operational state of the modem
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    def get_network_reg_state(self) -> int:
        """Inlcuded in Core

        ---

        Get the network registration state.
        This is buffered by the library and thus instantly available.

        Returns:
            int: The current modem registration state
        """

    def sleep(self,
        sleep_time_ms: int,
        light_sleep: bool = False,
        persist_mqtt_subs: bool = False
    ):
        """Inlcuded in Core

        ---

        Put the device to light or deepsleep.

        Using this method ensures the modem library is aware of the sleep,
        allowing it to put the modem-chip to sleep as well,
        and optionally allowing it to persist certain information.

        Args:
            sleep_time_ms (int):
                The time to sleep for in ms.
            light_sleep (bool, optional):
                True for lightsleep, False for deepsleep.
                Defaults to False.
            persist_mqtt_subs (bool, optional):
                Whether or not to persist the MQTT subscriptions in RTC.
                Defaults to False.
        """

    def register_application_queue_rsp_handler(self, start_pattern: bytes, handler: callable):
        """Inlcuded in Core

        ---

        Register your own queue response handler.

        WARNING: Do not use unless you know what you're doing!
        Wrong use can have unwanted consequences.

        Args:
            start_pattern (bytes):
                The start pattern to call your handler on if matched.
            handler (callable):
                A synchronous method to be called, signature: handler(cmd, at_rsp)
        """
    
    def unregister_application_queue_rsp_handler(self, handler: callable):
        """Inlcuded in Core

        ---

        Unregister previously registered queue response handler(s) based on method reference.

        WARNING: Do not use unless you know what you're doing!
        Wrong use can have unwanted consequences.

        Args:
            handler (callable):
                The handler to unregister
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

        """Provided by the PDPMixin (loaded by default)

        ---

        Creates a new packet data protocol (PDP).

        Args:
            context_id (int, optional):
                The PDP context ID.
                Defaults to 1.
            apn (str, optional):
                The access point name. 
                Defaults to ''.
            pdp_type (WalterModemPDPType, optional):
                The type of PDP context to create. 
                Defaults to WalterModemPDPType.IP.
            pdp_address (str, optional):
                Optional PDP address. 
                Defaults to None.
            header_comp (WalterModemPDPHeaderCompression, optional):
                The type of header compression to use.
                Defaults to WalterModemPDPHeaderCompression.OFF.
            data_comp (WalterModemPDPDataCompression, optional):
                The type of data compression to use.
                Defaults to WalterModemPDPDataCompression.OFF.
            ipv4_alloc_method (WalterModemPDPIPv4AddrAllocMethod, optional):
                The IPv4 alloction method.
                Defaults to WalterModemPDPIPv4AddrAllocMethod.DHCP.
            request_type (WalterModemPDPRequestType, optional):
                The type of PDP requests.
                Defaults to WalterModemPDPRequestType.NEW_OR_HANDOVER.
            pcscf_method (WalterModemPDPPCSCFDiscoveryMethod, optional):
                The method to use for P-CSCF discovery.
                Defaults to WalterModemPDPPCSCFDiscoveryMethod.AUTO.
            for_IMCN (bool, optional):
                Set when this PDP ctx is used for IM CN signalling.
                Defaults to False.
            use_NSLPI (bool, optional):
                Set when NSLPI is used.
                Defaults to False.
            use_secure_PCO (bool, optional):
                Set to use secure protocol config options.
                Defaults to False.
            use_NAS_ipv4_MTU_discovery (bool, optional):
                Set to use NAS for IPv4 MTU discovery.
                Defaults to False.
            use_local_addr_ind (bool, optional):
                Set when local IPs are supported in the TFT.
                Defaults to False.
            use_NAS_on_IPMTU_discovery (bool, optional):
                Set for NAS based no-IP MTU discovery.
                Defaults to False.
            rsp (ModemRsp | None, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def pdp_set_auth_params(self,
        context_id: int = 0,
        protocol: WalterModemPDPAuthProtocol = WalterModemPDPAuthProtocol.NONE,
        user_id: str | None = None,
        password: str | None = None,
        rsp: ModemRsp = None
    ) -> bool:
        """Provided by the PDPMixin (loaded by default)

        ---

        Specify authentication parameters for the PDP.

        Args:
            context_id (int, optional):
                The PDP context ID.
                Defaults to 1.
            protocol (WalterModemPDPAuthProtocol, optional):
                The used authentication protocol.
                Defaults to WalterModemPDPAuthProtocol.NONE.
            user_id (str, optional):
                User to use for authentication.
                Defaults to None.
            password (str, optional):
                Password to use for authentication.
                Defaults to None.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def pdp_context_set_active(self,
        active: bool = True,
        context_id: int = 0,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Provided by the PDPMixin (loaded by default)

        ---

        Activates or deactivates a given PDP context.

        Args:
            active (bool, optional):
                True to activate the PDP context, False to deactivate.
                Defaults to True.
            context_id (int, optional):
                The PDP context ID.
                Defaults to 1.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def pdp_set_attach_state(self,
        attach: bool = True,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Provided by the PDPMixin (loaded by default)

        ---

        Attaches to or detaches from the currently active PDP context for packet domain service.

        Args:
            attach (bool, optional):
                True to attach, False to detach.
                Defaults to True.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure

        :param attach: .
        :param rsp: 

        :return bool: 
        """

    async def pdp_get_addressess(self,
        context_id: int = 0,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Provided by the PDPMixin (loaded by default)

        ---

        Retrieves the list of PDP addresses for the specified PDP context ID.

        Args:
            context_id (int, optional):
                The PDP context ID.
                Defaults to 1.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

# ---
# PowerSavingMixin
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
        """Provided by the PowerSavingMixin (loaded by default)

        ---

        Configure PSM on the modem; enable, disable or reset PSM.

        What you get from the network may not be exactly the same as what was requested.

        "DISABLE_AND_DISCARD_ALL_PARAMS", sets manufacturer specific defaults if available.
    
        Args:
            mode (WalterModemPSMMode):
                Enable, Disable or Disable & Reset
            periodic_TAU_s (int, optional):
                specify the Periodic TAU in seconds.
                Defaults to None.
            active_time_s (int, optional):
                specify the Active Time in seconds.
                Defaults to None.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure 
        """

    async def config_edrx(self,
        mode: int,
        req_edrx_val: str | None = None,
        req_ptw: str | None = None,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Provided by the PowerSavingMixin (loaded by default)

        ---

        Configure eDRX on the modem.

        What you get from the network may not be exactly the same as what was requested.

        "DISABLE_AND_DISCARD_ALL_PARAMS", sets manufacturer specific defaults if available.

        Args
            mode (WalterModemEDRXMode):
                Enable, Enable Unsocilited, Disable or Disable & Reset.
            req_edrx_val (str, optional):
                Requested eDRX value.
                Defaults to None.
            param req_ptw (str, optional):
                Requested ptw value.
                Defaults to None
            param rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure 
        """

# ---
# SimNetworkMixin
# ---

    async def get_rssi(self, rsp: ModemRsp | None = None) -> bool:
        """Provided by the SimNetworkMixin (loaded by default)

        ---

        Retrieves the RSSI information.

        Args:
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure 
        """

    async def get_signal_quality(self, rsp: ModemRsp | None = None) -> bool:
        """Provided by the SimNetworkMixin (loaded by default)

        ---

        Retrieves information about the serving and neighbouring cells,
        including operator, cell ID, RSSI, and RSRP.

        Args:
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure 
        """

    async def get_cell_information(self,
        reports_type: WalterModemSQNMONIReportsType = WalterModemSQNMONIReportsType.SERVING_CELL,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Provided by the SimNetworkMixin (loaded by default)

        ---

        Retrieves the modem's identity details, including IMEI, IMEISV, and SVN.

        Args:
            reports_type (WalterModemSQNMONIReportsType, optional):
                The type of cell information to retreive.
                Defaults to WalterModemSQNMONIReportsType.SERVING_CELL.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure 
        """

    async def get_rat(self, rsp: ModemRsp | None = None) -> bool:
        """
        Provided by the SimNetworkMixin (loaded by default)

        ---

        Retrieves the Radio Access Technology (RAT) for the modem.

        Args:
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure 
        """

    async def set_rat(self, rat: int, rsp: ModemRsp | None = None) -> bool:
        """Provided by the SimNetworkMixin (loaded by default)

        ---

        Sets the Radio Access Technology (RAT) for the modem.

        Args:
            rat (WalterModemRat):
                The new RAT
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure 
        """

    async def get_radio_bands(self, rsp: ModemRsp | None = None) -> bool:
        """Provided by the SimNetworkMixin (loaded by default)

        ---

        Retrieves the radio bands the modem is configured to use for network connection.

        Args:
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure 
        """

    async def get_sim_state(self, rsp: ModemRsp | None = None) -> bool:
        """Provided by the SimNetworkMixin (loaded by default)

        ---

        Retrieves the state of the SIM card.

        Args:
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure 
        """

    async def unlock_sim(self, pin: str | None = None, rsp: ModemRsp | None = None) -> bool:
        """Provided by the SimNetworkMixin (loaded by default)

        ---

        Sets the SIM card's PIN code.

        The modem must be in FULL or NO_RF operational state.

        Args:
            pin (str, optional):
                The PIN code of the SIM card or NULL for no pin.
                Defaults to None.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def set_network_selection_mode(self,
        mode: WalterModemNetworkSelMode = WalterModemNetworkSelMode.AUTOMATIC,
        operator_name: str = '',
        operator_format: WalterModemOperatorFormat = WalterModemOperatorFormat.LONG_ALPHANUMERIC,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Provided by the SimNetworkMixin (loaded by default)

        ---

        Sets the network selection mode for Walter.

        This command is only available when the modem is in the fully operational state.

        Args:
            mode (WalterModemNetworkSelMode, optional):
                The network selection mode.
                Defaults to WalterModemNetworkSelMode.AUTOMATIC.
            operator_name (str, optional):
                The network operator name in case manual selection has been chosen.
                Defaults to ''.
            operator_format (WalterModemOperatorFormat, optional):
                The format in which the network operator name is passed.
                Defaults to WalterModemOperatorFormat.LONG_ALPHANUMERIC.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

# ---
# COAPMixin
# ---

    coap_context_states: tuple[ModemCoapContextState]
    """Provided by the CoapMixin

    ---

    State information about the CoAP contexts.

    TIP: The tuple index maps to the context ID.
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
        """Provided by the CoapMixin

        ---

        Create a CoAP context, required to send, receive & set CoAP options.

        If the server_address & server_port are provided, a connection attempt is made.

        If server_address & server_port are omitted and only local_port is provided,
        the context is created in listen mode, waiting for an incoming connection.

        Args:
            ctx_id (int):
                Context profile identifier (0, 1, 2)
            server_address (str, optional):
                IP addr/hostname of the CoAP server.
                Defaults to None.
            server_port (int, optional):
                The UDP remote port of the CoAP server.
                Defaults to None.
            local_port (int, optional):
                The UDP local port, if omitted, a randomly available port is assigned (recommended).
                Defaults to None.
            timeout (int, optional):
                The time (in seconds) to wait for a response from the CoAP server
                before aborting: 1-120.
                (independent of the ACK_TIMEOUT used for retransmission).
                Defaults to 20.
            dtls (bool, optional):
                Whether or not to use DTLS encryption.
                Defaults to False.
            secure_profile_id (int, optional):
                The SSL/TLS security profile configuration (ID) to use.
                Defaults to None.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def coap_context_close(self,
        ctx_id: int,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Provided by the CoapMixin

        ---

        Close a CoAP context.

        Args:
            ctx_id (int):
                Context profile identifier (0, 1, 2)
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure 
        """

    async def coap_set_options(self,
        ctx_id: int,
        action: WalterModemCoapOptionAction,
        option: WalterModemCoapOption,
        value: str | WalterModemCoapContentType | tuple[str] | None = None,
        rsp: ModemRsp | None = None,
    ) -> bool:
        """Provided by the CoapMixin

        ---

        Configure CoAP options for the next message to be sent.

        Options are to be configured one at a time.

        For repeatable options, up to 6 values can be provided (the order is respected).
        The repeatable options are:
        IF_MATCH, ETAG, LOCATION_PATH, LOCATION_PATH, URI_PATH, URI_QUERY, LOCATION_QUERY

        The values are to be passed along as extra params.

        Args:
            ctx_id (int):
                Context profile identifier (0, 1, 2)
            action (WalterModemCoapOptionAction):
                Action to perform
            option (WalterModemCoapOption):
                The option to perform the action on
            value (str | WalterModemCoapContentType | tuple[str], optional):
                The value(s) of the options.
                Defaults to None.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def coap_set_header(self,
        ctx_id: int,
        msg_id: int | None = None,
        token: str | None = None,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Provided by the CoapMixin

        ---

        Configure the coap header for the next message to be sent

        If only msg_id is set, the CoAP client sets a random token value.
        If only token is set, the CoAP client sets a random msg_id value.

        Args:
            ctx_id (int):
                Context profile identifier (0, 1, 2)
            msg_id (int, optional):
                Message ID of the CoAP header (0-65535)
                Defaults to None.
            token (str, optional):
                Hexidecimal format, token to be used in the CoAP header,
                specify: "NO_TOKEN" for a header without token.
                Defaults to None.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
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
        """Provided by the CoapMixin

        ---

        Send data over CoAP, if no data is sent, length must be set to zero.

        Args:
            ctx_id (int):
                Context profile identifier (0, 1, 2)
            m_type (WalterModemCoapType):
                CoAP message type
            method (WalterModemCoapMethod):
                GET, POST, PUT, DELETE
            data (bytes | bytearray | str | None, optional):
                Binary data to send (bytes, bytearray) or string (will be UTF-8 encoded).
                Defaults to None.
            length (int, optional):
                Length of the payload (auto-calculated if not provided).
                Defaults to None.
            path (str, optional):
                The URI_PATH to send on, this will set the path in the CoAP options before sending.
                Defaults to None.
            content_type (WalterModemCoapContentType, optional):
                The content_type, this will set the content type in the CoAP options before sending.
                Defaults to None.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def coap_receive_data(self,
        ctx_id: int,
        msg_id: int,
        length: int,
        max_bytes: int = 1024,
        rsp: ModemRsp = None
    ) -> bool:
        """Provided by the CoapMixin

        ---

        Read the contents of a CoAP message after it's ring has been received.

        Args:
            ctx_id (int):
                Context profile identifier (0, 1, 2)
            msg_id (int):
                CoAP message ID
            length (int):
                The length of the payload to receive (the length of the ring)
            max_bytes (int, optional):
                How many bytes of the message to payload to read at once.
                Defaults to 1024.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def coap_receive_options(self,
        ctx_id: int,
        msg_id: int,
        max_options: int = 32,
        rsp: ModemRsp = None
    ) -> bool:
        """Provided by the CoapMixin

        ---

        Read the options of a CoAP message after it's ring has been received.

        Args:
            ctx_id (int): Context profile identifier (0, 1, 2)
            msg_id (int): CoAP message ID
            max_options (int, optional):
                The maximum options that can be shown in the response (0-32).
                Defaults to 32.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
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
        """Provided by the GNSSMixin

        ---

        Configures Walter's GNSS receiver with persistent settings that
        may need to be reset after a modem firmware upgrade.

        Can also adjust sensitivity mode between fixes.
        Recommended to run at least once before using GNSS.

        Args:
            sens_mode (WalterModemGNSSSensMode, optional):
                The sensitivity mode.
                Defaults to WalterModemGNSSSensMode.HIGH.
            acq_mode (WalterModemGNSSAcqMode, optional):
                The acquisition mode.
                Defaults to WalterModemGNSSAcqMode.COLD_WARM_START.
            loc_mode (WalterModemGNSSLocMode, optional):
                The GNSS location mode.
                Defaults to WalterModemGNSSLocMode.ON_DEVICE_LOCATION.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def gnss_assistance_get_status(self,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Provided by the GNSSMixin

        ---

        Retrieves the status of the assistance data currently loaded in the GNSS subsystem.

        Args:
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
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

        Args:
            type (WalterModemGNSSAssistanceType, optional):
                The type of GNSS assistance data to update.
                Defaults to WalterModemGNSSAssistanceType.REALTIME_EPHEMERIS.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def gnss_perform_action(self,
        action: WalterModemGNSSAction = WalterModemGNSSAction.GET_SINGLE_FIX,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Provided by the GNSSMixin

        ---

        Programs the GNSS subsystem to perform a specified action.

        Args:
            action (WalterModemGNSSAction, optional):
                The action for the GNSS subsystem to perform.
                Defaults to WalterModemGNSSAction.GET_SINGLE_FIX.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def gnss_wait_for_fix(self) -> ModemGNSSFix:
        """Provided by the GNSSMixin

        ---

        Waits for a gnss fix before then returning it.

        Returns:
            ModemGNSSFix:
        """

# ---
# HTTPMixin
# ---

    async def http_did_ring(self, profile_id: int, rsp: ModemRsp | None = None
    ) -> bool:
        """Provided by the HTTPMixin

        ---

        Fetch http response to earlier http request, if any.

        Args:
            profile_id (int):
                HTTP profile ID (0, 1 or 2)
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
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
        """Provided by the HTTPMixin

        ---

        Configures an HTTP profile.
        
        The profile is stored persistently in the modem, 
        allowing reuse without needing to reset parameters in future sketches. 

        TLS and file uploads/downloads are not supported.

        Args:
            profile_id (int):
                HTTP profile ID (0, 1 or 2)
            server_address (str):
                The server name to connect to
            port (int, optional):
                The port of the server to connect to.
                Defaults to 80.
            use_basic_auth (bool, optional):
                Set true to use basic auth and send username/pw.
                Defaults to False.
            auth_user (str, optional):
                Username.
                Defaults to ''.
            auth_pass (str, optional):
                Password.
                Defaults to ''.
            tls_profile_id (int, optional):
                If provided, TLS is used with the given profile.
                Defaults to None.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def http_connect(self, profile_id: int, rsp: ModemRsp | None = None) -> bool:
        """Provided by the HTTPMixin

        ---

        Makes an HTTP connection using a predefined profile.

        This command is buggy and returns OK while the connection is being 
        established in the background.
        Poll http_get_context_status to check when the connection is ready.

        Args:
            profile_id (int):
                HTTP profile ID (0, 1 or 2)
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def http_close(self, profile_id: int, rsp: ModemRsp | None = None) -> bool:
        """Provided by the HTTPMixin

        ---

        Closes the HTTP connection for the given context.

        Args:
            profile_id (int):
                HTTP profile ID (0, 1 or 2)
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    def http_get_context_status(self, profile_id: int, rsp: ModemRsp | None = None) -> bool:
        """Provided by the HTTPMixin

        ---

        Gets the connection status of an HTTP context.

        Avoid connect and disconnect operations if possible (see implementation comments).

        Args:
            profile_id (int):
                HTTP profile ID (0, 1 or 2)
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def http_query(self,
        profile_id: int,
        uri: str,
        query_cmd: WalterModemHttpQueryCmd = WalterModemHttpQueryCmd.GET,
        extra_header_line: str | None = None,
        rsp: ModemRsp  | None = None
    ) -> bool:
        """Provided by the HTTPMixin

        ---

        Performs an HTTP GET, DELETE, or HEAD request.

        No need to open the connection with the buggy `http_connect` command
        unless TLS and a private key are required.

        Args:
            profile_id (int):
                HTTP profile id (0, 1 or 2)
            uri (str):
                The URI
            query_cmd (WalterModemHttpQueryCmd, optional):
                The http request method (get, delete or head).
                Defaults to WalterModemHttpQueryCmd.GET.
            extra_header_line (str, optional):
                Additional lines to be placed in the request's header.
                Defaults to None.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def http_send(self,
        profile_id: int,
        uri: str,
        data,
        send_cmd: WalterModemHttpSendCmd = WalterModemHttpSendCmd.POST,
        post_param: WalterModemHttpPostParam = WalterModemHttpPostParam.UNSPECIFIED,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Provided by the HTTPMixin

        ---

        Performs an HTTP POST or PUT request.

        No need to open the connection with the buggy `http_connect` command
        unless TLS and a private key are required.

        Args:
            profile_id (int):
                HTTP profile ID (0, 1 or 2)
            uri (str):
                The URI
            data (bytes | bytearray | str):
                Data to be sent to the server
            send_cmd (WalterModemHttpSendCmd, optional):
                The http request method (post, put).
                Defaults to WalterModemHttpSendCmd.POST.
            post_param (WalterModemHttpPostParam, optional):
                Content type.
                Defaults to WalterModemHttpPostParam.UNSPECIFIED.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
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
        """Provided by the MQTTMixin

        ---

        Configure the MQTT client without connecting.

        Args:
            client_id (str, optional):
                MQTT client ID to use.
                Defaults to the device MAC.
            user_name (str, optional):
                Optional username for authentication.
                Defaults to ''.
            password (str, optional):
                Optional password for authentication.
                Defaults to ''.
            tls_profile_id (int, optional):
                Optional TLS profile ID to use.
                Defaults to None.
            library_message_buffer (int, optional):
                Size of the library's internal MQTT message buffer.
                This buffer stores metadata for received messages but does not hold their payloads.
                The modem itself supports up to 100 messages, increasing this buffer significantly
                may consume excessive memory and is not recommended.
                Defaults to 16.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def mqtt_connect(self,
        server_name: str,
        port: int,
        keep_alive: int = 60,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Provided by the MQTTMixin

        ---

        Initialize MQTT and establish a connection.

        Args:
            server_name (str):
                MQTT broker hostname
            port (int):
                Port to connect to
            keep_alive (int, optional):
                Maximum keepalive time (in seconds).
                Defaults to 60.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def mqtt_disconnect(self, rsp: ModemRsp | None = None) -> bool:
        """Provided by the MQTTMixin

        ---
        
        Disconnect from an MQTT broker

        Args:
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def mqtt_publish(self,
        topic: str,
        data,
        qos: int,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Provided by the MQTTMixin

        ---

        Publish the passed data on the given MQTT topic using the earlier eastablished connection.

        Args:
            topic (str):
                The topic to publish on
            data (bytes | bytearray | str):
                The data to publish
            qos (int):
                Quality of Service (0: at least once, 1: at least once, 2: exactly once)
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def mqtt_subscribe(self,
        topic: str,
        qos: int = 1,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Provided by the MQTTMixin

        ---

        Subscribe to a given MQTT topic using the earlier established connection.

        Args:
            topic (str):
                The topic to subscribe to
            qos (int, optional):
                Quality of Service (0: at least once, 1: at least once, 2: exactly once).
                Defaults to 1.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def mqtt_did_ring(self,
        msg_list: list,
        topic: str | None = None,
        rsp: ModemRsp | None = None
        ) -> bool:
        """Provided by the MQTTMixin

        ---

        Poll if the modem has reported any incoming MQTT messages received on topics
        that we are subscribed on.

        No more than 1 message with QoS 0 are stored in the buffer,
        every new message with QoS 0 overwrites the previous
        (this only applies to messages with QoS 0)

        Args:
            msg_list (list):
                Refence to a list where the received messages will be put.
            topic (str, optional):
                The exact topic to filter on, leave as None for all topics.
                Defaults to None.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
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
        """Provided by the SocketMixin

        ---

        Creates a new socket in a specified PDP context.

        Additional socket settings can be applied.
        The socket can be used for communication.

        Args:
            pdp_context_id (int, optional):
                The PDP context ID.
                Defaults to 1.
            mtu (int, optional):
                The Maximum Transmission Unit used by the socket.
                Defaults to 300.
            exchange_timeout (int, optional):
                The maximum number of seconds this socket can be inactive.
                Defaults to 90.
            conn_timeout (int, optional):
                The maximum number of seconds this socket is allowed to try to connect.
                Defaults to 60.
            send_delay_ms (int, optional):
                The number of milliseconds send delay.
                Defaults to 5000.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def socket_connect(self,
        remote_host: str,
        remote_port: int,
        local_port: int = 0,
        socket_id: int = -1,
        protocol: WalterModemSocketProto = WalterModemSocketProto.UDP,
        accept_any_remote: WalterModemSocketAcceptAnyRemote = WalterModemSocketAcceptAnyRemote.DISABLED,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Provided by the SocketMixin

        ---

        Connects a socket to a remote host,
        allowing data exchange once the connection is successful.

        Args:
            remote_host (str):
                The remote IPv4/IPv6 or hostname to connect to
            remote_port (int):
                The remote port to connect on.
            local_port (int, optional):
                The local port in case of an UDP socket.
                Defaults to 0.
            socket_id (int, optional):
                The id of the socket to connect or -1 to re-use the last one.
                Defaults to -1.
            protocol (WalterModemSocketProto, optional):
                The protocol to use, UDP by default.
                Defaults to WalterModemSocketProto.UDP.
            accept_any_remote (WalterModemSocketAcceptAnyRemote, optional):
                How to accept remote UDP packets.
                Defaults to WalterModemSocketAcceptAnyRemote.DISABLED.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def socket_close(self,
        socket_id: int = -1,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Provided by the SocketMixin

        ---    
    
        Closes a socket. Sockets can only be closed when suspended; 
        active connections cannot be closed.        

        Args:
            socket_id (int, optional):
                The id of the socket to close or -1 to re-use the last one.
                Defaults to -1.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def socket_send(self,
        data,
        socket_id: int = -1,
        rai: WalterModemRai = WalterModemRai.NO_INFO,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Provided by the SocketMixin

        ---

        Sends data over a socket.

        Args:
            data (bytes | bytearray | str):
                The data to send
            socket_id (int, optional):
                The id of the socket to close or -1 to re-use the last one.
                Defaults to -1.
            rai (int, optional):
                The release assistance informatio.
                Defaults to WalterModemRai.NO_INFO.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """
# ---
# TLSCertsMixin
# ---

    async def tls_config_profile(self,
        profile_id: int,
        tls_version: WalterModemTlsVersion,
        tls_validation: WalterModemTlsValidation,
        ca_certificate_id: int | None = None,
        client_certificate_id: int | None = None,
        client_private_key: int | None = None,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Provided by the TLSCertsMixin

        ---

        Configures TLS profiles in the modem,
        including optional client authentication certificates, validation levels, and TLS version.
 
        This should be done in an initializer sketch, 
        allowing later HTTP, MQTT, CoAP, or socket sessions to use the preconfigured profile IDs.

        Args:
            profile_id (int):
                Security profile id (1-6)
            tls_version (WalterModemTlsVersion):
                TLS Version
            tls_validation (WalterModemTlsValidation):
                TLS validation level
            ca_certificate_id (int, optional):
                CA certificate for certificate validation (0-19).
                Defaults to None.
            client_certificate_id (int, optional):
                Client TLS certificate index (0-19).
                Defaults to None.
            client_private_key (int, optional):
                Client TLS private key index (0-19).
                Defaults to None.
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """

    async def tls_write_credential(self,
        is_private_key: bool,
        slot_idx: int,
        credential: str,
        rsp: ModemRsp | None = None
    ) -> bool:
        """Provided by the TLSCertsMixin

        ---

        Upload key or certificate to modem NVRAM.

        It is recommended to save credentials in index 10-19 to avoid overwriting preinstalled
        certificates and (if applicable) BlueCherry cloud platform credentials.

        Args:
            is_private_key (bool):
                True if it's a private key, False if it's a certificate
            slot_idx (int):
                Slot index within the modem NVRAM keystore
            credential (str):
                NULL-terminated string containing the PEM key/cert data
            rsp (ModemRsp, optional):
                Reference to a modem response instance.
                Defaults to None.

        Returns:
            bool: True on success, False on failure
        """
