import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles
import random


# ============================================================
# Safe signal helpers
# ============================================================

def safe_set(dut, name, value):
    try:
        sig = getattr(dut, name)
        width = len(sig)
        sig.value = value & ((1 << width) - 1)
    except:
        pass


def safe_get(dut, name, default=0):
    try:
        return int(getattr(dut, name).value)
    except:
        return default


# ============================================================
# Register map (simplified)
# ============================================================

class R:

    DST_CTRL = 0x0010
    DST_STATUS = 0x0014
    DST_DEPTH_CFG = 0x0018
    DST_WR_PTR = 0x0024

    CLA_CTRL = 0x0040
    CLA_STATUS = 0x0044
    CLA_SIG_MASK_0 = 0x0048
    CLA_SIG_MATCH_0 = 0x004C

    NTR_CTRL = 0x00A0
    NTR_STATUS = 0x00A4

    TR_WR_COUNT = 0x010C

    TS_CTRL = 0x0200
    TS_LO = 0x0208


# ============================================================
# APB Master
# ============================================================

class APBMaster:

    def __init__(self, dut):
        self.dut = dut

    async def idle(self):

        d = self.dut

        d.psel.value = 0
        d.penable.value = 0
        d.pwrite.value = 0
        d.paddr.value = 0
        d.pwdata.value = 0
        d.pstrb.value = 0xF


    async def write(self, addr, data):

        d = self.dut

        await RisingEdge(d.clk)

        d.psel.value = 1
        d.penable.value = 0
        d.pwrite.value = 1
        d.paddr.value = addr
        d.pwdata.value = data
        d.pstrb.value = 0xF

        await RisingEdge(d.clk)

        d.penable.value = 1

        while not int(d.pready.value):
            await RisingEdge(d.clk)

        await self.idle()


    async def read(self, addr):

        d = self.dut

        await RisingEdge(d.clk)

        d.psel.value = 1
        d.penable.value = 0
        d.pwrite.value = 0
        d.paddr.value = addr

        await RisingEdge(d.clk)

        d.penable.value = 1

        while not int(d.pready.value):
            await RisingEdge(d.clk)

        data = int(d.prdata.value)

        await self.idle()

        return data


# ============================================================
# Debug Bus Driver
# ============================================================

class DebugBusDriver:

    def __init__(self, dut):
        self.dut = dut

    def drive(self, value):

        value &= 0xFFFF

        safe_set(self.dut, "hw0", value)
        safe_set(self.dut, "hw1", value)
        safe_set(self.dut, "hw2", value)
        safe_set(self.dut, "hw3", value)

    def random(self):
        self.drive(random.randint(0, 0xFFFF))


# ============================================================
# Reset
# ============================================================

async def reset(dut):

    dut.reset_n.value = 0
    dut.reset_n_warm_ovrride.value = 0
    dut.cold_reset_n.value = 0

    await ClockCycles(dut.clk, 20)

    dut.cold_reset_n.value = 1
    dut.reset_n_warm_ovrride.value = 1
    dut.reset_n.value = 1

    await ClockCycles(dut.clk, 10)


async def start_env(dut):

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    await reset(dut)

    apb = APBMaster(dut)
    dbg = DebugBusDriver(dut)

    return apb, dbg


# ============================================================
# Test 1
# ============================================================

@cocotb.test()
async def test_01_reset(dut):

    apb, dbg = await start_env(dut)

    assert int(dut.reset_n.value) == 1


# ============================================================
# Test 2
# ============================================================

@cocotb.test()
async def test_02_apb_basic(dut):

    apb, dbg = await start_env(dut)

    val = await apb.read(R.DST_CTRL)

    dut._log.info(f"read {val}")


# ============================================================
# Test 3
# ============================================================

@cocotb.test()
async def test_03_apb_write_read(dut):

    apb, dbg = await start_env(dut)

    await apb.write(R.DST_DEPTH_CFG, 16)

    val = await apb.read(R.DST_DEPTH_CFG)

    assert val == 16


# ============================================================
# Debug bus tests
# ============================================================

@cocotb.test()
async def test_10_debug_bus_activity(dut):

    apb, dbg = await start_env(dut)

    await apb.write(R.DST_CTRL, 1)

    for i in range(64):

        dbg.drive(i)

        await RisingEdge(dut.clk)


# ============================================================
# CLA trigger test
# ============================================================

@cocotb.test()
async def test_20_cla_trigger(dut):

    apb, dbg = await start_env(dut)

    await apb.write(R.CLA_SIG_MASK_0, 0xFFFF)
    await apb.write(R.CLA_SIG_MATCH_0, 0xBEEF)

    await apb.write(R.CLA_CTRL, 1)

    dbg.drive(0xBEEF)

    await ClockCycles(dut.clk, 5)

    st = await apb.read(R.CLA_STATUS)

    dut._log.info(f"CLA status {st}")


# ============================================================
# DST overflow
# ============================================================

@cocotb.test()
async def test_30_dst_overflow(dut):

    apb, dbg = await start_env(dut)

    await apb.write(R.DST_DEPTH_CFG, 16)

    await apb.write(R.DST_CTRL, 1)

    for _ in range(100):

        dbg.random()

        await RisingEdge(dut.clk)


# ============================================================
# NTrace injection
# ============================================================

@cocotb.test()
async def test_40_ntrace_basic(dut):

    apb, dbg = await start_env(dut)

    await apb.write(R.NTR_CTRL, 1)

    for _ in range(20):

        safe_set(dut, "IRetire", 1)
        await RisingEdge(dut.clk)


# ============================================================
# Trace sink
# ============================================================

@cocotb.test()
async def test_50_trace_sink(dut):

    apb, dbg = await start_env(dut)

    await apb.write(R.DST_CTRL, 1)

    for i in range(64):

        dbg.drive(i)

        await RisingEdge(dut.clk)

    cnt = await apb.read(R.TR_WR_COUNT)

    dut._log.info(f"trace count {cnt}")


# ============================================================
# Time sync
# ============================================================

@cocotb.test()
async def test_60_timesync(dut):

    apb, dbg = await start_env(dut)

    lo = await apb.read(R.TS_LO)

    dut._log.info(f"time {lo}")


# ============================================================
# Stress test
# ============================================================

@cocotb.test()
async def test_75_random_stress(dut):

    apb, dbg = await start_env(dut)

    await apb.write(R.DST_CTRL, 1)
    await apb.write(R.CLA_CTRL, 1)
    await apb.write(R.NTR_CTRL, 1)

    for _ in range(500):

        dbg.random()

        if random.randint(0, 10) == 0:
            await apb.write(R.DST_DEPTH_CFG, random.randint(8, 64))

        await RisingEdge(dut.clk)
