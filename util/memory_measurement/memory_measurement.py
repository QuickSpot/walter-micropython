import asyncio
import micropython # type: ignore
import gc

def format_bytes(size, precision=2):
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    for unit in units:
        if size < 1024 or unit == 'PB':
            return f'{size:.{precision}f} {unit}'
        size /= 1024


gc.collect()
start = gc.mem_free()

from walter_modem import Modem
gc.collect()
after_import = gc.mem_free()

walter_modem = Modem()
gc.collect()
after_instance_creation = gc.mem_free()

async def begin_modem():
    await walter_modem.begin()

asyncio.run(begin_modem())
gc.collect()
after_modem_begin = gc.mem_free()

modem_import = start - after_import
modem_instantiation = after_import - after_instance_creation
modem_begin = after_instance_creation - after_modem_begin
total = modem_import + modem_instantiation + modem_begin

print('==== MEMORY MEASUREMENT ====')
print('Measuring free memory lost using gc (results are rough approximations)\n')
print(f'- {'Modem Import':<20}: {modem_import} bytes ({format_bytes(modem_import)}) ')
print(f'- {'Modem Instantiation':<20}: {modem_instantiation} bytes ({format_bytes(modem_instantiation)})')
print(f'- {'Modem Begin':<20}: {modem_begin} bytes ({format_bytes(modem_begin)})')
print(f'\nTotal: {total} bytes ({format_bytes(total)})')

print('==== Memory Map ====')
gc.collect()
micropython.mem_info(True)