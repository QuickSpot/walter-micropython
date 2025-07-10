from walter_modem.mixins._default_pdp import WalterModemPDPAuthProtocol

CELL_APN = ''
"""
The cellular Access Point Name (APN).
Leave blank to enable automatic APN detection, which is sufficient for most networks.
Manually set this only if your network provider specifies a particular APN.
"""

APN_USERNAME = ''
"""
The username for APN authentication.
Typically, this is not required and should be left blank.
Only provide a username if your network provider explicitly mandates it.
"""

APN_PASSWORD = ''
"""
The password for APN authentication.
This is generally unnecessary and should remain blank.
Set a password only if it is specifically required by your network provider.
"""

AUTHENTICATION_PROTOCOL = WalterModemPDPAuthProtocol.NONE
"""
The authentication protocol to use if requiren.
Leave as none when no username/password is set.
"""

SERVER_ADDRESS = 'walterdemo.quickspot.io'
"""
The address of the Walter Demo server.
"""

SERVER_PORT = 1999
"""
The UDP port of the Walter Demo server.
"""

SIM_PIN = None
"""
Optional: Set this only if your SIM card requires a PIN for activation. 
Most IoT SIMs do not need this.
"""

PACKET_SIZE = 29
"""
The size in bytes of hte uploaded data packet.
"""

MAX_GNSS_CONFIDENCE = 255.0
"""
The maximum GNSS confidence threshold.
All GNSS fixes with a confidence value below this number are considered valid.
"""

SLEEP_TIME = 60
"""
The time (in seconds) to sleep between readouts
"""