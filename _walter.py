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

from uasyncio import Event

# @brief This enum groups status codes of functions and operational components
# of the modem.
class ModemState:
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

# @brief The possible states that the SIM card can be in.
class ModemSimState:
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

# @brief The different types of 3GPP access technologies supported by Walter.
class ModemRat:
    LTEM = 0
    NBIOT = 1
    AUTO = 2

# @brief The different operational modes of the modem.
class ModemOpState:
    MINIMUM = 0
    FULL = 1
    NO_RF = 4
    MANUFACTURING = 5

# @brief The different network registration states that the modem can be in.
class ModemNetworkRegState:
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

# @brief The CME error reporting methods.
class ModemCMEErrorReportsType:
    OFF = 0
    NUMERIC = 1
    VERBOSE = 2
    
# @brief This CEREG unsolicited reporting methods.
class ModemCEREGReportsType:
    OFF = 0
    ENABLED = 1
    ENABLED_WITH_LOCATION = 2
    ENABLED_WITH_LOCATION_EMM_CAUSE = 3
    ENABLED_UE_PSM_WITH_LOCATION= 4
    ENABLED_UE_PSM_WITH_LOCATION_EMM_CAUSE = 5

# @brief All supported CME error codes.
class ModemCmeError:
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
    HW_CONFIG_FAILED_PINS_ALREADY_ASSIGNED = 543


"""The different states the raw RX response parser can be in."""
class ModemRspParserState:
    START_CR = 0
    START_LF = 1
    DATA = 2
    DATA_PROMPT = 3
    DATA_PROMPT_HTTP = 4
    DATA_HTTP_START1 = 5
    DATA_HTTP_START2 = 6
    END_LF = 7
    RAW = 8


"""The types of command supported by the queue task."""
class ModemCmdType:
    TX = 0
    TX_WAIT = 1
    WAIT = 2
    DATA_TX_WAIT = 3


"""The different states the AT command FSM can be in."""
class ModemCmdState:
    NEW = 2
    PENDING = 3
    RETRY_AFTER_ERROR = 4
    COMPLETE = 6


"""This enumeration represents the different states a PDP context can be in."""
class ModemPDPContextState:
    FREE = 0
    RESERVED = 1
    INACTIVE = 2
    ACTIVE = 3
    ATTACHED = 4


"""The supported packet data protocol types."""
class ModemPDPType:
    X25 = 0
    IP = 1
    IPV6 = 2
    IPV4V6 = 3
    OSPIH = 4
    PPP = 5
    NON_IP = 6


"""The supported packet data protocol header compression mechanisms."""
class ModemPDPHeaderCompression:
    OFF = 0
    ON = 1
    RFC1144 = 2
    RFC2507 = 3
    RFC3095 = 4
    UNSPEC = 99


"""The supported packet data protocol data compression mechanisms"""
class ModemPDPDataCompression:
    OFF = 0
    ON = 1
    V42BIS = 2
    V44 = 3
    UNSPEC = 99


"""The supported packet data protocol IPv4 address allocation methods."""
class ModemPDPIPv4AddrAllocMethod:
    NAS = 0
    DHCP = 1


"""The supported packet data protocol request types."""
class ModemPDPRequestType:
    NEW_OR_HANDOVER = 0
    EMERGENCY = 1
    NEW = 2
    HANDOVER = 3
    EMERGENCY_HANDOVER = 4


"""The supported types of P-CSCF discovery in a packet data context."""
class ModemPDPPCSCFDiscoveryMethod:
    AUTO = 0
    NAS = 1


"""The authentication protocol used within the PDP context."""
class ModemPDPAuthProtocol:
    NONE = 0
    PAP = 1
    CHAP = 2


"""This enum represents the different implemented response types."""
class ModemRspType:
    NO_DATA = 0
    OP_STATE = 1
    SIM_STATE = 2
    CME_ERROR = 3
    PDP_CTX_ID = 4
    BANDSET_CFG_SET = 5
    PDP_ADDR = 6
    SOCKET_ID = 7
    GNSS_ASSISTANCE_DATA = 8
    CLOCK = 9,
    REG_STATE = 10
    MQTT = 11
    HTTP_RESPONSE = 12
    COAP = 13


"""The supported network selection modes."""
class ModemNetworkSelMode:
    AUTOMATIC = 0
    MANUAL = 1
    UNREGISTER = 2
    MANUAL_AUTO_FALLBACK = 3


