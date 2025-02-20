"""
Copyright (C) 2023, DPTechnics bv
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

  1. Redistributions of source code must retain the above copyright notice,
     this list of conditions and the following disclaimer.

  2. Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in the
     documentation and/or other materials provided with the distribution.

  3. Neither the name of DPTechnics bv nor the names of its contributors may
     be used to endorse or promote products derived from this software
     without specific prior written permission.

  4. This software, with or without modification, must only be used with a
     Walter board from DPTechnics bv.

  5. Any software provided in binary form under this license must not be
     reverse engineered, decompiled, modified and/or disassembled.

THIS SOFTWARE IS PROVIDED BY DPTECHNICS BV “AS IS” AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY, NONINFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL DPTECHNICS BV OR CONTRIBUTORS BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from asyncio import Event

class Enum:
    reverse_mapping = {}
    @classmethod
    def get_value_name(cls, value: int):
        """Get the property name for any property value of the class."""
        if not hasattr(cls, '_reverse_mapping'):
            cls._reverse_mapping = {
                val: name for name, val in cls.__dict__.items()
                if isinstance(val, int)
            }

        return cls._reverse_mapping.get(value, f"Unknown code: {value}")

class ModemState(Enum):
    """Grouped status codes of functions and operational components of the modem."""
    OK = 0
    ERROR = 1
    TIMEOUT = 2
    NO_MEMORY = 3
    NO_FREE_PDP_CONTEXT = 4
    NO_SUCH_PDP_CONTEXT = 5
    NO_FREE_SOCKET = 6
    NO_SUCH_SOCKET = 7
    NO_SUCH_PROFILE = 8
    NOT_EXPECTING_RING = 9
    AWAITING_RING = 10
    BUSY = 11
    NO_DATA = 12

class ModemSimState(Enum):
    """SIM card states."""
    READY = 0
    PIN_REQUIRED = 1
    PUK_REQUIRED = 2
    PHONE_TO_SIM_PIN_REQUIRED = 3
    PHONE_TO_FIRST_SIM_PIN_REQUIRED = 4
    PHONE_TO_FIRST_SIM_PUK_REQUIRED = 5
    PIN2_REQUIRED = 6
    PUK2_REQUIRED = 7
    NETWORK_PIN_REQUIRED = 8
    NETWORK_PUK_REQUIRED = 9
    NETWORK_SUBSET_PIN_REQUIRED = 10
    NETWORK_SUBSET_PUK_REQUIRED = 11
    SERVICE_PROVIDER_PIN_REQUIRED = 12
    SERVICE_PROVIDER_PUK_REQUIRED = 13
    CORPORATE_SIM_REQUIRED = 14
    CORPORATE_PUK_REQUIRED = 15

class ModemRat(Enum):
    """Types of 3GPP access technologies supported by Walter."""
    LTEM = 0
    NBIOT = 1
    AUTO = 2

class ModemOpState(Enum):
    """Modem operational modes."""
    MINIMUM = 0
    FULL = 1
    NO_RF = 4
    MANUFACTURING = 5

class ModemNetworkRegState(Enum):
    """Modem network registration states."""
    NOT_SEARCHING = 0
    REGISTERED_HOME = 1
    SEARCHING = 2
    DENIED = 3
    UNKNOWN = 4
    REGISTERED_ROAMING = 5
    REGISTERED_SMS_ONLY_HOME = 6
    REGISTERED_SMS_ONLY_ROAMING = 7
    ATTACHED_EMERGENCY_ONLY = 8
    REGISTERED_CSFB_NOT_PREFERRED_HOME = 9
    REGISTERED_CSFB_NOT_PREFERRED_ROAMING = 10
    REGISTERED_TEMP_CONN_LOSS = 80

class ModemCMEErrorReportsType(Enum):
    """Modem CME error reporting methods."""
    OFF = 0
    NUMERIC = 1
    VERBOSE = 2
    
class ModemCEREGReportsType(Enum):
    """CEREG unsolicited reporting methods."""
    OFF = 0
    ENABLED = 1
    ENABLED_WITH_LOCATION = 2
    ENABLED_WITH_LOCATION_EMM_CAUSE = 3
    ENABLED_UE_PSM_WITH_LOCATION= 4
    ENABLED_UE_PSM_WITH_LOCATION_EMM_CAUSE = 5

class ModemCMEError(Enum):
    """CME error codes."""
    EQUIPMENT_FAILURE = 0
    NO_CONNECTION = 1
    PHONE_ADAPTER_LINK_RESERVED = 2
    OPERATION_NOT_ALLOWED = 3
    OPERATION_NOT_SUPPORTED = 4
    PH_SIM_PIN_REQUIRED = 5
    PH_FSIM_PIN_REQUIRED = 6
    PH_FSIM_PUK_REQUIRED = 7
    SIM_NOT_INSERTED = 10
    SIM_PIN_REQUIRED = 11
    SIM_PUK_REQUIRED = 12
    SIM_FAILURE = 13
    SIM_BUSY = 14
    SIM_WRONG = 15
    INCORRECT_PASSWORD = 16
    SIM_PIN2_REQUIRED = 17
    SIM_PUK2_REQUIRED = 18
    MEMORY_FULL = 20
    INVALID_INDEX = 21
    NOT_FOUND = 22
    MEMORY_FAILURE = 23
    TEXT_STRING_TOO_LONG = 24
    INVALID_CHARS_IN_TEXT_STRING = 25
    DIAL_STRING_TOO_LONG = 26
    INVALID_CHARS_IN_DIAL_STRING = 27
    NO_NETWORK_SERVICE = 30
    NETWORK_TIMEOUT = 31
    NETWORK_NOT_ALLOWED_EMERGENCY_CALS_ONLY = 32
    NETWORK_PERSONALIZATION_PIN_REQUIRED = 40
    NETWORK_PERSONALIZATION_PUK_REQUIRED = 41
    NETWORK_SUBSET_PERSONALIZATION_PIN_REQUIRED = 42
    NETWORK_SUBSET_PERSONALIZATION_PUK_REQUIRED = 43
    SERVICE_PROVIDER_PERSONALIZATION_PIN_REQUIRED = 44
    SERVICE_PROVIDER_PERSONALIZATION_PUK_REQUIRED = 45
    CORPORATE_PERSONALIZATION_PIN_REQUIRED = 46
    CORPORATE_PERSONALIZATION_PUK_REQUIRED = 47
    HIDDEN_KEY_REQUIRED = 48
    EAP_METHOD_NOT_SUPPORTED = 49
    INCORRECT_PARAMETERS = 50
    SYSTEM_FAILURE = 60
    UNKNOWN_ERROR = 100
    UPGRADE_FAILED_GENERAL_ERROR = 528
    UPGRADE_FAILED_CORRUPTED_IMAGE = 529
    UPGRADE_FAILED_INVALID_SIGNATURE = 530
    UPGRADE_FAILED_NETWORK_ERROR = 531
    UPGRADE_FAILED_ALREADY_IN_PROGRESS = 532
    UPGRADE_CANCEL_FAILED_NO_UPGRADE_IN_PROGRESS = 533
    HW_CONFIG_FAILED_GENERAL_ERROR = 540
    HW_CONFIG_FAILED_INVALID_FUNCTION = 541
    HW_CONFIG_FAILED_INVALID_FUNCTION_PARAM = 542
    HW_CONFIG_FAILED_PINS_ALREADY_ASSIGNED = 54
    WRONG_STATE = 551

class ModemSQNMONIReportsType(Enum):
    """SQNMONI cell information reporting scopes"""
    SERVING_CELL = 0
    INTRA_FREQUENCY_CELLS = 1
    INTER_FREQUENCY_CELLS = 2
    ALL_CELLS = 7
    SERVING_CELL_WITH_CINR = 9

class ModemRspParserState(Enum):
    """RAW RX response parser states."""
    START_CR = 0
    START_LF = 1
    DATA = 2
    DATA_PROMPT = 3
    DATA_PROMPT_HTTP = 4
    DATA_HTTP_START1 = 5
    DATA_HTTP_START2 = 6
    END_LF = 7
    RAW = 8


class ModemCmdType(Enum):
    """Queue task supported commands."""
    TX = 0
    TX_WAIT = 1
    WAIT = 2
    DATA_TX_WAIT = 3


class ModemCmdState(Enum):
    """AT command FSM supported states."""
    NEW = 2
    PENDING = 3
    RETRY_AFTER_ERROR = 4
    COMPLETE = 6


class ModemPDPContextState(Enum):
    """PDP context states."""
    FREE = 0
    RESERVED = 1
    INACTIVE = 2
    ACTIVE = 3
    ATTACHED = 4

class ModemPDPType(Enum):
    """Supported packet data protocol types."""
    X25 = 0
    IP = 1
    IPV6 = 2
    IPV4V6 = 3
    OSPIH = 4
    PPP = 5
    NON_IP = 6

class ModemPDPHeaderCompression(Enum):
    """Supported packet data protocol header compression mechanisms."""
    OFF = 0
    ON = 1
    RFC1144 = 2
    RFC2507 = 3
    RFC3095 = 4
    UNSPEC = 99

class ModemPDPDataCompression(Enum):
    """Supported packet data protocol data compression mechanisms."""
    OFF = 0
    ON = 1
    V42BIS = 2
    V44 = 3
    UNSPEC = 99

class ModemPDPIPv4AddrAllocMethod(Enum):
    """Supported packet data protocol IPv4 address allocation methods."""
    NAS = 0
    DHCP = 1

class ModemPDPRequestType(Enum):
    """Supported packet data protocol request types."""
    NEW_OR_HANDOVER = 0
    EMERGENCY = 1
    NEW = 2
    HANDOVER = 3
    EMERGENCY_HANDOVER = 4

class ModemPDPPCSCFDiscoveryMethod(Enum):
    """Supported types of P-CSCF discovery in a packet data context."""
    AUTO = 0
    NAS = 1

class ModemPDPAuthProtocol(Enum):
    """PDP context authentication protocols."""
    NONE = 0
    PAP = 1
    CHAP = 2

class ModemRspType(Enum):
    """Implemented response types."""
    NO_DATA = 0
    OP_STATE = 1
    RAT = 2
    RSSI = 3
    SIGNAL_QUALITY = 4
    SIM_STATE = 5
    CME_ERROR = 6
    PDP_CTX_ID = 7
    BANDSET_CFG_SET = 8
    PDP_ADDR = 9
    SOCKET_ID = 10
    GNSS_ASSISTANCE_DATA = 11
    CLOCK = 12
    MQTT = 13
    HTTP_RESPONSE = 14
    COAP = 15
    CELL_INFO = 16
    REG_STATE = 50

class ModemNetworkSelMode(Enum):
    """Support network selection modes."""
    AUTOMATIC = 0
    MANUAL = 1
    UNREGISTER = 2
    MANUAL_AUTO_FALLBACK = 4

class ModemOperatorFormat(Enum):
    """Supported netowrk operator formats."""
    LONG_ALPHANUMERIC = 0
    SHORT_ALPHANUMERIC = 1
    NUMERIC = 2

class ModemSocketState(Enum):
    """State of a socket."""
    FREE = 0
    RESERVED = 1
    CREATED = 2
    CONFIGURED = 3
    OPENED = 4
    LISTENING = 5
    CLOSED = 6

class ModemHttpContextState(Enum):
    """State of an http context."""
    IDLE = 0
    EXPECT_RING = 1
    GOT_RING = 2

class ModemSocketProto(Enum):
    """Protocol used by the socket."""
    TCP = 0
    UDP = 1

class ModemSocketAcceptAnyRemote(Enum):
    """
    Possible methodologies on how a socket handles data from other hosts
    besides the IP-address and remote port it is configured for.
    """
    DISABLED = 0
    REMOTE_RX_ONLY = 1
    REMOTE_RX_AND_TX = 2

class ModemRai(Enum):
    """
    In case of an NB-IoT connection the RAI (Release Assistance Information).
    The RAI is used to indicate to the entwork (MME) if there are going to be
    other transmissions or not
    """
    NO_INFO = 0
    NO_FURTHER_RXTX_EXPECTED = 1
    ONLY_SINGLE_RXTX_EXPECTED = 2

class ModemGNSSLocMode(Enum):
    """
    The GNSS location modus. When set to 'on-device location', the GNSS sybsystem
    will compute position and speed and estimate the error on these parameters.
    """
    ON_DEVICE_LOCATION = 0

class ModemGNSSSensMode(Enum):
    """
    The possible sensitivity settings use by Walter's GNSS receiver.
    his sets the amount of time that the receiver is actually on.
    More sensitivity requires more power.
    """
    LOW = 1
    MEDIUM = 2
    HIGH = 3

class ModemGNSSAcqMode(Enum):
    """
    The possible GNSS acquisition modes.
    In a cold or warm start situation Walter has no clue where he is on earth.
    In hot start mode Walter must know where he is within 100km.
    When no ephemerides are available and/or the time is not known cold start will be used automatically.
    """
    COLD_WARM_START = 0
    HOT_START = 1


class ModemGNSSAction(Enum):
    """Supported actions that Walter's GNSS can execute."""
    GET_SINGLE_FIX = 0
    CANCEL = 1


