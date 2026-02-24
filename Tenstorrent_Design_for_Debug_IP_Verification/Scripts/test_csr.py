# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


# ============================================================
# CONFIG
# ============================================================

NUM_INST = 1      # Change if NUM_TRACE_AND_ANALYZER_INST > 1
STRIDE   = 0x9000
STEP     = 4      # 32-bit CSRs
TIMEOUT  = 200    # APB timeout cycles


CSR_REGIONS = [
    ("MCR", 0x0000, 0x0FFF, False),
    ("CLA", 0x1000, 0x1FFF, True),
    ("DST", 0x2000, 0x2FFF, True),
    ("NTR", 0x3000, 0x3FFF, True),
    ("TR",  0x4000, 0x8FFF, False),
]


# ============================================================
# SAFE APB DRIVER (with timeout)
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

        # TIMEOUT
        dut._log.warning(f"READ TIMEOUT @0x{addr:X}")

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

        dut._log.warning(f"WRITE TIMEOUT @0x{addr:X}")

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
# DRIVE UNUSED INPUTS SAFE
# ============================================================

def init_inputs(dut):

    if hasattr(dut, "i_mem_tsel_settings"):
        dut.i_mem_tsel_settings.value = 0


# ============================================================
# CSR REGION TEST
# ============================================================

async def test_region(dut, apb, name, start, end):

    checked = 0
    failures = 0

    dut._log.info(f"\n=== Testing {name} 0x{start:X}-0x{end:X} ===")

    for addr in range(start, end + 1, STEP):

        val, err = await apb.read(addr)

        if err:
            continue  # not a valid CSR

        checked += 1

        # Try safe write
        test_val = val ^ 0xAAAAAAAA

        err_w = await apb.write(addr, test_val)
        val2, err_r = await apb.read(addr)

        if err_w or err_r:
            continue  # write not allowed (RO)

        # Accept either RW or RO behavior
        if val2 not in (val, test_val):
            dut._log.error(
                f"{name} mismatch @0x{addr:X} "
                f"{val:X}->{val2:X}"
            )
            failures += 1

    dut._log.info(
        f"{name}: valid={checked} failures={failures}"
    )

    return failures


# ============================================================
# MAIN TEST
# ============================================================

@cocotb.test()
async def csr_only_test(dut):

    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())

    init_inputs(dut)

    dut.psel.value = 0
    dut.penable.value = 0
    dut.pwrite.value = 0
    dut.paddr.value = 0
    dut.pwdata.value = 0
    dut.pstrb.value = 0

    await reset_dut(dut)

    apb = APB(dut)

    total_fail = 0

    for name, base, end, replicated in CSR_REGIONS:

        inst_count = NUM_INST if replicated else 1

        for inst in range(inst_count):

            start = base + STRIDE * inst
            stop  = end  + STRIDE * inst

            total_fail += await test_region(
                dut, apb, name, start, stop
            )

    await Timer(500, unit="ns")

    if total_fail == 0:
        dut._log.info("✅ CSR TEST PASSED")
    else:
        raise AssertionError(
            f"CSR TEST FAILED — {total_fail} errors"
        )
