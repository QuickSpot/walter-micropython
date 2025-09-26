import micropython # type: ignore
micropython.opt_level(1)
"""
Set the MicroPython opt level.
See: https://docs.micropython.org/en/latest/library/micropython.html#micropython.opt_level
"""

import asyncio
import network # type: ignore
import sys
import ubinascii # type: ignore

from walter_modem import Modem
from walter_modem.mixins.default_sim_network import *
from walter_modem.mixins.default_pdp import *
from walter_modem.mixins.socket import *

from walter_modem.coreEnums import (
    WalterModemNetworkRegState,
    WalterModemOpState
)

from walter_modem.coreStructs import (
    WalterModemRsp
)

import config # type: ignore

modem = Modem(SocketMixin, load_default_power_saving_mixin=False)
"""
The modem instance

Loading the Socket mixin for socket functionality.

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

counter = 0
"""
The counter used in the ping packets
"""

socket_id = None
"""
The id of the socket
"""

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
        
        print('  - Failed to connect to LTE network using: '
              f'{"LTE-M" if rat == WalterModemRat.LTEM else "NB-IoT"}')
        print('  - Switching modem to '
              f'{"NB-IoT" if rat == WalterModemRat.LTEM else "LTE-M"} and retrying...')

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

    if config.SIM_PIN != None and not await unlock_sim():
        return False
    
    if not await modem.pdp_context_create(
        apn=config.CELL_APN,
        rsp=modem_rsp
    ):
        print('Failed to create socket')
        return False
   
    if config.APN_USERNAME and not await modem.pdp_set_auth_params(
        protocol=config.AUTHENTICATION_PROTOCOL,
        user_id=config.APN_USERNAME,
        password=config.APN_PASSWORD
    ):
        print('Failed to set PDP context authentication parameters')

    print('Connecting to LTE Network')
    if not await lte_connect():
        return False
   
    print('Creating socket')
    if await modem.socket_create(rsp=modem_rsp):
        socket_id = modem_rsp.socket_id
    else:
        print('Failed to create socket')
        return False
    
    print('Connecting socket')
    if not await modem.socket_connect(
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