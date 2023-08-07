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

from machine import Pin, UART
import time
import uasyncio
import uselect
import sys
import random
from queue import Queue

CR = 13
LF = 10
PLUS = ord('+')
GREATER_THAN = ord('>')
SMALLER_THAN = ord('<')
SPACE = ord(' ')

"""
The default number of attempts to execute a command.
"""
WALTER_MODEM_DEFAULT_CMD_ATTEMPTS = 3

"""
The RX pin on which modem data is received.
"""
WALTER_MODEM_PIN_RX = 14

"""
The TX to which modem data must be transmitted.
"""
WALTER_MODEM_PIN_TX = 48

"""
The RTS pin on the ESP32 side.
"""
WALTER_MODEM_PIN_RTS = 21

"""
The CTS pin on the ESP32 size.
"""
WALTER_MODEM_PIN_CTS = 47

"""
The active low modem reset pin.
"""
WALTER_MODEM_PIN_RESET = 45

"""
The baud rate used to talk to the modem.
"""
WALTER_MODEM_BAUD = 115200

"""
The maximum number of seconds to wait.
"""
WALTER_MODEM_CMD_TIMEOUT = 5

"""
Any modem time below 1 Jan 2023 00:00:00 UTC is considered an invalid time.
"""
WALTER_MODEM_MIN_VALID_TIMESTAMP = 1672531200

"""
The maximum number of PDP contexts that the library can support.
"""
WALTER_MODEM_MAX_PDP_CTXTS = 8

"""
The maximum number of sockets that the library can support.
"""
WALTER_MODEM_MAX_SOCKETS = 6

"""
The max nr of http profiles
"""
WALTER_MODEM_MAX_HTTP_PROFILES = 3


import _walter


def modem_string(a_string):
    if a_string:
        return '"' + a_string + '"'
    else:
        return ''

def modem_bool(a_bool):
    if a_bool:
        return 1
    else:
        return 0

def pdp_type_as_string(pdp_type):
    if pdp_type == _walter.ModemPDPType.X25:
        return '"X.25"'
    if pdp_type == _walter.ModemPDPType.IP:
        return '"IP"'
    if pdp_type == _walter.ModemPDPType.IPV6:
        return '"IPV6"'
    if pdp_type == _walter.ModemPDPType.IPV4V6:
        return '"IPV4V6"'
    if pdp_type == _walter.ModemPDPType.OSPIH:
        return '"OPSIH"'
    if pdp_type == _walter.ModemPDPType.PPP:
        return '"PPP"'
    if pdp_type == _walter.ModemPDPType.NON_IP:
        return '"Non-IP"'
    return ''

def parse_cclk_time(time_str):
    # format: yy/mm/dd,hh:nn:ss+qq
    # where qq = tz offset in quarters of an hour
    yy = int(time_str[:2])
    mm = int(time_str[3:5])
    dd = int(time_str[6:8])
    hh = int(time_str[9:11])
    nn = int(time_str[12:14])
    ss = int(time_str[15:17])
    if time_str[17] == '+':
        qq = int(time_str[18:])
    else:
        qq = -int(time_str[18:])

    # 1970-1999 are invalid since micropython epoch starts at 2000
    if yy >= 70:
        return None

    yyyy = yy + 2000

    tm = (yyyy, mm, dd, hh, nn, ss, 0, 0, 0)

    # on arduino:
    # epoch (1 jan 1970) = 0
    # 1 jan 2000 = 946684800
    #
    # on micropython:
    # epoch (1 jan 2000) = 0
    # so add constant 946684800 to be compatible with our arduino lib

    time_val = time.mktime(tm) + 946684800 - (qq * 15 * 60)

    return time_val

def parse_gnss_time(time_str):
    # format: yyyy-mm-ddThh:nn
    yyyy = int(time_str[:4])
    mm = int(time_str[5:7])
    dd = int(time_str[8:10])
    hh = int(time_str[11:13])
    nn = int(time_str[14:16])
    if len(time_str) > 16:
        ss = int(time_str[17:19])
    else:
        ss = 0

    # 1970-1999 are invalid since micropython epoch starts at 2000
    if yyyy < 2000:
        return None

    tm = (yyyy, mm, dd, hh, nn, ss, 0, 0, 0)

    # on arduino:
    # epoch (1 jan 1970) = 0
    # 1 jan 2000 = 946684800
    #
    # on micropython:
    # epoch (1 jan 2000) = 0
    # so add constant 946684800 to be compatible with our arduino lib

    time_val = time.mktime(tm) + 946684800

    return time_val

def error_rsp(result):
    rsp = _walter.ModemRsp()
    rsp.result = result
    return rsp

