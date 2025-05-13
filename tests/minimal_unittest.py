import asyncio
import time
import sys

from walter_modem import Modem
from walter_modem.structs import ModemRsp
from walter_modem.enums import (
    WalterModemOpState,
    WalterModemNetworkRegState
)

GREEN_FG = '\033[32m'
RED_FG = '\033[31m'
BLACK_FG = '\033[30m'
YELLOW_FG = '\033[33m'
YELLOW_BG = '\033[43m'
RESET = '\033[0m'

class TestCase:
    def __init__(self):
        self.tests_run = 0
        self.passed = 0
        self.failed = 0
        self.errors = 0
        self._result_overwrite: tuple[bool, str] | None = (False, '')
        """For extension classes to overwrite the test result"""
    
    def print_success(self):
        print(f'{GREEN_FG}✔{RESET}', end=' ')
        self._result_overwrite = (False, '')
    
    def print_fail(self, msg):
        print(f'{RED_FG}✘ FAIL:{RESET}', msg, end=' ')
        self._result_overwrite = (False, '')
    
    def print_error(self, msg):
        print(f'{YELLOW_BG}{BLACK_FG}⚠ ERROR:{RESET}', msg, end=' ')
        self._result_overwrite = (False, '')
    
    def print_exception(self, exception):
        print(f'\n{YELLOW_BG}{BLACK_FG}!! ============== !!{RESET}')
        sys.print_exception(exception)
        print(f'{YELLOW_BG}{BLACK_FG}!! ============== !!{RESET}\n\n')
        self._result_overwrite = (False, '')

    def assert_equal(self, a, b):
        self.tests_run += 1
        if self._result_overwrite[0]:
            self.errors += 1
            self.print_error(self._result_overwrite[1])
        elif a != b:
            self.failed += 1
            self.print_fail(f'{a!r} != {b!r}')
        else:
            self.passed += 1
            self.print_success()

    def assert_not_equal(self, a, b):
        self.tests_run += 1
        if self._result_overwrite[0]:
            self.errors += 1
            self.print_error(self._result_overwrite[1])
        elif a == b:
            self.failed += 1
            self.print_fail(f'{a!r} == {b!r}')
        else:
            self.passed += 1
            self.print_success()

    def assert_true(self, a):
        self.tests_run += 1
        if self._result_overwrite[0]:
            self.errors += 1
            self.print_error(self._result_overwrite[1])
        elif not a:
            self.failed += 1
            self.print_fail(f'condition: "{a}" is not truthy')
        else:
            self.passed += 1
            self.print_success()

    def assert_false(self, a):
        self.tests_run += 1
        if self._result_overwrite[0]:
            self.errors += 1
            self.print_error(self._result_overwrite[1])
        elif a:
            self.failed += 1
            self.print_fail(f'condition: "{a}" is not falsy')
        else:
            self.passed += 1
            self.print_success()

    def assert_is(self, a, b):
        self.tests_run += 1
        if self._result_overwrite[0]:
            self.errors += 1
            self.print_error(self._result_overwrite[1])
        elif a is not b:
            self.failed += 1
            self.print_fail(f'{a!r} is not {b!r}')
        else:
            self.passed += 1
            self.print_success()

    def assert_is_not(self, a, b):
        self.tests_run += 1
        if self._result_overwrite[0]:
            self.errors += 1
            self.print_error(self._result_overwrite[1])
        elif a is b:
            self.failed += 1
            self.print_fail(f'{a!r} is {b!r}')
        else:
            self.passed += 1
            self.print_success()
    
    def assert_is_none(self, a):
        self.tests_run +=1
        if self._result_overwrite[0]:
            self.errors += 1
            self.print_error(self._result_overwrite[1])
        elif a is not None:
            self.failed += 1
            self.print_fail(f'{a!r} is not None')
        else:
            self.passed += 1
            self.print_success()
    
    def assert_is_not_none(self, a):
        self.tests_run +=1
        if self._result_overwrite[0]:
            self.errors += 1
            self.print_error(self._result_overwrite[1])
        elif a is None:
            self.failed += 1
            self.print_fail(f'{a!r} is None')
        else:
            self.passed += 1
            self.print_success()

    def assert_in(self, a, b):
        self.tests_run += 1
        if self._result_overwrite[0]:
            self.errors += 1
            self.print_error(self._result_overwrite[1])
        else:
            try:
                if a not in b:
                    self.failed += 1
                    self.print_fail(f'{a!r} is not in {b!r}')
                else:
                    self.passed += 1
                    self.print_success()
            except TypeError:
                self.failed += 1
                self.print_fail(f'{b!r}, of type {type(b)}, does not support membership checks')

    def assert_not_in(self, a, b):
        self.tests_run += 1
        if self._result_overwrite[0]:
            self.errors += 1
            self.print_error(self._result_overwrite[1])
        else:
            try:
                if a in b:
                    self.failed += 1
                    self.print_fail(f'{a!r} is in {b!r}')
                else:
                    self.passed += 1
                    self.print_success()
            except TypeError:
                self.failed += 1
                self.print_fail(f'{b!r}, of type {type(b)}, does not support membership checks')
    
    def assert_is_instance(self, a, b):
        self.tests_run += 1
        if self._result_overwrite[0]:
            self.errors += 1
            self.print_error(self._result_overwrite[1])
        else:
            if isinstance(b, tuple):
                for t in b:
                    if not isinstance(t, type):
                        self.failed += 1
                        self.print_fail(f'{b!r}; {t!r} is not a valid type')
                        return
            elif not isinstance(b, type):
                self.failed += 1
                self.print_fail(f'{b!r} is not a valid type')
                return

            if not isinstance(a, b):
                self.failed += 1
                self.print_fail(f'{a!r} is not of type {b!r}')
            else:
                self.passed += 1
                self.print_success()

    def assert_not_is_instance(self, a, b):
        self.tests_run += 1
        if self._result_overwrite[0]:
            self.errors += 1
            self.print_error(self._result_overwrite[1])
        else:
            if isinstance(b, tuple):
                for t in b:
                    if not isinstance(t, type):
                        self.failed += 1
                        self.print_fail(f'{b!r}; {t!r} is not a valid type')
                        return
            elif not isinstance(b, type):
                self.failed += 1
                self.print_fail(f'{b!r} is not a valid type')
                return

            if isinstance(a, b):
                self.failed += 1
                self.print_fail(f'{a!r} is of type {b!r}')
            else:
                self.passed += 1
                self.print_success()

    def assert_does_not_throw(self, a: callable, b: Exception | tuple, *args):
        self.tests_run += 1
        if not callable(a):
            raise TypeError(f'Expected callable, got {type(a)}')
        try:
            a(*args)
            if self._result_overwrite[0]:
                self.errors += 1
                self.print_error(self._result_overwrite[1])
                return
            self.passed += 1
            self.print_success()
        except b as e:
            self.failed += 1
            self.print_fail(f'{e!r} was thrown')

    def run(self):
        print('---')
        print(self.__class__.__name__)
        print('---')
        for name in dir(self):
            if name.startswith('test_'):
                test = getattr(self, name)
                start_time = time.ticks_ms()
                try:
                    print(f'{name[5:]:<{len(max(dir(self), key=len)) - 5}}', end=' : ')
                    test()
                except Exception as e:
                    self.tests_run += 1
                    self.errors += 1
                    self.print_error('An exception occured running the test')
                    self.print_exception(e)
                finally:
                    end_time = time.ticks_ms()
                    elapsed_ms = time.ticks_diff(end_time, start_time)
                    print(f'({(elapsed_ms / 1000):.2f}s)')

        self._report_results()

    def _report_results(self):
        passed_percentage = (self.passed / self.tests_run) * 100 if self.passed else 0
        percentage_color = GREEN_FG if passed_percentage >= 75 else (
            YELLOW_FG if passed_percentage >= 60 else RED_FG 
        )
        print(
            f'\nRan {self.tests_run} tests, '
            f'{percentage_color}{passed_percentage:.2f}%{RESET} passed'
        )
        if self.passed > 0: print(f'  {self.passed} passed')
        if self.failed > 0: print(f'  {self.failed} failed')
        if self.errors > 0: print(f'  {self.errors} errors')
        print('')

