import asyncio
import json
import sys

from machine import Pin, I2C, WDT, reset
from hdc1080 import HDC1080
from lps22hb import LPS22HB
from ltc4015 import LTC4015

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

hdc1080: HDC1080
lps22hb: LPS22HB
ltc4015: LTC4015

wdt = WDT(timeout=max(60000, (config.SLEEP_TIME * 1000) + 10000))
modem = Modem()
modem_rsp = ModemRsp()
rsrp = False

def get_data() -> dict:
    data_map = {
        'temperature': hdc1080.temperature,
        'humidity': hdc1080.humidity,
        'pressure': lps22hb.read_pressure,
        'input_voltage': ltc4015.get_input_voltage,
        'input_current': ltc4015.get_input_current,
        'system_voltage': ltc4015.get_system_voltage,
        'battery_voltage': ltc4015.get_battery_voltage,
        'battery_current': ltc4015.get_charge_current,
        'battery_percentage': ltc4015.get_estimated_battery_percentage,
        'rsrp': lambda: modem_rsp.signal_quality.rsrp if rsrp else None
    }

    data = {}

    for data_type, pin in config.BLYNK_DEVICE_PINS.items():
        if pin and (value := data_map[data_type]()) is not None:
            data[pin] = value

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
        wdt.feed()
    
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
    
    wdt.feed()
    
    if not await modem.set_network_selection_mode(ModemNetworkSelMode.AUTOMATIC):
        print('  - Failed to set network selection mode to automatic')
        return False
    
    wdt.feed()
    
    print('  - Waiting for network registration')
    if not await wait_for_network_reg_state(
        300,
        ModemNetworkRegState.REGISTERED_HOME,
        ModemNetworkRegState.REGISTERED_ROAMING
    ):
        if await modem.get_rat(rsp=modem_rsp):
            if not await modem.set_op_state(ModemOpState.MINIMUM):
                wdt.feed()
                print('  - Failed to connected using current RAT')
                return False
            
        wdt.feed()

        if not await wait_for_network_reg_state(5, ModemNetworkRegState.NOT_SEARCHING):
            print('  - Unexpected: modem not on standby after 5 seconds')
            return False
        
        wdt.feed()
        
        rat = modem_rsp.rat

        if _retry:
            print('  - Failed to connect using LTE-M and NB-IoT, no connection possible')
            
            if rat != ModemRat.LTEM:
                if not await modem.set_rat(ModemRat.LTEM):
                    print('  - Failed to set RAT back to *preferred* LTEM')
                await modem.reset()

                wdt.feed()
            
            return False
        
        wdt.feed()
        
        print(f'  - Failed to connect to LTE network using: {"LTE-M" if rat == ModemRat.LTEM else "NB-IoT"}')
        print(f'  - Switching modem to {"NB-IoT" if rat == ModemRat.LTEM else "LTE-M"} and retrying...')

        next_rat = ModemRat.NBIOT if rat == ModemRat.LTEM else ModemRat.LTEM

        if not await modem.set_rat(next_rat):
            print('  - Failed to switch RAT')
            return False
        
        wdt.feed()

        await modem.reset()
        return await lte_connect(_retry=True)
    
    return True

async def unlock_sim() -> bool:
    if not await modem.set_op_state(ModemOpState.NO_RF):
        print('  - Failed to set operational state to: NO RF')
        return False
    
    wdt.feed()

    # Give the modem time to detect the SIM
    asyncio.sleep(2)
    if await modem.unlock_sim(pin=config.SIM_PIN):
        print('  - SIM unlocked')
    else:
        print('  - Failed to unlock SIM card')
        return False
    
    wdt.feed()
   
    return True

async def await_http_response(http_profile: int, timeout_before_hard_reset: int = 300) -> bool:
    global modem_rsp

    for _ in range(timeout_before_hard_reset):
        if await modem.http_did_ring(profile_id=http_profile, rsp=modem_rsp):
            return True
        
        wdt.feed()
        await asyncio.sleep(1)

    # Hard reset because with query, we cannot manually close the connection,
    # It is managed (and thus closed) by the modem itself
    print(
        f'Modem is still waiting for response after {timeout_before_hard_reset}s'
        '(timeout_before_hard_reset)')
    print('Hard resetting...')
    reset()

def urlencode(params: dict) -> str:
    if len(params) <= 0:
        return ''
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
        return await await_http_response(http_profile=0)
    else:
        print(f'  Failed to fetch data (profile: {http_profile}, uri: {uri})')
        return False

async def modem_setup():
    global modem_rsp

    await modem.begin()

    if not await modem.check_comm():
        print('Modem communication error')
        return False
    
    wdt.feed()

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
    
    wdt.feed()
   
    if config.APN_USERNAME and not await modem.authenticate_PDP_context(modem_rsp.pdp_ctx_id):
        print('Failed to authenticate PDP context')
    
    if not await modem.tls_config_profile(
        profile_id=1,
        tls_validation=ModemTlsValidation.NONE,
        tls_version=ModemTlsVersion.TLS_VERSION_12
    ):
        print('Failed to configure TLS profile')
        return False
    
    wdt.feed()
    
    if not await modem.http_config_profile(
        profile_id=0,
        server_address=config.BLYNK_SERVER_ADDRESS,
        port=443,
        tls_profile_id=1
    ):
        print('Failed to configure HTTP profile')
        return False
    
    wdt.feed()
    
    print('Connecting to LTE Network')
    if not await lte_connect():
        print('Failed to connect to LTE Network')
        return False
    
    wdt.feed()
    
    return True

