import asyncio

from minimal_unittest import (
    AsyncTestCase,
    WalterModemAsserts,
    NetworkConnectivity
)

from walter_modem import Modem
from walter_modem.enums import (
    WalterModemState,
    WalterModemOpState,
    WalterModemCoapCloseCause,
    WalterModemCoapMethod,
    WalterModemCoapType,
    WalterModemCoapResponseCode,
    WalterModemCoapOptionAction,
    WalterModemCoapOption,
    WalterModemCoapContentType
)
from walter_modem.structs import (
    ModemRsp,
    ModemCoapContextState,
    ModemCoapResponse,
    ModemCoapOption
)

# To avoid disconnecting & reconnecting from the network too frequently;
# A single modem library instance is re-used, keeping a network connection open
# from the moment RequireNetworkConnection was first inheriteed.
modem = Modem()

class TestCoapContextCreate(
    AsyncTestCase,
    WalterModemAsserts,
    NetworkConnectivity
):  
    async def async_setup(self):
        await modem.begin()
        await self.ensure_network_connection(modem)
        self.register_fail_on_cme_error(modem)

    async def async_teardown(self):
        self.unregister_fail_on_cme_error(modem)
        await modem._run_cmd(
            at_cmd='AT+SQNCOAPCLOSE=0',
            at_rsp=b'OK'
        )
        await modem._run_cmd(
            at_cmd='AT+SQNCOAPCLOSE=1',
            at_rsp=b'OK'
        )
        await modem._run_cmd(
            at_cmd='AT+SQNCOAPCLOSE=2',
            at_rsp=b'OK'
        )

        modem.coap_context_states[0].rings.clear()
        modem.coap_context_states[1].rings.clear()
        modem.coap_context_states[2].rings.clear()

    # Context ID range validation

    async def test_fails_below_min_ctx_id(self):
        self.assert_false(await modem.coap_context_create(ctx_id=-1))

    async def test_fails_above_max_ctx_id(self):
        self.assert_false(await modem.coap_context_create(ctx_id=3))

    async def test_rsp_result_no_such_profile_on_invalid_ctx_id(self):
        modem_rsp = ModemRsp()
        await modem.coap_context_create(ctx_id=7, rsp=modem_rsp)
        self.assert_equal(WalterModemState.NO_SUCH_PROFILE, modem_rsp.result)

    # Timeout range validation

    async def test_fails_below_min_timeout(self):
        self.assert_false(await modem.coap_context_create(ctx_id=0, timeout=0))

    async def test_fails_above_max_timeout(self):
        self.assert_false(await modem.coap_context_create(ctx_id=0, timeout=121))

    async def test_rsp_result_error_on_invalid_timeout(self):
        modem_rsp = ModemRsp()
        await modem.coap_context_create(ctx_id=0, timeout=142, rsp=modem_rsp)
        self.assert_equal(WalterModemState.ERROR, modem_rsp.result)

    # AT command format

    async def test_sends_expected_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT+SQNCOAPCREATE=0,"test",5683,5683,0,60',
            lambda: modem.coap_context_create(
                ctx_id=0,
                server_address='test',
                server_port=5683,
                local_port=5683,
                timeout=60,
                dtls=False
            )
        )

    # Method run

    async def test_fails_on_unreachable_server(self):
        self.assert_false(await modem.coap_context_create(
            ctx_id=0,
            server_address='totally_valid_address',
            server_port=5555
        ))

    async def test_succeeds_on_reachable_server(self):
        self.assert_true(await modem.coap_context_create(
            ctx_id=0,
            server_address='coap.me',
            server_port=5683
        ))

    async def test_succeeds_on_listen_mode(self):
        self.assert_true(await modem.coap_context_create(
            ctx_id=1,
            local_port=5683
        ))

    # Mirror state

    async def test_ctx_0_mirror_state_set(self):
        self.assert_is_instance(modem.coap_context_states[0], ModemCoapContextState)
    
    async def test_ctx_1_mirror_state_set(self):
        self.assert_is_instance(modem.coap_context_states[1], ModemCoapContextState)
    
    async def test_ctx_2_mirror_state_set(self):
        self.assert_is_instance(modem.coap_context_states[2], ModemCoapContextState)
    
    async def test_ctx_state_not_configured_after_failed_run(self):
        await modem.coap_context_create(
            ctx_id=2,
            server_address='totally_valid_address',
            server_port=5556
        )
        self.assert_false(modem.coap_context_states[2].configured)
    
    async def test_ctx_state_configured_after_successful_run(self):
        await modem.coap_context_create(
            ctx_id=2,
            server_address='coap.me',
            server_port=5683
        )
        self.assert_true(modem.coap_context_states[2].configured)
    
    async def test_ctx_state_configured_mirrors_connected(self):
        self.assert_is(
            modem.coap_context_states[0].configured,
            modem.coap_context_states[0].connected
        )

