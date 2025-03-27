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

APN = ''
AUTH_PROTO = WalterModemPDPAuthProtocol.NONE
AUTH_USER = None
AUTH_PASS = None

modem = Modem()
modem_rsp = ModemRsp()

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

class TestModemPDPContextManagementPreConnection(unittest.AsyncTestCase):
    async def async_setup(self):
        await modem.begin()
    
    async def async_teardown(self):
        await modem._run_cmd(
            at_cmd=f'AT+CGDCONT={PDP_CTX_ID},"IP","",,,,1,0,0,0,0,0,0,,0',
            at_rsp=b'OK'
        )

    async def test_create_pdp_context_runs(self):
        self.assert_true(await modem.create_PDP_context())

    async def test_create_pdp_context_correctly_creates_context_in_modem(self):
        if not await modem.create_PDP_context(
            context_id=PDP_CTX_ID,
            apn=APN,
            type=WalterModemPDPType.IP,
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

        modem._register_application_queue_rsp_handler(b'+CGDCONT: ', cgdcont_handler)
        await modem._run_cmd(at_cmd='AT+CGDCONT?', at_rsp=b'OK')

        for _ in range(100):
            if pdp_ctx_str_from_modem is not None: break
            await asyncio.sleep(0.1)
        
        self.assert_equal(b'"IP","",,,,1,0,1,1,0,0,1,,0', pdp_ctx_str_from_modem)

    async def test_set_PDP_context_auth_params_context_runs(self):
        self.assert_true(
            await modem.set_PDP_context_auth_params(
                context_id=PDP_CTX_ID,
                protocol=AUTH_PROTO,
                user_id=AUTH_USER,
                password=AUTH_PASS
            )
        )

class TestModemPDPContextManagementPostConnection(unittest.AsyncTestCase):
    async def async_setup(self):
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
    
    async def test_set_PDP_context_state_runs(self):
        self.assert_true(
            await modem.set_PDP_context_state(
                active=True,
                context_id=PDP_CTX_ID,
            )
        )
    
    async def test_set_PDP_context_state_sets_state_in_modem(self):
        await modem.set_PDP_context_state(active=True, context_id=PDP_CTX_ID)
        
        pdp_state_from_modem = None

        def cgact_handler(cmd, at_rsp):
            nonlocal pdp_state_from_modem

            if int(chr(at_rsp[8])) == PDP_CTX_ID:
                pdp_state_from_modem = at_rsp[10:]

        modem._register_application_queue_rsp_handler(b'+CGACT: ', cgact_handler)
        await modem._run_cmd(at_cmd='AT+CGACT?', at_rsp=b'OK')

        for _ in range(100):
            if pdp_state_from_modem is not None: break
            await asyncio.sleep(0.1)
        
        self.assert_equal(b'1', pdp_state_from_modem)
    
    async def test_get_PDP_address_runs(self):
        self.assert_true(await modem.get_PDP_address(context_id=PDP_CTX_ID, rsp=modem_rsp))
    
    async def test_get_PDP_address_sets_correct_response_type(self):
        self.assert_equal(WalterModemRspType.PDP_ADDR, modem_rsp.type)
    
    async def test_get_PDP_address_sets_pdp_address_list(self):
        self.assert_is_instance(modem_rsp.pdp_address_list, list)


test_modem_pdp_context_management_pre_connection = TestModemPDPContextManagementPreConnection()
test_modem_pdp_context_management_post_connection = TestModemPDPContextManagementPostConnection()

test_modem_pdp_context_management_pre_connection.run()
test_modem_pdp_context_management_post_connection.run()