class Modem:
    def __init__(self):
        """The flag indicating if the modem is initialized."""
        self._initialized = False

        """The hardware serial peripheral used to talk to the modem."""
        self._uart = None

        """The current operational state of the modem."""
        self._op_state = _walter.ModemOpState.MINIMUM

        """The current network registration state of the modem."""
        self._reg_state = _walter.ModemNetworkRegState.NOT_SEARCHING

        """The PIN code when required for the installed SIM."""
        self._simPIN = None

        """The chosen network selection mode."""
        self._network_sel_mode = _walter.ModemNetworkSelMode.AUTOMATIC

        """An operator to use, this is ignored when automatic operator selection
        is used."""
        self._operator = _walter.ModemOperator()

        """The PDP context which is currently in use by the library or None when
        no PDP context is in use. In use doesn't mean that the 
        context is activated yet it is just a pointer to the PDP context
        which was last used by any of the functions that work with a PDP
        context."""
        self._pdp_ctx = None
        
        """The list of PDP context."""
        self._pdp_ctx_set = [_walter.ModemPDPContext(idx + 1) for idx in range(WALTER_MODEM_MAX_PDP_CTXTS)]

        """The list of sockets"""
        self._socket_set = [ _walter.ModemSocket(idx + 1) for idx in range(WALTER_MODEM_MAX_SOCKETS) ]

        """The socket which is currently in use by the library or None when no 
        socket is in use."""
        self._socket = None

        """The list of http contexts in the modem"""
        self._http_context_set = [ _walter.ModemHttpContext() for _ in range(WALTER_MODEM_MAX_HTTP_PROFILES) ]

        """Current http profile in use in the modem"""
        self._http_current_profile = 0xff

        """The GNSS fix which is currently being processed."""
        self._GNSSfix = _walter.ModemGNSSFix()

        """Task queue: commands and responses"""
        self._task_queue = None
        
        """Command queue: saved commands"""
        self._command_queue = None

        """Parser state"""
        self._parser_data = _walter.ModemATParserData()

        """GNSS fix waiters"""
        self._gnss_fix_lock = uasyncio.Lock()
        self._gnss_fix_waiters = []

    async def _queue_rx_buffer(self):
        """Copy the currently received data buffer into the task queue.
        
        This function will copy the current modem receive buffer into the
        task queue. When the buffer could not be placed in the queue it will
        be silently dropped.
        
        :returns: None.
        """
        qitem = _walter.ModemTaskQueueItem()
        qitem.rsp = self._parser_data.line

        await self._task_queue.put(qitem)

        self._parser_data.line = b''

    def _add_at_byte_to_buffer(self, data, raw_mode_active):
        """Handle an AT data byte.
        
        This function is used by the AT data parser to add a databyte to 
        the buffer currently in use or to reserve a new buffer to add a byte
        to.
        
        :param data: The data byte to handle.
        
        :returns: None.
        """
        
        if not raw_mode_active and data == CR:
            self._parser_data.state = _walter.ModemRspParserState.END_LF
            return

        self._parser_data.line += chr(data)

    async def _uart_reader(self):
        rx_stream = uasyncio.StreamReader(self._uart, {})

        while True:
            incoming_uart_data = bytearray(256)
            size = await rx_stream.readinto(incoming_uart_data)
            print('RX:[%s]' % incoming_uart_data[:size])
            for b in incoming_uart_data[:size]:
                if self._parser_data.state == _walter.ModemRspParserState.START_CR:
                    if b == CR:
                        self._parser_data.state = _walter.ModemRspParserState.START_LF
                    elif b == PLUS:
                        # This is the start of a new line in a multiline response
                        self._parser_data.state = _walter.ModemRspParserState.DATA
                        self._add_at_byte_to_buffer(b, False)
                
                elif self._parser_data.state == _walter.ModemRspParserState.START_LF:
                    if b == LF:
                        self._parser_data.state = _walter.ModemRspParserState.DATA
                
                elif self._parser_data.state == _walter.ModemRspParserState.DATA:
                    if b == GREATER_THAN:
                        self._parser_data.state = _walter.ModemRspParserState.DATA_PROMPT
                    elif b == SMALLER_THAN:
                        self._parser_data.state = _walter.ModemRspParserState.DATA_HTTP_START1
                
                    self._add_at_byte_to_buffer(b, False)
                    
                elif self._parser_data.state == _walter.ModemRspParserState.DATA_PROMPT:
                    self._add_at_byte_to_buffer(b, False)
                    if b == SPACE:
                        self._parser_data.state = _walter.ModemRspParserState.START_CR
                        await self._queue_rx_buffer()
                    else:
                        # state might have changed after detecting end \r
                        if self._parser_data.state == _walter.ModemRspParserState.DATA_PROMPT:
                            self._parser_data.state = _walter.ModemRspParserState.DATA
                
                elif self._parser_data.state == _walter.ModemRspParserState.DATA_HTTP_START1:
                    if b == SMALLER_THAN:
                        self._parser_data.state = _walter.ModemRspParserState.DATA_HTTP_START2
                    else:
                        self._parser_data.state = _walter.ModemRspParserState.DATA

                    self._add_at_byte_to_buffer(b, False)

                elif self._parser_data.state == _walter.ModemRspParserState.DATA_HTTP_START2:
                    if b == SMALLER_THAN and self._http_current_profile < WALTER_MODEM_MAX_HTTP_PROFILES:
                        # FIXME: modem might block longer than cmd timeout,
                        # will lead to retry, error etc - fix properly
                        self._parser_data.raw_chunk_size = _http_context_set[_http_current_profile].content_length + len("\r\nOK\r\n")
                        self._parser_data.state = _walter.ModemRspParserState.RAW
                    else:
                        self._parser_data.state = _walter.ModemRspParserState.DATA

                    self._add_at_byte_to_buffer(b, False)

                elif self._parser_data.state == _walter.ModemRspParserState.END_LF:
                    if b == LF:
                        chunk_size = 0 ### FIXME
                        #uint16_t chunkSize = _extractRawBufferChunkSize();
                        if chunk_size:
                            self._parser_data.raw_chunk_size = chunk_size
                            self._parser_data.line += b'\r'
                            self._parser_data.state = _walter.ModemRspParserState.RAW
                        else:
                            self._parser_data.state = _walter.ModemRspParserState.START_CR
                            await self._queue_rx_buffer()
                    else:
                        # only now we know the \r was thrown away for no good reason
                        self._parser_data.line += b'\r'

                        # next byte gets the same treatment; since we really are
                        # back in semi DATA state, as we now know
                        # (but > will not lead to data prompt mode)
                        self._add_at_byte_to_buffer(b, False)
                        if b != CR:
                            self._parser_data.state = _walter.ModemRspParserState.DATA

                elif self._parser_data.state == _walter.ModemRspParserState.RAW:
                    self._add_at_byte_to_buffer(b, True)
                    self._parser_data.raw_chunk_size -= 1

                    if self._parser_data.raw_chunk_size == 0:
                        self._parser_data.state = _walter.ModemRspParserState.START_CR
                        await self._queue_rx_buffer()

    async def _finish_queue_cmd(self, cmd, result):
        cmd.rsp.result = result

        if cmd.complete_handler:
            await cmd.complete_handler(result, cmd.rsp, cmd.complete_handler_arg)

        # we must unblock stuck cmd now
        cmd.state = _walter.ModemCmdState.COMPLETE
        cmd.event.set()

    async def _process_queue_cmd(self, tx_stream, cmd):
        if cmd.type == _walter.ModemCmdType.TX:
            print('TX:[%s]' % cmd.at_cmd)
            tx_stream.write(cmd.at_cmd)
            tx_stream.write(b'\r\n')
            await tx_stream.drain()
            await self._finish_queue_cmd(cmd, _walter.ModemState.OK)

        elif cmd.type == _walter.ModemCmdType.TX_WAIT \
        or cmd.type == _walter.ModemCmdType.DATA_TX_WAIT:
            if cmd.state == _walter.ModemCmdState.NEW:
                print('TX:[%s]' % cmd.at_cmd)
                tx_stream.write(cmd.at_cmd)
                if cmd.type == _walter.ModemCmdType.DATA_TX_WAIT:
                    tx_stream.write(b'\n')
                else:
                    tx_stream.write(b'\r\n')
                await tx_stream.drain()
                cmd.attempt = 1
                cmd.attempt_start = time.time()
                cmd.state = _walter.ModemCmdState.PENDING
                return
            else:
                tick_diff = time.time() - cmd.attempt_start
                timed_out = tick_diff >= WALTER_MODEM_CMD_TIMEOUT
                if timed_out or cmd.state == _walter.ModemCmdState.RETRY_AFTER_ERROR:
                    if cmd.attempt >= cmd.max_attempts:
                        if timed_out:
                            await self._finish_queue_cmd(cmd, _walter.ModemState.TIMEOUT)
                        else:
                            await self._finish_queue_cmd(cmd, _walter.ModemState.ERROR)
                    else:
                        print('TX:[%s]' % cmd.at_cmd)
                        tx_stream.write(cmd.at_cmd)
                        if cmd.type == _walter.ModemCmdType.DATA_TX_WAIT:
                            tx_stream.write(b'\n')
                        else:
                            tx_stream.write(b'\r\n')
                        await tx_stream.drain()
                        cmd.attempt += 1
                        cmd.attempt_start = time.time()
                        cmd.state = _walter.ModemCmdState.PENDING
                        return
                else:
                    return

        elif cmd.type == _walter.ModemCmdType.WAIT:
            if cmd.state == _walter.ModemCmdState.NEW:
                cmd.attempt_start = time.time()
                cmd.state = _walter.ModemCmdState.PENDING
                return
            else:
                tick_diff = time.time() - cmd.attempt_start
                if tick_diff >= WALTER_MODEM_CMD_TIMEOUT:
                    await _finish_queue_cmd(cmd, _walter.ModemState.TIMEOUT)
                else:
                    return

    async def _process_queue_rsp(self, tx_stream, cmd, at_rsp):
        """
        Process an AT response from the queue.

        This function is called in the queue processing task when an AT
        response is received from the modem. The function will process the
        response and notify blocked functions or call the correct callbacks.

        :param cmd: The pending command or None when no command is pending.
        :param at_rsp: The AT response.

        :return: None.
        """
        
        result = _walter.ModemState.OK

        if at_rsp.startswith("+CEREG: "):
            ce_reg = int(at_rsp.decode().split(':')[1].split(',')[0])
            self._reg_state = ce_reg
            # TODO: call correct handlers (also still todo in arduino version)

        elif at_rsp.startswith("> "):
            if cmd and cmd.data and cmd.type == _walter.ModemCmdType.DATA_TX_WAIT:
                print('TX:[%s]' % cmd.data)
                tx_stream.write(cmd.data)
                await tx_stream.drain()

        elif at_rsp.startswith("ERROR"):
            if cmd is not None:
                cmd.rsp.type = _walter.ModemRspType.NO_DATA
                cmd.state = _walter.ModemCmdState.RETRY_AFTER_ERROR
            return

        elif at_rsp.startswith("+CME ERROR: "):
            if cmd is not None:
                cme_error = int(at_rsp.decode().split(':')[1].split(',')[0])
                cmd.rsp.type = _walter.ModemRspType.CME_ERROR
                cmd.rsp.cme_error = cme_error
                cmd.state = _walter.ModemCmdState.RETRY_AFTER_ERROR
            return

        elif at_rsp.startswith("+CFUN: "):
            op_state = int(at_rsp.decode().split(':')[1].split(',')[0])
            self._op_state = op_state

            if cmd is None:
                return

            cmd.rsp.type = _walter.ModemRspType.OP_STATE
            cmd.rsp.op_state = self._op_state

        elif at_rsp.startswith("+SQNBANDSEL: "):
            data = at_rsp[len('+SQNBANDSEL: '):]

            # create the array and response type upon reception of the
            # first band selection
            if cmd.rsp.type != _walter.ModemRspType.BANDSET_CFG_SET:
                cmd.rsp.type = _walter.ModemRspType.BANDSET_CFG_SET
                cmd.rsp.band_sel_cfg_set = []

            bsel = _walter.ModemBandSelection()

            if data[0] == '0':
                bsel.rat = _walter.ModemRat.LTEM
            else:
                bsel.rat = _walter.ModemRat.NBIOT;

            # Parse operator name
            bsel.net_operator.format = _walter.ModemOperatorFormat.LONG_ALPHANUMERIC
            bsel_parts = data[2:].decode().split(',')
            bsel.net_operator.name = bsel_parts[0]

            # Parse configured bands
            # TODO

            cmd.rsp.band_sel_cfg_set.append(bsel)

        elif at_rsp.startswith("+CPIN: "):
            if cmd is None:
                return

            cmd.rsp.type = _walter.ModemRspType.SIM_STATE
            if at_rsp[len('+CPIN: '):] == b'READY':
                cmd.rsp.sim_state = _walter.ModemSimState.READY
            elif at_rsp[len('+CPIN: '):] == b"SIM PIN":
                cmd.rsp.sim_state = _walter.ModemSimState.PIN_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"SIM PUK":
                cmd.rsp.sim_state = _walter.ModemSimState.PUK_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"PH-SIM PIN":
                cmd.rsp.sim_state = _walter.ModemSimState.PHONE_TO_SIM_PIN_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"PH-FSIM PIN":
                cmd.rsp.sim_state = _walter.ModemSimState.PHONE_TO_FIRST_SIM_PIN_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"PH-FSIM PUK":
                cmd.rsp.sim_state = _walter.ModemSimState.PHONE_TO_FIRST_SIM_PUK_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"SIM PIN2":
                cmd.rsp.sim_state = _walter.ModemSimState.PIN2_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"SIM PUK2":
                cmd.rsp.sim_state = _walter.ModemSimState.PUK2_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"PH-NET PIN":
                cmd.rsp.sim_state = _walter.ModemSimState.NETWORK_PIN_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"PH-NET PUK":
                cmd.rsp.sim_state = _walter.ModemSimState.NETWORK_PUK_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"PH-NETSUB PIN":
                cmd.rsp.sim_state = _walter.ModemSimState.NETWORK_SUBSET_PIN_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"PH-NETSUB PUK":
                cmd.rsp.sim_state = _walter.ModemSimState.NETWORK_SUBSET_PUK_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"PH-SP PIN":
                cmd.rsp.sim_state = _walter.ModemSimState.SERVICE_PROVIDER_PIN_REQUIRED
            elif at_rsp[len('+CPIN: '):] == b"PH-SP PUK":
                cmd.rsp.sim_state = _walter.ModemSimState.SERVICE_PROVIDER_PUK_REQUIRED 
            elif at_rsp[len('+CPIN: '):] == b"PH-CORP PIN":
                cmd.rsp.sim_state = _walter.ModemSimState.CORPORATE_SIM_REQUIRED 
            elif at_rsp[len('+CPIN: '):] == b"PH-CORP PUK":
                cmd.rsp.sim_state = _walter.ModemSimState.CORPORATE_PUK_REQUIRED 
            else:
                cmd.rsp.type = _walter.ModemRspType.NO_DATA

        elif at_rsp.startswith("+CGPADDR: "):
            if not cmd:
                return

            cmd.rsp.type = _walter.ModemRspType.PDP_ADDR 
            cmd.rsp.pdp_address_list = []

            parts = at_rsp.decode().split(',')
            
            context_id = int(parts[0][len('+CGPADDR: '):])
            if len(parts) > 1 and parts[1]:
                cmd.rsp.pdp_address_list.append(parts[1][1:-1])
            if len(parts) > 2 and parts[2]:
                cmd.rsp.pdp_address_list.append(parts[2][1:-1])

        elif at_rsp.startswith("+CCLK: "):
            if not cmd:
                return

            cmd.rsp.type = _walter.ModemRspType.CLOCK
            time_str = at_rsp[len('+CCLK: '):].decode()[1:-1]   # strip double quotes
            cmd.rsp.clock = parse_cclk_time(time_str)

        elif at_rsp.startswith("<<<"):      # <<< is start of SQNHTTPRCV answer
            if self._http_current_profile >= WALTER_MODEM_MAX_HTTP_PROFILES or self._http_context_set[self._http_current_profile].state != _walter.ModemHttpContextState.GOT_RING:
                result = _walter.ModemState.ERROR
            else:
                if not cmd:
                    return

                cmd.rsp.type = _walter.ModemRspType.HTTP_RESPONSE
                cmd.rsp.http_response = _walter.ModemHttpResponse()
                cmd.rsp.http_response.http_status = self._http_context_set[self._http_current_profile].http_status
                cmd.rsp.http_response.data = at_rsp[3:]         # skip <<<

                # the complete handler will reset the state,
                # even if we never received <<< but got an error instead

        elif at_rsp.startswith("+SQNHTTPRING: "):
            profile_id_str, http_status_str, content_type, content_length_str = at_rsp[len("+SQNHTTPRING: "):].decode().split(',')
            profile_id = int(profile_id_str)
            http_status = int(http_status)
            content_length = int(content_length_str)

            if profile_id >= WALTER_MODEM_MAX_HTTP_PROFILES:
                # TODO: return error if modem returns invalid profile id.
                # problem: this message is an URC: the associated cmd
                # may be any random command currently executing */
                return

            # TODO: if not expecting a ring, it may be a bug in the modem
            # or at our side and we should report an error + read the
            # content to free the modem buffer
            # (knowing that this is a URC so there is no command
            # to give feedback to)
            if self._http_context_set[profile_id].state != _walter.ModemHttpContextState.EXPECT_RING:
                return

            # remember ring info
            self._http_context_set[profile_id].state = _walter.ModemHttpContextState.GOT_RING
            self._http_context_set[profile_id].http_status = http_status
            if self._http_context_set[profile_id].content_type:
                self._http_context_set[profile_id].content_type = content_type
            self._http_context_set[profile_id].content_length = content_length

        elif at_rsp.startswith("+SQNHTTPCONNECT: "):
            profile_id_str, result_code_str = at_rsp[len("+SQNHTTPCONNECT: "):].decode().split(',')
            profile_id = int(profile_id_str)
            result_code = int(result_code_str)

            if profile_id < WALTER_MODEM_MAX_HTTP_PROFILES:
                if result_code == 0:
                    self._http_context_set[profile_id].connected = True
                else:
                    self._http_context_set[profile_id].connected = False

        elif at_rsp.startswith("+SQNHTTPDISCONNECT: "):
            profile_id = int(at_rsp[len("+SQNHTTPDISCONNECT: "):].decode())

            if profile_id < WALTER_MODEM_MAX_HTTP_PROFILES:
                self._http_context_set[profile_id].connected = False

        elif at_rsp.startswith("+SQNHTTPSH: "):
            profile_id = int(at_rsp[len('+SQNHTTPSH: '):].decode())

            if profile_id < WALTER_MODEM_MAX_HTTP_PROFILES:
                self._http_context_set[profile_id].connected = False

        elif at_rsp.startswith("+SQNSH: "):
            socket_id = int(at_rsp[len('+SQNSH: '):].decode())
            try:
                _socket = self._socket_set[socket_id - 1]
            except:
                return

            self._socket = _socket
            _socket.state = _walter.ModemSocketState.FREE

        elif at_rsp.startswith("+LPGNSSFIXREADY: "):
            data = at_rsp[len("+LPGNSSFIXREADY: "):]

            parenthesis_open = False
            part_no = 0;
            start_pos = 0
            part = ''
            gnss_fix = _walter.ModemGNSSFix()

            for character_pos in range(len(data)):
                character = data[character_pos]
                part_complete = False

                if character == ord(',') and not parenthesis_open:
                    part = data[start_pos:character_pos]
                    part_complete = True;
                elif character == ord('('):
                    parenthesis_open = True
                elif character == ord(')'):
                    parenthesis_open = False
                elif character_pos + 1 == len(data):
                    part = data[start_pos:character_pos + 1]
                    part_complete = True

                if part_complete:
                    if part_no == 0:
                        gnss_fix.fix_id = int(part)
                    elif part_no == 1:
                        gnss_fix.timestamp = parse_gnss_time(part)
                    elif part_no == 2:
                        gnss_fix.time_to_fix = int(part)
                    elif part_no == 3:
                        gnss_fix.estimated_confidence = float(part)
                    elif part_no == 4:
                        gnss_fix.latitude = float(part)
                    elif part_no == 5:
                        gnss_fix.longitude = float(part)
                    elif part_no == 6:
                        gnss_fix.height = float(part)
                    elif part_no == 7:
                        gnss_fix.north_speed = float(part)
                    elif part_no == 8:
                        gnss_fix.east_speed = float(part)
                    elif part_no == 9:
                        gnss_fix.down_speed = float(part)
                    elif part_no == 10:
                         # Raw satellite signal sample is ignored
                        pass
                    else:
                        satellite_data = part.decode().split(',')

                        # Iterate through the satellite_data list, taking every two elements as pairs
                        for i in range(0, len(satellite_data), 2):
                            sat_no_str = satellite_data[i]
                            sat_sig_str = satellite_data[i + 1]

                            gnss_fix.sats.append(_walter.ModemGNSSSat(int(sat_no_str), int(sat_sig_str)))

                    # +2 for the comma and trailing space
                    part_no += 1;
                    start_pos = character_pos + 2
                    part = ''

            # notify every coroutine that is waiting for a fix
            async with self._gnss_fix_lock:
                for gnss_fix_waiter in self._gnss_fix_waiters:
                    gnss_fix_waiter.gnss_fix = gnss_fix
                    gnss_fix_waiter.event.set()

                self._gnss_fix_waiters = []

        elif at_rsp.startswith("+LPGNSSASSISTANCE: "):
            if not cmd:
                return

            if cmd.rsp.type != _walter.ModemRspType.GNSS_ASSISTANCE_DATA:
                cmd.rsp.type = _walter.ModemRspType.GNSS_ASSISTANCE_DATA
                cmd.rsp.gnss_assistance = _walter.ModemGNSSAssistance()

            data = at_rsp[len("+LPGNSSASSISTANCE: "):]
            part_no = 0;
            start_pos = 0
            part = ''
            gnss_details = None

            for character_pos in range(len(data)):
                character = data[character_pos]
                part_complete = False

                if character == ord(','):
                    part = data[start_pos:character_pos]
                    part_complete = True;
                elif character_pos + 1 == len(data):
                    part = data[start_pos:character_pos + 1]
                    part_complete = True

                if part_complete:
                    if part_no == 0:
                        if part[0] == ord('0'):
                            gnss_details = cmd.rsp.gnss_assistance.almanac
                        elif part[0] == ord('1'):
                            gnss_details = cmd.rsp.gnss_assistance.ephemeris
                    elif part_no == 1:
                        if gnss_details:
                            gnss_details.available = part[0] == ord('1')
                    elif part_no == 2:
                        if gnss_details:
                            gnss_details.last_update = int(part)
                    elif part_no == 3:
                        if gnss_details:
                            gnss_details.time_to_update = int(part)
                    elif part_no == 4:
                        if gnss_details:
                            gnss_details.time_to_expire = int(part)

                    # +2 for the comma and trailing space
                    part_no += 1;
                    start_pos = character_pos + 2
                    part = ''
                

