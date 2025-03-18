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

class WalterModemState(Enum):
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

class WalterModemSimState(Enum):
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

class WalterModemRat(Enum):
    """Types of 3GPP access technologies supported by Walter."""
    LTEM = 0
    NBIOT = 1
    AUTO = 2

class WalterModemOpState(Enum):
    """Modem operational modes."""
    MINIMUM = 0
    FULL = 1
    NO_RF = 4
    MANUFACTURING = 5

class WalterModemNetworkRegState(Enum):
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

class WalterModemCMEErrorReportsType(Enum):
    """Modem CME error reporting methods."""
    OFF = 0
    NUMERIC = 1
    VERBOSE = 2
    
class WalterModemCEREGReportsType(Enum):
    """CEREG unsolicited reporting methods."""
    OFF = 0
    ENABLED = 1
    ENABLED_WITH_LOCATION = 2
    ENABLED_WITH_LOCATION_EMM_CAUSE = 3
    ENABLED_UE_PSM_WITH_LOCATION= 4
    ENABLED_UE_PSM_WITH_LOCATION_EMM_CAUSE = 5

class WalterModemCMEError(Enum):
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

class WalterModemSQNMONIReportsType(Enum):
    """SQNMONI cell information reporting scopes"""
    SERVING_CELL = 0
    INTRA_FREQUENCY_CELLS = 1
    INTER_FREQUENCY_CELLS = 2
    ALL_CELLS = 7
    SERVING_CELL_WITH_CINR = 9

class WalterModemRspParserState(Enum):
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


class WalterModemCmdType(Enum):
    """Queue task supported commands."""
    TX = 0
    TX_WAIT = 1
    WAIT = 2
    DATA_TX_WAIT = 3


class WalterModemCmdState(Enum):
    """AT command FSM supported states."""
    NEW = 2
    PENDING = 3
    RETRY_AFTER_ERROR = 4
    COMPLETE = 6


class WalterModemPDPContextState(Enum):
    """PDP context states."""
    FREE = 0
    RESERVED = 1
    INACTIVE = 2
    ACTIVE = 3
    ATTACHED = 4

class WalterModemPDPType(Enum):
    """Supported packet data protocol types."""
    X25 = 0
    IP = 1
    IPV6 = 2
    IPV4V6 = 3
    OSPIH = 4
    PPP = 5
    NON_IP = 6

class WalterModemPDPHeaderCompression(Enum):
    """Supported packet data protocol header compression mechanisms."""
    OFF = 0
    ON = 1
    RFC1144 = 2
    RFC2507 = 3
    RFC3095 = 4
    UNSPEC = 99

class WalterModemPDPDataCompression(Enum):
    """Supported packet data protocol data compression mechanisms."""
    OFF = 0
    ON = 1
    V42BIS = 2
    V44 = 3
    UNSPEC = 99

class WalterModemPDPIPv4AddrAllocMethod(Enum):
    """Supported packet data protocol IPv4 address allocation methods."""
    NAS = 0
    DHCP = 1

class WalterModemPDPRequestType(Enum):
    """Supported packet data protocol request types."""
    NEW_OR_HANDOVER = 0
    EMERGENCY = 1
    NEW = 2
    HANDOVER = 3
    EMERGENCY_HANDOVER = 4

class WalterModemPDPPCSCFDiscoveryMethod(Enum):
    """Supported types of P-CSCF discovery in a packet data context."""
    AUTO = 0
    NAS = 1

class WalterModemPDPAuthProtocol(Enum):
    """PDP context authentication protocols."""
    NONE = 0
    PAP = 1
    CHAP = 2

class WalterModemRspType(Enum):
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
    HTTP = 14
    COAP = 15
    CELL_INFO = 16
    REG_STATE = 50

class WalterModemNetworkSelMode(Enum):
    """Support network selection modes."""
    AUTOMATIC = 0
    MANUAL = 1
    UNREGISTER = 2
    MANUAL_AUTO_FALLBACK = 4

