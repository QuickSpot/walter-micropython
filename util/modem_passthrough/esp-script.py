import asyncio
import os
import sys
from machine import UART, Pin

FILEPATH = '/remote/cmd'

task: asyncio.Task

# Initialize UART2
uart = UART(2,
            baudrate=115200,
            bits=8,
            parity=None,
            stop=1,
            flow=UART.RTS | UART.CTS,
            tx=48,
            rx=14,
            cts=47,
            rts=21,
            timeout=0,
            timeout_char=0,
            txbuf=2048,
            rxbuf=2048
        )

async def uart_reader():
    print('[i] >> Started UART Reader')
    while True:
        line = uart.readline()
        if line:
            line = line.replace(b'\x00', b'').strip()
            print(line.decode())
        await asyncio.sleep(0.5)

async def reset():
    reset_pin = Pin(45, Pin.OUT)
    reset_pin.off()
    await asyncio.sleep(0.1)
    reset_pin.on()

def ack_read():
    with open(FILEPATH, 'w') as f:
        f.write('READ')

def notif_fail():
    with open(FILEPATH, 'w') as f:
        f.write('PROGFAIL')

def ensure_no_interrupt():
    with open(FILEPATH, 'r+') as f:
        content = f.read().strip()

        if content is 'INTERRUPT':
            ack_read()

async def cmd_sender():
    attempts = 0
    while not 'remote' in os.listdir('/'):
        await asyncio.sleep(1)

        if attempts >= 10:
            print('[i] >> Remote was never mounted, exiting...')
            notif_fail()
            return

    while True:
        try:
            with open(FILEPATH, 'r+') as f:
                content = f.read().strip()
                
                if content is 'INTERRUPT':
                    ack_read()
                    break
                elif content is not None and content is not 'READ':
                    uart.write(content + '\r\n')
                    ack_read()

        except OSError as e:
            print("[i] >> Error reading or writing to file:", e)
            notif_fail()

        await asyncio.sleep(0.5)

async def main():
    global task
    task = asyncio.create_task(uart_reader())
    await reset()
    ensure_no_interrupt()
    await cmd_sender()

try:
    asyncio.run(main())
except KeyboardInterrupt:
    task.cancel()
except Exception as err:
    sys.print_exception(err)
    notif_fail()
