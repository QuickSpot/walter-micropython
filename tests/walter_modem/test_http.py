import asyncio
import micropython # type: ignore
micropython.opt_level(0)

import minimal_unittest as unittest
from walter_modem import Modem
from walter_modem.mixins.http import (
    HTTPMixin,
    WalterModemHttpQueryCmd
)
from walter_modem.coreEnums import (
    WalterModemNetworkRegState,
    WalterModemOpState
)
from walter_modem.coreStructs import (
    ModemRsp
)

HTTP_PROFILE_ID = 2
"""CAREFUL; The tests will overwrite this profile"""

modem = Modem(HTTPMixin)

async def await_connection():
        print('\nShowing uart debug logs:')
        modem.uart_debug = True

        for _ in range(600):
            if modem.get_network_reg_state() in (
                WalterModemNetworkRegState.REGISTERED_HOME,
                WalterModemNetworkRegState.REGISTERED_ROAMING
            ):
                modem.uart_debug = False
                return
            await asyncio.sleep(1)
        modem.uart_debug = False
        raise OSError('Connection Timed-out')

class TestHTTP(unittest.AsyncTestCase, unittest.WalterModemAsserts):
    async def async_setup(self):
        modem_rsp = ModemRsp()
        await modem.begin()

        await modem.pdp_context_create(context_id=1)

        await modem.get_op_state(rsp=modem_rsp)
        if modem_rsp.op_state is not WalterModemOpState.FULL:
            await modem.set_op_state(WalterModemOpState.FULL)

        await await_connection()

        self.did_ring_modem_rsp = ModemRsp()
    
    # ---
    # http_config_profile()

    async def test_http_config_profile_sends_correct_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT+SQNHTTPCFG=1,"www.example.com",80,0,"",""',
            lambda: modem.http_config_profile(
                profile_id=1,
                server_address='www.example.com',
                port=80,
                use_basic_auth=False,
                auth_user='',
                auth_pass='',
                tls_profile_id=None
            )
        )
    
    async def test_http_config_profile_runs(self):
        self.assert_true(await modem.http_config_profile(
            profile_id=1,
            server_address='www.example.com'
        ))
    
    # ---
    # http_query()

    async def test_http_query_runs(self):
        self.assert_true(await modem.http_query(
            profile_id=1,
            uri='/',
            query_cmd=WalterModemHttpQueryCmd.GET
        ))
    
    # ---
    # http_did_ring()

    async def test_http_did_ring_rings_after_query_ran(self):
        for _ in range(60):
            if await modem.http_did_ring(profile_id=1, rsp=self.did_ring_modem_rsp): break
            await asyncio.sleep(1)

        self.assert_is_not_none(self.did_ring_modem_rsp.http_response.data)
    
    async def test_http_did_ring_rang_http_status_is_200(self):
        self.assert_equal(200, self.did_ring_modem_rsp.http_response.http_status)
    
test_http = TestHTTP()
test_http.run()
