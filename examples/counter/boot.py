import asyncio
import network
import sys
import ubinascii

from walter_modem import Modem

from walter_modem.enums import (
    ModemNetworkRegState,
    ModemOpState,
    ModemNetworkSelMode,
)

from walter_modem.structs import (
    ModemRsp,
    ModemRat
)

import config

modem = Modem()
"""
The modem instance
"""

counter = 0
"""
The counter used in the ping packets
"""

socket_id = None
"""
The id of the socket
"""

modem_rsp = ModemRsp()
"""
The modem response object.
We re-use this single one, for memory efficiency.
"""

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
        
        print('  - Failed to connect to LTE network using: '
              f'{"LTE-M" if rat == ModemRat.LTEM else "NB-IoT"}')
        print('  - Switching modem to '
              f'{"NB-IoT" if rat == ModemRat.LTEM else "LTE-M"} and retrying...')

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
    await asyncio.sleep(2)
    if await modem.unlock_sim(pin=config.SIM_PIN):
        print('  - SIM unlocked')
    else:
        print('  - Failed to unlock SIM card')
        return False
   
    return True

async def setup():
    global socket_id
    global modem_rsp

    print('Walter Counter Example')
    print('---------------')
    print('Find your walter at: https://walterdemo.quickspot.io/')
    print('Walter\'s MAC is: %s' % ubinascii.hexlify(network.WLAN().config('mac'),':').decode(),
          end='\n\n')

    await modem.begin() 

    if not await modem.check_comm():
        print('Modem communication error')
        return False

    if await modem.get_op_state(rsp=modem_rsp) and modem_rsp.op_state is not None:
        print(f'Modem operatonal state: {ModemOpState.get_value_name(modem_rsp.op_state)}')
    else:
        print('Failed to retrieve modem operational state')
        return False

    if config.SIM_PIN != None and not await unlock_sim():
        return False
    
    if not await modem.create_PDP_context(
        apn=config.CELL_APN,
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
   
    print('Creating socket')
    if await modem.create_socket(pdp_context_id=modem_rsp.pdp_ctx_id, rsp=modem_rsp):
        socket_id = modem_rsp.socket_id
    else:
        print('Failed to create socket')
        return False   

    print('Configuring socket')
    if not await modem.config_socket(socket_id=socket_id):
        print('Failed to config socket')
        return False
    
    print('Connecting socket')
    if not await modem.connect_socket(
        remote_host=config.SERVER_ADDRESS,
        remote_port=config.SERVER_PORT,
        local_port=config.SERVER_PORT,
        socket_id=socket_id
    ):
        print('Failed to connect socket')
        return False
    
    return True

async def loop():
    global counter
    global socket_id
    data_buffer: bytearray = bytearray(network.WLAN().config('mac'))
    data_buffer.append(counter >> 8)
    data_buffer.append(counter & 0xff)

    print('Attempting to transmit data')
    if not await modem.socket_send(data=data_buffer, socket_id=socket_id):
        print('Failed to transmit data')
        return False
    
    print(f'Transmitted counter value: {counter}')
    counter += 1

    await asyncio.sleep(10)

async def main():
    try:
        if not await setup():
            print('Failed to complete setup, raising runtime error to stop the script.')
            raise RuntimeError()
        while True:
            await loop()
    except Exception as err:
        print('ERROR: (boot.py, main): ')
        sys.print_exception(err)
        print('Waiting 5 minutes before exiting')
        # Sleep a while to prevent getting stuck in an infite crash loop
        # And give time for the serial over usb to function
        await asyncio.sleep(300)

asyncio.run(main())