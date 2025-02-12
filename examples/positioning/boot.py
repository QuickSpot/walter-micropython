import asyncio

from walter import (
    Modem
)

from _walter import (
    ModemRspType,
    ModemRat,
    ModemNetworkRegState,
    ModemState,
    ModemOpState,
    ModemNetworkSelMode
)

CELL_APN = ''
"""
The cullular Access Point Name.
Leave blank for automatic APN detection.
"""

SERVER_ADDRESS = 'walterdemo.quickspot.io'
"""
The address of the Walter Demo server.
"""

SERVER_PORT = 1999
"""
The UDP port of the Walter Demo server.
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

modem = Modem()
"""
The modem instance
"""

data_buffer = bytearray(PACKET_SIZE)
"""
The buffer to transmit to the UDP server.
The first 6 bytes will be the MAC address of the Walter this code is running on.
"""

fix_rcvd = False
"""
Flag used to signal when a fix is received
"""

async def await_network_reg_state(timeout: int, *states: ModemNetworkRegState) -> bool:
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
    if modem.get_network_reg_state() in (
        ModemNetworkRegState.REGISTERED_HOME,
        ModemNetworkRegState.REGISTERED_ROAMING
    ):
        return True
    
    if (await modem.set_op_state(ModemOpState.FULL)).result != ModemState.OK:
        print('Failed to set operational state to full')
        return False
    
    if (await modem.set_network_selection_mode(ModemNetworkSelMode.AUTOMATIC)).result != ModemState.OK:
        print('Failed to set network selection mode to automatic')
        return False
    
    if not await await_network_reg_state(
        300,
        ModemNetworkRegState.REGISTERED_HOME,
        ModemNetworkRegState.REGISTERED_ROAMING
    ):
        modem_rsp = await modem.get_rat()

        if modem_rsp.result != ModemState.OK or (await modem.set_op_state(ModemOpState.MINIMUM)).result != ModemState.OK:
            print('Failed to connect using current RAT')
            return False

        if not await_network_reg_state(5, ModemNetworkRegState.NOT_SEARCHING):
            print('Unexpted: failed to put modem on standby (opState: MISSING), network registration still not "NOT_SEARCHING" after 5sec')
            return False
        
        rat = modem_rsp.data.rat

        if _retry:
            print('Failed to connect using LTE-M and NB-IoT, no connection possible')
            
            if rat != ModemRat.LTEM:
                if (await modem.set_rat(ModemRat.LTEM).result != ModemState.OK):
                    print('Failed to set RAT back to *preferred* LTEM')
                await modem.reset()
            
            return False
        
        print(f'Failed to connect to LTE network using: {'LTE-M' if rat == ModemRat.LTEM else 'NB-IoT'}')
        print(f'Switching modem to {'NB-IoT' if rat == ModemRat.LTEM else 'LTE-M'} and retrying...')

        next_rat = ModemRat.NBIOT if rat == ModemRat.LTEM else ModemRat.LTEM

        if (await modem.set_rat(next_rat)).result != ModemState.OK:
            print('Failed to switch RAT')
            return False
        
        await modem.reset()
        return lte_connect(_retry=True)