class ModemGNSSFixStatus(Enum):
    """GNSS fix statuses."""
    READY = 0
    STOPPED_BY_USER = 1
    NO_RTC = 2
    LTE_CONCURRENCY = 3


class ModemGNSSAssistanceType(Enum):
    """GNSS assistance types."""
    ALMANAC = 0
    REALTIME_EPHEMERIS = 1
    PREDICTED_EPHEMERIS = 2


class ModemHttpQueryCmd(Enum):
    """Possible commands for an HTTP query operation."""
    GET = 0
    HEAD = 1
    DELETE = 2


class ModemHttpSendCmd(Enum):
    """Possible commands for an HTTP send operation."""
    POST = 0
    PUT = 1


class ModemHttpPostParam(Enum):
    """Possible post params for a HTTP send operation."""
    URL_ENCODED = 0
    TEXT_PLAIN = 1
    OCTET_STREAM = 2
    FORM_DATA = 3
    JSON = 4
    UNSPECIFIED = 99

class ModemTlsValidation(Enum):
    """The TLS validation policy."""
    NONE = 0
    CA = 1
    URL = 4
    URL_AND_CA = 5

class ModemTlsVersion(Enum):
    """The TLS version to use."""
    TLS_VERSION_10 = 0
    TLS_VERSION_11 = 1
    TLS_VERSION_12 = 2
    TLS_VERSION_13 = 3
    TLS_VERSION_RESET = 255

