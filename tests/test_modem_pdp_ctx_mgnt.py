import asyncio
import minimal_unittest as unittest

from walter_modem import Modem
from walter_modem.enums import (
    WalterModemPDPAuthProtocol,
    WalterModemPDPType,
    WalterModemPDPHeaderCompression,
    WalterModemPDPDataCompression,
    WalterModemPDPIPv4AddrAllocMethod,
    WalterModemPDPRequestType,
    WalterModemPDPPCSCFDiscoveryMethod
)
from walter_modem.structs import (
    ModemRsp,
    WalterModemCMEError
)

modem = Modem()
modem_rsp = ModemRsp()

class TestModemPDPContextManagement(unittest.AsyncTestCase):
    async def async_setup(self):
        await modem.begin(False)
    
    async def async_teardown(self):
        await modem._run_cmd(
            at_cmd=f'AT+CGDCONT={self.test_pdp_ctx_id},"IP","",,,,1,0,0,0,0,0,0,,0',
            at_rsp=b'OK'
        )

    async def test_create_pdp_context_runs(self):
        self.assert_true(await modem.create_PDP_context())

    async def test_create_pdp_context_correctly_creates_context_in_modem(self):
        if not await modem.create_PDP_context(
            apn='',
            auth_proto=WalterModemPDPAuthProtocol.NONE,
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
            rsp=modem_rsp
        ):
            raise RuntimeError(
                'Failed to create PDP Context',
                WalterModemCMEError.get_value_name(modem_rsp.cme_error)
            )

        self.test_pdp_ctx_id = modem_rsp.pdp_ctx_id

        pdp_ctx_str_from_modem = None

        def cgdcont_handler(cmd, at_rsp):
            nonlocal pdp_ctx_str_from_modem

            if int(chr(at_rsp[10])) == self.test_pdp_ctx_id:
                pdp_ctx_str_from_modem = at_rsp[12:]

        modem._register_application_queue_rsp_handler(b'+CGDCONT: ', cgdcont_handler)
        await asyncio.sleep(1)
        await modem._run_cmd(at_cmd='AT+CGDCONT?', at_rsp=b'OK')

        for _ in range(100):
            if pdp_ctx_str_from_modem is not None: break
            await asyncio.sleep(0.1)
        
        self.assert_equal(b'"IP","",,,,1,0,1,1,0,0,1,,0', pdp_ctx_str_from_modem)

test_modem_pdp_context_management = TestModemPDPContextManagement()
test_modem_pdp_context_management.run()