"""The supported netowrk operator formats. """
class ModemOperatorFormat:
    LONG_ALPHANUMERIC = 0
    SHORT_ALPHANUMERIC = 1
    NUMERIC = 2
    

"""The state of a socket."""
class ModemSocketState:
    FREE = 0
    RESERVED = 1
    CREATED = 2
    CONFIGURED = 3
    OPENED = 4
    LISTENING = 5
    CLOSED = 6


"""The state of a http context."""
class ModemHttpContextState:
    IDLE = 0
    EXPECT_RING = 1
    GOT_RING = 2


"""The protocol that us used by the socket."""
class ModemSocketProto:
    TCP = 0
    UDP = 1


"""Possible methodologies on how a socket handles data from other 
 hosts besides the IP-address and remote port it is configured for.
"""
class ModemSocketAcceptAnyRemote:
    DISABLED = 0
    REMOTE_RX_ONLY = 1
    REMOTE_RX_AND_TX = 2


"""In case of an NB-IoT connection the RAI (Release Assistance Information).
The RAI is used to indicate to the network (MME) if there 
are going to be other transmissions or not.
"""
class ModemRai:
    NO_INFO = 0
    NO_FURTHER_RXTX_EXPECTED = 1
    ONLY_SINGLE_RXTX_EXPECTED = 2


"""The GNSS location modus. When set to 'on-device location' the GNSS 
subsystem will compute position and speed and estimate the error on these
parameters.
"""
class ModemGNSSLocMode:
    ON_DEVICE_LOCATION = 0


"""The possible sensitivity settings use by Walter's GNSS receiver. This
sets the amount of time that the receiver is actually on. More sensitivity
requires more power.
"""
class ModemGNSSSensMode:
    LOW = 1
    MEDIUM = 2
    HIGH = 3


"""The possible GNSS acquisition modes. In a cold or warm start situation 
 Walter has no clue where he is on earth. In hot start mode Walter must know
 where he is within 100km. When no ephemerides are available and/or the time
 is not known cold start will be used automatically.
"""
class ModemGNSSAcqMode:
    COLD_WARM_START = 0
    HOT_START = 1


"""The supported actions that Walter's GNSS can execute."""
class ModemGNSSAction:
    GET_SINGLE_FIX = 0
    CANCEL = 1


"""The possible GNSS fix statuses"""
class ModemGNSSFixStatus:
    READY = 0
    STOPPED_BY_USER = 1
    NO_RTC = 2
    LTE_CONCURRENCY = 3


"""The possible GNSS assistance types."""
class ModemGNSSAssistanceType:
    ALMANAC = 0
    REALTIME_EPHEMERIS = 1


"""The possible commands for a HTTP query operation."""
class ModemHttpQueryCmd:
    GET = 0
    HEAD = 1
    DELETE = 2


"""The possible commands for a HTTP send operation."""
class ModemHttpSendCmd:
    POST = 0
    PUT = 1


"""The possible post params for a HTTP send operation."""
class ModemHttpPostParam:
    URL_ENCODED = 0
    TEXT_PLAIN = 1
    OCTET_STREAM = 2
    FORM_DATA = 3
    JSON = 4


class ModemGNSSSat:
    """This class contains the number of satellites and the signal strength.
    """
    def __init__(self, sat_no, signal_strength):
        """The number of the satellite."""
        self.sat_no = sat_no
        """The CN0 signal strength of the satellite in dB/Hz. The minimum
        required signal strength is 30dB/Hz."""
        self.signal_strength = signal_strength


class ModemGNSSFix:
    """This structure represents a GNSS fix.
    """
    def __init__(self):
        """The status of the fix."""
        self.status = ModemGNSSFixStatus.READY
        
        """The id of the fix, always in [0-9]."""
        self.fix_id = 0
        
        """The time of the fix as a unix timestamp."""
        self.timestamp = 0
        
        """The number of milliseconds used to get the fix."""
        self.time_to_fix = 0
        
        """The estimated horizontal confidence of the fix in meters."""
        self.estimated_confidence = 20000000.0
        
        """The latitude of the fix."""
        self.latitude = 0.0
        
        """The longitude of the fix"""
        self.longitude = 0.0
        
        """The height above sea level."""
        self.height = 0.0
        
        """The speed in northern direction in meters per second"""
        self.north_speed = 0.0
        
        """The speed in eastern direction in meters per second."""
        self.east_speed = 0.0
        
        """The downwards speed in meters per second"""
        self.down_speed = 0.0
        
        """Satellite numbers and reception strength."""
        self.sats = []


