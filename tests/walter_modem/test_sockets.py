import asyncio
import network # type: ignore
import micropython # type: ignore
micropython.opt_level(0)

import minimal_unittest as unittest
from walter_modem import Modem
from walter_modem.mixins.socket import SocketMixin
from walter_modem.coreEnums import (
    WalterModemNetworkRegState,
    WalterModemOpState,
    WalterModemRspType,
)
from walter_modem.coreStructs import (
    ModemRsp
)

modem = Modem(SocketMixin)

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

class TestSockets(unittest.AsyncTestCase, unittest.WalterModemAsserts):
    async def async_setup(self):
        modem_rsp = ModemRsp()
        await modem.begin()

        await modem.pdp_context_create(context_id=1)

        await modem.get_op_state(rsp=modem_rsp)
        if modem_rsp.op_state is not WalterModemOpState.FULL:
            await modem.set_op_state(WalterModemOpState.FULL)

        await await_connection()

        self.socket_create_modem_rsp = ModemRsp()

    # ---
    # socket_create()

    async def test_socket_create_runs(self):
        self.assert_true(await modem.socket_create(rsp=self.socket_create_modem_rsp))
    
    async def test_socket_create_sends_correct_at_command(self):
        await self.assert_sends_at_command(
            modem,
            'AT+SQNSCFG=2,1,500,120,900,30',
            lambda: modem.socket_create(
                pdp_context_id=1,
                mtu=500,
                exchange_timeout=120,
                conn_timeout=90,
                send_delay_ms=3000
            )
        )
    
    async def test_socket_create_sets_correct_response_type(self):
        self.assert_equal(WalterModemRspType.SOCKET_ID, self.socket_create_modem_rsp.type)
    
    async def test_socket_create_sets_socket_id_in_response(self):
        self.assert_is_instance(self.socket_create_modem_rsp.socket_id, int)
    
    # ---
    # socket_connect()

    async def test_socket_connect_runs(self):
        self.assert_true(await modem.socket_connect(
            remote_host='walterdemo.quickspot.io',
            remote_port=1999,
            local_port=1999
        ))
    
    # ---
    # socket_send()

    async def test_socket_send_runs(self):
        data_buffer: bytearray = bytearray(network.WLAN().config('mac'))
        data_buffer.append(101 >> 8)
        data_buffer.append(101 & 0xff)
        print('On walterdemo.quickspot.io you should see 101 as count', end=' ')
        self.assert_true(await modem.socket_send(data=data_buffer))

    # ---
    # socket_close()

    async def test_socket_close(self):
        self.assert_true(await modem.socket_close())

test_sockets = TestSockets()
test_sockets.run()