#        if cmd:
#            print('process rsp to cmd:' + str(cmd) + ' ' + str(cmd.at_cmd) + ' ' + str(at_rsp) + ' expecting ' + str(cmd.at_rsp))
#        else:
#            print('process rsp without preceding cmd: ' + str(at_rsp))

        if not cmd or not cmd.at_rsp or cmd.type == _walter.ModemCmdType.TX or cmd.at_rsp != at_rsp:
            return

        await self._finish_queue_cmd(cmd, result)

    async def _queue_worker(self):
        tx_stream = uasyncio.StreamWriter(self._uart, {})
        cur_cmd = None

        while True:
            if not cur_cmd and not self._command_queue.empty():
                qitem = _walter.ModemTaskQueueItem()
                qitem.cmd = await self._command_queue.get()
            else:
                qitem = await self._task_queue.get()
                if type(qitem) != _walter.ModemTaskQueueItem:
                    print('Invalid task queue item: %s %s' % (type(qitem), str(qitem)))
                    continue

            # process or enqueue new command or response
            if qitem.cmd:
                if not cur_cmd:
                    cur_cmd = qitem.cmd
                else:
                    await self._command_queue.put(qitem.cmd)
            elif qitem.rsp:
                await self._process_queue_rsp(tx_stream, cur_cmd, qitem.rsp);

            # initial transmit of cmd + retransmits after timeout
            if cur_cmd:
                if cur_cmd.state == _walter.ModemCmdState.RETRY_AFTER_ERROR \
                or cur_cmd.state == _walter.ModemCmdState.NEW \
                or cur_cmd.state == _walter.ModemCmdState.PENDING:
                    await self._process_queue_cmd(tx_stream, cur_cmd)

                if cur_cmd.state == _walter.ModemCmdState.COMPLETE:
                    cur_cmd = None

    async def _run_cmd(self, at_cmd, at_rsp, data,
            complete_handler, complete_handler_arg,
            cmd_type, max_attempts):
        """Add a command to the command queue and await execution.
        
        This function add a command to the task queue. This function will 
        only fail when the command queue is full. The command which is put
        onto the queue will automatically get the WALTER_MODEM_CMD_STATE_NEW
        state. This function will never call any callbacks.
        
        :param at_cmd: NULL terminated array of command elements. The elements
        must stay available until the command is complete. The array is only
        shallow copied.
        :param at_rsp: The expected AT response.
        :param data: The extra data to be sent to the modem
        :param complete_handler: Optional complete handler function.
        :param complete_handler_arg: Optional argument for the complete handler.
        :param cmd_type: The type of queue AT command.
        :param max_attempts: The maximum number of retries for this command.
        
        :returns: Pointer to the command on success, NULL when no memory for
        the command was available.
        """
        cmd = _walter.ModemCmd()

        cmd.at_cmd = at_cmd
        cmd.at_rsp = at_rsp
        cmd.rsp = _walter.ModemRsp()
        cmd.type = cmd_type
        cmd.data = data
        cmd.complete_handler = complete_handler
        cmd.complete_handler_arg = complete_handler_arg
        cmd.max_attempts = max_attempts
        cmd.state = _walter.ModemCmdState.NEW
        cmd.attempt = 0
        cmd.attempt_start = 0

        qitem = _walter.ModemTaskQueueItem()
        qitem.cmd = cmd
        await self._task_queue.put(qitem)

        # we expect the queue runner to release the (b)lock.
        await cmd.event.wait()
        return cmd.rsp

    def begin(self, main_function=None):
        self._uart = UART(2, baudrate=WALTER_MODEM_BAUD, bits=8, parity=None, stop=1, \
                flow=UART.RTS|UART.CTS, tx=WALTER_MODEM_PIN_TX, \
                rx=WALTER_MODEM_PIN_RX, cts=WALTER_MODEM_PIN_CTS, \
                rts=WALTER_MODEM_PIN_RTS, timeout=0, timeout_char=0, \
                txbuf=2048, rxbuf=2048)

        self._task_queue = Queue()
        self._command_queue = Queue()

        uasyncio.run(self.reset())
        uasyncio.run(self.config_cme_error_reports(_walter.ModemCMEErrorReportsType.NUMERIC))
        uasyncio.run(self.config_cereg_reports(_walter.ModemCEREGReportsType.ENABLED))

        uasyncio.run(self.runner(main_function))

    async def runner(self, main_function):
        reader_task = uasyncio.create_task(self._uart_reader())
        worker_task = uasyncio.create_task(self._queue_worker())
        user_task = uasyncio.create_task(main_function())

        await reader_task
        await worker_task
        await user_task

    ### FIXME: remove tester - but it still comes in handy for a while for porting the arduino examples
    async def tester(self):
        uasyncio.create_task(self._uart_reader())
        uasyncio.create_task(self._queue_worker())

        # init modem state
        await self.reset()
        await self.config_cme_error_reports(_walter.ModemCMEErrorReportsType.NUMERIC)
        await self.config_cereg_reports(_walter.ModemCEREGReportsType.ENABLED)

        # TODO: onderstaande aan gebruiker overlaten
        # en er een aparte vrij te gebruiken publieke method van maken
        # en in run hier alleen nog de taak van queue_worker inline uitvoeren.
        # dan kan gebruiker ofwel uasyncio.run(modem.run())
        # ofwel eigen runner met create_task van modem.run
        # naast eigen task en/of andere await code in eigen runner
        # of zelfs rechtstreeks de aangeboden debugger async method.

        while True:
            list = uselect.select([sys.stdin], [], [], 0.01)
            if list[0]:
                at_cmd = input('enter command:')

                if at_cmd == 'rst':
                    rsp = await self.reset()
                elif at_cmd == 'cc':
                    rsp = await self.check_comm()
                elif at_cmd[:4] == 'cmee':
                    rsp = await self.config_cme_error_reports(int(at_cmd[4:]))
                elif at_cmd[:5] == 'cereg':
                    rsp = await self.config_cereg_reports(int(at_cmd[5:]))
                elif at_cmd == 'getreg':
                    rsp = self.get_network_reg_state()
                elif at_cmd[:4] == 'cfun':
                    if len(at_cmd) > 4:
                        rsp = await self.set_op_state(int(at_cmd[4:]))
                    else:
                        rsp = await self.get_op_state()
                elif at_cmd == "radio":
                    rsp = await self.get_radio_bands()
                elif at_cmd == "simS":
                    rsp = await self.get_sim_state()
                elif at_cmd == "simU":
                    rsp = await self.unlock_sim(None)
                elif at_cmd == "snsm":
                    rsp = await self.set_network_selection_mode(
                        _walter.ModemNetworkSelMode.AUTOMATIC, None,
                        _walter.ModemOperatorFormat.LONG_ALPHANUMERIC)
                elif at_cmd == "cPdp":
                    rsp = await self.create_PDP_context(None,
                        _walter.ModemPDPAuthProtocol.NONE, None, None,
                        _walter.ModemPDPType.IP, None,
                        _walter.ModemPDPHeaderCompression.OFF,
                        _walter.ModemPDPDataCompression.OFF,
                        _walter.ModemPDPIPv4AddrAllocMethod.DHCP,
                        _walter.ModemPDPRequestType.NEW_OR_HANDOVER,
                        _walter.ModemPDPPCSCFDiscoveryMethod.AUTO, False, True,
                        False, False, False, False)
                elif at_cmd == "aPdp":
                    rsp = await self.authenticate_PDP_context(1)
                elif at_cmd == "pdpA":
                    rsp = await self.set_PDP_context_active(True, 1)
                elif at_cmd == "pAtt":
                    rsp = await self.attach_PDP_context(True)
                elif at_cmd == "pdp@":
                    rsp = await self.get_PDP_address(1)
                elif at_cmd == "clk":
                    rsp = await self.get_clock()
                elif at_cmd == "sock1":
                    rsp = await self.create_socket(1, 300, 90, 60, 5000)
                elif at_cmd == "sock2":
                    rsp = await self.config_socket(1)
                elif at_cmd == "sock3":
                    rsp = await self.connect_socket("coap.bluecherry.io", 65535,
                            0, _walter.ModemSocketProto.UDP,
                            _walter.ModemSocketAcceptAnyRemote.DISABLED, 1)
                elif at_cmd == "sock4":
                    rsp = await self.socket_send('test', _walter.ModemRai.NO_INFO, 1)
                elif at_cmd == "sock0":
                    rsp = await self.close_socket(1)
                elif at_cmd == "config_gnss":
                    rsp = await self.config_gnss(
                            _walter.ModemGNSSSensMode.HIGH,
                            _walter.ModemGNSSAcqMode.COLD_WARM_START,
                            _walter.ModemGNSSLocMode.ON_DEVICE_LOCATION)
                elif at_cmd == "get_gnss":
                    rsp = await self.get_gnss_assistance_status()
                elif at_cmd == "update_gnss":
                    rsp = await self.update_gnss_assistance(_walter.ModemGNSSAssistanceType.ALMANAC)
                elif at_cmd == "gnss_action":
                    rsp = await self.perform_gnss_action(_walter.ModemGNSSAction.GET_SINGLE_FIX)
                elif at_cmd == "wait_gnss":
                    rsp = await self.wait_for_gnss_fix()
                else:
                    rsp = None
                    print('unrecognized command: [%s]' % at_cmd)

                if not rsp:
                    print('no or invalid response')
                else:
                    print('RESPONSE type=%d' % rsp.type)

                    if rsp.type == _walter.ModemRspType.NO_DATA:
                        print('no_data')
                    elif rsp.type == _walter.ModemRspType.REG_STATE:
                        print('reg_state=%d' % rsp.reg_state)
                    elif rsp.type == _walter.ModemRspType.BANDSET_CFG_SET:
                        for band_sel in rsp.band_sel_cfg_set:
                            print('rat=%d net_operator.name=[%s]' %
                                (band_sel.rat, band_sel.net_operator.name))
                    elif rsp.type == _walter.ModemRspType.CME_ERROR:
                        print('cme_error=%d' % rsp.cme_error)
                    elif rsp.type == _walter.ModemRspType.OP_STATE:
                        print('op_state=%d' % rsp.op_state)
                    elif rsp.type == _walter.ModemRspType.SIM_STATE:
                        print('sim_state=%d' % rsp.sim_state)
                    elif rsp.type == _walter.ModemRspType.PDP_CTX_ID:
                        print('pdp_ctx_id=%d' % rsp.pdp_ctx_id)
                    elif rsp.type == _walter.ModemRspType.SOCKET_ID:
                        print('socket_id=%d' % rsp.socket_id)
                    elif rsp.type == _walter.ModemRspType.PDP_ADDR:
                        for addr in rsp.pdp_address_list:
                            print('[%s]' % addr)
                    elif rsp.type == _walter.ModemRspType.CLOCK:
                        print('clock=%s' % rsp.clock)
                    elif rsp.type == _walter.ModemRspType.GNSS_ASSISTANCE_DATA:
                        print('gnss assistance almanac: available=%d last_update=%d time_to_update=%d time_to_expire=%d' %
                              (rsp.gnss_assistance.almanac.available,
                               rsp.gnss_assistance.almanac.last_update,
                               rsp.gnss_assistance.almanac.time_to_update,
                               rsp.gnss_assistance.almanac.time_to_expire))
                        print('gnss assistance ephemeris: available=%d last_update=%d time_to_update=%d time_to_expire=%d' %
                              (rsp.gnss_assistance.almanac.available,
                               rsp.gnss_assistance.almanac.last_update,
                               rsp.gnss_assistance.almanac.time_to_update,
                               rsp.gnss_assistance.almanac.time_to_expire))

                    print('READY. (%d)' % rsp.result)

            await uasyncio.sleep(1)

        # of anders 'wachten' tot tasks klaar zijn:
        #await task1
        #await task2

        # of beter: dit toepassen:
        # https://github.com/peterhinch/micropython-async/blob/master/v3/docs/TUTORIAL.md#224-a-typical-firmware-app

    async def reset(self):
        reset_pin = Pin(WALTER_MODEM_PIN_RESET, Pin.OUT)
        reset_pin.off()
        time.sleep(.01)
        reset_pin.on()

        return await self._run_cmd('', b'+SYSSTART', None,
                None, None,
                _walter.ModemCmdType.WAIT,
                WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def check_comm(self):
        return await self._run_cmd('AT', b'OK', None,
                None, None,
                _walter.ModemCmdType.TX_WAIT,
                WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def config_cme_error_reports(self, reports_type = _walter.ModemCMEErrorReportsType.NUMERIC):
        return await self._run_cmd('AT+CMEE=%d' % reports_type, b'OK', None,
               None, None,
               _walter.ModemCmdType.TX_WAIT,
               WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def config_cereg_reports(self, reports_type = _walter.ModemCEREGReportsType.ENABLED):
        return await self._run_cmd('AT+CEREG=%d' % reports_type, b'OK', None,
                None, None,
                _walter.ModemCmdType.TX_WAIT,
                WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    def get_network_reg_state(self):
        rsp = _walter.ModemRsp()

        rsp.result = _walter.ModemState.OK
        rsp.type = _walter.ModemRspType.REG_STATE
        rsp.reg_state = self._reg_state

        return rsp

    async def get_op_state(self):
        return await self._run_cmd('AT+CFUN?', b'OK', None,
                None, None,
                _walter.ModemCmdType.TX_WAIT,
                WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)
        
    async def set_op_state(self, op_state):
        return await self._run_cmd('AT+CFUN={}'.format(op_state), b'OK', None,
                None, None,
                _walter.ModemCmdType.TX_WAIT,
                WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)
        
    async def get_radio_bands(self):
        return await self._run_cmd("AT+SQNBANDSEL?", b"OK", None,
            None, None,
            _walter.ModemCmdType.TX_WAIT,
            WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def get_sim_state(self):
        return await self._run_cmd("AT+CPIN?", b"OK", None,
            None, None,
            _walter.ModemCmdType.TX_WAIT,
            WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def unlock_sim(self, pin = None):
        self._simPIN = pin;
        if self._simPIN == None:
            return await self.get_sim_state()
        
        return await self._run_cmd("AT+CPIN=%s" % pin, b"OK", None,
            None, None,
            _walter.ModemCmdType.TX_WAIT,
            WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def set_network_selection_mode(self, mode = _walter.ModemNetworkSelMode.AUTOMATIC, operator_name = '', format = _walter.ModemOperatorFormat.LONG_ALPHANUMERIC):
        self._network_sel_mode = mode;
        self._operator.format = format;
        self._operator.name = operator_name

        if mode == _walter.ModemNetworkSelMode.AUTOMATIC:
            return await self._run_cmd("AT+COPS=%d" % mode, b"OK", None,
                None, None,
                _walter.ModemCmdType.TX_WAIT,
                WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)
        else:
            return await self._run_cmd("AT+COPS={},{},{}".format(
                self._network_sel_mode, self._operator.format,
                modem_string(self._operator.name)), b"OK", None,
                None, None,
                _walter.ModemCmdType.TX_WAIT,
                WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def create_PDP_context(self, apn = None, auth_proto = _walter.ModemPDPAuthProtocol.NONE,
                auth_user = None, auth_pass = None, auth_type = _walter.ModemPDPType.IP,
                pdp_address = None, header_comp = _walter.ModemPDPHeaderCompression.OFF,
                data_comp = _walter.ModemPDPDataCompression.OFF,
                ipv4_alloc_method = _walter.ModemPDPIPv4AddrAllocMethod.DHCP,
                request_type = _walter.ModemPDPRequestType.NEW_OR_HANDOVER,
                pcscf_method = _walter.ModemPDPPCSCFDiscoveryMethod.AUTO,
                for_IMCN = False, use_NSLPI = True, use_secure_PCO = False,
                use_NAS_ipv4_MTU_discovery = False,
                use_local_addr_ind = False, use_NAS_on_IPMTU_discovery = False):
        _ctx = None
        for idx, ctx in enumerate(self._pdp_ctx_set):
            if ctx.state == _walter.ModemPDPContextState.FREE:
                ctx.state = _walter.ModemPDPContextState.RESERVED
                _ctx = ctx
                break

        if _ctx == None:
            rsp = _walter.ModemRsp()
            rsp.result = _walter.ModemState.NO_FREE_PDP_CONTEXT
            rsp.auth_type = _walter.ModemRspType.NO_DATA
            return rsp
        
        self._pdp_ctx = _ctx
        
        _ctx.type = auth_type
        _ctx.apn = apn
        _ctx.pdp_address = pdp_address
        _ctx.header_comp = header_comp
        _ctx.data_comp = data_comp
        _ctx.ipv4_alloc_method = ipv4_alloc_method
        _ctx.request_type = request_type
        _ctx.pcscf_method = pcscf_method
        _ctx.for_IMCN = for_IMCN
        _ctx.use_NSLPI = use_NSLPI
        _ctx.use_secure_PCO  = use_secure_PCO
        _ctx.use_NAS_ipv4_MTU_discovery = use_NAS_ipv4_MTU_discovery
        _ctx.use_local_addr_ind = use_local_addr_ind
        _ctx.use_NAS_non_IPMTU_discovery = use_NAS_on_IPMTU_discovery
        _ctx.auth_proto = auth_proto
        _ctx.auth_user = auth_user
        _ctx.auth_pass = auth_pass
        
        async def complete_handler(result, rsp, complete_handler_arg):
            ctx = complete_handler_arg
            rsp.type = _walter.ModemRspType.PDP_CTX_ID
            rsp.pdp_ctx_id = _ctx.id

            if result == _walter.ModemState.OK:
                ctx.state = _walter.ModemPDPContextState.INACTIVE

        return await self._run_cmd("AT+CGDCONT={},{},{},{},{},{},{},{},{},{},{},{},{},{},{}".format(
            _ctx.id, pdp_type_as_string(_ctx.type), modem_string(_ctx.apn),
            modem_string(_ctx.pdp_address), _ctx.data_comp,
            _ctx.header_comp, _ctx.ipv4_alloc_method, _ctx.request_type,
            _ctx.pcscf_method, modem_bool(_ctx.for_IMCN),
            modem_bool(_ctx.use_NSLPI), modem_bool(_ctx.use_secure_PCO),
            modem_bool(_ctx.use_NAS_ipv4_MTU_discovery),
            modem_bool(_ctx.use_local_addr_ind),
            modem_bool(_ctx.use_NAS_non_IPMTU_discovery)),
            b"OK", None,
            complete_handler, _ctx,
            _walter.ModemCmdType.TX_WAIT,
            WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def authenticate_PDP_context(self, context_id = None):
        try:
            _ctx = self._pdp_ctx_set[context_id - 1]
        except:
            rsp = _walter.ModemRsp()
            rsp.result = _walter.ModemState.NO_SUCH_PDP_CONTEXT
            rsp.type = _walter.ModemRspType.NO_DATA
            return rsp
        
        self._pdp_ctx = _ctx

        if _ctx.auth_proto == _walter.ModemPDPAuthProtocol.NONE:
            rsp = _walter.ModemRsp()
            rsp.result = _walter.ModemState.OK
            rsp.type = _walter.ModemRspType.NO_DATA
            return rsp

        return await self._run_cmd("AT+CGAUTH={},{},{},{}".format(
            _ctx.id, _ctx.auth_proto, modem_string(_ctx.auth_user),
            modem_string(_ctx.auth_pass)),
            b"OK", None,
            None, None,
            _walter.ModemCmdType.TX_WAIT,
            WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def set_PDP_context_active(self, active = True, context_id = -1):
        try:
            _ctx = self._pdp_ctx_set[context_id - 1]
        except:
            rsp = _walter.ModemRsp()
            rsp.result = _walter.ModemState.NO_SUCH_PDP_CONTEXT
            rsp.type = _walter.ModemRspType.NO_DATA
            return rsp
        
        self._pdp_ctx = _ctx

        async def complete_handler(result, rsp, complete_handler_arg):
            ctx = complete_handler_arg
            if result == _walter.ModemState.OK:
                # TODO (cf arduino): set all other PDP contexts inactive
                ctx.state = _walter.ModemPDPContextState.ACTIVE

        return await self._run_cmd("AT+CGACT={},{}".format(
            _ctx.id, modem_bool(active)),
            b"OK", None,
            complete_handler, _ctx,
            _walter.ModemCmdType.TX_WAIT,
            WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def attach_PDP_context(self, attached = True):
        async def complete_handler(result, rsp, complete_handler_arg):
            if result == _walter.ModemState.OK:
                if self._pdp_ctx:
                    self._pdp_ctx.state = _walter.ModemPDPContextState.ATTACHED

        return await self._run_cmd("AT+CGATT={}".format(
            modem_bool(attached)),
            b"OK", None,
            complete_handler, None,
            _walter.ModemCmdType.TX_WAIT,
            WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def get_PDP_address(self, context_id = -1):
        try:
            _ctx = self._pdp_ctx_set[context_id - 1]
        except:
            rsp = _walter.ModemRsp()
            rsp.result = _walter.ModemState.NO_SUCH_PDP_CONTEXT
            rsp.type = _walter.ModemRspType.NO_DATA
            return rsp
        
        self._pdp_ctx = _ctx

        return await self._run_cmd("AT+CGPADDR={}".format(_ctx.id),
            b"OK", None,
            None, None,
            _walter.ModemCmdType.TX_WAIT,
            WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def create_socket(self, pdp_context_id = -1, mtu = 300, exchange_timeout = 90,
            conn_timeout = 60, send_delay_ms = 5000):
        try:
            _ctx = self._pdp_ctx_set[pdp_context_id - 1]
        except:
            rsp = _walter.ModemRsp()
            rsp.result = _walter.ModemState.NO_SUCH_PDP_CONTEXT
            rsp.type = _walter.ModemRspType.NO_DATA
            return rsp
        
        self._pdp_ctx = _ctx

        _socket = None
        for socket in self._socket_set:
            if socket.state == _walter.ModemSocketState.FREE:
                socket.state = _walter.ModemSocketState.RESERVED
                _socket = socket
                break

        if _socket == None:
            rsp = _walter.ModemRsp()
            rsp.result = _walter.ModemState.NO_FREE_SOCKET
            rsp.type = _walter.ModemRspType.NO_DATA
            return rsp

        self._socket = _socket

        _socket.pdp_context_id = _ctx.id
        _socket.mtu = mtu
        _socket.exchange_timeout = exchange_timeout
        _socket.conn_timeout = conn_timeout
        _socket.send_delay_ms = send_delay_ms

        async def complete_handler(result, rsp, complete_handler_arg):
            sock = complete_handler_arg
            rsp.type = _walter.ModemRspType.SOCKET_ID
            rsp.socket_id = _socket.id

            if result == _walter.ModemState.OK:
                sock.state = _walter.ModemSocketState.CREATED

        return await self._run_cmd("AT+SQNSCFG={},{},{},{},{},{}".format(
            _socket.id, _ctx.id, _socket.mtu, _socket.exchange_timeout,
            _socket.conn_timeout * 10, _socket.send_delay_ms // 100),
            b"OK", None,
            complete_handler, _socket,
            _walter.ModemCmdType.TX_WAIT,
            WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def config_socket(self, socket_id = -1):
        try:
            _socket = self._socket_set[socket_id - 1]
        except:
            rsp = _walter.ModemRsp()
            rsp.result = _walter.ModemState.NO_SUCH_SOCKET
            rsp.type = _walter.ModemRspType.NO_DATA
            return rsp
        
        self._socket = _socket

        async def complete_handler(result, rsp, complete_handler_arg):
            sock = complete_handler_arg

            if result == _walter.ModemState.OK:
                sock.state = _walter.ModemSocketState.CONFIGURED

        return await self._run_cmd("AT+SQNSCFGEXT={},2,0,0,0,0,0".format(
            _socket.id),
            b"OK", None,
            complete_handler, _socket,
            _walter.ModemCmdType.TX_WAIT,
            WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def connect_socket(self, remote_host, remote_port,
            local_port = 0, protocol = _walter.ModemSocketProto.UDP,
            accept_any_remote = _walter.ModemSocketAcceptAnyRemote.DISABLED , socket_id = -1):
        try:
            _socket = self._socket_set[socket_id - 1]
        except:
            rsp = _walter.ModemRsp()
            rsp.result = _walter.ModemState.NO_SUCH_SOCKET
            rsp.type = _walter.ModemRspType.NO_DATA
            return rsp
        
        self._socket = _socket

        _socket.protocol = protocol
        _socket.accept_any_remote = accept_any_remote
        _socket.remote_host = remote_host
        _socket.remote_port = remote_port
        _socket.local_port = local_port

        async def complete_handler(result, rsp, complete_handler_arg):
            sock = complete_handler_arg

            if result == _walter.ModemState.OK:
                sock.state = _walter.ModemSocketState.OPENED

        return await self._run_cmd("AT+SQNSD={},{},{},{},0,{},1,{},0".format(
            _socket.id, _socket.protocol, _socket.remote_port,
            modem_string(_socket.remote_host), _socket.local_port,
            _socket.accept_any_remote),
            b"OK", None,
            complete_handler, _socket,
            _walter.ModemCmdType.TX_WAIT,
            WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def close_socket(self, socket_id = -1):
        try:
            _socket = self._socket_set[socket_id - 1]
        except:
            rsp = _walter.ModemRsp()
            rsp.result = _walter.ModemState.NO_SUCH_SOCKET
            rsp.type = _walter.ModemRspType.NO_DATA
            return rsp
        
        self._socket = _socket

        async def complete_handler(result, rsp, complete_handler_arg):
            sock = complete_handler_arg

            if result == _walter.ModemState.OK:
                sock.state = _walter.ModemSocketState.FREE

        return await self._run_cmd("AT+SQNSH={}".format(_socket.id),
            b"OK", None,
            complete_handler, _socket,
            _walter.ModemCmdType.TX_WAIT,
            WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def socket_send(self, data, rai = _walter.ModemRai.NO_INFO, socket_id = -1):
        try:
            _socket = self._socket_set[socket_id - 1]
        except:
            rsp = _walter.ModemRsp()
            rsp.result = _walter.ModemState.NO_SUCH_SOCKET
            rsp.type = _walter.ModemRspType.NO_DATA
            return rsp
        
        self._socket = _socket

        return await self._run_cmd("AT+SQNSSENDEXT={},{},{}".format(
            _socket.id, len(data), rai),
            b"OK", data,
            None, None,
            _walter.ModemCmdType.DATA_TX_WAIT,
            WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def get_clock(self):
        return await self._run_cmd('AT+CCLK?', b'OK', None,
                None, None,
                _walter.ModemCmdType.TX_WAIT,
                WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def config_gnss(self, sens_mode = _walter.ModemGNSSSensMode.HIGH, acq_mode = _walter.ModemGNSSAcqMode.COLD_WARM_START, loc_mode = _walter.ModemGNSSLocMode.ON_DEVICE_LOCATION):
        return await self._run_cmd("AT+LPGNSSCFG=%d,%d,2,,1,%d" %
                                   (loc_mode, sens_mode, acq_mode),
                                   b"OK", None,
                                   None, None,
                                   _walter.ModemCmdType.TX_WAIT,
                                   WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def get_gnss_assistance_status(self):
        return await self._run_cmd("AT+LPGNSSASSISTANCE?",
                                   b"OK", None,
                                   None, None,
                                   _walter.ModemCmdType.TX_WAIT,
                                   WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def update_gnss_assistance(self, ass_type = _walter.ModemGNSSAssistanceType.REALTIME_EPHEMERIS ):
        if ass_type == _walter.ModemGNSSAssistanceType.ALMANAC:
            expect_string = b"+LPGNSSASSISTANCE:0"
        elif ass_type == _walter.ModemGNSSAssistanceType.REALTIME_EPHEMERIS:
            expect_string = b"+LPGNSSASSISTANCE:1"
        else:
            expect_string = b"OK"

        return await self._run_cmd("AT+LPGNSSASSISTANCE=%d" % ass_type,
                                   expect_string, None,
                                   None, None,
                                   _walter.ModemCmdType.TX_WAIT,
                                   WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def perform_gnss_action(self, action = _walter.ModemGNSSAction.GET_SINGLE_FIX):
        if action == _walter.ModemGNSSAction.GET_SINGLE_FIX:
            action_str = "single"
        elif action == _walter.ModemGNSSAction.CANCEL:
            action_str = "stop"
        else:
            action_str = ""

        return await self._run_cmd("AT+LPGNSSFIXPROG=\"%s\"" % action_str,
                                   b"OK", None,
                                   None, None,
                                   _walter.ModemCmdType.TX_WAIT,
                                   WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def wait_for_gnss_fix(self):
        gnss_fix_waiter = _walter.ModemGnssFixWaiter()

        async with self._gnss_fix_lock:
            self._gnss_fix_waiters.append(gnss_fix_waiter)

        await gnss_fix_waiter.event.wait()

        return gnss_fix_waiter.gnss_fix

    async def http_did_ring(self, profile_id):
        if _http_current_profile != 0xff:
            return error_rsp(_walter.ModemState.ERROR)

        if profile_id >= WALTER_MODEM_MAX_HTTP_PROFILES:
            return error_rsp(_walter.ModemState.NO_SUCH_PROFILE)

        if self._http_context_set[profile_id].state == _walter.ModemHttpContextState.IDLE:
            return error_rsp(_walter.ModemState.NOT_EXPECTING_RING)

        if self._http_context_set[profile_id].state == _walter.ModemHttpContextState.EXPECT_RING:
            return error_rsp(_walter.ModemState.AWAITING_RING)

        if self._http_context_set[profile_id].state != _walter.ModemHttpContextState.GOT_RING:
            return error_rsp(_walter.ModemState.ERROR)

        # ok, got ring. http context fields have been filled.
        # http status 0 means: timeout (or also disconnected apparently)
        if self._http_context_set[profile_id].http_status == 0:
            self._http_context_set[profile_id].state = _walter.ModemHttpContextState.IDLE
            return error_rsp(_walter.ModemState.ERROR)

        self._http_current_profile = profile_id;

        async def complete_handler(result, rsp, complete_handler_arg):
            modem = complete_handler_arg
            modem._http_context_set[modem._http_current_profile].state = _walter.ModemHttpContextState.IDLE
            modem._http_current_profile = 0xff

        return await self._run_cmd("AT+SQNHTTPRCV={}".format(profile_id),
            b"<<<", None, complete_handler, self, _walter.ModemCmdType.TX_WAIT,
            WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def http_config_profile(self, profile_id, server_name, port = 80, use_basic_auth = False, auth_user = '', auth_pass = ''):
        if profile_id >= WALTER_MODEM_MAX_HTTP_PROFILES:
            return error_rsp(_walter.ModemState.NO_SUCH_PROFILE)

        return await self._run_cmd("AT+SQNHTTPCFG={},{},{},{},\"{}\",\"{}\"".format(profile_id, modem_string(server_name), port, modem_bool(use_basic_auth), auth_user, auth_pass),
            b"OK", None, None, None, _walter.ModemCmdType.TX_WAIT,
            WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def http_connect(self, profile_id):
        if profile_id >= WALTER_MODEM_MAX_HTTP_PROFILES:
            return error_rsp(_walter.ModemState.NO_SUCH_PROFILE)

        return await self._run_cmd("AT+SQNHTTPCONNECT={}".format(profile_id),
            b"OK", None, None, None, _walter.ModemCmdType.TX_WAIT,
            WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    async def http_close(self, profile_id):
        if profile_id >= WALTER_MODEM_MAX_HTTP_PROFILES:
            return error_rsp(_walter.ModemState.NO_SUCH_PROFILE)

        return await self._run_cmd("AT+SQNHTTPDISCONNECT={}".format(profile_id),
            b"OK", None, None, None, _walter.ModemCmdType.TX_WAIT,
            WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)

    def http_get_context_status(self, profile_id):
        if profile_id >= WALTER_MODEM_MAX_HTTP_PROFILES:
            return error_rsp(_walter.ModemState.NO_SUCH_PROFILE)

        # note: in my observation the SQNHTTPCONNECT command is to be avoided.
        # if the connection is closed by the server, you will not even
        # receive a +SQNHTTPSH disconnected message (you will on the next
        # connect attempt). reconnect will be impossible even if you try
        # to manually disconnect.
        # and a SQNHTTPQRY will still work and create its own implicit connection.
        #
        # (too bad: according to the docs SQNHTTPCONNECT is mandatory for
        # TLS connections)

        return self._http_context_set[profile_id].connected;

    async def http_query(profile_id, query_cmd, uri):
        if profile_id >= WALTER_MODEM_MAX_HTTP_PROFILES:
            return error_rsp(_walter.ModemState.NO_SUCH_PROFILE)

        if self._http_context_set[profile_id].state != _walter.ModemHttpContextState.IDLE:
            return error_rsp(_walter.ModemState.BUSY)

        async def complete_handler(result, rsp, complete_handler_arg):
            ctx = complete_handler_arg

            if result == _walter.ModemState.OK:
                ctx.state = _walter.ModemHttpContextState.EXPECT_RING

        return await self._run_cmd("AT+SQNHTTPQRY={},{},{}".format(profile_id, query_cmd, modem_string(uri)),
            b"OK", None, complete_handler, self._http_context_set[modem._http_current_profile],
            _walter.ModemCmdType.TX_WAIT, WALTER_MODEM_DEFAULT_CMD_ATTEMPTS)