class ModemGNSSAssistanceTypeDetails:
    """This class represents the details of a certain GNSS assistance"""
    def __init__(self):
        """True when assistance data is available."""
        self.available = False
        
        """The number of seconds since the last update of this type of 
        assistance data
        """
        self.last_update = 0
        
        """The number of seconds before this type of assistance data is available"""
        self.time_to_update = 0
        
        """The number of seconds after which this type of assistance data
        expires and cannot be used by the GNSS system."""
        self.time_to_expire = 0


class ModemGNSSAssistance:
    def __init__(self):
        """Almanac data details, this is not needed when real-time ephemeris
        data is available"""
        self.almanac = ModemGNSSAssistanceTypeDetails()
        
        """Real-time ephemeris data details. Use this kind of assistance 
        data for the fastest and most power efficient GNSS fix."""
        self.ephemeris = ModemGNSSAssistanceTypeDetails() 
 

class ModemOperator:
    """This class represents an operator
    """
    def __init__(self):
        """The format in which the operator is stored."""
        self.format = ModemOperatorFormat.LONG_ALPHANUMERIC
        
        """The name of the operator"""
        self.name = ""


class ModemBandSelection:
    """This class represents a band selection for a given radio access
    technology and operator."""
    def __init__(self):
        """The radio access technology for which the bands are configured"""
        self.rat = ModemRat.AUTO
        
        self.net_operator = ModemOperator()
        
        """When the bit is set the respective band is configured to be used.
        The bands are B1, B2, B3, B4, B5, B8, B12, B13, B14, B17, B18, B19, B20, 
        B25, B26, B28, B66, B71, B85. For example to check if B1 is configured
        one must do 'bands & 0x01'
        """
        self.bands = []
        

class ModemHttpResponse:
    """This class represents a http response."""
    def __init__(self):
        self.http_status = 0
        self.content_length = 0
        self.data = b''
        self.content_type = ''


class ModemRsp:
    """This class represents a response 
    """
    def __init__(self):
        """The result of the executed command."""
        self.result = ModemState.OK

        """The data type of the response"""
        self.type = ModemRspType.NO_DATA
        
        """The operational state of the modem."""
        self.op_state = None
        
        """The network registration state of the modem."""
        self.reg_state = None
        
        """The state of the SIM card"""
        self.sim_state = None
        
        """The CME error received from the modem."""
        self.cme_error = None
        
        """The ID of a PDP context."""
        self.pdp_ctx_id = None
        
        """The band selection configuration set."""
        self.band_sel_cfg_set = None
        
        """The list of addresses of a cert"""
        self.pdp_address_list = None
        
        """The ID of the socket."""
        self.socket_id = None
        
        """The band selection configuration set."""
        self.gnss_assistance = None
        
        """Unix timestamp of the current time and date in the modem."""
        self.clock = None

        """HTTP response"""
        self.http_response = None


class ModemCmd:
    """This structure represents an AT command to be added to the command queue.
    """
    def __init__(self):
        """The current state of the command."""
        self.state = ModemCmdState.NEW
        
        """The type of AT command."""
        self.type = ModemCmdType.TX_WAIT
        
        """The AT command without the trailing \r\n."""
        self.at_cmd = b''
        
        """Pointer to the data buffer to transmit in case of a
        WALTER_MODEM_CMD_TYPE_DATA_TX_WAIT command."""
        self.data = None
        
        """The expected command response starting string."""
        self.at_rsp = None
        
        """The maximum number of attempts to execute the command."""
        self.max_attempts = 0
        
        """The current attempt number."""
        self.attempt = 0
        
        """The time on which the current attempt was started."""
        self.attempt_start = 0
        
        """Pointer to the response object to store the command results in."""
        self.rsp = None
        
        """Pointer to a function which is called before the command user
        callback is called. This pointer is used to manage internal library 
        state."""
        self.complete_handler = None
        
        """Pointer to an argument used by the complete_handler."""
        self.complete_handler_arg = None

        """Event for letting main user program wait on a blocking call"""
        self.event = Event()