class ModemGNSSSat:
    """
    Contains the number of satellites and the signal strength.
    """
    def __init__(self, sat_no, signal_strength):
        """
        The number of the satellite.

        :param sat_no:
        :param signal_strength: The CN0 signal strength of the sattellite in dB/Hz, minimum is 30dB/Hz
        """
        self.sat_no = sat_no
        self.signal_strength = signal_strength


class ModemGNSSFix:
    """
    Structure represents a GNSS fix.
    """
    def __init__(self):
        self.status = ModemGNSSFixStatus.READY
        """The status of the fix."""
        
        self.fix_id = 0
        """The id of the fix, always in [0-9]."""
        
        self.timestamp = 0
        """The time of the fix as a unix timestamp."""
        
        self.time_to_fix = 0
        """The number of milliseconds used to get the fix."""
        
        self.estimated_confidence = 20000000.0
        """The estimated horizontal confidence of the fix in meters."""
        
        self.latitude = 0.0
        """The latitude of the fix."""
        
        self.longitude = 0.0
        """The longitude of the fix"""
        
        self.height = 0.0
        """The height above sea level."""
        
        self.north_speed = 0.0
        """The speed in northern direction in meters per second"""
        
        self.east_speed = 0.0
        """The speed in eastern direction in meters per second."""
        
        self.down_speed = 0.0
        """The downwards speed in meters per second"""
        
        self.sats = []
        """Satellite numbers and reception strength."""


