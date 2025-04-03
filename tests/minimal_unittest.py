import asyncio
import time

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
    
    def print_success(self):
        print(f'{GREEN_FG}✔{RESET}', end=' ')
    
    def print_fail(self, msg):
        print(f'{RED_FG}✘ FAIL:{RESET}', msg, end=' ')
    
    def print_error(self, msg):
        print(f'{YELLOW_BG}{BLACK_FG}⚠ ERROR:{RESET}', msg, end=' ')

    def assert_equal(self, a, b):
        self.tests_run += 1
        if a != b:
            self.failed += 1
            self.print_fail(f'{a!r} != {b!r}')
        else:
            self.passed += 1
            self.print_success()

    def assert_not_equal(self, a, b):
        self.tests_run += 1
        if a == b:
            self.failed += 1
            self.print_fail(f'{a!r} == {b!r}')
        else:
            self.passed += 1
            self.print_success()

    def assert_true(self, a):
        self.tests_run += 1
        if not a:
            self.failed += 1
            self.print_fail(f'condition: "{a}" is not truthy')
        else:
            self.passed += 1
            self.print_success()

    def assert_false(self, a):
        self.tests_run += 1
        if a:
            self.failed += 1
            self.print_fail(f'condition: "{a}" is not falsy')
        else:
            self.passed += 1
            self.print_success()

    def assert_is(self, a, b):
        self.tests_run += 1
        if a is not b:
            self.failed += 1
            self.print_fail(f'{a!r} is not {b!r}')
        else:
            self.passed += 1
            self.print_success()

    def assert_is_not(self, a, b):
        self.tests_run += 1
        if a is b:
            self.failed += 1
            self.print_fail(f'{a!r} is {b!r}')
        else:
            self.passed += 1
            self.print_success()
    
    def assert_is_none(self, a):
        self.tests_run +=1
        if a is not None:
            self.failed += 1
            self.print_fail(f'{a!r} is not None')
        else:
            self.passed += 1
            self.print_success()
    
    def assert_is_not_none(self, a):
        self.tests_run +=1
        if a is None:
            self.failed += 1
            self.print_fail(f'{a!r} is None')
        else:
            self.passed += 1
            self.print_success()

    def assert_in(self, a, b):
        self.tests_run += 1
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
                    self.print_error(e)
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
                        self.print_error(e)
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
        expected_cmd: str,
        method: callable,
        at_rsp_pattern: bytes = b'OK',
        timeout_s = 5
    ):
        self.tests_run += 1
        if callable(method):
            sent_cmd = None

            def cmd_handler(cmd, at_rsp):
                nonlocal sent_cmd
                sent_cmd = cmd.at_cmd
            modem_instance._register_application_queue_rsp_handler(at_rsp_pattern, cmd_handler)

            await method()
            
            for _ in range(timeout_s):
                if sent_cmd is not None: break
                await asyncio.sleep(1)
            modem_instance._unregister_application_queue_rsp_handler(cmd_handler)

            if expected_cmd == sent_cmd:
                self.passed += 1
                self.print_success()
            else:
                self.failed += 1
                self.print_fail(f'Sent command: {sent_cmd} is not expected: {expected_cmd}')
        else:
            self.errors += 1
            self.print_error('Provided method is not callable')
