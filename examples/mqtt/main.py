import micropython # type: ignore
micropython.opt_level(1)
"""
Set the MicroPython opt level.
See: https://docs.micropython.org/en/latest/library/micropython.html#micropython.opt_level
"""

import asyncio
import network # type: ignore
import sys

from walter_modem import Modem
from walter_modem.coreEnums import *
from walter_modem.coreStructs import *
from walter_modem.mixins.default_sim_network import *
from walter_modem.mixins.default_pdp import *
from walter_modem.mixins.mqtt import *
from walter_modem.mixins.tls_certs import *

# region CONFIG VARIABLES

# IMPORTANT
# This is an example sketch with verbose comments and logging,
# in production codde such verbose comments could be left out to reduce codesize.

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

#endregion

modem = Modem(MQTTMixin, TLSCertsMixin, load_default_power_saving_mixin=False)
"""
The modem instance

Loading the MQTT mixin for MQTT functionality.
Loading the TLSCertsMixin to work with tls profiles.

Specificying to not load the default power saving mixin,
as we're not using it in this simple example.
Although in most real-life scenarios it is advised to
configure power-saving for reduced energy consumption
"""

modem_rsp = WalterModemRsp()
"""
The modem response object that is (re-)used 
when we need information from the modem.
"""

def get_unique_topic():
    mac = network.WLAN().config('mac')
    suffix = ''.join('{:02X}'.format(byte) for byte in mac[-3:])
    return f'walter/mqtt-example/{suffix}'


topic = MQTT_TOPIC if MQTT_TOPIC is not None else get_unique_topic()

async def wait_for_network_reg_state(timeout: int, *states: WalterModemNetworkRegState) -> bool:
    """
    Wait for the modem network registration state to reach the desired state(s).
    
    :param timeout: Timeout period (in seconds)
    :param states: One or more states to wait for

    :return: True if the current state matches any of the provided states, False if timed out.
    """
    for _ in range(timeout):
        if modem.get_network_reg_state() in states:
            return True
        
        await asyncio.sleep(1)
    
    return False

async def lte_connect(_retry: bool = False) -> bool:
    """
    Connect to the LTE network.

    Attempts to connect the modem to the LTE network.
    If no connection could be made within five minutes, the function retries with another RAT.
    If the second attempt fails too, the function returns False.

    :param _retry: Only used by recursive call on second attempt with other RAT.

    :return bool: True on success, False on failure.
    """
    global modem_rsp

    if modem.get_network_reg_state() in (
        WalterModemNetworkRegState.REGISTERED_HOME,
        WalterModemNetworkRegState.REGISTERED_ROAMING
    ):
        return True
    
    if not await modem.set_op_state(WalterModemOpState.FULL):
        print('  - Failed to set operational state to full')
        return False
    
    if not await modem.set_network_selection_mode(WalterModemNetworkSelMode.AUTOMATIC):
        print('  - Failed to set network selection mode to automatic')
        return False
    
    print('  - Waiting for network registration')
    if not await wait_for_network_reg_state(
        300,
        WalterModemNetworkRegState.REGISTERED_HOME,
        WalterModemNetworkRegState.REGISTERED_ROAMING
    ):
        if await modem.get_rat(rsp=modem_rsp):
            if not await modem.set_op_state(WalterModemOpState.MINIMUM):
                print('  - Failed to connected using current RAT')
                return False

        if not await wait_for_network_reg_state(5, WalterModemNetworkRegState.NOT_SEARCHING):
            print('  - Unexpected: modem not on standby after 5 seconds')
            return False
        
        rat = modem_rsp.rat

        if _retry:
            print('  - Failed to connect using LTE-M and NB-IoT, no connection possible')
            
            if rat != WalterModemRat.LTEM:
                if not await modem.set_rat(WalterModemRat.LTEM):
                    print('  - Failed to set RAT back to *preferred* LTEM')
                await modem.reset()
            
            return False
        
        print(f'  - Failed to connect to LTE network using: {"LTE-M" if rat == WalterModemRat.LTEM else "NB-IoT"}')
        print(f'  - Switching modem to {"NB-IoT" if rat == WalterModemRat.LTEM else "LTE-M"} and retrying...')

        next_rat = WalterModemRat.NBIOT if rat == WalterModemRat.LTEM else WalterModemRat.LTEM

        if not await modem.set_rat(next_rat):
            print('  - Failed to switch RAT')
            return False
        
        await modem.reset()
        return await lte_connect(_retry=True)
    
    return True