class TestCoapContextClose(
    AsyncTestCase,
    WalterModemAsserts,
    NetworkConnectivity
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent
        await self.ensure_network_connection(modem)
        self.register_fail_on_cme_error(modem)

        await modem._run_cmd(
            at_cmd='AT+SQNCOAPCREATE=0,"coap.me",5683',
            at_rsp=b'+SQNCOAPCONNECTED: '
        )
        await modem._run_cmd(
            at_cmd='AT+SQNCOAPCREATE=1,"coap.me",5683',
            at_rsp=b'+SQNCOAPCONNECTED: '
        )
    
    async def async_teardown(self):
        self.unregister_fail_on_cme_error(modem)

    # Context ID range validation

    async def test_fails_below_min_ctx_id(self):
        self.assert_false(await modem.coap_context_close(ctx_id=-1))

    async def test_fails_above_max_ctx_id(self):
        self.assert_false(await modem.coap_context_close(ctx_id=3))

    async def test_rsp_result_no_such_profile_on_invalid_ctx_id(self):
        modem_rsp = ModemRsp()
        await modem.coap_context_close(ctx_id=7, rsp=modem_rsp)
        self.assert_equal(WalterModemState.NO_SUCH_PROFILE, modem_rsp.result)

    # Method run

    async def test_succeeds_closing_active_connection(self):
        self.assert_true(await modem.coap_context_close(ctx_id=1))
    
    # Mirror state

    async def test_ctx_state_not_configured_after_close(self):
        self.assert_false(modem.coap_context_states[1].configured)
    
    async def test_ctx_state_not_connected_after_close(self):
        self.assert_false(modem.coap_context_states[1].connected)
    
    async def test_ctx_state_cause_equals_user_after_manual_close(self):
        self.assert_equal(WalterModemCoapCloseCause.USER, modem.coap_context_states[1].cause)
    
    async def test_ctx_state_cause_equals_network_after_network_close(self):
        await modem.set_op_state(WalterModemOpState.MINIMUM)
        await asyncio.sleep(2) # closed URC should've been triggered by now
        self.assert_equal(WalterModemCoapCloseCause.NETWORK, modem.coap_context_states[0].cause)

class TestCoapSetOptions(
    AsyncTestCase,
    WalterModemAsserts,
    NetworkConnectivity
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent
        await self.ensure_network_connection(modem)
        self.register_fail_on_cme_error(modem)

        await modem._run_cmd(
            at_cmd='AT+SQNCOAPCREATE=0,"coap.me",5683',
            at_rsp=b'OK'
        )
    
    async def async_teardown(self):
        self.unregister_fail_on_cme_error(modem)
        await modem._run_cmd(
            at_cmd='AT+SQNCOAPCLOSE=0',
            at_rsp=b'OK'
        )
    
    # Context ID range validation
    
    async def test_fails_below_min_ctx_id(self):
        self.assert_false(await modem.coap_set_options(
            ctx_id=-1,
            action=WalterModemCoapOptionAction.READ,
            option=WalterModemCoapOption.URI_PATH
        ))
    
    async def test_fails_above_max_ctx_id(self):
        self.assert_false(await modem.coap_set_options(
            ctx_id=3,
            action=WalterModemCoapOptionAction.READ,
            option=WalterModemCoapOption.URI_PATH
        ))
    
    async def test_rsp_result_no_such_profile_on_invalid_ctx_id(self):
        modem_rsp = ModemRsp()
        await modem.coap_set_options(
            ctx_id=7,
            action=WalterModemCoapOptionAction.READ,
            option=WalterModemCoapOption.URI_PATH,
            rsp=modem_rsp
        )

        self.assert_equal(WalterModemState.NO_SUCH_PROFILE, modem_rsp.result)
    
    # Repeatable options validtion

    async def test_multiple_values_fails_on_non_repeatable_option(self):
        self.assert_false(await modem.coap_set_options(
            ctx_id=0,
            action=WalterModemCoapOptionAction.SET,
            option=WalterModemCoapOption.CONTENT_TYPE,
            value=(WalterModemCoapContentType.TEXT_PLAIN, WalterModemCoapContentType.IMAGE_JPEG)
        ))
    
    async def test_multiple_values_fails_above_max(self):
        self.assert_false(await modem.coap_set_options(
            ctx_id=0,
            action=WalterModemCoapOptionAction.SET,
            option=WalterModemCoapOption.URI_PATH,
            value=('Why', 'did', 'the', 'modem', 'break', 'up?', '...', 'signal', 'loss', ':)')
        ))
    
    # AT command format

    async def test_sends_expected_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT+SQNCOAPOPT=0,0,11,".well-known","core"',
            lambda: modem.coap_set_options(
                ctx_id=0,
                action=WalterModemCoapOptionAction.SET,
                option=WalterModemCoapOption.URI_PATH,
                value=('.well-known','core')
            )
        )

        await modem._run_cmd('AT+SQNCOAPOPT=0,1,11', b'OK')
    
    # Action: SET

    async def test_action_set_runs(self):
        self.assert_true(await modem.coap_set_options(
            ctx_id=0,
            action=WalterModemCoapOptionAction.SET,
            option=WalterModemCoapOption.CONTENT_TYPE,
            value=WalterModemCoapContentType.TEXT_PLAIN
        ))

        await modem._run_cmd('AT+SQNCOAPOPT=0,1,12', b'OK')

    # Action: DELETE

    async def test_action_delete_runs(self):
        await modem._run_cmd('AT+SQNCOAPOPT=0,0,12,"0"', b'OK')

        self.assert_true(await modem.coap_set_options(
            ctx_id=0,
            action=WalterModemCoapOptionAction.DELETE,
            option=WalterModemCoapOption.CONTENT_TYPE
        ))
    
    # Action: READ

    async def test_action_read_runs(self):
        await modem._run_cmd('AT+SQNCOAPOPT=0,0,12,"50"', b'OK')

        self.assert_true(await modem.coap_set_options(
            ctx_id=0,
            action=WalterModemCoapOptionAction.READ,
            option=WalterModemCoapOption.CONTENT_TYPE
        ))

        await modem._run_cmd('AT+SQNCOAPOPT=0,1,12', b'OK')
    
    async def test_action_read_sets_option_value_in_rsp(self):
        await modem._run_cmd('AT+SQNCOAPOPT=0,0,11,".well-known","core"', b'OK')

        modem_rsp = ModemRsp()
        await modem.coap_set_options(
            ctx_id=0,
            action=WalterModemCoapOptionAction.READ,
            option=WalterModemCoapOption.URI_PATH,
            rsp=modem_rsp
        )
        
        expected = ModemCoapOption(0, 11, '".well-known","core"')
        reality = modem_rsp.coap_options
        self.assert_equal(
            (expected.ctx_id, expected.option, expected.value),
            (reality.ctx_id, reality.option, reality.value)
        )

        await modem._run_cmd('AT+SQNCOAPOPT=0,1,11', b'OK')

    # Action: EXTEND

    async def test_action_extend_runs(self):
        modem._run_cmd('AT+SQNCOAPOPT=0,0,11,"the","answer","is","always"', b'OK')

        self.assert_true(await modem.coap_set_options(
            ctx_id=0,
            action=WalterModemCoapOptionAction.EXTEND,
            option=WalterModemCoapOption.URI_PATH,
            value='yes'
        ))

        modem._run_cmd('AT+SQNCOAPOPT=0,1,11', b'OK')
    
class TestCoapSetHeader(
    AsyncTestCase,
    WalterModemAsserts,
    NetworkConnectivity
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent
        await self.ensure_network_connection(modem)
        self.register_fail_on_cme_error(modem)

        await modem._run_cmd(
            at_cmd='AT+SQNCOAPCREATE=0,"coap.me",5683',
            at_rsp=b'+SQNCOAPCONNECTED: '
        )   

    async def async_teardown(self):
        self.unregister_fail_on_cme_error(modem)
        await modem._run_cmd(
            at_cmd='AT+SQNCOAPCLOSE=0',
            at_rsp=b'OK'
        )

    # Context ID range validation
    
    async def test_fails_below_min_ctx_id(self):
        self.assert_false(await modem.coap_set_header(
            ctx_id=-1,
            msg_id=42
        ))
    
    async def test_fails_above_max_ctx_id(self):
        self.assert_false(await modem.coap_set_header(
            ctx_id=3,
            msg_id=1701
        ))
    
    async def test_rsp_result_no_such_profile_on_invalid_ctx_id(self):
        modem_rsp = ModemRsp()
        await modem.coap_set_header(
            ctx_id=7,
            msg_id=19,
            rsp=modem_rsp
        )

        self.assert_equal(WalterModemState.NO_SUCH_PROFILE, modem_rsp.result)
    
    # Message ID validation

    async def test_fails_below_min_msg_id(self):
        self.assert_false(await modem.coap_set_header(
            ctx_id=0,
            msg_id=-1
        ))

    async def test_fails_below_min_msg_id(self):
        self.assert_false(await modem.coap_set_header(
            ctx_id=0,
            msg_id=65536
        ))

    async def test_rsp_result_error_on_invalid_msg_id(self):
        modem_rsp = ModemRsp()
        await modem.coap_set_header(
            ctx_id=0,
            msg_id=75454,
            rsp=modem_rsp
        )

        self.assert_equal(WalterModemState.ERROR, modem_rsp.result)
    
    # Token validation

    async def test_fails_on_too_long_token(self):
        self.assert_false(await modem.coap_set_header(
            ctx_id=0,
            token='D1AD7314FB251B3FC'
        ))
    
    async def test_fails_on_invalid_hex_in_token(self):
        self.assert_false(await modem.coap_set_header(
            ctx_id=0,
            token='NCC-1701'
        ))
    
    async def test_rsp_result_error_on_invalid_token(self):
        modem_rsp = ModemRsp()
        await modem.coap_set_header(
            ctx_id=0,
            token='NCC-1701-D',
            rsp=modem_rsp
        )

        self.assert_equal(WalterModemState.ERROR, modem_rsp.result)
    
    # AT command format

    async def test_sends_expected_at_cmd(self):
        await self.assert_sends_at_command(
            modem,
            'AT+SQNCOAPHDR=0,47457,"74EBFDE0"',
            lambda: modem.coap_set_header(
                ctx_id=0,
                msg_id=47457,
                token='74EBFDE0'
            )
        )

class TestCoapSend(
    AsyncTestCase,
    WalterModemAsserts,
    NetworkConnectivity
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent
        await self.ensure_network_connection(modem)
        self.register_fail_on_cme_error(modem)

        await modem._run_cmd(
            at_cmd='AT+SQNCOAPCREATE=0,"coap.me",5683',
            at_rsp=b'+SQNCOAPCONNECTED: '
        )
    
    async def async_teardown(self):
        self.unregister_fail_on_cme_error(modem)
        await modem._run_cmd(
            at_cmd='AT+SQNCOAPCLOSE=0',
            at_rsp=b'OK'
        )
        modem.coap_context_states[0].rings.clear()
    
    # Context ID range validation
    
    async def test_fails_below_min_ctx_id(self):
        self.assert_false(await modem.coap_send(
            ctx_id=-1,
            m_type=WalterModemCoapType.CON,
            method=WalterModemCoapMethod.GET,
            length=0,
            data=None
        ))

    async def test_fails_above_max_ctx_id(self):
        self.assert_false(await modem.coap_send(
            ctx_id=3,
            m_type=WalterModemCoapType.CON,
            method=WalterModemCoapMethod.GET,
            length=0,
            data=None
        ))

    async def test_rsp_result_no_such_profile_on_invalid_ctx_id(self):
        modem_rsp = ModemRsp()
        await modem.coap_send(
            ctx_id=7,
            m_type=WalterModemCoapType.CON,
            method=WalterModemCoapMethod.GET,
            length=0,
            data=None,
            rsp=modem_rsp
        )
        self.assert_equal(WalterModemState.NO_SUCH_PROFILE, modem_rsp.result)

    # Length range validation

    async def test_fails_below_min_length(self):
        self.assert_false(await modem.coap_send(
            ctx_id=0,
            m_type=WalterModemCoapType.CON,
            method=WalterModemCoapMethod.GET,
            length=-1,
            data=None
        ))

    async def test_fails_above_max_length(self):
        self.assert_false(await modem.coap_send(
            ctx_id=0,
            m_type=WalterModemCoapType.CON,
            method=WalterModemCoapMethod.GET,
            length=1025,  # Max is 1024 per documentation
            data=None
        ))

    async def test_rsp_result_error_on_invalid_length(self):
        modem_rsp = ModemRsp()
        await modem.coap_send(
            ctx_id=0,
            m_type=WalterModemCoapType.CON,
            method=WalterModemCoapMethod.GET,
            length=2000,
            data=None,
            rsp=modem_rsp
        )
        self.assert_equal(WalterModemState.ERROR, modem_rsp.result)

    # AT command format

    async def test_sends_expected_at_cmd_get_no_data(self):
        await modem._run_cmd('AT+SQNCOAPOPT=0,0,11,".well-known"',b'OK')
        await modem._run_cmd('AT+SQNCOAPOPT=0,0,11,"core"',b'OK')
        await self.assert_sends_at_command(
            modem,
            'AT+SQNCOAPSEND=0,0,1,0',
            lambda: modem.coap_send(
                ctx_id=0,
                m_type=WalterModemCoapType.CON,
                method=WalterModemCoapMethod.GET,
                length=0,
                data=None
            )
        )

    # Method run tests with coap.me endpoints
    # GET tests

    async def test_get_well_known_core(self):
        self.assert_true(await modem.coap_send(
            ctx_id=0,
            m_type=WalterModemCoapType.CON,
            method=WalterModemCoapMethod.GET,
            length=0,
            data=None,
            path='/.well-known/core'
        ))

    async def test_get_test_endpoint(self):
        await asyncio.sleep(5) # Lower chances of another ring-(response) coming in.
        modem.coap_context_states[0].rings.clear()
        self.assert_true(await modem.coap_send(
            ctx_id=0,
            m_type=WalterModemCoapType.CON,
            method=WalterModemCoapMethod.GET,
            length=0,
            data=None,
            path='test' # Testing different ways of giving path along (with and without /)
        ))

    async def test_get_test_endpoint_rang_205_content(self):
        while len(modem.coap_context_states[0].rings) <= 0:
            await asyncio.sleep(3)
        
        ring = modem.coap_context_states[0].rings.pop()
        self.assert_equal(
            WalterModemCoapResponseCode.CONTENT,
            ring.rsp_code
        )

    # POST tests

    async def test_post_test_endpoint(self):
        test_data = 'Hello from Walter Modem'
        modem.coap_context_states[0].rings.clear()
        self.assert_true(await modem.coap_send(
            ctx_id=0,
            m_type=WalterModemCoapType.CON,
            method=WalterModemCoapMethod.POST,
            length=len(test_data),
            data=test_data,
            path='/test',
            content_type=WalterModemCoapContentType.APPLICATION_JSON
        ))

    async def test_post_test_endpoint_rang_201_created(self):
        while len(modem.coap_context_states[0].rings) <= 0:
            await asyncio.sleep(3)
        
        ring = modem.coap_context_states[0].rings.pop()
        self.assert_equal(
            WalterModemCoapResponseCode.CREATED,
            ring.rsp_code
        )

    # PUT tests

    async def test_put_test_endpoint(self):
        test_data = 'Updated resource data'
        modem.coap_context_states[0].rings.clear()
        self.assert_true(await modem.coap_send(
            ctx_id=0,
            m_type=WalterModemCoapType.CON,
            method=WalterModemCoapMethod.PUT,
            length=len(test_data),
            data=test_data,
            path='test'
        ))

    async def test_put_test_endpoint_rang_204_changed(self):
        while len(modem.coap_context_states[0].rings) <= 0:
            await asyncio.sleep(3)
        
        ring = modem.coap_context_states[0].rings.pop()
        self.assert_equal(
            WalterModemCoapResponseCode.CHANGED,
            ring.rsp_code
        )

    # DELETE tests

    async def test_delete_test_endpoint(self):
        modem.coap_context_states[0].rings.clear()
        self.assert_true(await modem.coap_send(
            ctx_id=0,
            m_type=WalterModemCoapType.CON,
            method=WalterModemCoapMethod.DELETE,
            length=0,
            data=None,
            path='test'
        ))

    async def test_delete_test_endpoint_rang_202_deleted(self):
        while len(modem.coap_context_states[0].rings) <= 0:
            await asyncio.sleep(3)
        
        ring = modem.coap_context_states[0].rings.pop()
        self.assert_equal(
            WalterModemCoapResponseCode.DELETED,
            ring.rsp_code
        )

    # Data Formats

    async def test_str_data_format(self):
        test_string = 'String payload test'
        self.assert_true(await modem.coap_send(
            ctx_id=0,
            m_type=WalterModemCoapType.CON,
            method=WalterModemCoapMethod.POST,
            length=len(test_string),
            data=test_string,
            path='test'
        ))

    async def test_bytes_data_format(self):
        test_binary = b'\x01\x02\x03\x04\x05'
        self.assert_true(await modem.coap_send(
            ctx_id=0,
            m_type=WalterModemCoapType.CON,
            method=WalterModemCoapMethod.POST,
            length=len(test_binary),
            data=test_binary
        ))

    # Length calculation tests

    async def test_auto_length_calculation_with_string(self):
        test_data = 'Auto-length test'
        self.assert_true(await modem.coap_send(
            ctx_id=0,
            m_type=WalterModemCoapType.CON,
            method=WalterModemCoapMethod.POST,
            data=test_data,
            path='.well-known/core'
        ))
        
    async def test_auto_length_calculation_with_bytes(self):
        test_data = b'Binary auto-length test'
        self.assert_true(await modem.coap_send(
            ctx_id=0,
            m_type=WalterModemCoapType.CON,
            method=WalterModemCoapMethod.POST,
            data=test_data,
            path='/.well-known/core'
        ))

class TestCoapReceiveData(
    AsyncTestCase,
    WalterModemAsserts,
    NetworkConnectivity
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent
        await self.ensure_network_connection(modem)
        self.register_fail_on_cme_error(modem)
    
        await modem._run_cmd(
            at_cmd='AT+SQNCOAPCREATE=0,"coap.me",5683',
            at_rsp=b'+SQNCOAPCONNECTED: '
        )

    async def async_teardown(self):
        self.unregister_fail_on_cme_error(modem)
        await modem._run_cmd(
            at_cmd='AT+SQNCOAPCLOSE=0',
            at_rsp=b'OK'
        )

    # Context ID range validation

    async def test_fails_below_min_ctx_id(self):
        rsp = ModemRsp()
        self.assert_false(await modem.coap_receive_data(
            ctx_id=-1,
            msg_id=1,
            length=10
        ))

    async def test_fails_above_max_ctx_id(self):
        rsp = ModemRsp()
        self.assert_false(await modem.coap_receive_data(
            ctx_id=3,
            msg_id=1,
            length=10
        ))

    async def test_rsp_result_no_such_profile_on_invalid_ctx_id(self):
        rsp = ModemRsp()
        await modem.coap_receive_data(ctx_id=7, msg_id=1, length=10, rsp=rsp)
        self.assert_equal(WalterModemState.NO_SUCH_PROFILE, rsp.result)

    # max_bytes range validation

    async def test_fails_below_min_max_bytes(self):
        rsp = ModemRsp()
        self.assert_false(await modem.coap_receive_data(
            ctx_id=0,
            msg_id=1,
            length=10,
            max_bytes=-1,
        ))

    async def test_fails_above_max_max_bytes(self):
        rsp = ModemRsp()
        self.assert_false(await modem.coap_receive_data(
            ctx_id=0,
            msg_id=1,
            length=10,
            max_bytes=2048
        ))

    async def test_rsp_result_error_on_invalid_max_bytes(self):
        rsp = ModemRsp()
        await modem.coap_receive_data(ctx_id=0, msg_id=1, length=10, max_bytes=-1, rsp=rsp)
        self.assert_equal(WalterModemState.ERROR, rsp.result)

    # Length validation

    async def test_fails_with_negative_length(self):
        rsp = ModemRsp()
        self.assert_false(await modem.coap_receive_data(
            ctx_id=0,
            msg_id=1,
            length=-1
        ))

    async def test_rsp_result_error_on_negative_length(self):
        rsp = ModemRsp()
        await modem.coap_receive_data(ctx_id=0, msg_id=1, length=-1, rsp=rsp)
        self.assert_equal(WalterModemState.ERROR, rsp.result)

    # Method run

    async def test_sends_expected_at_cmd(self):
        modem.coap_context_states[0].rings.clear()
        await modem._run_cmd('AT+SQNCOAPOPT=0,0,11,"test"',b'OK')
        await modem.coap_send(0,WalterModemCoapType.CON,WalterModemCoapMethod.GET)

        while len(modem.coap_context_states[0].rings) <= 0:
            await asyncio.sleep(3)
        ring = modem.coap_context_states[0].rings.pop()

        await self.assert_sends_at_command(
            modem,
            f'AT+SQNCOAPRCV={ring.ctx_id},{ring.msg_id},512',
            lambda: modem.coap_receive_data(
                ctx_id=ring.ctx_id,
                msg_id=ring.msg_id,
                length=ring.length,
                max_bytes=512
            )
        )
    
    async def test_coap_response_is_set_in_modem_rsp(self):
        modem.coap_context_states[0].rings.clear()
        await modem._run_cmd('AT+SQNCOAPOPT=0,0,11,"test"',b'OK')
        await modem.coap_send(0,WalterModemCoapType.CON,WalterModemCoapMethod.GET)

        while len(modem.coap_context_states[0].rings) <= 0:
            await asyncio.sleep(3)
        ring = modem.coap_context_states[0].rings.pop()

        modem_rsp = ModemRsp()
        await modem.coap_receive_data(
            ctx_id=ring.ctx_id,
            msg_id=ring.msg_id,
            length=ring.length,
            rsp=modem_rsp
        )
        self.assert_is_instance(modem_rsp.coap_rcv_response, ModemCoapResponse)
        print(f'\n  payload: {modem_rsp.coap_rcv_response.payload}')

class TestCoapReceiveOptions(
    AsyncTestCase,
    WalterModemAsserts,
    NetworkConnectivity
):
    async def async_setup(self):
        await modem.begin() # Modem begin is idempotent
        await self.ensure_network_connection(modem)
        self.register_fail_on_cme_error(modem)
    
        await modem._run_cmd(
            at_cmd='AT+SQNCOAPCREATE=0,"coap.me",5683',
            at_rsp=b'+SQNCOAPCONNECTED: '
        )

    async def async_teardown(self):
        self.unregister_fail_on_cme_error(modem)
        await modem._run_cmd(
            at_cmd='AT+SQNCOAPCLOSE=0',
            at_rsp=b'OK'
        )

    # Context ID range validation

    async def test_fails_below_min_ctx_id(self):
        rsp = ModemRsp()
        self.assert_false(await modem.coap_receive_options(
            ctx_id=-1,
            msg_id=1
        ))

    async def test_fails_above_max_ctx_id(self):
        rsp = ModemRsp()
        self.assert_false(await modem.coap_receive_options(
            ctx_id=3,
            msg_id=1
        ))

    async def test_rsp_result_no_such_profile_on_invalid_ctx_id(self):
        rsp = ModemRsp()
        await modem.coap_receive_options(ctx_id=7, msg_id=1, rsp=rsp)
        self.assert_equal(WalterModemState.NO_SUCH_PROFILE, rsp.result)

    # max_options range validation

    async def test_fails_below_min_max_options(self):
        rsp = ModemRsp()
        self.assert_false(await modem.coap_receive_options(
            ctx_id=0,
            msg_id=1,
            max_options=-1,
        ))

    async def test_fails_above_max_max_options(self):
        rsp = ModemRsp()
        self.assert_false(await modem.coap_receive_options(
            ctx_id=0,
            msg_id=1,
            max_options=33
        ))

    async def test_rsp_result_error_on_invalid_max_options(self):
        rsp = ModemRsp()
        await modem.coap_receive_options(ctx_id=0, msg_id=1, max_options=-1, rsp=rsp)
        self.assert_equal(WalterModemState.ERROR, rsp.result)

    # Method run

    async def test_sends_expected_at_cmd(self):
        modem.coap_context_states[0].rings.clear()
        await modem._run_cmd('AT+SQNCOAPOPT=0,0,11,"test"',b'OK')
        await modem.coap_send(0,WalterModemCoapType.CON,WalterModemCoapMethod.GET)

        while len(modem.coap_context_states[0].rings) <= 0:
            await asyncio.sleep(3)
        ring = modem.coap_context_states[0].rings.pop()

        await self.assert_sends_at_command(
            modem,
            f'AT+SQNCOAPRCVO={ring.ctx_id},{ring.msg_id},12',
            lambda: modem.coap_receive_options(
                ctx_id=ring.ctx_id,
                msg_id=ring.msg_id,
                max_options=12
            )
        )
    
    async def test_coap_options_is_set_in_modem_rsp(self):
        modem.coap_context_states[0].rings.clear()
        await modem._run_cmd('AT+SQNCOAPOPT=0,0,11,"test"',b'OK')
        await modem.coap_send(0,WalterModemCoapType.CON,WalterModemCoapMethod.GET)

        while len(modem.coap_context_states[0].rings) <= 0:
            await asyncio.sleep(3)
        ring = modem.coap_context_states[0].rings.pop()

        modem_rsp = ModemRsp()
        await modem.coap_receive_options(
            ctx_id=ring.ctx_id,
            msg_id=ring.msg_id,
            rsp=modem_rsp
        )
        self.assert_is_instance(modem_rsp.coap_options[0], ModemCoapOption)

testcases = [testcase() for testcase in (
    TestCoapContextCreate,
    TestCoapContextClose,
    TestCoapSetOptions,
    TestCoapSetHeader,
    TestCoapSend,
    TestCoapReceiveData,
    TestCoapReceiveOptions,
)]

for testcase in testcases:
    testcase.run()