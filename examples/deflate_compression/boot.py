"""
Copyright (C) 2024, DPTechnics bv
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

import deflate
import esp32
import time

from walter_unified_comm import WalterComm, PreferredConnType, HttpContentType

comm = WalterComm(
    # Preferred order of connection type attempt
    # eg. Try LTE-M first, then WLAN, then NB-IoT
    preferred_conn = PreferredConnType.LTEM_WLAN_NBIOT,
    wlan_ssid = "WLAN_SSID",
    wlan_key = "WLAN_KEY",
    )

while True:
    try:
        # Read the internal MCU temperature
        mcu_temp = esp32.mcu_temperature()

        # Create a JSON string with the temperature data
        json_data = '{"mcu_temperature": %.2f}' % mcu_temp

        # Compress the JSON string using deflate
        with open("data.zlib", "wb") as f:
            with deflate.DeflateIO(f, deflate.ZLIB) as d:
                d.write(json_data.encode("utf-8"))

        # Read and send the compressed temperature data
        with open("data.zlib", "rb") as f:
            data = f.read()
            comm.http.post_sync("URL",
                                HttpContentType.OCTET_STREAM,
                                data)

        except Exception as e:
            print("Error during upload:", e)

        time.sleep(10)
