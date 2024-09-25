import time
import walter
import _walter
import network
import uasyncio
import urequests

# PreferredConnType class representing the different types of preferred network
# connections. Each constant corresponds to a specific connection methodology:
# - WLAN_LTEM_NBIOT (0): Try WLAN first, then LTE-M, then NB-IoT
# - WLAN_NBIOT_LTEM (1): Try WLAN first, then NB-IoT, then LTE-M
# - LTEM_WLAN_NBIOT (2): Try LTE-M first, then WLAN, then NB-IoT
# - LTEM_NBIOT_WLAN (3): Try LTE-M first, then NB-IoT, then WLAN
# - NBIOT_WLAN_LTEM (4): Try NB-IoT first, then WLAN, then LTE-M
# - NBIOT_LTEM_WLAN (5): Try NB-IoT first, then LTE-M, then WLAN
# - LTEM_NBIOT (6): Try LTE-M first, then NB-IoT, don't use WLAN
# - NBIOT_LTEM (7): Try NB-IoT first, then LTE-M, don't use WLAN
# - WLAN_ONLY (8): Use only WLAN connectivity
# - LTEM_ONLY (9): Use only LTE-M connectivity
# - NBIOT_ONLY (10): Use only NB-IoT connectivity
class PreferredConnType:
    WLAN_LTEM_NBIOT = 0
    WLAN_NBIOT_LTEM = 1
    LTEM_WLAN_NBIOT = 2
    LTEM_NBIOT_WLAN = 3
    NBIOT_WLAN_LTEM = 4
    NBIOT_LTEM_WLAN = 5
    LTEM_NBIOT = 6
    NBIOT_LTEM = 7
    WLAN_ONLY = 8
    LTEM_ONLY = 9
    NBIOT_ONLY = 10

    # Sets for quick has_x lookups
    WLAN_TYPES = { WLAN_LTEM_NBIOT,
                   WLAN_NBIOT_LTEM,
                   LTEM_WLAN_NBIOT,
                   LTEM_NBIOT_WLAN,
                   NBIOT_WLAN_LTEM,
                   NBIOT_LTEM_WLAN,
                   WLAN_ONLY }

    CELLULAR_TYPES = { WLAN_LTEM_NBIOT,
                       WLAN_NBIOT_LTEM,
                       LTEM_WLAN_NBIOT,
                       LTEM_NBIOT_WLAN,
                       NBIOT_WLAN_LTEM,
                       NBIOT_LTEM_WLAN,
                       LTEM_NBIOT,
                       NBIOT_LTEM,
                       LTEM_ONLY,
                       NBIOT_ONLY }

    @staticmethod
    def has_wlan(pref_connection):
        return pref_connection in PreferredConnType.WLAN_TYPES

    @staticmethod
    def has_cellular(pref_connection):
        return pref_connection in PreferredConnType.CELLULAR_TYPES

