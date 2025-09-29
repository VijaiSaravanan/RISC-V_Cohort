import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

clk_period = 10  # ns

async def init_clock(dut):
    cocotb.start_soon(Clock(dut.clk, clk_period, units="ns").start())

@cocotb.test()
async def test_reset(dut):
    """Test synchronous reset."""
    await init_clock(dut)
    dut.rst.value = 1
    dut.en.value = 0
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)
    assert dut.count.value.to_unsigned() == 0, f"Reset failed: {dut.count.value}"

@cocotb.test()
async def test_counting(dut):
    """Test counting from 0 to 31 with enable=1."""
    await init_clock(dut)
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    dut.en.value = 1

    for i in range(32):
        await RisingEdge(dut.clk)
        assert dut.count.value.to_unsigned() == i, f"Counting failed at {i}: {dut.count.value}"

@cocotb.test()
async def test_enable_disable(dut):
    """Test that counter holds value when enable=0."""
    await init_clock(dut)
    dut.rst.value = 1
    dut.en.value = 1
    await RisingEdge(dut.clk)
    dut.rst.value = 0

    # count a few cycles with enable=1
    for _ in range(4):
        await RisingEdge(dut.clk)

    # now disable counting
    dut.en.value = 0
    await RisingEdge(dut.clk)  # wait one clock after disabling

    hold_val = dut.count.value.to_unsigned()
    for _ in range(5):
        await RisingEdge(dut.clk)
        val = dut.count.value.to_unsigned()
        assert val == hold_val, f"Counter incremented while enable=0: {val}"

@cocotb.test()
async def test_wraparound(dut):
    """Test wrap-around from 31 to 0."""
    await init_clock(dut)
    dut.rst.value = 1
    dut.en.value = 1
    await RisingEdge(dut.clk)
    dut.rst.value = 0

    # set counter to 30 manually if needed
    while dut.count.value.to_unsigned() != 31:
        await RisingEdge(dut.clk)

    # next clock should wrap to 0
    await RisingEdge(dut.clk)
    assert dut.count.value.to_unsigned() == 0, f"Wrap-around failed: {dut.count.value}"
