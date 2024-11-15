"""
Test of the modems MQTT capabilities

based on ModemMqttTest.ino:

https://github.com/QuickSpot/walter-arduino/blob/main/examples/ModemMqttTest/ModemMqttTest.ino

with added TLS support.
The required certificates need to be stored in the NVRAM of the modem first!
(see 'upload_tls_certificates.py' in same folder)
"""

import uasyncio
import ubinascii
import network
import walter
import _walter

# settings for Soracom SIM card
# APN = "soracom.io"
# APN_USERNAME = 'sora'
# APN_PASSWORD = 'sora'

# settings for 1nce SIM card
APN = "iot.1nce.net"
APN_USERNAME = ''
APN_PASSWORD = ''

TLS_PROFILE = 1

MQTT_ADDR = "xxx.xxx.xxx.xxx" # some MQTT server
MQTT_PORT = 8883 # standard port for MQTT with TLS
MQTT_USERNAME = 'user'
MQTT_PASSWORD = 'pass!'
MQTT_SUB_TOPIC = 'test0'
MQTT_PUB_TOPIC = 'test1'
MQTT_QOS = 0

modem = None
ctx_id = None
counter = 0
device_eui = None

async def setup():
    print("Walter modem MQTT test v0.0.1")
    
    global device_eui
    device_eui = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
    print("Walter's EUI is: %s" % device_eui)

    rsp = await modem.check_comm()
    if rsp.result != _walter.ModemState.OK:
        print("Modem communication error")
        return False

    rsp = await modem.get_op_state()
    if rsp.result != _walter.ModemState.OK:
        print("Could not retrieve modem operational state")
        return False

    print('Modem operational state: %d' % rsp.op_state)

#     rsp = await modem.get_radio_bands()
#     if rsp.result != _walter.ModemState.OK:
#         print("Could not retrieve configured radio bands")
#         return False
# 
#     print('Modem is configured for the following bands:')
#     for band_sel in rsp.band_sel_cfg_set:
#         print('rat=%d net_operator.name=[%s]' %
#             (band_sel.rat, band_sel.net_operator.name))
#         for band in band_sel.bands:
#             print('  band:%d' % band)

    rsp = await modem.set_op_state(_walter.ModemOpState.NO_RF)
    if rsp.result != _walter.ModemState.OK:
        print("Could not set operational state to NO RF")
        return False

    print("Successfully set operational state to NO RF")

    # Give the modem time to detect the SIM
    await uasyncio.sleep(2)
  
    rsp = await modem.unlock_sim(None)
    if rsp.result != _walter.ModemState.OK:
        print("Could not unlock SIM card")
        return False

    print("Successfully unlocked SIM card")

    # Create PDP context
    rsp = await modem.create_PDP_context(APN,
        _walter.ModemPDPAuthProtocol.PAP, APN_USERNAME, APN_PASSWORD,
        _walter.ModemPDPType.IP, None,
        _walter.ModemPDPHeaderCompression.OFF,
        _walter.ModemPDPDataCompression.OFF,
        _walter.ModemPDPIPv4AddrAllocMethod.DHCP,
        _walter.ModemPDPRequestType.NEW_OR_HANDOVER,
        _walter.ModemPDPPCSCFDiscoveryMethod.AUTO, False, True,
        False, False, False, False)

    if rsp.result != _walter.ModemState.OK:
        print("Could not create PDP context")
        return False

    print("Created PDP context")

    # Authenticate the PDP context
    global ctx_id
    ctx_id = rsp.pdp_ctx_id
    if APN_USERNAME:
        rsp = await modem.authenticate_PDP_context(ctx_id)
        if rsp.result != _walter.ModemState.OK:
            print("Could not authenticate the PDP context")
            return False
        print("Authenticated the PDP context")
    else:
        print("No authentication required.")

    # set operational state to FULL
    rsp = await modem.set_op_state(_walter.ModemOpState.FULL)
    if rsp.result != _walter.ModemState.OK:
        print("Could not set operational state to FULL")
        return False

    print("Successfully set operational state to FULL")

    # Set the network operator selection to automatic */
    rsp = await modem.set_network_selection_mode(
        _walter.ModemNetworkSelMode.AUTOMATIC, None,
        _walter.ModemOperatorFormat.LONG_ALPHANUMERIC)
    if rsp.result != _walter.ModemState.OK:
        print("Could not set the network selection mode to automatic")
        return False

    print("Network selection mode to was set to automatic")

    # Wait for the network to become available */
    rsp = modem.get_network_reg_state()
    while rsp.reg_state != _walter.ModemNetworkRegState.REGISTERED_HOME and rsp.reg_state != _walter.ModemNetworkRegState.REGISTERED_ROAMING:
        await uasyncio.sleep(.1)
        rsp = modem.get_network_reg_state()

    print("Connected to the network")

    # Activate the PDP context
    rsp = await modem.set_PDP_context_active(True, ctx_id)
    if rsp.result != _walter.ModemState.OK:
        print("Could not activate the PDP context")
        return False

    print("Activated the PDP context")

    # Attach the PDP context
    rsp = await modem.attach_PDP_context(True)
    if rsp.result != _walter.ModemState.OK:
        print("Could not attach to the PDP context")
        return False

    print("Attached to the PDP context")

    rsp = await modem.get_PDP_address(ctx_id)
    if rsp.result != _walter.ModemState.OK:
        print("Could not retrieve PDP context addresses")
        return False

    print("PDP context address list:")
    for addr in rsp.pdp_address_list:
        print('- %s' % addr)

    rsp = await modem.tls_config_profile(TLS_PROFILE, _walter.ModemTlsValidation.CA, _walter.ModemTlsVersion.V12, 6, None, None)
    if rsp.result != _walter.ModemState.OK:
        print("Failed to configure TLS.")
        return False
    
    print('TLS configured.')
    
    # using the device eui as 
    rsp = await modem.mqtt_connect(MQTT_ADDR, MQTT_PORT, device_eui, MQTT_USERNAME, MQTT_PASSWORD, TLS_PROFILE)
    if rsp.result != _walter.ModemState.OK:
        print("Failed to connect to MQTT server.")
        return False
    
    print('Connected to MQTT server.')
    
    rsp = await modem.mqtt_subscribe(MQTT_SUB_TOPIC, MQTT_QOS)
    if rsp.result != _walter.ModemState.OK:
        print("Failed to subscribe to topic.")
        return False
    
    print('Subscribed to topic "{}".'.format(MQTT_SUB_TOPIC))

#     rsp = await modem.mqtt_disconnect()
#     if rsp.result != _walter.ModemState.OK:
#         print("Error when disconnecting from MQTT server.")
#         return False
#     
#     print('Disconnected from MQTT server.')
    
    return True


async def loop():
    n = await modem.mqtt_receive()
    if n:
        print("{} new mqtt messages.".format(n))
        while True:
            msg = modem.get_mqtt_message()
            if msg:
                print("Topic: {}\r\n{}".format(msg.topic, msg.payload))
                
            else:
                break
    
    await uasyncio.sleep(1)
    
    global device_eui
    if n:
        await modem.mqtt_publish(
             MQTT_PUB_TOPIC,
             "Walter {} has received {} message(s).".format(device_eui, n),
             0
        )

    return True

async def main():
    if not await setup():
        return
    print('setup finished. waiting for messages...')
    while True:
        if not await loop():
            break


modem = walter.Modem()
modem.begin(main)