# CommState class representing the state of the Radio Access Technology (RAT)
# that the unified communication library is currently using.
# - DISCONNECTED (0): The device is disconnected and never connected before.
# - WLAN_CONNECTING (1): The WLAN is connecting.
# - WLAN_CONNECTED (2): The WLAN is connected.
# - WLAN_DISCONNECTED (3): The WLAN is disconnected.
# - LTEM_CONNECTING (4): The LTE-M is connecting.
# - LTEM_CONNECTED (5): The LTE-M is connected.
# - LTEM_DISCONNECTED (6): The LTE-M is disconnected.
# - NBIOT_CONNECTING (7): The NB-IoT is connecting.
# - NBIOT_CONNECTED (8): The NB-IoT is connected.
# - NBIOT_DISCONNECTED (9): The NB-IoT is disconnected.
class CommState:
    DISCONNECTED = 0
    WLAN_CONNECTING = 1
    WLAN_CONNECTED = 2
    WLAN_DISCONNECTED = 3
    LTEM_CONNECTING = 4
    LTEM_CONNECTED = 5,
    LTEM_DISCONNECTED = 6,
    NBIOT_CONNECTING = 7
    NBIOT_CONNECTED = 8,
    NBIOT_DISCONNECTED = 9

    @staticmethod
    def get_next_rat(
            preferred_conn: int,
            comm_state: int,
            cur_comm_failed: bool = False):
        if comm_state == CommState.DISCONNECTED:
            if (
                preferred_conn == PreferredConnType.WLAN_LTEM_NBIOT or
                preferred_conn == PreferredConnType.WLAN_NBIOT_LTEM or
                preferred_conn == PreferredConnType.WLAN_ONLY
            ):
                return CommState.WLAN_CONNECTING
            elif (
                preferred_conn == PreferredConnType.LTEM_WLAN_NBIOT or
                preferred_conn == PreferredConnType.LTEM_NBIOT_WLAN or
                preferred_conn == PreferredConnType.LTEM_NBIOT or
                preferred_conn == PreferredConnType.LTEM_ONLY
            ):
                return CommState.LTEM_CONNECTING
            elif (
                preferred_conn == PreferredConnType.NBIOT_WLAN_LTEM or
                preferred_conn == PreferredConnType.NBIOT_LTEM_WLAN or
                preferred_conn == PreferredConnType.NBIOT_LTEM or
                preferred_conn == PreferredConnType.NBIOT_ONLY
            ):
                return CommState.NBIOT_CONNECTING

        elif (
            comm_state == CommState.WLAN_CONNECTING or
            comm_state == CommState.WLAN_DISCONNECTED
        ):
            if not cur_comm_failed:
                return CommState.WLAN_CONNECTING
            else:
                if preferred_conn == PreferredConnType.WLAN_LTEM_NBIOT:
                    return CommState.LTEM_CONNECTING
                elif preferred_conn == PreferredConnType.WLAN_NBIOT_LTEM:
                    return CommState.NBIOT_CONNECTING
                elif preferred_conn == PreferredConnType.LTEM_WLAN_NBIOT:
                    return CommState.NBIOT_CONNECTING
                elif preferred_conn == PreferredConnType.LTEM_NBIOT_WLAN:
                    return CommState.LTEM_CONNECTING
                elif preferred_conn == PreferredConnType.NBIOT_WLAN_LTEM:
                    return CommState.LTEM_CONNECTING
                elif preferred_conn == PreferredConnType.NBIOT_LTEM_WLAN:
                    return CommState.NBIOT_CONNECTING
                elif preferred_conn == PreferredConnType.LTEM_NBIOT:
                    return CommState.LTEM_CONNECTING
                elif preferred_conn == PreferredConnType.NBIOT_LTEM:
                    return CommState.NBIOT_CONNECTING
                elif preferred_conn == PreferredConnType.WLAN_ONLY:
                    return CommState.WLAN_CONNECTING
                elif preferred_conn == PreferredConnType.LTEM_ONLY:
                    return CommState.LTEM_CONNECTING
                elif preferred_conn == PreferredConnType.NBIOT_ONLY:
                    return CommState.NBIOT_CONNECTING

        elif comm_state == CommState.WLAN_CONNECTED:
            return CommState.WLAN_CONNECTED

        elif (
            comm_state == CommState.LTEM_CONNECTING or
            comm_state == CommState.LTEM_DISCONNECTED
        ):
            if not cur_comm_failed:
                return CommState.LTEM_CONNECTING
            else:
                if preferred_conn == PreferredConnType.WLAN_LTEM_NBIOT:
                    return CommState.NBIOT_CONNECTING
                elif preferred_conn == PreferredConnType.WLAN_NBIOT_LTEM:
                    return CommState.WLAN_CONNECTING
                elif preferred_conn == PreferredConnType.LTEM_WLAN_NBIOT:
                    return CommState.WLAN_CONNECTING
                elif preferred_conn == PreferredConnType.LTEM_NBIOT_WLAN:
                    return CommState.NBIOT_CONNECTING
                elif preferred_conn == PreferredConnType.NBIOT_WLAN_LTEM:
                    return CommState.NBIOT_CONNECTING
                elif preferred_conn == PreferredConnType.NBIOT_LTEM_WLAN:
                    return CommState.WLAN_CONNECTING
                elif preferred_conn == PreferredConnType.LTEM_NBIOT:
                    return CommState.NBIOT_CONNECTING
                elif preferred_conn == PreferredConnType.NBIOT_LTEM:
                    return CommState.NBIOT_CONNECTING
                elif preferred_conn == PreferredConnType.WLAN_ONLY:
                    return CommState.WLAN_CONNECTING
                elif preferred_conn == PreferredConnType.LTEM_ONLY:
                    return CommState.LTEM_CONNECTING
                elif preferred_conn == PreferredConnType.NBIOT_ONLY:
                    return CommState.NBIOT_CONNECTING

        elif comm_state == CommState.LTEM_CONNECTED:
            return CommState.LTEM_CONNECTED

        elif (
            comm_state == CommState.NBIOT_CONNECTING or
            comm_state == CommState.NBIOT_DISCONNECTED
        ):
            if not cur_comm_failed:
                return CommState.NBIOT_CONNECTING
            else:
                if preferred_conn == PreferredConnType.WLAN_LTEM_NBIOT:
                    return CommState.WLAN_CONNECTING
                elif preferred_conn == PreferredConnType.WLAN_NBIOT_LTEM:
                    return CommState.LTEM_CONNECTING
                elif preferred_conn == PreferredConnType.LTEM_WLAN_NBIOT:
                    return CommState.LTEM_CONNECTING
                elif preferred_conn == PreferredConnType.LTEM_NBIOT_WLAN:
                    return CommState.WLAN_CONNECTING
                elif preferred_conn == PreferredConnType.NBIOT_WLAN_LTEM:
                    return CommState.WLAN_CONNECTING
                elif preferred_conn == PreferredConnType.NBIOT_LTEM_WLAN:
                    return CommState.LTEM_CONNECTING
                elif preferred_conn == PreferredConnType.LTEM_NBIOT:
                    return CommState.LTEM_CONNECTING
                elif preferred_conn == PreferredConnType.NBIOT_LTEM:
                    return CommState.LTEM_CONNECTING
                elif preferred_conn == PreferredConnType.WLAN_ONLY:
                    return CommState.WLAN_CONNECTING
                elif preferred_conn == PreferredConnType.LTEM_ONLY:
                    return CommState.LTEM_CONNECTING
                elif preferred_conn == PreferredConnType.NBIOT_ONLY:
                    return CommState.NBIOT_CONNECTING

        elif comm_state == CommState.NBIOT_CONNECTED:
            return CommState.NBIOT_CONNECTED

