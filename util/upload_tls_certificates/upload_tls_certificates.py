"""
Script to store TLS certificates in the NVRAM of the modem.
"""
import asyncio

from walter_modem import Modem

from walter_modem.enums import (
    WalterModemState,
    WalterModemOpState
)

from walter_modem.structs import (
    ModemRsp
)

modem = Modem()
"""
The modem instance
"""

modem_rsp = ModemRsp()
"""
The modem response object.
We re-use this single one, for memory efficiency.
"""

# fill in your own ca cert or import the text file instead,
# add client cert and client key if needed.
ca_cert = """-----BEGIN CERTIFICATE-----
(...)
-----END CERTIFICATE-----"""

async def main():
    await modem.begin()

    if not await modem.check_comm():
        print('Modem communication error')
        return False

    if await modem.get_op_state(rsp=modem_rsp) and modem_rsp.op_state is not None:
        print(f'Modem operatonal state: {WalterModemOpState.get_value_name(modem_rsp.op_state)}')
    else:
        print('Failed to retrieve modem operational state')
        return False
    
    # only using ca cert here, however, you can set cert & priv_key too if needed
    if not await modem.tls_provision_keys(
        walter_certificate=None,
        walter_private_key=None,
        ca_certificate=ca_cert
    ):
        print("Could not upload certificate.")
        return False
    
    print ('Certificates uploaded')

asyncio.run(main())