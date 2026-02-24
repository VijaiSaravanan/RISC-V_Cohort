# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


# -------------------------------------------------
# Reset sequence (active LOW)
# -------------------------------------------------
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


# -------------------------------------------------
# Drive unused inputs to safe values
# -------------------------------------------------
def init_unused_inputs(dut):

    dut.i_mem_tsel_settings.value = 0

    for name in [
        "hw0","hw1","hw2","hw3","hw4","hw5","hw6","hw7",
        "hw8","hw9","hw10","hw11","hw12","hw13","hw14","hw15",
        "Time_Tick","xtrigger_in","time_match_event",
        "IRetire","IType","IAddr","ILastSize","Tstamp",
        "Priv","Context","Tval","Error","TrigControl",
        "CoreTime"
    ]:
        if hasattr(dut, name):
            getattr(dut, name).value = 0

    if hasattr(dut, "EXT_TR_SlvResp"):
        dut.EXT_TR_SlvResp.value = 0

    if hasattr(dut, "JT_TR_SlvReq"):
        dut.JT_TR_SlvReq.value = 0


# -------------------------------------------------
# APB WRITE
# -------------------------------------------------
async def apb_write(dut, addr, data, pstrb):

    await RisingEdge(dut.clk)

    dut.psel.value = 1
    dut.pwrite.value = 1
    dut.paddr.value = addr
    dut.pstrb.value = pstrb
    dut.pwdata.value = data
    dut.penable.value = 0

    await RisingEdge(dut.clk)
    dut.penable.value = 1

    while (dut.pready.value == 0) and (dut.pslverr.value == 0):
        await RisingEdge(dut.clk)

    dut.psel.value = 0
    dut.penable.value = 0

    if dut.pslverr.value == 1:
        dut._log.error(f"WRITE PSLVERR at addr 0x{addr:X}")
        return True

    dut._log.info(f"WRITE OK: addr=0x{addr:X} data=0x{data:X}")
    return False


# -------------------------------------------------
# APB READ (non-fatal)
# -------------------------------------------------
async def apb_read(dut, addr, expected_data, err_expected):

    await RisingEdge(dut.clk)

    dut.psel.value = 1
    dut.pwrite.value = 0
    dut.paddr.value = addr
    dut.penable.value = 0

    await RisingEdge(dut.clk)
    dut.penable.value = 1

    while (dut.pready.value == 0) and (dut.pslverr.value == 0):
        await RisingEdge(dut.clk)

    error = False

    # ----- PSLVERR case -----
    if dut.pslverr.value == 1:

        if err_expected:
            dut._log.info(
                f"READ OK (Expected PSLVERR) addr=0x{addr:X}"
            )
        else:
            dut._log.error(
                f"UNEXPECTED PSLVERR at addr=0x{addr:X}"
            )
            error = True

    # ----- Normal read -----
    else:
        if err_expected:
            dut._log.error(
                f"Expected PSLVERR but none at addr=0x{addr:X}"
            )
            error = True
        else:
            read_val = int(dut.prdata.value)

            if read_val != expected_data:
                dut._log.error(
                    f"READ MISMATCH addr=0x{addr:X} "
                    f"got=0x{read_val:X} expected=0x{expected_data:X}"
                )
                error = True
            else:
                dut._log.info(
                    f"READ OK: addr=0x{addr:X} data=0x{read_val:X}"
                )

    dut.psel.value = 0
    dut.penable.value = 0

    return error


# -------------------------------------------------
# Parse traffic file line
# -------------------------------------------------
def parse_line(line):

    parts = line.strip().split()
    if len(parts) != 4:
        raise ValueError("Invalid traffic format")

    op = parts[0]
    addr = int(parts[1], 16)
    data = int(parts[2], 16)
    extra = int(parts[3], 16)

    return op, addr, data, extra


# -------------------------------------------------
# MAIN TEST
# -------------------------------------------------
@cocotb.test()
async def dfd_mmrs_test(dut):

    # Start clock (50 MHz)
    cocotb.start_soon(Clock(dut.clk, 20, unit="ns").start())

    init_unused_inputs(dut)

    # Initialize APB signals
    dut.paddr.value = 0
    dut.psel.value = 0
    dut.penable.value = 0
    dut.pwrite.value = 0
    dut.pstrb.value = 0
    dut.pwdata.value = 0

    await reset_dut(dut)

    filename = "cla_apb_traffic.txt"

    fail_count = 0

    with open(filename, "r") as f:
        for line in f:
            if not line.strip():
                continue

            op, addr, data, extra = parse_line(line)

            if op == "write":
                err = await apb_write(dut, addr, data, extra)
                if err:
                    fail_count += 1

            elif op == "read":
                err_expected = extra & 0x1
                err = await apb_read(dut, addr, data, err_expected)
                if err:
                    fail_count += 1

            else:
                dut._log.error(f"Unsupported operation {op}")
                fail_count += 1

    await Timer(1000, unit="ns")

    # Final result
    if fail_count == 0:
        dut._log.info("✅ ALL TRANSACTIONS PASSED")
    else:
        raise AssertionError(
            f"❌ TEST FAILED — {fail_count} transaction(s) mismatched"
        )
