# Minimal Unittest

This is a minimal unit-test implimentation tailored for micropython.
It includes all the standard asserts and measures how long each assert took.

## Usage

This uses the principle of test-cases; a class in which several tests are grouped.
Simply inherit from `TestCase`, prefix the test methods with "test_"
and call the `run()` method to run all tests.

Every test method should have 1 assert call.

> [!NOTE]
> `TestCase` only support synchronous methods,
> to work with asynchronous methods; inherit from `AsyncTestCase` instead.

```py
import minimal_unittest as unittest

class TestExample(unittest.TestCase):
    def test_example(self):
        # ...
        self.assert_is_not_none(var)

test_example = TestExample()
test_example.run()
```

> [!WARNING]
> It is advised to run the test files using
> [`mpremote run`](https://docs.micropython.org/en/latest/reference/mpremote.html#mpremote-command-run)\
> flashing them onto the board as `boot.py` or `main.py` may cause the tests
> to run indefinitly if not handled correctly.

## Asserts

The supported assert methods are as follows:

### Assert Equal

Asserts the two given arguments are equal.

```py
self.assert_equal('A', 'A')
```

### Assert Not Equal

Asserts the two given arguments are not equal.

```py
self.assert_not_equal('a', 'A')
```

### Assert True

Asserts the given argument evaluates truthy.

```py
self.assert_true('FOO'.isupper())
```

### Assert False

Asserts the given argument evaluates falsy.

```py
self.assert_false('Foo'.isupper())
```

### Assert Is

Assert the two given arguments are the same *(memory reference)*.

> [!WARNING]
> MicroPython, like CPython, may intern small integers and short strings for efficiency.
> This means that seemingly distinct objects might reference the same memory location:
> ```py
> a = 42
> b = 42
> assert_is(a, b)  # May pass unexpectedly
> ```
> This optimization varies by implementation and can cause unexpected results with is.
> For reliable equality checks, use == unless object identity is necessary.

```py
l = [1, 2, 3]
n = l[0]
self.assert_is(l[0], n)
```

### Assert Is Not

Assert the two given arguments are not the same *(memory reference)*.

> [!WARNING]
> The same warning stated above, for assert is, also applies here.\
> For reliable equality checks, use != unless object identity is necessary.

```py
self.assert_is_not([1], [1])
```

### Assert Is None

Assert the given argument is `None`.

```py
self.assert_is_none(None)
```

### Assert Is Not None

Assert the given argument is not `None`.

```py
self.assert_is_not_none('a')
```

### Assert In

Assert the first argument is in or part of the second argument.

```py
l = [1, 2, 3]
self.assert_in(2, l)
```

### Assert Not In

Assert the first argument is not in or part of the second argument.

```py
l = [1, 2, 3]
self.assert_not_in(4, l)
```

### Assert Is Instance

Asserts the first argument is an instance of second argument

> [!NOTE]
> The second argument can be a tuple of types,
> eg. `(str, int)` if something may be a string or int to pass

```py
self.assert_is_instance('a', str)
```

### Assert Not Is Instance

Asserts the first argument is not an instance of second argument

> [!NOTE]
> The second argument can be a tuple of types,
> eg. `(str, int)` if something may not be a string or int to pass

```py
self.assert_is_instance(4, str)
```

### Asser Does Not Throw

Asserts the callable *(first argument)*does not throw set exception(s) *(second argument)*

> [!NOTE]
> After arg1 & arg2, all additional provided arguments
> are passed onto the callable *(arg1)*.

```py
self.assert_does_not_throw(self.sum, Exception, 1, 2)
```
