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
import network
import json
import sys
import ubinascii

from walter import (
    Modem
)

from _walter import (
    ModemCMEError,
    ModemGNSSAction,
    ModemGNSSAssistanceType,
    ModemHttpResponse,
    ModemHttpQueryCmd,
    ModemNetworkRegState,
    ModemNetworkSelMode,
    ModemOpState,
    ModemRai,
    ModemRat,
    ModemRsp,
    ModemRspType,
    ModemState,
    ModemTlsValidation,
    ModemTlsVersion
)

CELL_APN = ''
"""
The cellular Access Point Name (APN).
Leave blank for automatic APN detection, which is sufficient for most networks.
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

SIM_PIN = None
"""
Optional: Set this only if your SIM card requires a PIN for activation. 
Most IoT SIMs do not need this.
"""

WEATHER_API_ADRESS = 'run.mocky.io'
"""
The address of the chosen weather API
"""

REVERSE_GEOCODING_API = 'nominatim.openstreetmap.org'
"""
The address of the reverse chosen geococding API
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

location: tuple[float, float] = 50.84, 4.35
"""
Current Location (lat & lon), default is Brussels
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


async def lte_connect(_retry: bool = False, _print_lpad = '  ') -> bool:
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
        print(f'{_print_lpad}- Failed to set operational state to full')
        return False
    
    if (
        await modem.set_network_selection_mode(ModemNetworkSelMode.AUTOMATIC)
    ).result != ModemState.OK:
        print(f'{_print_lpad}- Failed to set network selection mode to automatic')
        return False
    
    print(f'{_print_lpad}- Waiting for network registration')
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
            print(f'{_print_lpad}  - Failed to connect using current RAT')
            return False

        if not await wait_for_network_reg_state(5, ModemNetworkRegState.NOT_SEARCHING):
            print(f'{_print_lpad}  - Unexpected: modem not on standby after 5 seconds')
            return False
        
        rat = modem_rsp.rat

        if _retry:
            print(f'{_print_lpad}  - Failed to connect using LTE-M and NB-IoT, no connection possible')
            
            if rat != ModemRat.LTEM:
                if (await modem.set_rat(ModemRat.LTEM)).result != ModemState.OK:
                    print(f'{_print_lpad}  - Failed to set RAT back to *preferred* LTEM')
                await modem.reset()
            
            return False
        
        print(
            f'{_print_lpad}  - Failed to connect to LTE network using: '
            f'{"LTE-M" if rat == ModemRat.LTEM else "NB-IoT"}'
        )
        print(
            f'{_print_lpad}  - Switching modem to '
            f'{"NB-IoT" if rat == ModemRat.LTEM else "LTE-M"} and retrying...'
        )

        next_rat = ModemRat.NBIOT if rat == ModemRat.LTFalseEM else ModemRat.LTEM

        if (await modem.set_rat(next_rat)).result != ModemState.OK:
            print(f'{_print_lpad}  - Failed to switch RAT')
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
        print('    - Failed to set operational state to minimum')
        return False

    if await wait_for_network_reg_state(5, ModemNetworkRegState.NOT_SEARCHING):
        return True
    
    print(
        '    - Failed to disconnect, '
        'modem network registration state still not "NOT SEARCHING" after 5 seconds'
    )
    return False

def check_assistance_data(modem_rsp) -> tuple[bool, bool]:
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
        print(
            '    - Almanac data is available '
            f'and should be updated within {almanac.time_to_update}'
        )
    else:
        print('    - Almanac data is not available.')

    if ephemeris.available:
        print(
            '    - Real-time ephemeris data is available '
            f'and should be updated within {ephemeris.time_to_update}'
        )
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
    modem_rsp: ModemRsp = await modem.get_clock()
    if modem_rsp.result != ModemState.OK:
        print('    - Failed to retrieve modem time')
        return False
    
    if not modem_rsp.clock:
        print('    - Modem time is invalid, connecting to LTE')
        if not await lte_connect(_print_lpad = '      '):
            print('    - Failed to connect to LTE')
            return False
        
    for i in range(5):
        modem_rsp = await modem.get_clock()
        if modem_rsp.result != ModemState.OK:
            print('    - Failed to retrieve modem time')
            return False
        
        if modem_rsp.clock:
            print(f'    - Synchronised clock with network: {modem_rsp.clock}')
            break
        elif i == 4:
            print('    - Could not sync time with network')

        await asyncio.sleep(.5)

    modem_rsp = await modem.get_gnss_assistance_status()
    if (
        modem_rsp.result != ModemState.OK or 
        modem_rsp.type != ModemRspType.GNSS_ASSISTANCE_DATA
    ):
        print('    - Failed to request GNSS assistance status')
        return False
    
    update_almanac, update_ephemeris = check_assistance_data(modem_rsp)
    
    if update_almanac:
        print('    - Updating Almanac data')
        if not await lte_connect():
            print('    - Failed to connect to LTE network')
            return False
        
        if ((await modem.update_gnss_assistance(ModemGNSSAssistanceType.ALMANAC)).result
            != ModemState.OK):
            print('    - Failed to update almanac data')
            return False
        
    if update_ephemeris:
        print('    - Updating Ephemeris data')
        if not await lte_connect():
            print('    - Failed to connect to LTE network')
            return False
        
        if (
            (await modem.update_gnss_assistance(ModemGNSSAssistanceType.REALTIME_EPHEMERIS)).result
            != ModemState.OK):
            print('    - Failed to update ephemeris data')
            return False
        
    return True

async def unlock_sim() -> bool:
    if (await modem.set_op_state(ModemOpState.NO_RF)).result != ModemState.OK:
        print('    - Failed to set operational state to: NO RF')
        return False

    # Give the modem time to detect the SIM
    asyncio.sleep(2)
    if (await modem.unlock_sim(pin=SIM_PIN)).result != ModemState.OK:
        print('    - Failed to unlock SIM card')
        return False
    else:
        print('    - SIM unlocked')
   
    return True

async def set_location():
    global location

    print('  - Checking GNSS assistance data...')
    if not await update_gnss_assistance():
        print('  - Failed to update GNSS assistance data')

    print('  - Attempting to request a GNSS fix')
    gnss_fix = None
    for i in range(3):
        if i > 0:
            print(f'    - trying again, run: {i+1}/3')
        await lte_disconnect()
        modem_rsp: ModemRsp = await modem.perform_gnss_action(ModemGNSSAction.GET_SINGLE_FIX)
        if modem_rsp.result != ModemState.OK:
            print(
                '    - Failed to request GNSS fix',
                ModemCMEError.get_value_name(modem_rsp.cme_error)
            )
            continue
        
        print('    - Requested GNSS fix')
        print('    - Waiting for GNSS fix')
        gnss_fix = await modem.wait_for_gnss_fix()

        if gnss_fix.estimated_confidence <= MAX_GNSS_CONFIDENCE:
            print(f'    - Fix success, estimated confidence: {gnss_fix.estimated_confidence}')
            break

    if gnss_fix.estimated_confidence > MAX_GNSS_CONFIDENCE:
        print(
            f'    - GNSS fix confidence ({gnss_fix.estimated_confidence:.2f}) '
            f'exceeds max confidence of {MAX_GNSS_CONFIDENCE}'
        )
        print('    - Not accurate enough, values will not be used')
        

    if gnss_fix != None:
        above_threshold = 0
        for sat in gnss_fix.sats:
            if sat.signal_strength >= 30:
                above_threshold += 1
    
        print('  - GNSS fix attempt finished')
        print(f'     Confidence: {gnss_fix.estimated_confidence:.2f}')
        print(f'     Latitude: {gnss_fix.latitude:.06f}')
        print(f'     Longitude: {gnss_fix.longitude:.06f}')
        print(f'     Satcount: {len(gnss_fix.sats)}')
        print(f'     Good sats: {above_threshold}')

        lat: float = gnss_fix.latitude
        lon: float = gnss_fix.longitude

        if gnss_fix.estimated_confidence > MAX_GNSS_CONFIDENCE:
            gnss_fix.sats = []
            print('  - Failed to get a valid fix, using default location')
        else:
            location = lat, lon

async def await_http_response(http_profile: int, timeout: int = 10) -> ModemHttpResponse | None:
    for _ in range(timeout):
        modem_rsp = await modem.http_did_ring(profile_id=http_profile)
        if modem_rsp.result == ModemState.OK:
            return modem_rsp.http_response
        
        await asyncio.sleep(1)
    
    return None

async def fetch_data(url: str, http_profile: int, extra_header_line: str = None) -> dict | None:
    modem_rsp = await modem.http_query(
        profile_id=http_profile,
        uri=url,
        query_cmd=ModemHttpQueryCmd.GET,
        extra_header_line=extra_header_line
    )
    if modem_rsp.result != ModemState.OK:
        print(f'  Failed to fetch data (profile: {http_profile})')
        return None
    
    http_response = await await_http_response(http_profile=http_profile)
    if not http_response or not http_response.data:
        print('  Unexpected, http_response does not have propery data')
        return None
    
    return json.loads(http_response.data)


async def setup():
    print('Walter Weather Example')
    print('Using the Open Meteo weather-api')
    print('---------------', end='\n\n')

    await modem.begin(debug_log=False)

    modem_rsp = await modem.create_PDP_context(
        apn=CELL_APN,
        auth_user=APN_USERNAME,
        auth_pass=APN_PASSWORD
    )
    if modem_rsp.result != ModemState.OK:
        print('Failed to create PDP context')
        return False

    if (await modem.config_gnss()).result != ModemState.OK:
        print('Failed to configure GNSS subsystem')
        return False
    
    print('Setting Location')
    await set_location()

    if (await modem.http_config_profile(1, server_address=WEATHER_API_ADRESS)).result != ModemState.OK:
        print('Failed to configure HTTP profile')
        return False
    
    if (await modem.tls_config_profile(1, tls_version=ModemTlsVersion.TLS_VERSION_12, tls_validation=ModemTlsValidation.NONE)).result != ModemState.OK:
        print('Failed to configure TLS profile')
        return False
    
    if (await modem.http_config_profile(2, server_address=REVERSE_GEOCODING_API, port=443, tls_profile_id=1)).result != ModemState.OK:
        print('Failed to configure HTTP profile')
        return False

    print('Attempting to connect to LTE')
    if not await lte_connect():
        print('Failed to connect to LTE')
        return None
    
    return True

async def loop():
    print('Fetching weather data...')
    weather_data = await fetch_data(url='/v3/c62f2a8a-625b-44b6-9631-363e874a7e30', http_profile=1)

    if weather_data != None:
        dates = weather_data["daily"]["time"]
        min_temps = weather_data["daily"]["temperature_2m_min"]
        max_temps = weather_data["daily"]["temperature_2m_max"]
        precipitation_sums = weather_data["daily"]["precipitation_sum"]

        unit_min_temp = weather_data["daily_units"]["temperature_2m_min"]
        unit_max_temp = weather_data["daily_units"]["temperature_2m_max"]
        unit_precip = weather_data["daily_units"]["precipitation_sum"]

    print('Fetching location address name (reverse geocoding)')

    location_name_data = await fetch_data(
        url=f'/reverse?format=json&lat={location[0]}&lon={location[1]}',
        http_profile=2,
        extra_header_line='User-Agent: Walter Modem Library, weather example sketch'
    )

    if location_name_data != None:
        city = location_name_data['address']['city']
        country = location_name_data['address']['country']

    if weather_data != None:
        # Header
        print("\n" + "=" * 50)
        city_str = city or ""
        country_str = country or ""
        separator = "," if city or country else ":"

        print('Weather Forecast for: ')
        print(f'  {city_str}{separator}{country_str}')
        print(f'  lat: {weather_data['latitude']:.2f}, lon: {weather_data['longitude']:.2f}')
        print("=" * 50)

        # Table Header
        print(f'{'Date':<12} {'Min Temp':<11} {'Max Temp':<11} Precipitation')
        print("-" * 50)

        # Table Data rows
        for i in range(7):
            print(
                f"{dates[i]:<12} "
                f"{min_temps[i]:>6.2f} {unit_min_temp:<5} "
                f"{max_temps[i]:>6.2f} {unit_max_temp:<5} "
                f"{precipitation_sums[i]:>7.2f} {unit_precip:<5}"
            )

        print("=" * 50, end='\r\n\r\n')
    else:
        print('Failed to fetch weather data')

async def main():
    try:
        if not await setup():
            print('Failed to complete setup, raising runtime error to stop')
            raise RuntimeError()
        while True:
            await loop()
            print('Sleeping for 5 minutes before starting again...')
            await asyncio.sleep(300)
    except Exception as err:
        print('ERROR: (boot.py, main): ')
        sys.print_exception(err)
        print('Waiting 5 minutes before exiting')
        # Sleep a while to prevent getting stuck in an infite crash loop
        # And give time for the serial over usb to function
        asyncio.sleep(300)
    
asyncio.run(main())