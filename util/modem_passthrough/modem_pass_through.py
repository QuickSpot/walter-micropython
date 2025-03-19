import asyncio
from machine import UART, Pin
import sys
import select

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
    print('Started Uart Reader')
    while True:
        line = uart.readline()
        if line:
            line = line.strip()
            print('RX: ', line)
        await asyncio.sleep(0.5)

async def reset():
    reset_pin = Pin(45, Pin.OUT)
    reset_pin.off()
    await asyncio.sleep(0.1)
    reset_pin.on()

async def cmd_sender():
    while True:
        try:
            with open('/remote/cmd_passthrough', 'r+') as f:
                content = f.read().strip()
                
                if content is not None and content is not 'READ':
                    print("New data:", content)

                    with open('/remote/cmd_passthrough', 'w') as cf:
                        cf.write('READ')

        except OSError as e:
            print("Error reading or writing to file:", e)

        await asyncio.sleep(0.5)

async def main():
    global task
    task = asyncio.create_task(uart_reader())
    await reset()
    await cmd_sender()

try:
    asyncio.run(main())
except KeyboardInterrupt:
    task.cancel()
    pass
