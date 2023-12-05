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

import uasyncio
import ubinascii
import esp32
import network
import walter
import _walter

SERV_ADDR = "64.225.64.140"
SERV_PORT = 1999
HTTP_PROFILE = 1
modem = None
ctx_id = None
counter = 0
post_mode = False
http_receive_attempts_left = 0


async def setup():
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

    rsp = await modem.get_radio_bands()
    if rsp.result != _walter.ModemState.OK:
        print("Could not retrieve configured radio bands")
        return False

    print('Modem is configured for the following bands:')
    for band_sel in rsp.band_sel_cfg_set:
        print('rat=%d net_operator.name=[%s]' %
            (band_sel.rat, band_sel.net_operator.name))
        for band in band_sel.bands:
            print('  band:%d' % band)

    rsp = await modem.set_op_state(_walter.ModemOpState.NO_RF)
    if rsp.result != _walter.ModemState.OK:
        print("Could not set operational state to NO RF")
        return False

    print("Successfully set operational state to NO RF")

    # Give the modem time to detect the SIM
    await uasyncio.sleep(2)
  
    rsp = await modem.unlock_sim(None)
    if rsp.result != _walter.ModemState.OK:
        print("Could not unlock SIM card")
        return False

    print("Successfully unlocked SIM card")

    # Create PDP context
    rsp = await modem.create_PDP_context('soracom.io',
        _walter.ModemPDPAuthProtocol.PAP, 'sora', 'sora',
        _walter.ModemPDPType.IP, None,
        _walter.ModemPDPHeaderCompression.OFF,
        _walter.ModemPDPDataCompression.OFF,
        _walter.ModemPDPIPv4AddrAllocMethod.DHCP,
        _walter.ModemPDPRequestType.NEW_OR_HANDOVER,
        _walter.ModemPDPPCSCFDiscoveryMethod.AUTO, False, True,
        False, False, False, False)

    if rsp.result != _walter.ModemState.OK:
        print("Could not create PDP context")
        return False

    print("Created PDP context")

    # Authenticate the PDP context
    global ctx_id
    ctx_id = rsp.pdp_ctx_id
    rsp = await modem.authenticate_PDP_context(ctx_id)
    if rsp.result != _walter.ModemState.OK:
        print("Could not authenticate the PDP context")
        return False

    print("Authenticated the PDP context")

    # set operational state to FULL
    rsp = await modem.set_op_state(_walter.ModemOpState.FULL)
    if rsp.result != _walter.ModemState.OK:
        print("Could not set operational state to FULL")
        return False

    print("Successfully set operational state to FULL")

    # Set the network operator selection to automatic */
    rsp = await modem.set_network_selection_mode(
        _walter.ModemNetworkSelMode.AUTOMATIC, None,
        _walter.ModemOperatorFormat.LONG_ALPHANUMERIC)
    if rsp.result != _walter.ModemState.OK:
        print("Could not set the network selection mode to automatic")
        return False

    print("Network selection mode to was set to automatic")

    # Wait for the network to become available */
    rsp = modem.get_network_reg_state()
    while rsp.reg_state != _walter.ModemNetworkRegState.REGISTERED_HOME and rsp.reg_state != _walter.ModemNetworkRegState.REGISTERED_ROAMING:
        await uasyncio.sleep(.1)
        rsp = modem.get_network_reg_state()

    print("Connected to the network")

    # Activate the PDP context
    rsp = await modem.set_PDP_context_active(True, ctx_id)
    if rsp.result != _walter.ModemState.OK:
        print("Could not activate the PDP context")
        return False

    print("Activated the PDP context")

    # Attach the PDP context
    rsp = await modem.attach_PDP_context(True)
    if rsp.result != _walter.ModemState.OK:
        print("Could not attach to the PDP context")
        return False

    print("Attached to the PDP context")

    rsp = await modem.get_PDP_address(ctx_id)
    if rsp.result != _walter.ModemState.OK:
        print("Could not retrieve PDP context addresses")
        return False

    print("PDP context address list:")
    for addr in rsp.pdp_address_list:
        print('- %s' % addr)

    # Construct a socket
    rsp = await modem.create_socket(ctx_id, 300, 90, 60, 5000)
    if rsp.result != _walter.ModemState.OK:
        print("Could not create a new socket")
        return False

    print("Created a new socket")

    rsp = await modem.config_socket(1)
    if rsp.result != _walter.ModemState.OK:
        print("Could not configure the socket")
        return False

    print("Successfully configured the socket")

    # Connect to the UDP test server
    rsp = await modem.connect_socket(SERV_ADDR, SERV_PORT,
            SERV_PORT, _walter.ModemSocketProto.UDP,
            _walter.ModemSocketAcceptAnyRemote.DISABLED, 1)
    if rsp.result != _walter.ModemState.OK:
        print("Could not connect UDP socket")
        return False

    print("Connected to UDP server %s:%d" % (SERV_ADDR, SERV_PORT))

    # Configure http profile for a simple test
    rsp = await modem.http_config_profile(HTTP_PROFILE, "coap.bluecherry.io")
    if rsp.result != _walter.ModemState.OK:
        print('Could not configure http profile')
        return False

    print("Successfully configured the http profile")

    return True


async def loop():
    global counter

    # UDP test

    data_buf = bytearray(network.WLAN().config('mac'))
    data_buf.append(counter >> 8)
    data_buf.append(counter & 0xff)

    rsp = await modem.socket_send(data_buf, _walter.ModemRai.NO_INFO, 1)
    if rsp.result != _walter.ModemState.OK:
        print("Could not transmit data")
        return False

    print("Transmitted counter value %d" % counter)
    counter += 1

    await uasyncio.sleep(10)

    # HTTP test

    global http_receive_attempts_left
    global post_mode

    if http_receive_attempts_left == 0:
        if not post_mode:
            rsp = await modem.http_query(HTTP_PROFILE, '/', _walter.ModemHttpQueryCmd.GET)
            post_mode = True
        else:
            rsp = await modem.http_send(HTTP_PROFILE, '/', data_buf)
            post_mode = False

        if rsp.result != _walter.ModemState.OK:
            print('http query failed (next time post_mode=%d)' % post_mode)
            return False

        print('http query performed (next time post_mode=%d)' % post_mode)
        http_receive_attempts_left = 3

    else:
        http_receive_attempts_left -= 1

        rsp = await modem.http_did_ring(HTTP_PROFILE)
        if rsp.result ==_walter.ModemState.OK:
            http_receive_attempts_left = 0

            print('http status code: %d' % rsp.http_response.http_status)
            print('content type: %s' % rsp.http_response.content_type)
            print(rsp.http_response.data)

        else:
            print('http response not yet received')

    return True


async def main():
    if not await setup():
        return

    while True:
        if not await loop():
            break


modem = walter.Modem()
modem.begin(main)
