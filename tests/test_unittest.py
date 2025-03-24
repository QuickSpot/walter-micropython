import minimal_unittest as unittest 

class TestMinimalUnitTest(unittest.TestCase):
    def test_assert_equal(self):
        self.assert_equal('A', 'A')
    
    def test_assert_true(self):
        l = [1, 2 ,3]
        self.assert_true(isinstance(l, list) and len(l) == 3)

    def test_assert_false(self):
        self.assert_false('Foo'.isupper())

    # Makse sure the asserts fail as expected

    def test_assert_equal_fails(self):
        self.assert_equal('A', 'a')

    def test_assert_true_fails(self):
        self.assert_true(isinstance('foo', int))

    def test_assert_false_fails(self):
        self.assert_false('A' == 'A')

test_unittest = TestMinimalUnitTest()
test_unittest.run()