async def unlock_sim() -> bool:
    if not await modem.set_op_state(WalterModemOpState.NO_RF):
        print('  - Failed to set operational state to: NO RF')
        return False

    # Give the modem time to detect the SIM
    await asyncio.sleep(2)
    if await modem.unlock_sim(pin=SIM_PIN):
        print('  - SIM unlocked')
    else:
        print('  - Failed to unlock SIM card')
        return False
   
    return True

async def setup():
    global modem_rsp
    use_tls = int(MQTT_PORT) == 8883

    print('Walter MQTT Example')
    print('---------------')
    print(f'Configured broker: {MQTT_SERVER_ADDRESS}:{MQTT_PORT}')
    print(f'Topic: {topic}')

    await modem.begin()

    if not await modem.check_comm():
        print('Modem communication error')
        return False
    
    if SIM_PIN != None and not await unlock_sim():
        return False
    
    if not await modem.pdp_context_create(
        apn=CELL_APN,
        rsp=modem_rsp
    ):
        print('Failed to create socket')
        return False
   
    if APN_USERNAME and not await modem.pdp_set_auth_params(
        protocol=AUTHENTICATION_PROTOCOL,
        user_id=APN_USERNAME,
        password=APN_PASSWORD
    ):
        print('Failed to set PDP context authentication protocol')

    print('Connecting to LTE Network')
    if not await lte_connect():
        return False
    
    if use_tls:
        if not await modem.tls_config_profile(
            profile_id=1,
            tls_validation=WalterModemTlsValidation.NONE,
            tls_version=WalterModemTlsVersion.TLS_VERSION_13
        ):
            print('Failed to configure TLS profile')
            return False
    
    print('Configurng MQTT')
    if not await modem.mqtt_config(
        user_name=MQTT_USERNAME,
        password=MQTT_PASSWORD,
        tls_profile_id=1 if use_tls else None
    ):
        print('Failed to configure MQTT')
        return False
    
    print('Connecting to MQTT server')
    if not await modem.mqtt_connect(
        server_name=MQTT_SERVER_ADDRESS,
        port=int(MQTT_PORT),
    ):
        print('Failed to connect to MQTT server')
        return False
    
    print('Connected to MQTT server')

    return True

async def loop():
    global modem_rsp
    mqtt_messages = []

    if await modem.mqtt_did_ring(msg_list=mqtt_messages, rsp=modem_rsp):
        print(f'New MQTT message (topic: {modem_rsp.mqtt_response.topic}, qos: {modem_rsp.mqtt_response.qos})')
        print(mqtt_messages.pop())
    else:
        if modem_rsp.result != WalterModemState.NO_DATA:
            print('Fault with mqtt_did_ring: '
                  f'{WalterModemState.get_value_name(modem_rsp.result)}')

async def main():
    try:
        if not await setup():
            print('Failed to complete setup, raising runtime error to stop the script')
            raise RuntimeError()

        payload = MESSAGE.encode() if isinstance(MESSAGE, str) else MESSAGE
        
        if not await modem.mqtt_publish(
            topic=topic,
            data=payload,
            qos=PUBLISH_QOS
        ):
            print('Failed to publish message')
            raise RuntimeError()
        print('Message published')

        if await modem.mqtt_subscribe(
            topic=topic,
            qos=SUBSCRIBE_QOS
        ):
            print(f'Subscribed to topic: "{topic}"')
        else:
            print('Failed to subscribe to topic, raising runtime error to stop the script')
            raise RuntimeError()

        while True:
            await loop()
            await asyncio.sleep(1)
    except Exception as err:
        print('ERROR: (boot.py, main): ')
        sys.print_exception(err)
        print('Waiting 5 minutes before exiting')
        # Sleep a while to prevent getting stuck in an infite crash loop
        # And give time for the serial over usb to function
        await asyncio.sleep(300)

asyncio.run(main())