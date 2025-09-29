import cocotb
from cocotb.triggers import Timer
import random

@cocotb.test()
async def adder_basic_test(dut):
    """Basic test for adder"""
    for i in range(5):
        a_val = random.randint(0, 15)
        b_val = random.randint(0, 15)
        dut.a.value = a_val
        dut.b.value = b_val

        await Timer(2, units="ns")

        expected = a_val + b_val
        assert dut.sum.value == expected, f"Mismatch: {dut.sum.value} != {expected}"
