import asyncio
import json
import sys

from walter_modem import Modem
from walter_modem.enums import (
    ModemNetworkRegState,
    ModemOpState,
    ModemNetworkSelMode,
    ModemHttpQueryCmd,
    ModemTlsValidation,
    ModemTlsVersion
)
from walter_modem.structs import (
    ModemRsp,
    ModemRat
)

import config

modem = Modem()
modem_rsp = ModemRsp()

IC2_BUS_POWER_PIN = 1
IC2_SDA_PIN = 42
IC2_SCL_PIN = 2


def get_temperature_data():
    # TODO: actually impliment
    return 18

def get_rsrp_data():
    # TODO: actaully impliment
    return -100

def get_data() -> dict:
    data_map = {
        'temperature': get_temperature_data,
        'rsrp': get_rsrp_data
    }

    data = {}

    for data_type, pin in config.BLYNK_DEVICE_PINS.items():
        if pin:
            data[pin] = data_map[data_type]()

    return data


async def wait_for_network_reg_state(timeout: int, *states: ModemNetworkRegState) -> bool:
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
        ModemNetworkRegState.REGISTERED_HOME,
        ModemNetworkRegState.REGISTERED_ROAMING
    ):
        return True
    
    if not await modem.set_op_state(ModemOpState.FULL):
        print('  - Failed to set operational state to full')
        return False
    
    if not await modem.set_network_selection_mode(ModemNetworkSelMode.AUTOMATIC):
        print('  - Failed to set network selection mode to automatic')
        return False
    
    print('  - Waiting for network registration')
    if not await wait_for_network_reg_state(
        300,
        ModemNetworkRegState.REGISTERED_HOME,
        ModemNetworkRegState.REGISTERED_ROAMING
    ):
        if await modem.get_rat(rsp=modem_rsp):
            if not await modem.set_op_state(ModemOpState.MINIMUM):
                print('  - Failed to connected using current RAT')
                return False

        if not await wait_for_network_reg_state(5, ModemNetworkRegState.NOT_SEARCHING):
            print('  - Unexpected: modem not on standby after 5 seconds')
            return False
        
        rat = modem_rsp.rat

        if _retry:
            print('  - Failed to connect using LTE-M and NB-IoT, no connection possible')
            
            if rat != ModemRat.LTEM:
                if not await modem.set_rat(ModemRat.LTEM):
                    print('  - Failed to set RAT back to *preferred* LTEM')
                await modem.reset()
            
            return False
        
        print(f'  - Failed to connect to LTE network using: {"LTE-M" if rat == ModemRat.LTEM else "NB-IoT"}')
        print(f'  - Switching modem to {"NB-IoT" if rat == ModemRat.LTEM else "LTE-M"} and retrying...')

        next_rat = ModemRat.NBIOT if rat == ModemRat.LTEM else ModemRat.LTEM

        if not await modem.set_rat(next_rat):
            print('  - Failed to switch RAT')
            return False
        
        await modem.reset()
        return await lte_connect(_retry=True)
    
    return True

async def unlock_sim() -> bool:
    if not await modem.set_op_state(ModemOpState.NO_RF):
        print('  - Failed to set operational state to: NO RF')
        return False

    # Give the modem time to detect the SIM
    asyncio.sleep(2)
    if await modem.unlock_sim(pin=config.SIM_PIN):
        print('  - SIM unlocked')
    else:
        print('  - Failed to unlock SIM card')
        return False
   
    return True

async def await_http_response(http_profile: int, timeout: int = 10) -> bool:
    global modem_rsp

    for _ in range(timeout):
        print('if http_did_ring')
        if await modem.http_did_ring(profile_id=http_profile, rsp=modem_rsp):
            print('was true')
            return True
        
        await asyncio.sleep(1)
    
    return False

def urlencode(params: dict) -> str:
    return '&'.join(f'{key}={value}' for key, value in params.items())

async def fetch(
    http_profile: int,
    path: str = '',
    query_string: str = None,
    extra_header_line: str = None
) -> bool:
    global modem_rsp

    uri = f'{path}{"?" + query_string if query_string is not None else ""}'
    if await modem.http_query(
        profile_id=http_profile,
        uri=uri,
        query_cmd=ModemHttpQueryCmd.GET,
        extra_header_line=extra_header_line,
        rsp=modem_rsp
    ):
        print('awaiting http response')
        return await await_http_response(http_profile=0)
    else:
        print(f'  Failed to fetch data (profile: {http_profile}, uri: {uri})')
        return False

async def setup():
    global modem_rsp
    print('Walter Feels Example')
    print('---------------', end='\n\n')

    await modem.begin(debug_log=True)

    if not await modem.check_comm():
        print('Modem communication error')
        return False

    if config.SIM_PIN != None and not await unlock_sim():
        return False
    
    if not await modem.create_PDP_context(
        apn=config.CELL_APN,
        auth_user=config.APN_USERNAME,
        auth_pass=config.APN_PASSWORD,
        rsp=modem_rsp
    ):
        print('Failed to create pdp context')
        return False
   
    if config.APN_USERNAME and not await modem.authenticate_PDP_context(modem_rsp.pdp_ctx_id):
        print('Failed to authenticate PDP context')
    
    if not await modem.tls_config_profile(
        profile_id=1,
        tls_validation=ModemTlsValidation.NONE,
        tls_version=ModemTlsVersion.TLS_VERSION_12
    ):
        print('Failed to configure TLS profile')
        return False
    
    if not await modem.http_config_profile(
        profile_id=0,
        server_address=config.BLYNK_SERVER_ADDRESS,
        port=443,
        tls_profile_id=1
    ):
        print('Faield to configure HTTP profile')
        return False
    
    print('Connecting to LTE Network')
    if not await lte_connect():
        print('Failed to connect to LTE Network')
        return False
    
    return True

async def loop():
    global modem_rsp

    data = get_data()
    if await fetch(
        http_profile=0,
        path='/external/api/batch/update',
        query_string=f'token={config.BLYNK_TOKEN}&{urlencode(data)}'
    ):
        print(modem_rsp.http_response.http_status)

async def main():
    try:
        if not await setup():
            print('Failed to complete setup, raising runtime error to stop')
            raise RuntimeError()
        while True:
            await loop()
            await asyncio.sleep(10)
    except Exception as err:
        print('ERROR: (boot.py, main): ')
        sys.print_exception(err)
        print('Waiting 5 minutes before exiting')
        # Sleep a while to prevent getting stuck in an infite crash loop
        # And give time for the serial over usb to function
        asyncio.sleep(300)

asyncio.run(main())