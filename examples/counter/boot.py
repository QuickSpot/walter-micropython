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
import esp32
import network
import sys
import ubinascii

from walter import (
    Modem
)

from _walter import (
    ModemCMEError,
    ModemGNSSAction,
    ModemGNSSAssistanceType,
    ModemNetworkRegState,
    ModemNetworkSelMode,
    ModemOpState,
    ModemRai,
    ModemRat,
    ModemRsp,
    ModemRspType,
    ModemState
)

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

SERVER_ADDRESS = 'walterdemo.quickspot.io'
"""
The address of the Walter Demo server.
"""

SERVER_PORT = 1999
"""
The UDP port of the Walter Demo server.
"""

SIM_PIN = None
"""
Optional: Set this only if your SIM card requires a PIN for activation. 
Most IoT SIMs do not need this.
"""

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
        print('  ↳ Failed to set operational state to full')
        return False
    
    if (await modem.set_network_selection_mode(ModemNetworkSelMode.AUTOMATIC)).result != ModemState.OK:
        print('  ↳ Failed to set network selection mode to automatic')
        return False
    
    print('  ↳ Waiting for network registration')
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
            print('  ↳ Failed to connect using current RAT')
            return False

        if not await wait_for_network_reg_state(5, ModemNetworkRegState.NOT_SEARCHING):
            print('  ↳ Unexpected: modem not on standby after 5 seconds')
            return False
        
        rat = modem_rsp.rat

        if _retry:
            print('  ↳ Failed to connect using LTE-M and NB-IoT, no connection possible')
            
            if rat != ModemRat.LTEM:
                if (await modem.set_rat(ModemRat.LTEM)).result != ModemState.OK:
                    print('  ↳ Failed to set RAT back to *preferred* LTEM')
                await modem.reset()
            
            return False
        
        print(f'  ↳ Failed to connect to LTE network using: {"LTE-M" if rat == ModemRat.LTEM else "NB-IoT"}')
        print(f'  ↳ Switching modem to {"NB-IoT" if rat == ModemRat.LTEM else "LTE-M"} and retrying...')

        next_rat = ModemRat.NBIOT if rat == ModemRat.LTEM else ModemRat.LTEM

        if (await modem.set_rat(next_rat)).result != ModemState.OK:
            print('  ↳ Failed to switch RAT')
            return False
        
        await modem.reset()
        return await lte_connect(_retry=True)
    
    return True

async def unlock_sim() -> bool:
    if (await modem.set_op_state(ModemOpState.NO_RF)).result != ModemState.OK:
        print('  ↳ Failed to set operational state to: NO RF')
        return False

    # Give the modem time to detect the SIM
    asyncio.sleep(2)
    if (await modem.unlock_sim(pin=SIM_PIN)).result != ModemState.OK:
        print('  ↳ Failed to unlock SIM card')
        return False
    else:
        print('  ↳ SIM unlocked')
   
    return True

async def setup():
    global socket_id
    print('Walter Counter Example')
    print('---------------')
    print('Find your walter at: https://walterdemo.quickspot.io/')
    print('Walter\'s MAC is: %s' % ubinascii.hexlify(network.WLAN().config('mac'),':').decode(), end='\n\n')

    await modem.begin(debug_log=False)

    if (await modem.check_comm()).result != ModemState.OK:
        print('Modem communication error')
        return
   
    modem_rsp: ModemRsp = await modem.get_op_state()
    if modem_rsp.result == ModemState.OK and modem_rsp.op_state is not None:
        print(f'Modem operatonal state: {ModemOpState.get_value_name(modem_rsp.op_state)}')
    else:
        print('Failed to retrieve modem operational state')
        return
   
    modem_rsp: ModemRsp = await modem.get_radio_bands()
    if modem_rsp.result == ModemState.OK and modem_rsp.band_sel_cfg_list is not None:
        print('Modem is configured for the following bands:')
        for band_sel in modem_rsp.band_sel_cfg_list:
            print(
                f'- rat: {'LTE-M' if band_sel.rat == ModemRat.LTEM else 'NB-IoT'},'
                f'net operator: {band_sel.net_operator.name}'
            )
            print(f'  - bands: {', '.join(str(band) for band in band_sel.bands)}')
    else:
        print('Failed to retrieve the configured radio bands')

    if SIM_PIN != None and not await unlock_sim():
        return False
   
    modem_rsp = await modem.create_PDP_context(
        apn=CELL_APN,
        auth_user=APN_USERNAME,
        auth_pass=APN_PASSWORD
    )
    if modem_rsp.result != ModemState.OK:
        print('Failed to create PDP context')
        return False
   
    pdp_ctx_id = modem_rsp.pdp_ctx_id
   
    if APN_USERNAME and (await modem.authenticate_PDP_context()).result != ModemState.OK:
        print('Failed to authenticate PDP context')

    print('Connecting to LTE Network')
    if not await lte_connect():
        return False
   
    print('Creating socket')
    modem_rsp = await modem.create_socket(pdp_context_id=pdp_ctx_id)
    if modem_rsp.result != ModemState.OK:
        print('Failed to create socket')
        return False
   
    socket_id = modem_rsp.socket_id
   
    if (await modem.config_socket(socket_id=socket_id)).result != ModemState.OK:
        print('Faield to config socket')
        return False

    if (await modem.connect_socket(
        remote_host=SERVER_ADDRESS,
        remote_port=SERVER_PORT,
        local_port=SERVER_PORT,
        socket_id=socket_id
        )).result != ModemState.OK:
        print('Failed to connect socket')
        return False

async def loop():
    global counter
    global socket_id
    data_buffer: bytearray = bytearray(network.WLAN().config('mac'))
    data_buffer.append(counter >> 8)
    data_buffer.append(counter & 0xff)

    modem_rsp: ModemRsp = await modem.socket_send(data=data_buffer, socket_id=socket_id)
    if modem_rsp.result != ModemState.OK:
        print('Failed to transmit data')
        return False
    
    print(f'Transmitted counter value: {counter}')
    counter += 1

    await asyncio.sleep(10)

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