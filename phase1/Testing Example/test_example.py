import example

"""
Usage Instructions:

Dependencies:
Install pytest in terminal: pip install pytest

Commands:
Run a certain test (ex: just test_add_1):           pytest test_example.py::Test_Add::test_add_1 -v
Run a certain class of tests (ex: just Test_Add):   pytest test_example.py::Test_Add -v
Run all the tests in the file:                      pytest test_example.py -v

Test Class - helps with organizing tests for different functionalities

"""


class Test_Add:
    def test_add_1(self):
        assert example.add(2, 3) == 5

    def test_add_2(self):
        assert example.add(4, 5) == 9


class Test_Multiply:
    def test_mult_1(self):
        assert example.multiply(2, 3) == 6

    def test_mult_2(self):
        assert example.multiply(4, 5) == 20