class AsyncTestCase(TestCase):
    async def async_setup(self):
        """Override for async test setup"""
        pass

    async def async_teardown(self):
        """Override for async cleanup"""
        pass

    async def assert_does_not_throw(self, a: callable, b: Exception | tuple, *args):
        self.tests_run += 1
        if not callable(a):
            raise TypeError(f'Expected callable, got {type(a)}')
        try:
            await a(*args)
            if self._result_overwrite[0]:
                self.errors += 1
                self.print_error(self._result_overwrite[1])
                return
            self.passed += 1
            self.print_success()
        except b as e:
            self.failed += 1
            self.print_fail(f'{e!r} was thrown')

    def run(self):
        asyncio.run(self.async_run_tests())

    async def async_run_tests(self):
        print('---')
        print(self.__class__.__name__)
        print('---')
        print('ⴵ Running setup...')
        try:
            await self.async_setup()
        except Exception as e:
            self.print_error(e)
            self.print_error('An exception occured running the test')
            self.print_exception(e)
            return
        print('➜ Setup complete\n')
        try:
            for name in dir(self):
                if name.startswith('test_'):
                    test = getattr(self, name)
                    start_time = time.ticks_ms()
                    try:
                        print(f'{name[5:]:<{len(max(dir(self), key=len)) - 5}}', end=' : ')
                        await test()
                    except Exception as e:
                        self.tests_run += 1
                        self.errors += 1
                        self.print_error('An exception occured running the test')
                        self.print_exception(e)
                    finally:
                        end_time = time.ticks_ms()
                        elapsed_ms = time.ticks_diff(end_time, start_time)
                        print(f'({(elapsed_ms / 1000):.2f}s)')
        finally:
            print('\nⴵ Running teardown...')
            await self.async_teardown()
            print('➜ Teardown complete')
        self._report_results()

