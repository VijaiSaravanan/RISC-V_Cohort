import cocotb
from cocotb.triggers import Timer
import random


@cocotb.test()
async def basic_addition_test(dut):
    """Check if Wallace tree sums inputs correctly"""

    IN_N = int(dut.IN_N)  # number of inputs
    W = int(dut.W)        # bit width

    # Create random input values
    inputs = [random.randint(-(2**(W-1)), 2**(W-1)-1) for _ in range(IN_N)]

    # Pack into flat vector
    flat_val = 0
    for i, val in enumerate(inputs):
        # mask to W bits
        masked_val = val & ((1 << W) - 1)
        flat_val |= masked_val << (i * W)

    dut.in_vec_flat.value = flat_val

    # Wait for combinational logic to settle
    await Timer(1, units="ns")

    # Golden reference
    expected = sum(inputs)

    dut_val = dut.out.value.signed_integer
    assert dut_val == expected, f"Mismatch! Got {dut_val}, expected {expected}"


@cocotb.test()
async def multiple_random_tests(dut):
    """Run multiple random vectors"""

    IN_N = int(dut.IN_N)
    W = int(dut.W)

    for _ in range(10):
        inputs = [random.randint(-(2**(W-1)), 2**(W-1)-1) for _ in range(IN_N)]

        flat_val = 0
        for i, val in enumerate(inputs):
            masked_val = val & ((1 << W) - 1)
            flat_val |= masked_val << (i * W)

        dut.in_vec_flat.value = flat_val
        await Timer(1, units="ns")

        expected = sum(inputs)
        dut_val = dut.out.value.signed_integer
        assert dut_val == expected, f"Mismatch! Got {dut_val}, expected {expected}"