class ModemGNSSAssistanceTypeDetails:
    """Represents the details of a certain GNSS assistance."""
    def __init__(self):
        self.available = False
        """True when assistance data is available."""
        
        self.last_update = 0
        """The number of seconds since the last update of this type of assistance data"""
        
        self.time_to_update = 0
        """The number of seconds before this type of assistance data is available"""
        
        self.time_to_expire = 0
        """
        The number of seconds after which this type of assistance data
        expires and cannot be used by the GNSS system.
        """


class ModemGNSSAssistance:
    def __init__(self):
        self.almanac = ModemGNSSAssistanceTypeDetails()
        """
        Almanac data details, this is not needed when real-time ephemeris
        data is available
        """
        
        self.realtime_ephemeris = ModemGNSSAssistanceTypeDetails() 
        """
        Real-time ephemeris data details. Use this kind of assistance 
        data for the fastest and most power efficient GNSS fix.
        """

        self.predicted_ephemeris = ModemGNSSAssistanceTypeDetails() 
        """Predicted ephemeris data details."""
 

class ModemOperator:
    """Represents an operator"""
    def __init__(self):
        self.format = ModemOperatorFormat.LONG_ALPHANUMERIC
        """The format in which the operator is stored."""
        
        self.name = ""
        """The name of the operator"""