# HttpContentType class representing the different supported HTTP content types 
# in this unified communications library. 
class HttpContentType:
    X_WWW_FORM_URLENCODED = 0
    TEXT_PLAIN = 1
    OCTET_STREAM = 2
    FORM_DATA = 3
    JSON = 4
    UNSPECIFIED = 5

    @staticmethod
    def to_string(http_content_type) -> str:
        if http_content_type == HttpContentType.X_WWW_FORM_URLENCODED:
            return "application/x-www-form-urlencoded"
        elif http_content_type == HttpContentType.TEXT_PLAIN:
            return "text/plain"
        elif http_content_type == HttpContentType.OCTET_STREAM:
            return "application/octet-stream"
        elif http_content_type == HttpContentType.FORM_DATA:
            return "multipart/form-data"
        elif http_content_type == HttpContentType.JSON:
            return "application/json"
        else:
            return ""

    @staticmethod
    def to_walter(http_content_type) -> _walter.ModemHttpPostParam:
        if http_content_type == HttpContentType.X_WWW_FORM_URLENCODED:
            return _walter.ModemHttpPostParam.URL_ENCODED
        elif http_content_type == HttpContentType.TEXT_PLAIN:
            return _walter.ModemHttpPostParam.TEXT_PLAIN
        elif http_content_type == HttpContentType.OCTET_STREAM:
            return _walter.ModemHttpPostParam.OCTET_STREAM
        elif http_content_type == HttpContentType.FORM_DATA:
            return _walter.ModemHttpPostParam.FORM_DATA
        elif http_content_type == HttpContentType.JSON:
            return _walter.ModemHttpPostParam.JSON
        else:
            return _walter.ModemHttpPostParam.UNSPECIFIED

# Split a URL string into the host, port and path
def split_url(url):
    if "://" in url:
        url = url.split("://")[1]
    if "/" in url:
        netloc, path = url.split("/", 1)
        path = "/" + path
    else:
        netloc = url
        path = "/"
    if ":" in netloc:
        host, port = netloc.split(":")
        port = int(port)
    else:
        host = netloc
        port = None
    return host, port, path

