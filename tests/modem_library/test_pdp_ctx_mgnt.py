import asyncio
import minimal_unittest as unittest

from walter_modem import Modem
from walter_modem.enums import (
    WalterModemPDPAuthProtocol,
    WalterModemPDPType,
    WalterModemPDPIPv4AddrAllocMethod,
    WalterModemPDPRequestType,
    WalterModemPDPPCSCFDiscoveryMethod,
    WalterModemNetworkRegState,
    WalterModemRspType
)
from walter_modem.structs import (
    ModemRsp,
    WalterModemCMEError,
    WalterModemOpState
)

PDP_CTX_ID = 2
APN = ''
AUTH_PROTO = WalterModemPDPAuthProtocol.NONE
AUTH_USER = None
AUTH_PASS = None

modem = Modem()

async def await_connection():
        print('\nShowing modem debug logs:')
        modem.debug_log = True

        for _ in range(600):
            if modem.get_network_reg_state() in (
                WalterModemNetworkRegState.REGISTERED_HOME,
                WalterModemNetworkRegState.REGISTERED_ROAMING
            ):
                modem.debug_log = False
                return
            await asyncio.sleep(1)
        modem.debug_log = False
        raise OSError('Connection Timed-out')

class TestPDPContextManagementPreConnection(unittest.AsyncTestCase, unittest.WalterModemAsserts):
    async def async_setup(self):
        await modem.begin()
    
    async def async_teardown(self):
        await modem._run_cmd(
            at_cmd=f'AT+CGDCONT={PDP_CTX_ID},"IP","",,,,1,0,0,0,0,0,0,,0',
            at_rsp=b'OK'
        )
    
    # ---
    # create_pdp_context()

    async def test_create_pdp_context_runs(self):
        self.assert_true(await modem.create_PDP_context())

    async def test_create_pdp_context_correctly_creates_context_in_modem(self):
        modem_rsp = ModemRsp()
        if not await modem.create_PDP_context(
            context_id=PDP_CTX_ID,
            apn=APN,
            pdp_type=WalterModemPDPType.IP,
            ipv4_alloc_method=WalterModemPDPIPv4AddrAllocMethod.DHCP,
            request_type=WalterModemPDPRequestType.NEW_OR_HANDOVER,
            pcscf_method=WalterModemPDPPCSCFDiscoveryMethod.NAS,
            for_IMCN=True,
            use_NSLPI=False,
            use_secure_PCO=False,
            use_NAS_ipv4_MTU_discovery=True,
            use_local_addr_ind=False,
            use_NAS_on_IPMTU_discovery=False,
        ):
            raise RuntimeError(
                'Failed to create PDP Context',
                WalterModemCMEError.get_value_name(modem_rsp.cme_error)
            )

        pdp_ctx_str_from_modem = None

        def cgdcont_handler(cmd, at_rsp):
            nonlocal pdp_ctx_str_from_modem

            if int(chr(at_rsp[10])) == PDP_CTX_ID:
                pdp_ctx_str_from_modem = at_rsp[12:]

        modem.register_application_queue_rsp_handler(b'+CGDCONT: ', cgdcont_handler)
        await modem._run_cmd(at_cmd='AT+CGDCONT?', at_rsp=b'OK')

        for _ in range(100):
            if pdp_ctx_str_from_modem is not None: break
            await asyncio.sleep(0.1)
        
        self.assert_equal(b'"IP","",,,,1,0,1,1,0,0,1,,0', pdp_ctx_str_from_modem)
    
    # ---
    # set_pdp_auth_params()

    async def test_set_pdp_auth_params_runs(self):
        self.assert_true(
            await modem.set_PDP_auth_params(
                context_id=PDP_CTX_ID,
                protocol=AUTH_PROTO,
                user_id=AUTH_USER,
                password=AUTH_PASS
            )
        )
    
    async def test_set_pdp_auth_params_sends_correct_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            f'AT+CGAUTH={PDP_CTX_ID},{AUTH_PROTO},'
            f'"{AUTH_USER if AUTH_USER else ''}","{AUTH_PASS if AUTH_PASS else ''}"',
            lambda: modem.set_PDP_auth_params(PDP_CTX_ID, AUTH_PROTO, AUTH_USER, AUTH_PASS)
        )

class TestPDPContextManagementPostConnection(unittest.AsyncTestCase, unittest.WalterModemAsserts):
    async def async_setup(self):
        modem_rsp = ModemRsp()
        await modem.begin()

        await modem.create_PDP_context(context_id=PDP_CTX_ID)

        await modem.get_op_state(rsp=modem_rsp)
        if modem_rsp.op_state is not WalterModemOpState.FULL:
            await modem.set_op_state(WalterModemOpState.FULL)

        await await_connection()

    async def async_teardown(self):
        await modem._run_cmd(
            at_cmd=f'AT+CGACT=0,{PDP_CTX_ID}',
            at_rsp=b'OK'
        )
    
    # ---
    # set_pdp_context_active()
    
    async def test_set_pdp_context_active_runs(self):
        self.assert_true(
            await modem.set_PDP_context_active(
                active=True,
                context_id=PDP_CTX_ID,
            )
        )
    
    async def test_set_pdp_context_active_sends_correct_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            f'AT+CGACT=1,{PDP_CTX_ID}',
            lambda: modem.set_PDP_context_active(True, PDP_CTX_ID)
        )
    
    # ---
    # get_pdp_address()
    
    async def test_get_pdp_address_runs(self):
        modem_rsp = ModemRsp()
        self.assert_true(await modem.get_PDP_address(context_id=PDP_CTX_ID, rsp=modem_rsp))
    
    async def test_get_pdp_address_sets_correct_response_type(self):
        modem_rsp = ModemRsp()
        await modem.get_PDP_address(context_id=PDP_CTX_ID, rsp=modem_rsp)
        self.assert_equal(WalterModemRspType.PDP_ADDR, modem_rsp.type)
    
    async def test_get_pdp_address_sets_pdp_address_list_in_response(self):
        modem_rsp = ModemRsp()
        await modem.get_PDP_address(context_id=PDP_CTX_ID, rsp=modem_rsp)
        self.assert_is_instance(modem_rsp.pdp_address_list, list)
    
    # ---
    # attach_pdp_context()
    
    async def test_set_network_attachment_state_runs(self):
        self.assert_true(await modem.set_network_attachment_state(attach=True))
    
    async def test_set_network_attachment_state_sends_correct_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT+CGATT=1',
            lambda: modem.set_network_attachment_state(True)
        )


test_pdp_context_management_pre_connection = TestPDPContextManagementPreConnection()
test_pdp_context_management_post_connection = TestPDPContextManagementPostConnection()

test_pdp_context_management_pre_connection.run()
test_pdp_context_management_post_connection.run()
