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
import struct
import ubinascii
import esp32
import network
import walter
import _walter


SERV_ADDR = "64.225.64.140"
SERV_PORT = 1999
MAX_GNSS_CONFIDENCE = 500.0
modem = None
gnss_fix = None
fix_rcvd = False
ctx_id = None


async def SLEEPING(msg):
    pass
    #print('SLEEPING: %s' % msg)
    #await uasyncio.sleep(2)


async def lte_init(apn, user, password):
    # create pdp context
    await SLEEPING('11 lte init: create pdp context')
    if user:
        rsp = await modem.create_PDP_context(apn,
            _walter.ModemPDPAuthProtocol.PAP, user, password,
            _walter.ModemPDPType.IP, None,
            _walter.ModemPDPHeaderCompression.OFF,
            _walter.ModemPDPDataCompression.OFF,
            _walter.ModemPDPIPv4AddrAllocMethod.DHCP,
            _walter.ModemPDPRequestType.NEW_OR_HANDOVER,
            _walter.ModemPDPPCSCFDiscoveryMethod.AUTO, False, True,
            False, False, False, False)
    else:
        rsp = await modem.create_PDP_context(apn,
            _walter.ModemPDPAuthProtocol.NONE, None, None,
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

    # Authenticate the PDP context
    global ctx_id
    ctx_id = rsp.pdp_ctx_id
    await SLEEPING('12 lte init: auth pdp context')
    rsp = await modem.authenticate_PDP_context(ctx_id)
    if rsp.result != _walter.ModemState.OK:
        print("Could not authenticate the PDP context")
        return False

    return True


async def wait_for_gnss_fix():
    global gnss_fix
    global fix_rcvd

    while True:
        gnss_fix = await modem.wait_for_gnss_fix()
        fix_rcvd = True


async def lte_disconnect():
    await SLEEPING('13 lte disconnect: set op state minimum')
    rsp = await modem.set_op_state(_walter.ModemOpState.MINIMUM)
    if rsp.result != _walter.ModemState.OK:
        print("Could not set operational state to MINIMUM")
        return False

    rsp = modem.get_network_reg_state()
    while rsp.reg_state != _walter.ModemNetworkRegState.NOT_SEARCHING:
        await uasyncio.sleep(.1)
        rsp = modem.get_network_reg_state()

    print("Disconnected from the network")
    return True


async def lte_connect():
    # Set the operational state to full
    await SLEEPING('14 lte connect: set op state full')
    rsp = await modem.set_op_state(_walter.ModemOpState.FULL)
    if rsp.result != _walter.ModemState.OK:
        print("Could not set operational state to FULL")
        return False

    # Set the network operator selection to automatic */
    await SLEEPING('15 lte connect: set network selection mode')
    rsp = await modem.set_network_selection_mode(
        _walter.ModemNetworkSelMode.AUTOMATIC, None,
        _walter.ModemOperatorFormat.LONG_ALPHANUMERIC)
    if rsp.result != _walter.ModemState.OK:
        print("Could not set the network selection mode to automatic")
        return False

    # Wait for the network to become available */
    await SLEEPING('16 lte connect: wait for network to become available')
    rsp = modem.get_network_reg_state()
    while rsp.reg_state != _walter.ModemNetworkRegState.REGISTERED_HOME and rsp.reg_state != _walter.ModemNetworkRegState.REGISTERED_ROAMING:
        await uasyncio.sleep(.1)
        rsp = modem.get_network_reg_state()

    # Stabilization time
    print("Connected to the network")
    return True


async def socket_connect(ip, port):
    # Activate the PDP context
    await SLEEPING('17 socket connect: set pdp context active')
    rsp = await modem.set_PDP_context_active(True, ctx_id)
    if rsp.result != _walter.ModemState.OK:
        print("Could not activate the PDP context")
        return False

    # Attach the PDP context
    await SLEEPING('18 socket connect: attach pdp context')
    rsp = await modem.attach_PDP_context(True)
    if rsp.result != _walter.ModemState.OK:
        print("Could not attach to the PDP context")
        return False

    # Construct a socket
    await SLEEPING('19 socket connect: create socket')
    rsp = await modem.create_socket(ctx_id, 300, 90, 60, 5000)
    if rsp.result != _walter.ModemState.OK:
        print("Could not create a new socket")
        return False

    await SLEEPING('20 socket connect: config socket')
    rsp = await modem.config_socket(1)
    if rsp.result != _walter.ModemState.OK:
        print("Could not configure the socket")
        return False

    # Connect to the UDP test server
    await SLEEPING('21 socket connect: connect socket')
    rsp = await modem.connect_socket(ip, port,
            0, _walter.ModemSocketProto.UDP,
            _walter.ModemSocketAcceptAnyRemote.DISABLED, 1)
    if rsp.result != _walter.ModemState.OK:
        print("Could not connect UDP socket")
        return False

    print("Connected to UDP server %s:%d" % (ip, port))

    return True


def check_assistance_data(rsp):
    update_almanac = False
    update_ephemeris = False

    if rsp.gnss_assistance.almanac.available:
        print("Almanac data is available and should be updated within %ds" % rsp.gnss_assistance.almanac.time_to_update)
        if rsp.gnss_assistance.almanac.time_to_update <= 0:
            update_almanac = True
    else:
        print("Almanac data is not available.")
        update_almanac = True

    if rsp.gnss_assistance.ephemeris.available:
        print("Real-time ephemeris data is available and should be updated within %ds" % rsp.gnss_assistance.ephemeris.time_to_update)
        if rsp.gnss_assistance.ephemeris.time_to_update <= 0:
            update_ephemeris = True
    else:
        print("Real-time ephemeris data is not available.")
        update_ephemeris = True

    return update_almanac, update_ephemeris


async def update_gnss_assistance():
    lte_connected = False

    await SLEEPING('22 update gnss assistance: lte disconnect')
    await lte_disconnect()

    # Even with valid assistance data the system clock could be invalid
    await SLEEPING('23 update gnss assistance: get clock')
    rsp = await modem.get_clock()
    if rsp.result != _walter.ModemState.OK:
        print("Could not check the modem time")
        return False

    if not rsp.clock:
        # The system clock is invalid, connect to LTE network to sync time
        await SLEEPING('24 update gnss assistance: lte connect')
        if not await lte_connect():
            print("Could not connect to LTE network")
            return False

        lte_connected = True

        # Wait for the modem to synchronize time with the LTE network, try 5 times
        # with a delay of 500ms.
        for i in range(5):
            await SLEEPING('25 update gnss assistance: get clock with lte connection')
            rsp = await modem.get_clock()
            if rsp.result != _walter.ModemState.OK:
                print("Could not check the modem time")
                return False

            if rsp.clock:
                print("Synchronized clock with network: %d" % rsp.clock)
                break
            elif i == 4:
                print("Could not sync time with network")
                return False

            await uasyncio.sleep(.5)

    # Check the availability of assistance data
    await SLEEPING('26 update gnss assistance: get gnss assistance status')
    rsp = await modem.get_gnss_assistance_status()
    if rsp.result != _walter.ModemState.OK or rsp.type != _walter.ModemRspType.GNSS_ASSISTANCE_DATA:
        print("Could not request GNSS assistance status")
        return False

    update_almanac, update_ephemeris = check_assistance_data(rsp)

    if not update_almanac and not update_ephemeris:
        if lte_connected:
            await SLEEPING('27 update gnss assistance: lte disconnect')
            if not await lte_disconnect():
                print("Could not disconnect from the LTE network")
                return False

        return True

    if not lte_connected:
        await SLEEPING('28 update gnss assistance: lte sconnect')
        if not await lte_connect():
            print("Could not connect to LTE network")
            return False

    if update_almanac:
        await SLEEPING('29 update gnss assistance: first update gnss assistance call')
        rsp = await modem.update_gnss_assistance(_walter.ModemGNSSAssistanceType.ALMANAC)
        if rsp.result != _walter.ModemState.OK:
            print("Could not update almanac data")
            return False

    if update_ephemeris:
        await SLEEPING('29 update gnss assistance: second update gnss assistance call')
        rsp = await modem.update_gnss_assistance(_walter.ModemGNSSAssistanceType.REALTIME_EPHEMERIS)
        if rsp.result != _walter.ModemState.OK:
            print("Could not update real-time ephemeris data")
            return False

    await SLEEPING('30 update gnss assistance: get gnss assistance status')
    rsp = await modem.get_gnss_assistance_status()
    if rsp.result != _walter.ModemState.OK or rsp.type != _walter.ModemRspType.GNSS_ASSISTANCE_DATA:
        print("Could not request GNSS assistance status")
        return False

    check_assistance_data(rsp)
  
    await SLEEPING('31 update gnss assistance: lte disconnect')
    if not await lte_disconnect():
        print("Could not disconnect from the LTE network")
        return False

    return True


async def setup():
    print("Walter Positioning v0.0.1")

    print("Walter's MAC is: %s" % ubinascii.hexlify(network.WLAN().config('mac'),':').decode())

    if not await lte_init(None, None, None):
        print("Could not initialize LTE network parameters")
        return False

    print("Initialized LTE parameters")

    await SLEEPING('1 set op state minimum')
    rsp = await modem.set_op_state(_walter.ModemOpState.MINIMUM)
    if rsp.result != _walter.ModemState.OK:
        print("Could not set operational state to MINIMUM")
        return False

    await uasyncio.sleep(.5)
  
    await SLEEPING('2 config gnss')
    rsp = await modem.config_gnss(
            _walter.ModemGNSSSensMode.HIGH,
            _walter.ModemGNSSAcqMode.COLD_WARM_START,
            _walter.ModemGNSSLocMode.ON_DEVICE_LOCATION)
    if rsp.result != _walter.ModemState.OK:
        print("Could not configure the GNSS subsystem")
        return False
    
    await SLEEPING('3 create task wait for gnss fix')
    uasyncio.create_task(wait_for_gnss_fix())

    return True


async def loop():
    global fix_rcvd
    global gnss_fix

    await SLEEPING('4 update gnss assistance')
    if not await update_gnss_assistance():
        print("Could not update GNSS assistance data")
        return False

    # Try up to 5 times to get a good fix
    for i in range(5):
        await SLEEPING('5 request fix')
        fix_rcvd = False
        rsp = await modem.perform_gnss_action(_walter.ModemGNSSAction.GET_SINGLE_FIX)
        if rsp.result != _walter.ModemState.OK:
            print("Could not request GNSS fix")
            return False

        print("Started GNSS fix")

        while not fix_rcvd:
            await uasyncio.sleep(.5)

        if gnss_fix.estimated_confidence <= MAX_GNSS_CONFIDENCE:
          break

    above_threshold = 0
    for sat in gnss_fix.sats:
        if sat.signal_strength >= 30:
            above_threshold += 1

    print("GNSS fix attempt finished:")
    print("  Confidence: %.02f" % gnss_fix.estimated_confidence)
    print("  Latitude: %.06f" % gnss_fix.latitude)
    print("  Longitude: %.06f" % gnss_fix.longitude)
    print("  Satcount: %d" % len(gnss_fix.sats))
    print("  Good sats: %d" % above_threshold)

    # read temperature
    # ?? TODO

    lat = gnss_fix.latitude
    lon = gnss_fix.longitude
    lat_bytes = struct.pack('f', lat)
    lon_bytes = struct.pack('f', lon)
  
    if gnss_fix.estimated_confidence > MAX_GNSS_CONFIDENCE:
        gnss_fix.sats = []
        lat = 0.0
        lon = 0.0
        print("Could not get a valid fix")

    # Construct the minimal sensor + GNSS
    # XXX check the datagram construction for endianness issues
    #raw_temp = (temp + 50) * 100;
    data_buf = bytearray(network.WLAN().config('mac'))
    data_buf.append(0x2)
    data_buf.append(0)          # temperature not supported
    data_buf.append(0)          # temperature not supported
    data_buf.append(len(gnss_fix.sats))
    data_buf.append(lat_bytes[0])
    data_buf.append(lat_bytes[1])
    data_buf.append(lat_bytes[2])
    data_buf.append(lat_bytes[3])
    data_buf.append(lon_bytes[0])
    data_buf.append(lon_bytes[1])
    data_buf.append(lon_bytes[2])
    data_buf.append(lon_bytes[3])
    
    await SLEEPING('6 lte connect')
    if not await lte_connect():
        print("Could not connect to the LTE network")
        return False

    await SLEEPING('7 connect to udp server socket')
    if not await socket_connect(SERV_ADDR, SERV_PORT):
        print("Could not connect to UDP server socket")
        return False

    await SLEEPING('8 socket send')
    rsp = await modem.socket_send(data_buf, _walter.ModemRai.NO_INFO, 1)
    if rsp.result != _walter.ModemState.OK:
        print("Could not transmit data")
        return False

    await uasyncio.sleep(5)

    await SLEEPING('9 close socket')
    rsp = await modem.close_socket(ctx_id)
    if rsp.result != _walter.ModemState.OK:
        print("Could not close the socket")
        return False

    # TODO: this is missing in C version?
    await SLEEPING('10 disconnect lte')
    await lte_disconnect()

    return True


async def main():
    if not await setup():
        return

    while True:
        if not await loop():
            break


modem = walter.Modem()
modem.begin(main)
