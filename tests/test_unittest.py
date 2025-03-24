import minimal_unittest as unittest

class TestMinimalUnitTest(unittest.TestCase):
    def test_assert_equal(self):
        self.assert_equal('A', 'A')

    def test_assert_not_equal(self):
        self.assert_not_equal('a', 'A')
    
    def test_assert_true(self):
        l = [1, 2 ,3]
        self.assert_true(isinstance(l, list) and len(l) == 3)

    def test_assert_false(self):
        self.assert_false('Foo'.isupper())

    def test_assert_is(self):
        l = [1, 2, 3]
        n = l[0]
        self.assert_is(l[0], n)
    
    def test_assert_is_not(self):
        self.assert_is_not([1], [1])

    def test_assert_is_none(self):
        self.assert_is_none(None)
    
    def test_assert_is_not_none(self):
        self.assert_is_not_none('a')

    def test_assert_in(self):
        l = [1, 2, 3]
        self.assert_in(2, l)
    
    def test_assert_not_in(self):
        l = [1, 2, 3]
        self.assert_not_in(4, l)
    
    def test_assert_is_instance(self):
        self.assert_is_instance('a', str)
    
    def test_assert_not_is_instance(self):
        self.assert_not_is_instance('a', int)

    # Makse sure the asserts fail as expected

    def test_assert_equal_fails(self):
        self.assert_equal('A', 'a')

    def test_assert_not_equal_fails(self):
        self.assert_not_equal('A', 'A')

    def test_assert_true_fails(self):
        self.assert_true(isinstance('foo', int))

    def test_assert_false_fails(self):
        self.assert_false('FOO'.isupper())

    def test_assert_is_fails(self):
        self.assert_is([1], [1])
    
    def test_assert_is_not_fails(self):
        l = [1, 2, 3]
        n = l[0]
        self.assert_is_not(l[0], n)

    def test_assert_is_none_fails(self):
        self.assert_is_none('a')
    
    def test_assert_is_not_none_fails(self):
        self.assert_is_not_none(None)

    def test_assert_in_fails(self):
        l = [1, 2, 3]
        self.assert_in(4, l)
    
    def test_assert_not_in_fails(self):
        l = [1, 2, 3]
        self.assert_not_in(2, l)
    
    def test_assert_is_instance_fails(self):
        self.assert_is_instance('a', int)
    
    def test_assert_not_is_instance_fails(self):
        self.assert_not_is_instance(1, int)
    
    def test_assert_is_instance_does_not_error(self):
        self.assert_is_instance(1, 1)
    
    def test_assert_not_is_instance_does_not_error(self):
        self.assert_not_is_instance(1, 1)


test_unittest = TestMinimalUnitTest()
test_unittest.run()