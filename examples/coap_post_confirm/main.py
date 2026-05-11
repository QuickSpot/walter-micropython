# pyright: reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportArgumentType=false, reportCallIssue=false, reportGeneralTypeIssues=false
import micropython # type: ignore
micropython.opt_level(1)

import asyncio
import sys

from walter_modem import Modem
from walter_modem.coreEnums import *
from walter_modem.coreStructs import *
from walter_modem.mixins.default_sim_network import *
from walter_modem.mixins.default_pdp import *
from walter_modem.mixins.coap import *

# region CONFIG

CELL_APN = ''
APN_USERNAME = ''
APN_PASSWORD = ''
AUTHENTICATION_PROTOCOL = WalterModemPDPAuthProtocol.NONE
SIM_PIN = None

COAP_SERVER_ADDRESS = 'coap.me'
COAP_SERVER_PORT = 5683
COAP_PATH = 'test'
COAP_PAYLOAD = '{"message":"Hello from Walter MicroPython"}'

COAP_CTX_ID = 0
COAP_TIMEOUT_SECONDS = 60
RING_WAIT_SECONDS = 20

# endregion

modem = Modem(CoapMixin, load_default_power_saving_mixin=False)
modem_rsp = WalterModemRsp()


async def wait_for_network_reg_state(timeout: int, *states: WalterModemNetworkRegState) -> bool:
    for _ in range(timeout):
        if modem.get_network_reg_state() in states:
            return True
        await asyncio.sleep(1)
    return False


async def unlock_sim() -> bool:
    if not await modem.set_op_state(WalterModemOpState.NO_RF):
        print('Failed to set operational state to NO_RF')
        return False

    await asyncio.sleep(2)
    if await modem.unlock_sim(pin=SIM_PIN):
        print('SIM unlocked')
        return True

    print('Failed to unlock SIM card')
    return False


async def lte_connect(_retry: bool = False) -> bool:
    if modem.get_network_reg_state() in (
        WalterModemNetworkRegState.REGISTERED_HOME,
        WalterModemNetworkRegState.REGISTERED_ROAMING
    ):
        return True

    if not await modem.set_op_state(WalterModemOpState.FULL):
        print('Failed to set operational state to FULL')
        return False

    if not await modem.set_network_selection_mode(WalterModemNetworkSelMode.AUTOMATIC):
        print('Failed to set network selection mode to AUTOMATIC')
        return False

    if await wait_for_network_reg_state(
        300,
        WalterModemNetworkRegState.REGISTERED_HOME,
        WalterModemNetworkRegState.REGISTERED_ROAMING
    ):
        return True

    if await modem.get_rat(rsp=modem_rsp):
        rat = modem_rsp.rat
    else:
        print('Failed to read RAT')
        return False

    if _retry:
        print('Failed to connect on both LTE-M and NB-IoT')
        return False

    next_rat = WalterModemRat.NBIOT if rat == WalterModemRat.LTEM else WalterModemRat.LTEM
    print('Network attach timed out, switching RAT and retrying')

    if not await modem.set_op_state(WalterModemOpState.MINIMUM):
        print('Failed to set operational state to MINIMUM')
        return False

    if not await wait_for_network_reg_state(5, WalterModemNetworkRegState.NOT_SEARCHING):
        print('Modem did not reach NOT_SEARCHING state')
        return False

    if not await modem.set_rat(next_rat):
        print('Failed to switch RAT')
        return False

    await modem.reset()
    return await lte_connect(_retry=True)


async def wait_for_coap_confirmation(ctx_id: int, timeout_s: int) -> WalterModemCoapRing | None:
    for _ in range(timeout_s):
        if len(modem.coap_context_states[ctx_id].rings) > 0:
            return modem.coap_context_states[ctx_id].rings.pop()
        await asyncio.sleep(1)
    return None


async def lte_disconnect() -> bool:
    if modem.get_network_reg_state() == WalterModemNetworkRegState.NOT_SEARCHING:
        return True

    if not await modem.set_op_state(WalterModemOpState.MINIMUM):
        print('Failed to set operational state to MINIMUM during disconnect')
        return False

    if await wait_for_network_reg_state(15, WalterModemNetworkRegState.NOT_SEARCHING):
        return True

    print('Modem did not reach NOT_SEARCHING during disconnect')
    return False


async def cleanup_modem_state():
    # Close CoAP context only if still connected.
    if modem.coap_context_states[COAP_CTX_ID].connected:
        if await modem.coap_context_close(COAP_CTX_ID):
            print('CoAP context closed')
        else:
            print('Failed to close CoAP context cleanly')

    if await lte_disconnect():
        print('Modem disconnected cleanly')
    else:
        print('Modem disconnect did not complete cleanly')


async def run_example() -> bool:
    print('Walter CoAP POST + Confirmation Example')
    print('----------------------------------------')
    print(f'Server: {COAP_SERVER_ADDRESS}:{COAP_SERVER_PORT}')
    print(f'Path: /{COAP_PATH}')

    try:
        await modem.begin()

        if not await modem.check_comm():
            print('Modem communication failed')
            return False

        if SIM_PIN is not None and not await unlock_sim():
            return False

        if not await modem.pdp_context_create(apn=CELL_APN, rsp=modem_rsp):
            print('Failed to create PDP context')
            return False

        if APN_USERNAME and not await modem.pdp_set_auth_params(
            protocol=AUTHENTICATION_PROTOCOL,
            user_id=APN_USERNAME,
            password=APN_PASSWORD
        ):
            print('Failed to set APN authentication parameters')
            return False

        print('Attaching to network...')
        if not await lte_connect():
            print('Failed to attach to network')
            return False

        print('Creating CoAP context...')
        if not await modem.coap_context_create(
            ctx_id=COAP_CTX_ID,
            server_address=COAP_SERVER_ADDRESS,
            server_port=COAP_SERVER_PORT,
            timeout=COAP_TIMEOUT_SECONDS,
            rsp=modem_rsp
        ):
            print('Failed to create CoAP context')
            return False

        print('Sending CoAP POST...')
        if not await modem.coap_send(
            ctx_id=COAP_CTX_ID,
            m_type=WalterModemCoapType.CON,
            method=WalterModemCoapMethod.POST,
            path=COAP_PATH,
            content_type=WalterModemCoapContentType.APPLICATION_JSON,
            data=COAP_PAYLOAD,
            rsp=modem_rsp
        ):
            print('Failed to send CoAP POST')
            return False

        print('Waiting for confirmation ring...')
        ring = await wait_for_coap_confirmation(COAP_CTX_ID, RING_WAIT_SECONDS)
        if ring is None:
            print('No confirmation ring received within timeout')
            return False

        print(f'Received ring: msg_id={ring.msg_id}, rsp_code={ring.rsp_code}, length={ring.length}')

        if ring.rsp_code in (
            WalterModemCoapResponseCode.CREATED,
            WalterModemCoapResponseCode.CHANGED,
            WalterModemCoapResponseCode.CONTENT
        ):
            print('POST confirmed by server')
        else:
            print('Server returned non-success CoAP response')

        if ring.length > 0:
            if await modem.coap_receive_data(
                ctx_id=ring.ctx_id,
                msg_id=ring.msg_id,
                length=ring.length,
                rsp=modem_rsp
            ):
                response = modem_rsp.coap_rcv_response
                print('Response payload:')
                print(response.payload)

        return True
    finally:
        await cleanup_modem_state()


async def main():
    ok = await run_example()
    print('Done' if ok else 'Failed')


try:
    asyncio.run(main())
except (KeyboardInterrupt, Exception) as e:
    sys.print_exception(e) # type: ignore
