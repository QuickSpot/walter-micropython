"""
Script to store TLS certificates in the NVRAM of the modem.

(I am using only the ca certificate, no client certificate, but
the script should also work with client cert and key.)
"""

import uasyncio
import ubinascii
import network
import walter
import _walter

modem = None

# fill in your own ca cert or import the text file instead,
# add client cert and client key if needed.
ca_cert = """-----BEGIN CERTIFICATE-----
(...)
-----END CERTIFICATE-----"""

async def main():
    print("Walter modem test v0.0.1")

    print("Walter's MAC is: %s" % ubinascii.hexlify(network.WLAN().config('mac'),':').decode())

    rsp = await modem.check_comm()
    if rsp.result != _walter.ModemState.OK:
        print("Modem communication error")
        return False

    rsp = await modem.get_op_state()
    if rsp.result != _walter.ModemState.OK:
        print("Could not retrieve modem operational state")
        return False

    print('Modem operational state: %d' % rsp.op_state)
    
    # the arguments are client cert, client key, and ca cert
    # only using ca cert here
    rsp = await modem.tls_provision_keys(None, None, ca_cert)
    if rsp.result != _walter.ModemState.OK:
        print("Could not upload certificate.")
        return False

    print('CA certificate uploaded.')
    
modem = walter.Modem()
modem.begin(main)
