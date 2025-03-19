import asyncio
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
    print('Started UART Reader')
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

async def cmd_sender():
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