class ModemBandSelection:
    """Represents a band selection for a given radio access technology and operator."""
    def __init__(self):
        self.rat = ModemRat.AUTO
        """The radio access technology for which the bands are configured"""
        
        self.net_operator = ModemOperator()
        
        self.bands: list[int] = []
        """
        When the bit is set the respective band is configured to be used.
        The bands are B1, B2, B3, B4, B5, B8, B12, B13, B14, B17, B18, B19, B20, 
        B25, B26, B28, B66, B71, B85. For example to check if B1 is configured
        one must do 'bands & 0x01'
        """
        

class ModemHttpResponse:
    """Represents an http response."""
    def __init__(self):
        self.http_status = 0
        self.content_length = 0
        self.data = b''
        self.content_type = ''


class ModemSignalQuality:
    """Grouping the RSRQ and RSPR signal quality parameters."""
    def __init__(self):
        self.rsrq = None
        """The RSRQ in 10ths of dB"""

        self.rsrp = None
        """The RSPR in dBm"""


class ModemRsp:
    """Represents a response """
    def __init__(self):
        self.result: ModemState | None = ModemState.OK
        """The result of the executed command."""

        self.type: ModemRspType | None = ModemRspType.NO_DATA
        """The data type of the response"""
        
        self.reg_state: ModemNetworkRegState | None = None
        """The network registration state of the modem."""
        
        self.op_state: ModemOpState | None = None
        """The operational state of the modem."""
        
        self.sim_state: ModemSimState | None = None
        """The state of the SIM card"""
        
        self.cme_error: ModemCMEError | None = None
        """The CME error received from the modem."""
        
        self.pdp_ctx_id: int | None = None
        """The ID of a PDP context."""
        
        self.rat: int | None = None
        """The radio access technology"""

        self.rssi: int | None = None
        """The RSSI of the signal in dBm"""

        self.signal_quality: ModemSignalQuality | None = None
        """Signal quality"""

        self.band_sel_cfg_list: list[ModemBandSelection] | None = None
        """The band selection configuration set."""
        
        self.pdp_address_list: list | None = None
        """The list of addresses of a cert"""
        
        self.socket_id: int | None = None
        """The ID of the socket."""
        
        self.gnss_assistance: ModemGNSSAssistance | None = None
        """The band selection configuration set."""
        
        self.clock: float | None = None
        """Unix timestamp of the current time and date in the modem."""

        """ TODO  mqtt_data"""

        self.http_response: ModemHttpResponse | None = None
        """HTTP response"""

        """ TODO  coap_response"""

        self.cell_information: ModemCellInformation | None = None


