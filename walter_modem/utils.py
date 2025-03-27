import network
import time
import ubinascii


from .enums import (
    WalterModemPDPType
)

def get_mac() -> str:
    return ubinascii.hexlify(network.WLAN().config('mac'),':').decode()

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

def modem_string(string: str) -> str:
    return '' if string is None else f'"{string}"'

def modem_bool(b: bool) -> int:
    return 1 if b else 0

def log(level, msg):
    print(f'WalterModem [{level:<9}]: {msg}')
