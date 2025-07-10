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

SIM_PIN = None
"""
Optional: Set this only if your SIM card requires a PIN for activation. 
Most IoT SIMs do not need this.
"""

MQTT_SERVER_ADDRESS = 'test.mosquitto.org'
"""
The address of the MQTT server.
"""

MQTT_PORT = '1883'
"""
The port of the MQTT server to use.
8883 is the startard port for MQTT with TLS
"""

MQTT_USERNAME = ''
"""
If requruired,
The username used to authenticate with the MQTT broker
"""

MQTT_PASSWORD = ''
"""
If required,
The password used to authenticate with the MQTT broker
"""

MQTT_TOPIC = None
"""
MQTT topic to use.  
Set to None to auto-generate: 'walter/mqtt-example/' + last 6 hex chars of the MAC address.
"""

PUBLISH_QOS = 0
SUBSCRIBE_QOS = 0
"""
The Quality of Service (QoS) levels for sent (published) and received (subscribed) MQTT messages.

0: At most once  - No acknowledgment, message may be lost.
1: At least once - Acknowledged, but may be delivered multiple times.
2: Exactly once  - Guaranteed delivery without duplicates, highest overhead.

Note: The higher the QoS, the more overhead and latency.
"""


MESSAGE = 'Hi from walter'
"""
Custom message to publish to the broker.
(the topic it publishes & subscribes to will be printed)
"""