class WalterModemAsserts:
    async def assert_sends_at_command(self,
        modem_instance,
        expected_cmd: str | tuple,
        method: callable,
        at_rsp_pattern: bytes = b'OK',
        timeout_s = 5
    ):
        self.tests_run += 1
        if callable(method):
            sent_cmd = None
            error = False

            def cmd_handler(cmd, at_rsp):
                nonlocal sent_cmd
                nonlocal error

                sent_cmd = cmd.at_cmd
                if b'ERROR' in at_rsp: error = True

            modem_instance.register_application_queue_rsp_handler(at_rsp_pattern, cmd_handler)
            modem_instance.register_application_queue_rsp_handler(b'ERROR', cmd_handler)
            modem_instance.register_application_queue_rsp_handler(b'+CME ERROR:', cmd_handler)

            await method()
            
            for _ in range(timeout_s):
                if sent_cmd is not None: break
                await asyncio.sleep(1)
            modem_instance.unregister_application_queue_rsp_handler(cmd_handler)

            if error:
                self.failed += 1
                self.print_fail(f'Sent command: {sent_cmd} resulted in an ERROR from the modem')
                return

            if ((isinstance(expected_cmd, tuple) and sent_cmd in expected_cmd) or
            (isinstance(expected_cmd, str) and sent_cmd == expected_cmd)):
                self.passed += 1
                self.print_success()
            else:
                self.failed += 1
                self.print_fail(f'Sent command: {sent_cmd} is not expected: {expected_cmd}')
        else:
            self.errors += 1
            self.print_error('Provided method is not callable')

    def _cme_err_handler(self, cmd, at_rsp):
        self._result_overwrite = (True, at_rsp[1:].decode())
    
    def register_fail_on_cme_error(self, modem_instance: Modem):
        modem_instance.register_application_queue_rsp_handler(b'+CME ERROR: ', self._cme_err_handler)
    
    def unregister_fail_on_cme_error(self, modem_instance: Modem):
        modem_instance.unregister_application_queue_rsp_handler(self._cme_err_handler)
    
class NetworkConnectivity:
    async def await_connection(self, modem_instance: Modem):
        print('Showing modem debug logs:')
        modem_instance.debug_log = True
        for _ in range(600):
            if modem_instance.get_network_reg_state() in (
                WalterModemNetworkRegState.REGISTERED_HOME,
                WalterModemNetworkRegState.REGISTERED_ROAMING
            ):
                modem_instance.debug_log = False
                return
            await asyncio.sleep(1)
        modem_instance.debug_log = False
        raise OSError('Connection Timed-out')
    
    async def ensure_network_connection(self, modem_instance: Modem):
        modem_rsp = ModemRsp()
        await modem_instance.get_op_state(rsp=modem_rsp)
        if modem_rsp.op_state is not WalterModemOpState.FULL:
            print('Establishing network connection...')
            await modem_instance.set_op_state(WalterModemOpState.FULL)
        
        await self.await_connection(modem_instance=modem_instance)
        print('Connected to network\n')