class ModemATParserData:
    def __init__(self):
        """The FSM state the parser currently is in."""
        self.state = ModemRspParserState.START_CR
        
        """The buffer currently used by the parser."""
        self.line = b''

        """In raw data chunk parser state, we remember nr expected bytes"""
        self.raw_chunk_size = 0


class ModemTaskQueueItem:
    """This class represents an item in the task queue.
    """
    def __init__(self):
        """Pointer to an AT response or None when this is an AT command"""
        self.rsp = None 
        
        """The AT command pointer in case rsp is None"""
        self.cmd = None


class ModemPDPContext:
    """This class represents a PDP context."""
    def __init__(self, id):
        """The state of the PDP context."""
        self.state = ModemPDPContextState.FREE
        
        """The ID of this PDP data context."""
        self.id = id
        
        """The type of packet data protocol."""
        self.type = ModemPDPType.IP
        
        """"The APN to use"""
        self.apn = ""
        
        """The FDP address od this context."""
        self.pdp_address = ""
        
        """A secondary IPv6 PDPaddress when dual stack is enabled."""
        self.pdp_address2 = ""
        
        """The header compression used in the PDP context"""
        self.header_comp = ModemPDPHeaderCompression.UNSPEC
        
        """The data compression method used in the PDP context"""
        self.data_comp = ModemPDPDataCompression.UNSPEC
        
        """The IPv4 address allocation method used in the PDP context"""
        self.ipv4_alloc_method = ModemPDPIPv4AddrAllocMethod.NAS
        
        """The packet data protocol request type"""
        self.request_type = ModemPDPRequestType.NEW_OR_HANDOVER
        
        """The method to use for p-CSCF discovery"""
        self.pcscf_method = ModemPDPPCSCFDiscoveryMethod.AUTO
        
        """Flag indicating if the PDP context is used for IM CN 
        subsystem-related signalling"""
        self.for_IMCN = False
        
        """Flag indicating if the PDP context should use Non-Access Stratum 
        (NAS) Signalling Low Priority Indication (NSLPI)"""
        self.use_NSLPI = False
        
        """Flag indicating if the Protocol Configuration Options (PCO) should be protected"""
        self.use_secure_PCO = False
        
        """Flag indicating if NAS signalling should be used to discover the 
        IPv4 MTU"""
        self.use_NAS_ipv4_MTU_discovery = False
        
        """Flag indicating if the system supports local IP addresses in the 
        Traffic Flow Template (TFT)"""
        self.use_local_addr_ind = False
        
        """Flag indicating if NAS should be used to discover the MTU of non-IP
        PDP contexts"""
        self.use_NAS_non_IPMTU_discovery = False
        
        """"The authentication protocol used to activate the PDP"""
        self.auth_proto = ModemPDPAuthProtocol.NONE
        
        """The user to authenticate."""
        self.auth_user = ""
        
        """The password to authenticate"""
        self.auth_pass = ""


class ModemSocket:
    """This class represents a socket."""
    def __init__(self, id):
        """The state of the socket."""
        self.state = ModemSocketState.FREE

        """The socket identifier."""
        self.id = id

        """The PDP context ID in which the socket is created."""
        self.pdp_context_id = 1

        """Maximum transmission unit used by the TCP/UDP/IP stack."""
        self.mtu = 300

        """The socket exchange timeout in seconds."""
        self.exchange_timeout = 90

        """The connection timeout in seconds."""
        self.conn_timeout = 60

        """The number of milliseconds after which the transmit buffer is 
        effectively transmitted."""
        self.send_delay_ms = 5000

        """The protocol to use."""
        self.protocol = ModemSocketProto.UDP

        """How to handle data from other hosts than the remote host and port 
        that the socket is configured for."""
        self.accept_any_remote = ModemSocketAcceptAnyRemote.DISABLED

        """The IPv4 or IPv6 address of the remote host or a hostname in which 
        case a DNS query will be executed in the background."""
        self.remote_host = ""

        """The remote port to connect to."""
        self.remote_port = 0

        """In case of UDP, this is the local port number to which the remote 
        host can send an answer."""
        self.local_port = 0


class ModemGnssFixWaiter:
    """This class represents a wait_for_gnss_fix call that is waiting for data"""
    def __init__(self):
        self.event = Event()
        self.gnss_fix = None


class ModemHttpContext:
    """This class represents a socket."""
    def __init__(self):
        self.connected = False
        self.state = ModemHttpContextState.IDLE
        self.http_status = 0
        self.content_length = 0
        self.content_type = ''
