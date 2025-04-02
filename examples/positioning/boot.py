import asyncio
import esp32
import network
import sys
import struct
import ubinascii

from walter_modem import Modem
from walter_modem.enums import (
    WalterModemCMEError,
    WalterModemGNSSAction,
    WalterModemGNSSAssistanceType,
    WalterModemNetworkRegState,
    WalterModemNetworkSelMode,
    WalterModemOpState,
    WalterModemRai,
    WalterModemRat,
    WalterModemRspType
)
from walter_modem.structs import (
    ModemRsp
)

import config

modem = Modem()
"""
The modem instance
"""

modem_rsp = ModemRsp()
"""
The modem response object that's (re-)used 
when we need information from the modem.
"""

socket_id: int
"""
Variable to store the socket_id once made.
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
        print('    - Failed to set operational state to full')
        return False
    
    if not await modem.set_network_selection_mode(WalterModemNetworkSelMode.AUTOMATIC):
        print('    - Failed to set network selection mode to automatic')
        return False
    
    print('    - Waiting for network registration')
    if not await wait_for_network_reg_state(
        300,
        WalterModemNetworkRegState.REGISTERED_HOME,
        WalterModemNetworkRegState.REGISTERED_ROAMING
    ):
        if await modem.get_rat(rsp=modem_rsp):
            if not await modem.set_op_state(WalterModemOpState.MINIMUM):
                print('    - Failed to connected using current RAT')
                return False

        if not await wait_for_network_reg_state(5, WalterModemNetworkRegState.NOT_SEARCHING):
            print('    - Unexpected: modem not on standby after 5 seconds')
            return False
        
        rat = modem_rsp.rat

        if _retry:
            print('    - Failed to connect using LTE-M and NB-IoT, no connection possible')
            
            if rat != WalterModemRat.LTEM:
                if not await modem.set_rat(WalterModemRat.LTEM):
                    print('    - Failed to set RAT back to *preferred* LTEM')
                await modem.reset()
            
            return False
        
        print('    - Failed to connect to LTE network using: '
              f'{"LTE-M" if rat == WalterModemRat.LTEM else "NB-IoT"}')
        print('    - Switching modem to '
              f'{"NB-IoT" if rat == WalterModemRat.LTEM else "LTE-M"} and retrying...')

        next_rat = WalterModemRat.NBIOT if rat == WalterModemRat.LTEM else WalterModemRat.LTEM

        if not await modem.set_rat(next_rat):
            print('    - Failed to switch RAT')
            return False
        
        await modem.reset()
        return await lte_connect(_retry=True)
    
    return True

async def lte_disconnect() -> bool:
    """
    Disconnect from the LTE network

    This function will disconnect the modem from the LTE network.
    This function blocks until the modem is successfully disconnected.

    :return bool: True on success, False on failure
    """
    if modem.get_network_reg_state() == WalterModemNetworkRegState.NOT_SEARCHING:
        return True
    
    if not await modem.set_op_state(WalterModemOpState.MINIMUM):
        print('    - Failed to set operational state to minimum')
        return False

    if await wait_for_network_reg_state(5, WalterModemNetworkRegState.NOT_SEARCHING):
        return True
    
    print('    - Failed to disconnect, modem network registration state still not'
          '"NOT SEARCHING" after 5 seconds')
    return False

async def lte_transmit(socket_id: int, address: str, port: int, buffer: bytearray) -> bool:
    """
    Transmit to an UDP socket

    This will connect to the given address, transmit the data and then close the socket.

    :param socket_id: The id of the modem socket to use for the connect
    :param address: The address of the server to connect to.
    :param port: The socket port to connect to.
    :param buffer: The buffer containing the packet data.
    :param length: The length in bytes that need to be transmitted.

    :return bool: True on success, False on failure
    """
    if not await modem.connect_socket(
        remote_host=address,
        remote_port=port,
        socket_id=socket_id,
        local_port=port
    ):
        print('  - Failed to connect to UDP socket')
        return False
    
    print(f'  - Connected to UDP server: {address}:{port}')

    if not await modem.socket_send(
        data=buffer,
        socket_id=1,
        rai=WalterModemRai.NO_INFO
    ):
        print('  - Failed to transmit to UDP socket')
        return False
    
    if not await modem.close_socket(
        socket_id=socket_id
    ):
        print('  - Failed to close UDP socket')
        return False
    
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

def check_assistance_data() -> tuple[bool, bool]:
    """
    Check the assistance data in the modem response.

    This function check the availability of assistance data in the modem's response.

    :param modem_rsp: The modem resonse to check
    
    :return tuple: bools representing wether or not almanac or ephemeris should be updated
    """
    almanac = modem_rsp.gnss_assistance.almanac
    ephemeris = modem_rsp.gnss_assistance.realtime_ephemeris

    update_almanac = (not almanac.available) or (almanac.time_to_update <= 0)
    update_ephemeris = (not ephemeris.available) or (ephemeris.time_to_update <= 0)

    if almanac.available:
        print('    - Almanac data is available and '
              f'should be updated within {almanac.time_to_update}')
    else:
        print('    - Almanac data is not available.')

    if ephemeris.available:
        print('    - Real-time ephemeris data is available and '
              f'should be updated within {ephemeris.time_to_update}')
    else:
        print('    - Real-time ephemeris data is not available.')

    return update_almanac, update_ephemeris

async def update_gnss_assistance() -> bool:
    """
    This function will update GNNS assistance data when needed.

    Check if the current real-time ephemeris data is good enough to get a fast GNSS fix.
    If not, the function will connect to the LTE network to download newer assistance data.

    :return bool: True on success, False on failure
    """
    global modem_rsp

    if not await modem.get_clock(rsp=modem_rsp):
        print('  - Failed to retrieve modem time')
        return False
    
    if not modem_rsp.clock:
        print('  - Modem time is invalid, connecting to LTE')
        if not await lte_connect():
            print('  - Failed to connect to LTE')
            return False
        
    for i in range(5):
        if not await modem.get_clock(rsp=modem_rsp):
            print('  - Failed to retrieve modem time')
            return False
        
        if modem_rsp.clock:
            print(f'  - Synchronised clock with network: {modem_rsp.clock}')
            break
        elif i == 4:
            print('  - Could not sync time with network')

        await asyncio.sleep(.5)

    if not await modem.get_gnss_assistance_status(rsp=modem_rsp):
        if modem_rsp.type != WalterModemRspType.GNSS_ASSISTANCE_DATA:
            print('  - Failed to request GNSS assistance status')
            return False
    
    update_almanac, update_ephemeris = check_assistance_data()
    
    if update_almanac:
        print('  - Updating Almanac data')
        if not await lte_connect():
            print('  - Failed to connect to LTE network')
            return False
        
        if not await modem.update_gnss_assistance(WalterModemGNSSAssistanceType.ALMANAC):
            print('  - Failed to update almanac data')
            return False
        
    if update_ephemeris:
        print('  - Updating Ephemeris data')
        if not await lte_connect():
            print('  - Failed to connect to LTE network')
            return False
        
        if not await modem.update_gnss_assistance(WalterModemGNSSAssistanceType.REALTIME_EPHEMERIS):
            print('  - Failed to update ephemeris data')
            return False
        
    return True

async def setup():
    global socket_id

    print('Walter Positioning Example')
    print('---------------')
    print('Find your walter at: https://walterdemo.quickspot.io/')
    print('Walter\'s MAC is: %s'
          % ubinascii.hexlify(network.WLAN().config('mac'),':').decode(), end='\n\n')
    
    await modem.begin()

    if not await modem.check_comm():
        print('Modem communication error')
        return False
    
    if config.SIM_PIN != None and not await unlock_sim():
        return False
    
    if not await modem.create_PDP_context(
        apn=config.CELL_APN,
        rsp=modem_rsp
    ):
        print('Failed to create socket')
        return False
   
    if config.APN_USERNAME and not await modem.set_PDP_auth_params(
        protocol=config.AUTHENTICATION_PROTOCOL,
        user_id=config.APN_USERNAME,
        password=config.APN_PASSWORD
    ):
        print('Failed to set PDP context authentication paramaters')

    print('Connecting to LTE Network')
    if not await lte_connect():
        return False
   
    print('Creating socket')
    if await modem.create_socket(rsp=modem_rsp):
        socket_id = modem_rsp.socket_id
    else:
        print('Failed to create socket')
        return False   

    if not await modem.config_socket(socket_id=socket_id):
        print('Failed to config socket')
        return False
    
    if not await modem.config_gnss():
        print('Failed to configure GNSS subsystem')
        return False
    
    return True
    
async def loop():
    global modem_rsp

    print('Checking GNSS assistance data...')
    if not await update_gnss_assistance():
        print('Failed to update GNSS assistance data')

    print('Attempting to request a GNSS fix')
    gnss_fix = None
    for i in range(5):
        if i > 0:
            print(f'  - trying again, run: {i+1}/5')
        await lte_disconnect()

        if not await modem.perform_gnss_action(
            action=WalterModemGNSSAction.GET_SINGLE_FIX,
            rsp=modem_rsp
        ):
            print('  - Failed to request GNSS fix',
                  WalterModemCMEError.get_value_name(modem_rsp.cme_error))
            continue

        print('  - Requested GNSS fix')
        print('  - Waiting for GNSS fix')
        gnss_fix = await modem.wait_for_gnss_fix()

        if gnss_fix.estimated_confidence <= config.MAX_GNSS_CONFIDENCE:
            print(f'  - Fix success, estimated confidence: {gnss_fix.estimated_confidence}')
            break

    if gnss_fix.estimated_confidence > config.MAX_GNSS_CONFIDENCE:
        print(f'  - GNSS fix confidence ({gnss_fix.estimated_confidence:.2f}) '
              f'exceeds max confidence of {config.MAX_GNSS_CONFIDENCE}')
        print('  - Not accurate enough, values will not be used')
        

    if gnss_fix != None:
        above_threshold = 0
        for sat in gnss_fix.sats:
            if sat.signal_strength >= 30:
                above_threshold += 1
    
        print('GNSS fix attempt finished')
        print(f'  Confidence: {gnss_fix.estimated_confidence:.2f}')
        print(f'  Latitude: {gnss_fix.latitude:.06f}')
        print(f'  Longitude: {gnss_fix.longitude:.06f}')
        print(f'  Satcount: {len(gnss_fix.sats)}')
        print(f'  Good sats: {above_threshold}')

        lat: float = gnss_fix.latitude
        lon: float = gnss_fix.longitude

        if gnss_fix.estimated_confidence > config.MAX_GNSS_CONFIDENCE:
            gnss_fix.sats = []
            lat = 0.0
            lon = 0.0
            print('Failed to get a valid fix')
    else:
        lat: float = 0
        lon: float = 0

    print('Connecting to LTE')
    if not await lte_connect():
        print('Failed to connect to LTE')

    if not await modem.get_cell_information(rsp=modem_rsp):
        print('Failed to request cell information',
              WalterModemCMEError.get_value_name(modem_rsp.cme_error))
    else:
        print('Connected on band {} using operator {} ({}{})'.format(
            modem_rsp.cell_information.band,
            modem_rsp.cell_information.net_name,
            modem_rsp.cell_information.cc,
            modem_rsp.cell_information.nc
        ))
        print(f'cell ID {modem_rsp.cell_information.cid}')
        print('Signal strength: RSRP: {:.2f}, RSRQ: {:.2f}.'.format(
            modem_rsp.cell_information.rsrp,
            modem_rsp.cell_information.rsrq
        ))

    mcu_temperature: float = esp32.mcu_temperature()

    data_buffer: bytearray = bytearray(network.WLAN().config('mac'))
    data_buffer.append(0x2)
    data_buffer.extend(struct.pack('>h', (mcu_temperature + 50) * 100))
    data_buffer.append(len(gnss_fix.sats) if gnss_fix else 255)
    data_buffer.extend(struct.pack('<f', lat))
    data_buffer.extend(struct.pack('<f', lon))

    if hasattr(modem_rsp, 'cell_information') and modem_rsp.cell_information:
        data_buffer.append(modem_rsp.cell_information.cc >> 8)
        data_buffer.append(modem_rsp.cell_information.cc & 0xFF)
        data_buffer.append(modem_rsp.cell_information.nc >> 8)
        data_buffer.append(modem_rsp.cell_information.nc & 0xFF)
        data_buffer.append(modem_rsp.cell_information.tac >> 8)
        data_buffer.append(modem_rsp.cell_information.tac & 0xFF)
        data_buffer.append((modem_rsp.cell_information.cid >> 24) & 0xFF)
        data_buffer.append((modem_rsp.cell_information.cid >> 16) & 0xFF)
        data_buffer.append((modem_rsp.cell_information.cid >> 8) & 0xFF)
        data_buffer.append(modem_rsp.cell_information.cid & 0xFF)
        data_buffer.append(int(modem_rsp.cell_information.rsrp * -1))
    else:
        data_buffer.extend(b'\x00' * 11)

    print('Transmitting data to server')
    await lte_transmit(
        socket_id=socket_id,
        address=config.SERVER_ADDRESS,
        port=config.SERVER_PORT,
        buffer=data_buffer
    )

async def main():
    try:
        if not await setup():
            print('Failed to complete setup, raising runtime error to stop')
            raise RuntimeError()
        
        while True:
            await loop()
            print(f'sleeping for {config.SLEEP_TIME}sec')
            await asyncio.sleep(config.SLEEP_TIME)
    except Exception as err:
        print('ERROR: (boot.py, main): ')
        sys.print_exception(err)
        print(f'Waiting {config.SLEEP_TIME} seconds before exiting')
        # Sleep a while to prevent getting stuck in an infite crash loop
        # And give time for the serial over usb to function
        await asyncio.sleep(config.SLEEP_TIME)

asyncio.run(main())