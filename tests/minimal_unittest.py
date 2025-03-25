import asyncio
import time

class TestCase:
    def __init__(self):
        self.tests_run = 0
        self.passed = 0
        self.failed = 0
        self.errors = 0

    def assert_equal(self, a, b):
        self.tests_run += 1
        if a != b:
            self.failed += 1
            print(f'✘ FAIL: {a!r} != {b!r}', end=' ')
        else:
            self.passed += 1
            print('✔', end=' ')

    def assert_not_equal(self, a, b):
        self.tests_run += 1
        if a == b:
            self.failed += 1
            print(f'✘ FAIL: {a!r} == {b!r}', end=' ')
        else:
            self.passed += 1
            print('✔', end=' ')

    def assert_true(self, a):
        self.tests_run += 1
        if not a:
            self.failed += 1
            print(f'✘ FAIL: condition is not truthy', end=' ')
        else:
            self.passed += 1
            print('✔', end=' ')

    def assert_false(self, a):
        self.tests_run += 1
        if a:
            self.failed += 1
            print(f'✘ FAIL: condition is not falsy', end=' ')
        else:
            self.passed += 1
            print('✔', end=' ')

    def assert_is(self, a, b):
        self.tests_run += 1
        if a is not b:
            self.failed += 1
            print(f'✘ FAIL: {a!r} is not {b!r}', end=' ')
        else:
            self.passed += 1
            print('✔', end=' ')

    def assert_is_not(self, a, b):
        self.tests_run += 1
        if a is b:
            self.failed += 1
            print(f'✘ FAIL: {a!r} is {b!r}', end=' ')
        else:
            self.passed += 1
            print('✔', end=' ')
    
    def assert_is_none(self, a):
        self.tests_run +=1
        if a is not None:
            self.failed += 1
            print(f'✘ FAIL: {a!r} is not None', end=' ')
        else:
            self.passed += 1
            print('✔', end=' ')
    
    def assert_is_not_none(self, a):
        self.tests_run +=1
        if a is None:
            self.failed += 1
            print(f'✘ FAIL: {a!r} is None', end=' ')
        else:
            self.passed += 1
            print('✔', end=' ')

    def assert_in(self, a, b):
        self.tests_run += 1
        try:
            if a not in b:
                self.failed += 1
                print(f'✘ FAIL: {a!r} is not in {b!r}', end=' ')
            else:
                self.passed += 1
                print('✔', end=' ')
        except TypeError:
            self.failed += 1
            print(f'✘ FAIL: {b!r}, of type {type(b)}, does not support membership checks', end=' ')

    def assert_not_in(self, a, b):
        self.tests_run += 1
        try:
            if a in b:
                self.failed += 1
                print(f'✘ FAIL: {a!r} is in {b!r}', end=' ')
            else:
                self.passed += 1
                print('✔', end=' ')
        except TypeError:
            self.failed += 1
            print(f'✘ FAIL: {b!r}, of type {type(b)}, does not support membership checks', end=' ')
    
    def assert_is_instance(self, a, b):
        self.tests_run += 1
        if isinstance(b, tuple):
            for t in b:
                if not isinstance(t, type):
                    self.failed += 1
                    print(f'✘ FAIL: {b!r}; {t!r} is not a valid type', end=' ')
                    return
        elif not isinstance(b, type):
            self.failed += 1
            print(f'✘ FAIL: {b!r} is not a valid type', end=' ')
            return

        if not isinstance(a, b):
            self.failed += 1
            print(f'✘ FAIL: {a!r} is not of type {b!r}', end=' ')
        else:
            self.passed += 1
            print('✔', end=' ')

    def assert_not_is_instance(self, a, b):
        self.tests_run += 1
        if isinstance(b, tuple):
            for t in b:
                if not isinstance(t, type):
                    self.failed += 1
                    print(f'✘ FAIL: {b!r}; {t!r} is not a valid type', end=' ')
                    return
        elif not isinstance(b, type):
            self.failed += 1
            print(f'✘ FAIL: {b!r} is not a valid type', end=' ')
            return

        if isinstance(a, b):
            self.failed += 1
            print(f'✘ FAIL: {a!r} is of type {b!r}', end=' ')
        else:
            self.passed += 1
            print('✔', end=' ')

    def assert_does_not_throw(self, a: callable, b: Exception | tuple, *args):
        self.tests_run += 1
        try:
            a(*args)
            self.passed += 1
            print('✔', end=' ')
        except b as e:
            self.failed += 1
            print(f'✘ FAIL: {e!r} was thrown', end=' ')

    def run(self):
        print(self.__class__.__name__)
        print('-' * len(self.__class__.__name__))
        for name in dir(self):
            if name.startswith('test_'):
                test = getattr(self, name)
                start_time = time.ticks_ms()
                try:
                    print(f'{name:<{len(max(dir(self), key=len))}}', end=' : ')
                    test()
                except Exception as e:
                    self.errors += 1
                    print(f'⚠ ERROR: {e}', end=' ')
                finally:
                    end_time = time.ticks_ms()
                    elapsed_ms = time.ticks_diff(end_time, start_time)
                    print(f'({(elapsed_ms / 1000):.2f} s)')

        self._report_results()

    def _report_results(self):
        passed_percentage = (self.passed / self.tests_run) * 100 if self.passed else 0
        print(f'\nRan {self.tests_run} tests, {passed_percentage:.2f}% passed')
        if self.passed > 0: print(f'  {self.passed} passed')
        if self.failed > 0: print(f'  {self.failed} failed')
        if self.errors > 0: print(f'  {self.errors} errors')

class AsyncTestCase(TestCase):
    async def async_setup(self):
        """Override for async test setup"""
        pass

    async def async_teardown(self):
        """Override for async cleanup"""
        pass

    async def assert_does_not_throw(self, a: callable, b: Exception | tuple, *args):
        self.tests_run += 1
        try:
            await a(*args)
            self.passed += 1
            print('✔', end=' ')
        except b as e:
            self.failed += 1
            print(f'✘ FAIL: {e!r} was thrown', end=' ')

    def run(self):
        asyncio.run(self.async_run_tests())

    async def async_run_tests(self):
        await self.async_setup()
        try:
            for name in dir(self):
                if name.startswith('test_'):
                    test = getattr(self, name)
                    start_time = time.ticks_ms()
                    try:
                        print(f'{name:<{len(max(dir(self), key=len))}}', end=' : ')
                        try:
                            await test()
                        except TypeError:
                            test()
                    except Exception as e:
                        self.errors += 1
                        print(f'⚠ ERROR: {e}', end=' ')
                    finally:
                        end_time = time.ticks_ms()
                        elapsed_ms = time.ticks_diff(end_time, start_time)
                        print(f'({(elapsed_ms / 1000):.2f} s)')
        finally:
            await self.async_teardown()
        self._report_results()