class ModemCmd:
    """Structure epresenting an AT command to be added to the command queue."""
    def __init__(self):
        self.state = ModemCmdState.NEW
        """The current state of the command."""
        
        self.type = ModemCmdType.TX_WAIT
        """The type of AT command."""
        
        self.at_cmd = b''
        """The AT command without the trailing \r\n."""
        
        self.data = None
        """
        Pointer to the data buffer to transmit in case of a
        WALTER_MODEM_CMD_TYPE_DATA_TX_WAIT command.
        """
        
        self.at_rsp = None
        """The expected command response starting string."""
        
        self.max_attempts = 0
        """The maximum number of attempts to execute the command."""
        
        self.attempt = 0
        """The current attempt number."""
        
        self.attempt_start = 0
        """The time on which the current attempt was started."""
        
        self.rsp = None
        """Pointer to the response object to store the command results in."""
        
        self.complete_handler = None
        """
        Pointer to a function which is called before the command user callback is called.
        This pointer is used to manage internal library 
        state.
        """
        
        self.complete_handler_arg = None
        """Pointer to an argument used by the complete_handler."""

        self.event = Event()
        """Event for letting main user program wait on a blocking call"""


class ModemATParserData:
    def __init__(self):
        self.state = ModemRspParserState.START_CR
        """The FSM state the parser currently is in."""
        
        self.line = b''
        """The buffer currently used by the parser."""

        self.raw_chunk_size = 0
        """In raw data chunk parser state, we remember nr expected bytes"""


class ModemTaskQueueItem:
    """Represents an item in the task queue."""
    def __init__(self):
        self.rsp = None 
        """Pointer to an AT response or None when this is an AT command"""
        
        self.cmd = None
        """The AT command pointer in case rsp is None"""


class ModemPDPContext:
    """Represents a PDP context."""
    def __init__(self, id):
        self.state = ModemPDPContextState.FREE
        """The state of the PDP context."""
        
        self.id = id
        """The ID of this PDP data context."""
        
        self.type = ModemPDPType.IP
        """The type of packet data protocol."""
        
        self.apn = ""
        """"The APN to use"""
        
        self.pdp_address = ""
        """The FDP address od this context."""
        
        self.pdp_address2 = ""
        """A secondary IPv6 PDPaddress when dual stack is enabled."""
        
        self.header_comp = ModemPDPHeaderCompression.UNSPEC
        """The header compression used in the PDP context"""
        
        self.data_comp = ModemPDPDataCompression.UNSPEC
        """The data compression method used in the PDP context"""
        
        self.ipv4_alloc_method = ModemPDPIPv4AddrAllocMethod.NAS
        """The IPv4 address allocation method used in the PDP context"""
        
        self.request_type = ModemPDPRequestType.NEW_OR_HANDOVER
        """The packet data protocol request type"""
        
        self.pcscf_method = ModemPDPPCSCFDiscoveryMethod.AUTO
        """The method to use for p-CSCF discovery"""
        
        self.for_IMCN = False
        """Flag indicating if the PDP context is used for IM CN 
        subsystem-related signalling"""
        
        self.use_NSLPI = False
        """Flag indicating if the PDP context should use Non-Access Stratum 
        (NAS) Signalling Low Priority Indication (NSLPI)"""
        
        self.use_secure_PCO = False
        """Flag indicating if the Protocol Configuration Options (PCO) should be protected"""
        
        self.use_NAS_ipv4_MTU_discovery = False
        """Flag indicating if NAS signalling should be used to discover the 
        IPv4 MTU"""
        
        self.use_local_addr_ind = False
        """Flag indicating if the system supports local IP addresses in the 
        Traffic Flow Template (TFT)"""
        
        self.use_NAS_non_IPMTU_discovery = False
        """Flag indicating if NAS should be used to discover the MTU of non-IP
        PDP contexts"""
        
        self.auth_proto = ModemPDPAuthProtocol.NONE
        """"The authentication protocol used to activate the PDP"""
        
        self.auth_user = ""
        """The user to authenticate."""
        
        self.auth_pass = ""
        """The password to authenticate"""