class WalterModemOperatorFormat(Enum):
    """Supported netowrk operator formats."""
    LONG_ALPHANUMERIC = 0
    SHORT_ALPHANUMERIC = 1
    NUMERIC = 2

class WalterModemSocketState(Enum):
    """State of a socket."""
    FREE = 0
    RESERVED = 1
    CREATED = 2
    CONFIGURED = 3
    OPENED = 4
    LISTENING = 5
    CLOSED = 6

class WalterModemHttpContextState(Enum):
    """State of an http context."""
    IDLE = 0
    EXPECT_RING = 1
    GOT_RING = 2

class WalterModemMqttState(Enum):
    CONNECTED = 0
    DISCONNECTED = 0

class WalterModemSocketProto(Enum):
    """Protocol used by the socket."""
    TCP = 0
    UDP = 1

class WalterModemSocketAcceptAnyRemote(Enum):
    """
    Possible methodologies on how a socket handles data from other hosts
    besides the IP-address and remote port it is configured for.
    """
    DISABLED = 0
    REMOTE_RX_ONLY = 1
    REMOTE_RX_AND_TX = 2

class WalterModemRai(Enum):
    """
    In case of an NB-IoT connection the RAI (Release Assistance Information).
    The RAI is used to indicate to the entwork (MME) if there are going to be
    other transmissions or not
    """
    NO_INFO = 0
    NO_FURTHER_RXTX_EXPECTED = 1
    ONLY_SINGLE_RXTX_EXPECTED = 2

class WalterModemGNSSLocMode(Enum):
    """
    The GNSS location modus. When set to 'on-device location', the GNSS sybsystem
    will compute position and speed and estimate the error on these parameters.
    """
    ON_DEVICE_LOCATION = 0

class WalterModemGNSSSensMode(Enum):
    """
    The possible sensitivity settings use by Walter's GNSS receiver.
    This sets the amount of time that the receiver is actually on.
    More sensitivity requires more power.
    """
    LOW = 1
    MEDIUM = 2
    HIGH = 3

class WalterModemGNSSAcqMode(Enum):
    """
    The possible GNSS acquisition modes.
    In a cold or warm start situation Walter has no clue where he is on earth.
    In hot start mode Walter must know where he is within 100km.
    When no ephemerides are available and/or the time is not known cold start will be used automatically.
    """
    COLD_WARM_START = 0
    HOT_START = 1


class WalterModemGNSSAction(Enum):
    """Supported actions that Walter's GNSS can execute."""
    GET_SINGLE_FIX = 0
    CANCEL = 1


class WalterModemGNSSFixStatus(Enum):
    """GNSS fix statuses."""
    READY = 0
    STOPPED_BY_USER = 1
    NO_RTC = 2
    LTE_CONCURRENCY = 3


class WalterModemGNSSAssistanceType(Enum):
    """GNSS assistance types."""
    ALMANAC = 0
    REALTIME_EPHEMERIS = 1
    PREDICTED_EPHEMERIS = 2


class WalterModemHttpQueryCmd(Enum):
    """Possible commands for an HTTP query operation."""
    GET = 0
    HEAD = 1
    DELETE = 2


class WalterModemHttpSendCmd(Enum):
    """Possible commands for an HTTP send operation."""
    POST = 0
    PUT = 1


class WalterModemHttpPostParam(Enum):
    """Possible post params for a HTTP send operation."""
    URL_ENCODED = 0
    TEXT_PLAIN = 1
    OCTET_STREAM = 2
    FORM_DATA = 3
    JSON = 4
    UNSPECIFIED = 99

class WalterModemTlsValidation(Enum):
    """The TLS validation policy."""
    NONE = 0
    CA = 1
    URL = 4
    URL_AND_CA = 5

class WalterModemTlsVersion(Enum):
    """The TLS version to use."""
    TLS_VERSION_10 = 0
    TLS_VERSION_11 = 1
    TLS_VERSION_12 = 2
    TLS_VERSION_13 = 3
    TLS_VERSION_RESET = 255