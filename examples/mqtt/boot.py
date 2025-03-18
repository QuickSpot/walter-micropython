import asyncio
import network
import sys

from walter_modem import Modem

from walter_modem.enums import (
    WalterModemNetworkRegState,
    WalterModemState,
    WalterModemOpState,
    WalterModemNetworkSelMode,
    WalterModemPDPAuthProtocol,
    WalterModemTlsValidation,
    WalterModemTlsVersion
)

from walter_modem.structs import (
    ModemRsp,
    WalterModemRat
)

import config

modem = Modem()
"""
The modem instance
"""

modem_rsp = ModemRsp()
"""
The modem response object.
We re-use this single one, for memory efficiency.
"""

def match_auth_proto():
    if config.AUTH_PROTOCOL == 'PAP': return WalterModemPDPAuthProtocol.PAP
    if config.AUTH_PROTOCOL == 'CHAP': return WalterModemPDPAuthProtocol.CHAP
    return WalterModemPDPAuthProtocol.NONE

pdp_auth_proto = match_auth_proto()

def get_unique_topic():
    mac = network.WLAN().config('mac')
    return f'walter/mqtt-example/{''.join('{:02X}'.format(byte) for byte in mac[-3:])}'


topic = config.MQTT_TOPIC if config.MQTT_TOPIC is not None else get_unique_topic()

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
    if await modem.unlock_sim(pin=config.SIM_PIN):
        print('  - SIM unlocked')
    else:
        print('  - Failed to unlock SIM card')
        return False
   
    return True

async def setup():
    global modem_rsp

    print('Walter MQTT Example')
    print('---------------')
    print(f'Configured broker: {config.MQTT_SERVER_ADDRESS}:{config.MQTT_PORT}')
    print(f'Topic: {topic}')

    await modem.begin()

    if not await modem.check_comm():
        print('Modem communication error')
        return False
    
    if config.SIM_PIN != None and not await unlock_sim():
        return False
    
    if not await modem.create_PDP_context(
        apn=config.CELL_APN,
        auth_proto=pdp_auth_proto,
        auth_user=config.APN_USERNAME,
        auth_pass=config.APN_PASSWORD,
        rsp=modem_rsp
    ):
        print('Failed to create socket')
        return False
   
    if config.APN_USERNAME and not await modem.authenticate_PDP_context():
        print('Failed to authenticate PDP context')

    print('Connecting to LTE Network')
    if not await lte_connect():
        return False
    
    if not await modem.tls_config_profile(
        profile_id=1,
        tls_validation=WalterModemTlsValidation.NONE,
        tls_version=WalterModemTlsVersion.TLS_VERSION_13
    ):
        print('Failed to configure TLS profile')
        return False
    
    print('Configurng MQTT')
    if not await modem.mqtt_config(
        user_name=config.MQTT_USERNAME,
        password=config.MQTT_PASSWORD,
        tls_profile_id=1
    ):
        print('Failed to configure MQTT')
        return False
    
    print('Connecting to MQTT server')
    if not await modem.mqtt_connect(
        server_name=config.MQTT_SERVER_ADDRESS,
        port=int(config.MQTT_PORT),
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
        
        if not await modem.mqtt_publish(
            topic=topic,
            data=config.MESSAGE,
            qos=config.PUBLISH_QOS
        ):
            print('Failed to publish message')
        print('Message Published')

        if await modem.mqtt_subscribe(
            topic=topic,
            qos=config.SUBSCRIBE_QOS
        ):
            print(f'Subscribed to topic: "{topic}"')
        else:
            print('Failed to subscribe to topic, raising runtime error to stop the script')

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