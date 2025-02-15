"""
Copyright (C) 2023, DPTechnics bv
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

  1. Redistributions of source code must retain the above copyright notice,
     this list of conditions and the following disclaimer.

  2. Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in the
     documentation and/or other materials provided with the distribution.

  3. Neither the name of DPTechnics bv nor the names of its contributors may
     be used to endorse or promote products derived from this software
     without specific prior written permission.

  4. This software, with or without modification, must only be used with a
     Walter board from DPTechnics bv.

  5. Any software provided in binary form under this license must not be
     reverse engineered, decompiled, modified and/or disassembled.

THIS SOFTWARE IS PROVIDED BY DPTECHNICS BV “AS IS” AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY, NONINFRINGEMENT, AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL DPTECHNICS BV OR CONTRIBUTORS BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import asyncio
import sys
import esp32
import network
import struct
import ubinascii

from walter import (
    Modem
)

from _walter import (
    ModemRat,
    ModemRai,
    ModemRsp,
    ModemRspType,
    ModemNetworkRegState,
    ModemState,
    ModemOpState,
    ModemNetworkSelMode,
    ModemGNSSAssistanceType,
    ModemGNSSAction,
    ModemCMEError
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

async def wait_for_network_reg_state(timeout: int, *states: ModemNetworkRegState) -> bool:
    """
    Wait for the modem network registration state to reach the desired state(s).
    
    :param timeout: Timeout period (in seconds)
    :param states: One or more states to wait for

    :return: True if the current state matches any of the provided states, False if timed out.
    """
    for _ in range(timeout):
        if modem.get_network_reg_state().reg_state in states:
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
        print('│  ├─ Failed to set operational state to full')
        return False
    
    if (await modem.set_network_selection_mode(ModemNetworkSelMode.AUTOMATIC)).result != ModemState.OK:
        print('│  ├─ Failed to set network selection mode to automatic')
        return False
    
    print('│  ├─ Waiting for network registration')
    if not await wait_for_network_reg_state(
        300,
        ModemNetworkRegState.REGISTERED_HOME,
        ModemNetworkRegState.REGISTERED_ROAMING
    ):
        modem_rsp: ModemRsp = await modem.get_rat()

        if (
            modem_rsp.result != ModemState.OK or
            (await modem.set_op_state(ModemOpState.MINIMUM)).result != ModemState.OK
        ):
            print('│  ├─ Failed to connect using current RAT')
            return False

        if not await wait_for_network_reg_state(5, ModemNetworkRegState.NOT_SEARCHING):
            print('│  ├─ Unexpected: modem not on standby after 5 seconds')
            return False
        
        rat = modem_rsp.data.rat

        if _retry:
            print('│  ├─ Failed to connect using LTE-M and NB-IoT, no connection possible')
            
            if rat != ModemRat.LTEM:
                if (await modem.set_rat(ModemRat.LTEM)).result != ModemState.OK:
                    print('│  ├─ Failed to set RAT back to *preferred* LTEM')
                await modem.reset()
            
            return False
        
        print(f'│  ├─ Failed to connect to LTE network using: {"LTE-M" if rat == ModemRat.LTEM else "NB-IoT"}')
        print(f'│  ├─ Switching modem to {"NB-IoT" if rat == ModemRat.LTEM else "LTE-M"} and retrying...')

        next_rat = ModemRat.NBIOT if rat == ModemRat.LTEM else ModemRat.LTEM

        if (await modem.set_rat(next_rat)).result != ModemState.OK:
            print('│  ├─ Failed to switch RAT')
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
    if modem.get_network_reg_state() == ModemNetworkRegState.NOT_SEARCHING:
        return True
    
    if (await modem.set_op_state(ModemOpState.MINIMUM)).result != ModemState.OK:
        print('│  ├─ Failed to set operational state to minimum')
        return False

    if await wait_for_network_reg_state(5, ModemNetworkRegState.NOT_SEARCHING):
        return True
    
    print('│  ├─ Failed to disconnect, modem network registration state still not "NOT SEARCHING" after 5 seconds')
    return False

async def lte_transmit(address: str, port: int, buffer: bytearray) -> bool:
    """
    Transmit to an UDP socket

    This function will configure the modem to set up, connect, transmit and close to an UDP socket.

    :param address: The address of the server to connect to.
    :param port: The socket port to connect to.
    :param buffer: The buffer containing the packet data.
    :param length: The length in bytes that need to be transmitted.

    :return bool: True on success, False on failure
    """
    print('├─ Connecting to LTE')
    if not await lte_connect():
        return False

    if (await modem.create_socket()).result != ModemState.OK:
        print('├─ Failed to create a new UDP socket')
        return False
    
    if (await modem.config_socket()).result != ModemState.OK:
        print('├─ Failed to configure UDP socket')
        return False
    
    if (await modem.connect_socket(address, port, port)).result != ModemState.OK:
        print('├─ Failed to connect to UDP socket')
        return False
    
    print(f'├─ Connected to UDP server: {address}:{port}')

    if (await modem.socket_send(buffer, ModemRai.NO_INFO, 1)).result != ModemState.OK:
        print('├─ Failed to transmit to UDP socket')
        return False
    
    if (await modem.close_socket()).result != ModemState.OK:
        print('├─ Failed to close UDP socket')
        return False
    
    return True

def check_assistance_data(modem_rsp):
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
        print(f'│  ├─ Almanac data is available and should be updated within {almanac.time_to_update}')
    else:
        print('│  ├─ Almanac data is not available.')

    if ephemeris.available:
        print(f'│  ├─ Real-time ephemeris data is available and should be updated within {ephemeris.time_to_update}')
    else:
        print('│  ├─ Real-time ephemeris data is not available.')

    return update_almanac, update_ephemeris

async def update_gnss_assistance():
    """
    This function will update GNNS assistance data when needed.

    Check if the current real-time ephemeris data is good enough to get a fast GNSS fix.
    If not, the function will connect to the LTE network to download newer assistance data.

    :return bool: True on success, False on failure
    """
    modem_rsp: ModemRsp = await modem.get_clock()
    if modem_rsp.result != ModemState.OK:
        print('├─ Failed to retrieve modem time')
        return False
    
    if not modem_rsp.clock:
        print('├─ Modem time is invalid, connecting to LTE')
        if not await lte_connect():
            print('├─ Failed to connect to LTE')
            return False
        
    for i in range(5):
        modem_rsp = await modem.get_clock()
        if modem_rsp.result != ModemState.OK:
            print('├─ Failed to retrieve modem time')
            return False
        
        if modem_rsp.clock:
            print(f'  ↳ Synchronised clock with network: {modem_rsp.clock}')
            break
        elif i == 4:
            print('├─ Could not sync time with network')

        await asyncio.sleep(.5)

    modem_rsp = await modem.get_gnss_assistance_status()
    if (
        modem_rsp.result != ModemState.OK or 
        modem_rsp.type != ModemRspType.GNSS_ASSISTANCE_DATA
    ):
        print('├─ Failed to request GNSS assistance status')
        return False
    
    update_almanac, update_ephemeris = check_assistance_data(modem_rsp)
    
    if update_almanac:
        if not await lte_connect():
            print('├─ Failed to connect to LTE network')
            return False
        
        if ((await modem.update_gnss_assistance(ModemGNSSAssistanceType.ALMANAC)).result
            != ModemState.OK):
            print('├─ Failed to update almanac data')
            return False
        
    if update_ephemeris:
        if not await lte_connect():
            print('├─ Failed to connect to LTE network')
            return False
        
        if (
            (await modem.update_gnss_assistance(ModemGNSSAssistanceType.REALTIME_EPHEMERIS)).result
            != ModemState.OK):
            print('├─ Failed to update ephemeris data')
            return False
        
    return True

async def setup():
    print('Walter Positioning Demo Sketch')
    print('---------------')
    print('Find your walter at: https://walterdemo.quickspot.io/')
    print('Walter\'s MAC is: %s' % ubinascii.hexlify(network.WLAN().config('mac'),':').decode(), end='\n\n')

    await modem.begin(debug_log=False)

    if (await modem.create_PDP_context(CELL_APN)).result != ModemState.OK:
        print('Failed to create PDP context')

    if (await modem.config_gnss()).result != ModemState.OK:
        print('Failed to configure GNSS subsystem')

async def loop():
    print('Checking GNSS assistance data...')
    if not await update_gnss_assistance():
        print('Failed to update GNSS assistance data')

    print('Attempting to request a GNSS fix')
    gnss_fix = None
    for i in range(5):
        if i > 0:
            print(f'  ↳ trying again, run: {i+1}/5')
        await lte_disconnect()
        modem_rsp: ModemRsp = await modem.perform_gnss_action(ModemGNSSAction.GET_SINGLE_FIX)
        if modem_rsp.result != ModemState.OK:
            print('  ↳ Failed to request GNSS fix', ModemCMEError.get_value_name(modem_rsp.cme_error))
            continue
        
        print('  ↳ Requested GNSS fix')
        print('  ↳ Waiting for GNSS fix')
        gnss_fix = await modem.wait_for_gnss_fix()

        if gnss_fix.estimated_confidence <= MAX_GNSS_CONFIDENCE:
            print(f'  ↳ Fix success, estimated confidence: {gnss_fix.estimated_confidence}')
            break

    if gnss_fix.estimated_confidence > MAX_GNSS_CONFIDENCE:
        print(f'  ↳ GNSS fix confidence ({gnss_fix.estimated_confidence:.2f}) exceeds max confidence of {MAX_GNSS_CONFIDENCE}')
        print('  ↳ Not accurate enough, values will not be used')
        

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

        if gnss_fix.estimated_confidence > MAX_GNSS_CONFIDENCE:
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

    modem_rsp = await modem.get_cell_information()
    if modem_rsp.result != ModemState.OK:
        print('Failed to request cell information', ModemCMEError.get_value_name(modem_rsp.cme_error))
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

    if hasattr(modem_rsp, 'cell_information'):
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
    await lte_transmit(SERVER_ADDRESS, SERVER_PORT, data_buffer)
    await asyncio.sleep(5)

async def main():
    try:
        await setup()
        while True:
            await loop()
    except Exception as err:
        print('ERROR: (boot.py, main): ')
        sys.print_exception(err)
        print('Waiting 5 minutes before exiting')
        # Sleep a while to prevent getting stuck in an infite crash loop
        # And give time for the serial over usb to function
        asyncio.sleep(300)

asyncio.run(main())