from asyncio import Event

from .enums import (
    WalterModemCMEError,
    WalterModemCmdState,
    WalterModemCmdType,
    WalterModemGNSSFixStatus,
    WalterModemHttpContextState,
    WalterModemNetworkRegState,
    WalterModemOpState,
    WalterModemOperatorFormat,
    WalterModemPDPAuthProtocol,
    WalterModemPDPDataCompression,
    WalterModemPDPHeaderCompression,
    WalterModemPDPIPv4AddrAllocMethod,
    WalterModemPDPPCSCFDiscoveryMethod,
    WalterModemPDPRequestType,
    WalterModemPDPType,
    WalterModemRat,
    WalterModemRspParserState,
    WalterModemRspType,
    WalterModemSimState,
    WalterModemSocketAcceptAnyRemote,
    WalterModemSocketProto,
    WalterModemSocketState,
    WalterModemState
)


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
        self.status = WalterModemGNSSFixStatus.READY
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
        self.format = WalterModemOperatorFormat.LONG_ALPHANUMERIC
        """The format in which the operator is stored."""
        
        self.name = ""
        """The name of the operator"""


class ModemBandSelection:
    """Represents a band selection for a given radio access technology and operator."""
    def __init__(self):
        self.rat = WalterModemRat.LTEM
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

class ModemMQTTResponse:
    def __init__(self, topic, qos):
        self.topic = topic
        self.qos = qos

class ModemSignalQuality:
    """Grouping the RSRQ and RSPR signal quality parameters."""
    def __init__(self):
        self.rsrq: int = None
        """The RSRQ in 10ths of dB"""

        self.rsrp: int = None
        """The RSPR in dBm"""


class ModemRsp:
    """Represents a response """
    def __init__(self):
        self.result: WalterModemState | None = WalterModemState.OK
        """The modem state after running the last command"""

        self.type: WalterModemRspType | None = WalterModemRspType.NO_DATA
        """The data type of the response"""
        
        self.reg_state: WalterModemNetworkRegState | None = None
        """The network registration state of the modem."""
        
        self.op_state: WalterModemOpState | None = None
        """The operational state of the modem."""
        
        self.sim_state: WalterModemSimState | None = None
        
        self.cme_error: WalterModemCMEError | None = None
        """The CME error last received from the modem."""
        
        self.rat: int | None = None
        """The radio access technology"""

        self.rssi: int | None = None
        """The RSSI of the signal in dBm"""

        self.signal_quality: ModemSignalQuality | None = None

        self.band_sel_cfg_list: list[ModemBandSelection] | None = None
        """The band selection configuration list."""
        
        self.pdp_address_list: list | None = None
        
        self.socket_id: int | None = None
        
        self.gnss_assistance: ModemGNSSAssistance | None = None
        """The band selection configuration list."""
        
        self.clock: float | None = None
        """Unix timestamp of the current time and date in the modem."""

        self.http_response: ModemHttpResponse | None = None

        self.mqtt_response: ModemMQTTResponse | None = None

        self.cell_information: ModemCellInformation | None = None

class ModemMqttMessage:
    def __init__(self, topic, length, qos, message_id = None, payload = None):
        self.topic = topic
        """The topic to which the message is published"""
        self.length = length
        """The length of the payload"""
        self.qos = qos
        """The quality of service"""
        self.message_id = message_id
        """The message ID"""
        self.payload = payload
        """The payload of the message"""
        self.free = True
        """Has the message been received from the buffer of the modem?"""

class ModemCmd:
    """Structure epresenting an AT command to be added to the command queue."""
    def __init__(self):
        self.state = WalterModemCmdState.NEW
        """The current state of the command."""
        
        self.type = WalterModemCmdType.TX_WAIT
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

        self.ring_return = None
        """Optional pointer to any mutable variable which may be provided with a ring"""
        
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
        self.state = WalterModemRspParserState.START_CR
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

class ModemSocket:
    """Represents a socket."""
    def __init__(self, id):
        self.state = WalterModemSocketState.FREE
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

        self.protocol = WalterModemSocketProto.UDP
        """The protocol to use."""

        self.accept_any_remote = WalterModemSocketAcceptAnyRemote.DISABLED
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
        self.state = WalterModemHttpContextState.IDLE
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