# WalterCommHttp class representing the HTTP(S) part of the unified
# communication library
class WalterCommHttp:
    # Class constants
    DEFAULT_HTTP_PROFILE = 1
    HTTP_POST_TIMEOUT = 5
    
    def __init__(
            self,
            comm: WalterComm,
            cell_http_profile: int = DEFAULT_HTTP_PROFILE):
        self.comm = comm
        self.cell_http_profile = cell_http_profile

    async def __exec(self, method: str, url: str, content_type: int, body) -> Bool:
        connected = await self.comm.connect()
        i = 0
        while not connected:
            if i > 2:
                print("Could not connect to one of the preferred connection types")
                return False
            i += 1
            connected = await self.comm.connect(comm_failed = True)
        if self.comm.comm_state == CommState.WLAN_CONNECTED:
            headers = (
                {} if content_type == HttpContentType.UNSPECIFIED
                else {"Content-Type": HttpContentType.to_string(content_type)}
            )
            try:
                if method == "GET":
                    response = urequests.get(url)
                elif method == "PUT":
                    response = urequests.put(url, headers=headers, data=body)
                elif method == "POST":
                    response = urequests.post(url, headers=headers, data=body)
                elif method == "DELETE":
                    response = urequests.delete(url)
                else:
                    print("Unsupported HTTP method")
                    return False
                print(f"Status: {response.status_code}")
                print(f"Response: {response.text}")
                response.close()
            except Exception as e:
                print(f"Error making HTTP request: {e}")
                return False
        elif (
            self.comm.comm_state == CommState.LTEM_CONNECTED or
            self.comm.comm_state == CommState.NBIOT_CONNECTED
        ):
            host, port, path = split_url(url)
            rsp = await self.comm.modem.http_config_profile(
                self.cell_http_profile, host, port)
            if rsp.result != _walter.ModemState.OK:
                print("Could not configure cellular modem HTTP profile")
                return False

            if method == "GET":
                rsp = await self.comm.modem.http_query(
                    self.cell_http_profile,
                    path,
                    _walter.ModemHttpQueryCmd.GET)
                if rsp.result != _walter.ModemState.OK:
                    rsp = await self.comm.modem.http_close(self.cell_http_profile)
                    print("Failed to send HTTP GET request over cellular")
                    return False
            elif method == "PUT":
                rsp = await self.comm.modem.http_send(
                    self.cell_http_profile,
                    path,
                    body,
                    _walter.ModemHttpSendCmd.PUT,
                    HttpContentType.to_string(content_type))
                if rsp.result != _walter.ModemState.OK:
                    rsp = await self.comm.modem.http_close(self.cell_http_profile)
                    print("Failed to send HTTP PUT request over cellular")
                    return False
            elif method == "POST":
                rsp = await self.comm.modem.http_send(
                    self.cell_http_profile,
                    path,
                    body,
                    _walter.ModemHttpSendCmd.POST,
                    HttpContentType.to_string(content_type))
                if rsp.result != _walter.ModemState.OK:
                    rsp = await self.comm.modem.http_close(self.cell_http_profile)
                    print("Failed to send HTTP POST request over cellular")
            elif method == "DELETE":
                rsp = await self.comm.modem.http_query(
                    self.cell_http_profile,
                    path,
                    _walter.ModemHttpQueryCmd.DELETE)
                if rsp.result != _walter.ModemState.OK:
                    rsp = await self.comm.modem.http_close(self.cell_http_profile)
                    print("Failed to send HTTP DELETE request over cellular")
            rsp = await self.comm.modem.http_did_ring(self.cell_http_profile)
            i = 0
            while rsp.result != _walter.ModemState.OK:
                if i > self.__class__.HTTP_POST_TIMEOUT:
                    print("Could not receive HTTP response")
                    return False
                rsp = await self.comm.modem.http_did_ring(self.cell_http_profile)
                i += 1
                await uasyncio.sleep(1)
            print(f"Status: {rsp.http_response.http_status}")
            print(f"Response: {rsp.http_response.data.decode('utf-8')}")
            rsp = await self.comm.modem.http_close(self.cell_http_profile)
        return True

    async def get(self, url: str, content_type: HttpContentType = HttpContentType.UNSPECIFIED):
        return await self.__exec("GET", url, content_type, None)

    async def put(self, url: str, content_type: HttpContentType = HttpContentType.UNSPECIFIED, body = None):
        return await self.__exec("PUT", url, content_type, body)

    async def post(self, url: str, content_type: HttpContentType = HttpContentType.UNSPECIFIED, body = None):
        return await self.__exec("POST", url, content_type, body)

    async def delete(self, url: str, content_type: HttpContentType = HttpContentType.UNSPECIFIED, body = None):
        return await self.__exec("DELETE", url, content_type, body)
    
    def get_sync(self, url: str, content_type: HttpContentType = HttpContentType.UNSPECIFIED):
        return uasyncio.run(self.__exec("GET", url, content_type, None))

    def put_sync(self, url: str, content_type: HttpContentType = HttpContentType.UNSPECIFIED, body = None):
        return uasyncio.run(self.__exec("PUT", url, content_type, body))

    def post_sync(self, url: str, content_type: HttpContentType = HttpContentType.UNSPECIFIED, body = None):
        return uasyncio.run(self.__exec("POST", url, content_type, body))

    def delete_sync(self, url: str, content_type: HttpContentType = HttpContentType.UNSPECIFIED, body = None):
        return uasyncio.run(self.__exec("DELETE", url, content_type, body))

