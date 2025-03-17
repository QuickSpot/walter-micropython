import network
import time
import ubinascii


from .enums import (
    WalterModemPDPType
)

def get_mac() -> str:
    return ubinascii.hexlify(network.WLAN().config('mac'),':').decode()

def bytes_to_str(byte_data):
    """Convert byte data to a string."""
    if isinstance(byte_data, bytearray):
        try:
            return byte_data.decode('utf-8', 'replace')
        except Exception:
            return byte_data
    return byte_data

def parse_cclk_time(time_str: str) -> float | None:
    """
    :param time_str: format: yy/mm/dd,hh:nn:ss+qq where qq = tz offset in quarters of an hour
    """
    yy = int(time_str[:2])
    mm = int(time_str[3:5])
    dd = int(time_str[6:8])
    hh = int(time_str[9:11])
    nn = int(time_str[12:14])
    ss = int(time_str[15:17])
    if time_str[17] == '+':
        qq = int(time_str[18:])
    else:
        qq = -int(time_str[18:])

    # 1970-1999 are invalid since micropython epoch starts at 2000
    if yy >= 70:
        return None

    yyyy = yy + 2000

    tm = (yyyy, mm, dd, hh, nn, ss, 0, 0, 0)

    # on arduino:
    # epoch (1 jan 1970) = 0
    # 1 jan 2000 = 946684800
    #
    # on micropython:
    # epoch (1 jan 2000) = 0
    # so add constant 946684800 to be compatible with our arduino lib

    time_val = time.mktime(tm) + 946684800 - (qq * 15 * 60)

    return time_val

def parse_gnss_time(time_str: str) -> float | None:
    """
    :param time_str: format: yyyy-mm-ddThh:nn
    """
    yyyy = int(time_str[:4])
    mm = int(time_str[5:7])
    dd = int(time_str[8:10])
    hh = int(time_str[11:13])
    nn = int(time_str[14:16])
    if len(time_str) > 16:
        ss = int(time_str[17:19])
    else:
        ss = 0

    # 1970-1999 are invalid since micropython epoch starts at 2000
    if yyyy < 2000:
        return None

    tm = (yyyy, mm, dd, hh, nn, ss, 0, 0, 0)

    # on arduino:
    # epoch (1 jan 1970) = 0
    # 1 jan 2000 = 946684800
    #
    # on micropython:
    # epoch (1 jan 2000) = 0
    # so add constant 946684800 to be compatible with our arduino lib

    time_val = time.mktime(tm) + 946684800

    return time_val

def pdp_type_as_string(pdp_type: int) -> str:
    if pdp_type == WalterModemPDPType.X25:
        return '"X.25"'
    if pdp_type == WalterModemPDPType.IP:
        return '"IP"'
    if pdp_type == WalterModemPDPType.IPV6:
        return '"IPV6"'
    if pdp_type == WalterModemPDPType.IPV4V6:
        return '"IPV4V6"'
    if pdp_type == WalterModemPDPType.OSPIH:
        return '"OPSIH"'
    if pdp_type == WalterModemPDPType.PPP:
        return '"PPP"'
    if pdp_type == WalterModemPDPType.NON_IP:
        return '"Non-IP"'
    return ''

def modem_string(string: str) -> str:
    if string:
        return '"' + string + '"'
    else:
        return ''

def modem_bool(a_bool):
    if a_bool:
        return 1
    else:
        return 0

def log(level, msg):
    print(f'WalterModem [{level:<9}]: {msg}')
