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

    def assert_true(self, condition):
        self.tests_run += 1
        if not condition:
            self.failed += 1
            print(f'✘ FAIL: condition is not truthy', end=' ')
        else:
            self.passed += 1
            print('✔', end=' ')

    def assert_false(self, condition):
        self.tests_run += 1
        if condition:
            self.failed += 1
            print(f'✘ FAIL: condition is not falsy', end=' ')
        else:
            self.passed += 1
            print('✔', end=' ')

    def run(self):
        print(self.__class__.__name__)
        print('-' * len(self.__class__.__name__))
        for name in dir(self):
            if name.startswith('test_'):
                test = getattr(self, name)
                start_time = time.time()
                try:
                    print(f'{name:<{len(max(dir(self), key=len))}}', end=' : ')
                    test()
                except Exception as e:
                    self.errors += 1
                    print(f'⚠ ERROR: {e}', end=' ')
                finally:
                    end_time = time.time()
                    print(f'({(end_time - start_time):.2f} s)')

        self._report_results()

    def _report_results(self):
        print(f'\nRan {self.tests_run} tests, {(self.passed / self.tests_run) * 100}% passed')
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

    def run(self):
        asyncio.run(self.async_run_tests())

    async def async_run_tests(self):
        await self.async_setup()
        try:
            for name in dir(self):
                if name.startswith('test_'):
                    test = getattr(self, name)
                    start_time = time.time()
                    try:
                        if asyncio.iscoroutinefunction(test):
                            await test()
                        else:
                            test()
                    except Exception as e:
                        self.errors += 1
                        print(f"ERROR in {name}: {e}")
                    finally:
                        end_time = time.time()
                        self.tests_times[name] = end_time - start_time
        finally:
            await self.async_teardown()
        self._report_results()