class ModemSocket:
    """Represents a socket."""
    def __init__(self, id):
        self.state = ModemSocketState.FREE
        """The state of the socket."""

        self.id = id
        """The socket identifier."""

        self.pdp_context_id = 1
        """The PDP context ID in which the socket is created."""

        self.mtu = 300
        """Maximum transmission unit used by the TCP/UDP/IP stack."""

        self.exchange_timeout = 90
        """The socket exchange timeout in seconds."""

        self.conn_timeout = 60
        """The connection timeout in seconds."""

        self.send_delay_ms = 5000
        """The number of milliseconds after which the transmit buffer is 
        effectively transmitted."""

        self.protocol = ModemSocketProto.UDP
        """The protocol to use."""

        self.accept_any_remote = ModemSocketAcceptAnyRemote.DISABLED
        """How to handle data from other hosts than the remote host and port 
        that the socket is configured for."""

        self.remote_host = ""
        """The IPv4 or IPv6 address of the remote host or a hostname in which 
        case a DNS query will be executed in the background."""

        self.remote_port = 0
        """The remote port to connect to."""

        self.local_port = 0
        """In case of UDP, this is the local port number to which the remote 
        host can send an answer."""


class ModemGnssFixWaiter:
    """Represents a wait_for_gnss_fix call that is waiting for data"""
    def __init__(self):
        self.event = Event()
        self.gnss_fix = None


class ModemHttpContext:
    """Represents a socket."""
    def __init__(self):
        self.connected = False
        self.state = ModemHttpContextState.IDLE
        self.http_status = 0
        self.content_length = 0
        self.content_type = ''

class ModemCellInformation:
    """Grouping of all possible cell monitoring response values"""
    def __init__(self):
        self.net_name: str = ''
        """Name of the network operator"""

        self.cc: int = 0
        """Mobile country code"""

        self.nc: int = 0
        """Network operator code"""

        self.rsrp: float = 0.0
        """Reference signal Received Power"""

        self.cinr: float = 0.0
        """Carrier to Interference-plus-Noise Ratio"""

        self.rsrq: float = 0.0
        """Reference Signal Received Quality"""

        self.tac: int = 0
        """Tracking Area Code"""

        self.pci: int = 0
        """Physical Cell ID"""

        self.earfcn: int = 0
        """E-UTRA Assigned Radio Channel"""

        self.rssi: float = 0.0
        """Received signal strength in dBm"""

        self.paging: int = 0
        """DRX cycle in number of radio frames (1 frame = 10 ms)"""

        self.cid: int = 0
        """25-bit E-UTRAN Cell Identity"""

        self.band: int = 0
        """Band Number"""

        self.bw: int = 0
        """Downlink bandwidth in kHz"""

        self.ce_level: int = 0
        """Coverage Enhancement Level"""