# WalterComm is a unified communications library which makes it possible to
# send and receive messages using various protocols without having to worry
# about the underlying RAT (Radio Access Technology)
class WalterComm:
    def __init__(
            self,
            preferred_conn = PreferredConnType.WLAN_LTEM_NBIOT, 
            wlan_ssid: str = None,
            wlan_bssid: str = None,
            wlan_security = None,
            wlan_user: str = None,
            wlan_key: str = None,
            wlan_conn_timeout_sec: int = 30,
            cell_apn: str = None,
            cell_apn_user: str = None,
            cell_apn_password: str = None,
            cell_conn_timeout_sec: int = 60):
        # Network settings
        self.preferred_conn = preferred_conn
        self.wlan_ssid = wlan_ssid
        self.wlan_bssid = wlan_bssid
        self.wlan_security = wlan_security
        self.wlan_user = wlan_user
        self.wlan_key = wlan_key
        self.wlan_conn_timeout_sec = wlan_conn_timeout_sec
        self.cell_apn = cell_apn
        self.cell_apn_user = cell_apn_user
        self.cell_apn_password = cell_apn_password
        self.cell_conn_timeout_sec = cell_conn_timeout_sec

        # Internal state and network devices
        self.comm_state = CommState.DISCONNECTED
        self.wlan = network.WLAN(network.STA_IF)
        self.modem = walter.Modem()
        self.pdp_context_id = None

        # Protocol class instantiations
        self.http = WalterCommHttp(self)

        # Initialize the modem if required
        if PreferredConnType.has_cellular(self.preferred_conn):
            self.modem.begin()

    async def _connect_wlan(self) -> bool:
        if self.comm_state == CommState.WLAN_CONNECTED:
            self.wlan.config(pm=None)
            return True

        self.wlan.active(True)
        if not self.wlan.isconnected():
            print("Connecting to WLAN network...")
            # TODO: also configure other settings
            self.wlan.connect(self.wlan_ssid, self.wlan_key)

            # Non-blocking wait for connection with timeout
            start_time = time.time()
            while not self.wlan.isconnected():
                if time.time() - start_time > self.wlan_conn_timeout_sec:
                    print("Timed out while connecting to WLAN network")
                    self._disconnect_wlan()
                    return False
                await uasyncio.sleep(1)

        self.comm_state = CommState.WLAN_CONNECTED
        print("WLAN connected:", self.wlan.ifconfig())
        return True

    def _suspend_wlan(self):
        self.wlan.config(pm=network.PM_MAX)
        return

    def _disconnect_wlan(self):
        self.wlan.disconnect()
        self.comm_state = CommState.WLAN_DISCONNECTED
        print("WLAN disconnected")
        return

    async def _connect_cellular(self) -> bool:
        if (
            self.comm_state == CommState.LTEM_CONNECTED or
            self.comm_state == CommState.NBIOT_CONNECTED
        ):
            return True

        rsp = await self.modem.get_rat()
        if rsp.result != _walter.ModemState.OK:
            print("Could not retrieve current cellular RAT")
            return False

        rat = (
            _walter.ModemRat.LTEM if self.comm_state == CommState.LTEM_CONNECTING
            else _walter.ModemRat.NBIOT
        )
        if rsp.rat != rat:
            rsp = await self.modem.set_rat(rat)
            if rsp.result != _walter.ModemState.OK:
                print("Could not change cellular modem RAT")
                return False
            await self.modem.reset()
            uasyncio.sleep(0.1)

        if self.cell_apn_user is None and self.cell_apn_password is None:
            rsp = await self.modem.create_PDP_context(
                apn = self.cell_apn if self.cell_apn is not None else "")
            if rsp.result != _walter.ModemState.OK:
                print("Could not create PDP context")
                return False
            self.pdp_ctx_id = rsp.pdp_ctx_id
        else:
            rsp = await self.modem.create_PDP_context(
                apn = self.cell_apn if self.cell_apn is not None else "",
                auth_user = self.cell_apn_user,
                auth_pass = self.cell_apn_password)
            if rsp.result != _walter.ModemState.OK:
                print("Could not create PDP context")
                return False
            self.pdp_ctx_id = rsp.pdp_ctx_id
            rsp = await self.modem.authenticate_PDP_context(ctx_id)
            if rsp.result != _walter.ModemState.OK:
                print("Could not authenticate the PDP context")
                return False
        rsp = await self.modem.set_op_state(_walter.ModemOpState.FULL)
        if rsp.result != _walter.ModemState.OK:
            print("Could not set cellular modem operational state to FULL")
            return False
        
        i = 0
        rsp = self.modem.get_network_reg_state()
        while (
            rsp.reg_state != _walter.ModemNetworkRegState.REGISTERED_HOME and
            rsp.reg_state != _walter.ModemNetworkRegState.REGISTERED_ROAMING
        ):
            if i > self.cell_conn_timeout_sec:
                print("Timed out while connecting to %s" % (
                    "LTE-M" if self.comm_state == CommState.LTEM_CONNECTING
                    else "NB-IoT"
                    )
                )
                await self._disconnect_cellular()
                return False
            i += 1
            await uasyncio.sleep(1)
            rsp = self.modem.get_network_reg_state()

        conn_rat = (
            CommState.LTEM_CONNECTED if self.comm_state == CommState.LTEM_CONNECTING
            else CommState.NBIOT_CONNECTED
        )
        print("%s connected" % ("LTE-M" if conn_rat == CommState.LTEM_CONNECTED else "NB-IoT"))
        self.comm_state = conn_rat
        return True

    def _suspend_cellular(self):
        # TODO: implement
        return

    async def _disconnect_cellular(self):
        rsp = await self.modem.set_op_state(_walter.ModemOpState.MINIMUM)
        if rsp.result != _walter.ModemState.OK:
            print("Could not set cellular modem operational state to MINIMUM") 
        if (
            self.comm_state == CommState.LTEM_CONNECTED or
            self.comm_state == CommState.LTEM_CONNECTING
        ):
            self.comm_state = CommState.LTEM_DISCONNECTED
            print("LTE-M disconnected")
        elif (
            self.comm_state == CommState.NBIOT_CONNECTED or
            self.comm_state == CommState.NBIOT_CONNECTING
        ):
            self.comm_state = CommState.NBIOT_DISCONNECTED
            print("NB-IoT disconnected")
        return

    async def connect(self, comm_failed: bool = False) -> bool:
        if (
            self.comm_state == CommState.WLAN_CONNECTED or
            self.comm_state == CommState.LTEM_CONNECTED or
            self.comm_state == CommState.NBIOT_CONNECTED
            ):
            return True

        next_rat = CommState.get_next_rat(self.preferred_conn, self.comm_state, comm_failed)
        self.comm_state = next_rat

        if next_rat == CommState.WLAN_CONNECTING:
            return await self._connect_wlan()
        elif (
            next_rat == CommState.LTEM_CONNECTING or
            next_rat == CommState.NBIOT_CONNECTING
        ):
            return await self._connect_cellular()
        return False

    def suspend(self):
        if self.comm_state == CommState.WLAN_CONNECTED:
            self._suspend_wlan()

        elif (
            self.comm_state == CommState.LTEM_CONNECTED or
            self.comm_state == CommState.NBIOT_CONNECTED
        ):
            self._suspend_cellular()
        return

    def disconnect(self):
        if (
            self.comm_state == CommState.WLAN_CONNECTED or
            self.comm_state == CommState.WLAN_CONNECTING
        ):
            self._disconnect_wlan()

        elif (
            self.comm_state == CommState.LTEM_CONNECTED or
            self.comm_state == CommState.LTEM_CONNECTING or
            self.comm_state == CommState.NBIOT_CONNECTED or
            self.comm_state == CommState.NBIOT_CONNECTING
        ):
            self._disconnect_cellular()
        return
