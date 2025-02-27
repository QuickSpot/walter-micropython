CELL_APN = ''
"""
The cellular Access Point Name (APN).
Leave blank for automatic APN detection, which is sufficient for most networks.
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

SIM_PIN = None
"""
Optional: Set this only if your SIM card requires a PIN for activation. 
Most IoT SIMs do not need this.
"""

BLYNK_SERVER_ADDRESS = 'blynk.cloud'
"""
The blynk server address: eg: "blynk.cloud", "lon1.blynk.cloud", ...
"""

BLYNK_TOKEN = ''
"""
Your device auth token
"""

BLYNK_DEVICE_PINS = {
    'temperature': None,
    'humitidy': None,
    'pressure': None,
    'input_voltage': None,
    'input_current': None,
    'system_voltage': None,
    'battery_voltage': None,
    'battery_current': None,
    'battery_percentage': None,
    'rsrp': None
}
"""
Virtual Pins corresponding to the supported measurements
"""