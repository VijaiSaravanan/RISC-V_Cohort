import cocotb
from cocotb.triggers import Timer
import random


async def apply_and_check(dut, a, b, cin):
    """Helper: drive inputs and check outputs"""
    dut.a.value = a
    dut.b.value = b
    dut.cin.value = cin
    await Timer(1, "ns")  # wait for combinational logic

    expected = a + b + cin
    exp_sum = expected & 0xF       # 4-bit result
    exp_cout = (expected >> 4) & 1 # carry out

    got_sum = int(dut.sum.value)
    got_cout = int(dut.cout.value)

    assert got_sum == exp_sum, \
        f"FAIL: a={a}, b={b}, cin={cin} -> sum={got_sum}, expected {exp_sum}"
    assert got_cout == exp_cout, \
        f"FAIL: a={a}, b={b}, cin={cin} -> cout={got_cout}, expected {exp_cout}"


@cocotb.test()
async def test_basic(dut):
    """Basic sanity cases"""
    await apply_and_check(dut, 0, 0, 0)
    await apply_and_check(dut, 1, 1, 0)
    await apply_and_check(dut, 7, 8, 0)
    await apply_and_check(dut, 15, 15, 1)


@cocotb.test()
async def test_all_combinations(dut):
    """Exhaustive test: all possible inputs"""
    for a in range(16):
        for b in range(16):
            for cin in [0, 1]:
                await apply_and_check(dut, a, b, cin)


@cocotb.test()
async def test_random(dut):
    """Random stress test with 5-bit values masked to 4-bit"""
    for _ in range(50):
        a = random.randint(0, 31)
        b = random.randint(0, 31)
        cin = random.randint(0, 1)
        await apply_and_check(dut, a & 0xF, b & 0xF, cin)
