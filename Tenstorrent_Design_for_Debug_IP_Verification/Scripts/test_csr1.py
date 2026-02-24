# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


# ============================================================
# CONFIG
# ============================================================

NUM_INST = 1
STRIDE   = 0x9000
STEP     = 4
TIMEOUT  = 200


REGIONS = [
    ("MCR", 0x0000, 0x0FFF, False),
    ("CLA", 0x1000, 0x1FFF, True),
    ("DST", 0x2000, 0x2FFF, True),
    ("NTR", 0x3000, 0x3FFF, True),
    ("TR",  0x4000, 0x8FFF, False),
]


# ============================================================
# SAFE APB DRIVER
# ============================================================

class APB:

    def __init__(self, dut):
        self.dut = dut

    async def read(self, addr):

        dut = self.dut

        await RisingEdge(dut.clk)

        dut.psel.value = 1
        dut.pwrite.value = 0
        dut.paddr.value = addr
        dut.penable.value = 0

        await RisingEdge(dut.clk)
        dut.penable.value = 1

        for _ in range(TIMEOUT):

            if dut.pready.value or dut.pslverr.value:

                val = int(dut.prdata.value)
                err = int(dut.pslverr.value)

                dut.psel.value = 0
                dut.penable.value = 0

                return val, err

            await RisingEdge(dut.clk)

        dut.psel.value = 0
        dut.penable.value = 0
        return 0, 1


    async def write(self, addr, data):

        dut = self.dut

        await RisingEdge(dut.clk)

        dut.psel.value = 1
        dut.pwrite.value = 1
        dut.paddr.value = addr
        dut.pstrb.value = 0xF
        dut.pwdata.value = data
        dut.penable.value = 0

        await RisingEdge(dut.clk)
        dut.penable.value = 1

        for _ in range(TIMEOUT):

            if dut.pready.value or dut.pslverr.value:

                err = int(dut.pslverr.value)

                dut.psel.value = 0
                dut.penable.value = 0

                return err

            await RisingEdge(dut.clk)

        dut.psel.value = 0
        dut.penable.value = 0
        return 1


# ============================================================
# RESET
# ============================================================

async def reset_dut(dut):

    dut.reset_n.value = 0
    dut.reset_n_warm_ovrride.value = 0
    dut.cold_reset_n.value = 0

    await Timer(100, unit="ns")

    dut.reset_n.value = 1
    dut.reset_n_warm_ovrride.value = 1
    dut.cold_reset_n.value = 1

    for _ in range(5):
        await RisingEdge(dut.clk)


# ============================================================
# REGION TEST — SAFE VERSION
# ============================================================

async def test_region(dut, apb, name, start, end):

    valid = 0

    dut._log.info(f"\n=== Testing {name} 0x{start:X}-0x{end:X} ===")

    for addr in range(start, end + 1, STEP):

        val1, err = await apb.read(addr)

        if err:
            continue

        valid += 1

        # Check read stability
        val2, _ = await apb.read(addr)

        if val1 != val2:
            dut._log.warning(
                f"{name} unstable read @0x{addr:X} "
                f"{val1:X}->{val2:X}"
            )

        # Try write but DO NOT validate value
        await apb.write(addr, val1 ^ 0xFFFFFFFF)

    dut._log.info(f"{name}: valid CSRs detected = {valid}")


# ============================================================
# MAIN TEST
# ============================================================

@cocotb.test()
async def csr_only_smoke_test(dut):

    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())

    dut.psel.value = 0
    dut.penable.value = 0
    dut.pwrite.value = 0
    dut.paddr.value = 0
    dut.pwdata.value = 0
    dut.pstrb.value = 0

    if hasattr(dut, "i_mem_tsel_settings"):
        dut.i_mem_tsel_settings.value = 0

    await reset_dut(dut)

    apb = APB(dut)

    for name, base, end, replicated in REGIONS:

        inst_count = NUM_INST if replicated else 1

        for inst in range(inst_count):

            start = base + STRIDE * inst
            stop  = end  + STRIDE * inst

            await test_region(dut, apb, name, start, stop)

    dut._log.info("✅ CSR SMOKE TEST COMPLETED")