async def ltc4015_setup():
    ltc4015.initialize()
    ltc4015.suspend_charging()
    ltc4015.enable_force_telemetry()
    asyncio.sleep_ms(100)
    ltc4015.disable_force_telemetry()
    ltc4015.start_charging()
    ltc4015.enable_mppt()

async def setup() -> bool:
    global hdc1080
    global lps22hb
    global ltc4015

    print('Walter Feels Example')
    print('---------------', end='\n\n')
    wdt.feed()

    # Output pins
    PWR_3V3_EN_PIN = Pin(0, Pin.OUT)
    PWR_12V_EN_PIN = Pin(43, Pin.OUT)
    I2C_BUS_PWR_EN_PIN = Pin(1, Pin.OUT)
    CAN_EN_PIN = Pin(44, Pin.OUT)
    SDI12_TX_EN_PIN = Pin(10, Pin.OUT)
    SDI12_RX_EN_PIN = Pin(9, Pin.OUT)
    RS232_TX_EN_PIN = Pin(17, Pin.OUT)
    RS232_RX_EN_PIN = Pin(16, Pin.OUT)
    RS485_TX_EN_PIN = Pin(18, Pin.OUT)
    RS485_RX_EN_PIN = Pin(8, Pin.OUT)
    CO2_EN_PIN = Pin(13, Pin.OUT)
    CO2_SCL_PIN = Pin(11, Pin.OUT)

    # Input pins
    I2C_SDA_PIN = Pin(42, Pin.OPEN_DRAIN)
    I2C_SCL_PIN = Pin(2, Pin.OPEN_DRAIN)
    SD_CMD_PIN = Pin(6, Pin.IN)
    SD_CLK_PIN = Pin(5, Pin.IN)
    SD_DAT0_PIN = Pin(4, Pin.IN)
    GPIO_A_PIN = Pin(39, Pin.IN)
    GPIO_B_PIN = Pin(38, Pin.IN)
    SER_RX_PIN = Pin(41, Pin.IN)
    SER_TX_PIN = Pin(40, Pin.IN)
    CAN_RX_PIN = Pin(7, Pin.IN)
    CAN_TX_PIN = Pin(15, Pin.IN)
    CO2_SDA_PIN = Pin(12, Pin.IN)

    # Disable all peripherals
    PWR_3V3_EN_PIN.value(1)
    PWR_12V_EN_PIN.value(0)
    I2C_BUS_PWR_EN_PIN.value(0)
    CAN_EN_PIN.value(1)
    SDI12_TX_EN_PIN.value(0)
    SDI12_RX_EN_PIN.value(0)
    RS232_TX_EN_PIN.value(0)
    RS232_RX_EN_PIN.value(1)
    RS485_TX_EN_PIN.value(0)
    RS485_RX_EN_PIN.value(1)
    CO2_EN_PIN.value(1)

    # Initialize I2C
    i2c = I2C(0, scl=I2C_SCL_PIN, sda=I2C_SDA_PIN)

    # Initialize charging
    ltc4015 = LTC4015(i2c, 3, 4)
    I2C_BUS_PWR_EN_PIN.value(1)
    ltc4015.initialize()
    ltc4015.enable_coulomb_counter()
    I2C_BUS_PWR_EN_PIN.value(0)

    # Initialize modem
    if not await modem_setup():
        print('Failed to setup modem')
        return False
    
    wdt.feed()

    # Enable 3.3V and I2C bus power, wait for sensors to boot
    PWR_3V3_EN_PIN.value(0)
    I2C_BUS_PWR_EN_PIN.value(1)
    asyncio.sleep(1)

    # Initialize the sensors
    hdc1080 = HDC1080(i2c)
    hdc1080.config(mode=1)
    lps22hb = LPS22HB(i2c)
    lps22hb.begin()
    await ltc4015_setup()

    return True

async def loop():
    global modem_rsp
    global rsrp

    wdt.feed()

    if await modem.get_signal_quality(rsp=modem_rsp):
        rsrp = True

    wdt.feed()

    data = get_data()
    if await fetch(
        http_profile=0,
        path='/external/api/batch/update',
        query_string=f'token={config.BLYNK_TOKEN}&{urlencode(data)}'
    ):
        if modem_rsp.http_response.http_status == 200:
            print('sent data:')
            for pin, value in data.items():
                data_type = '?'
                for k, v in config.BLYNK_DEVICE_PINS.items():
                    if v == pin:
                        data_type = k
                        break
                print(f'  {data_type} ({pin}): {value}')
        else:
            print(f'HTTP status: {modem_rsp.http_response.http_status}')
            print(json.loads(modem_rsp.http_response.data))

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
        print(f'Waiting 10 seconds before hard resetting')
        # Sleep a while to prevent getting stuck in an infite crash loop
        # And give time for the serial over usb to function
        await asyncio.sleep(10)
        reset()

asyncio.run(main())