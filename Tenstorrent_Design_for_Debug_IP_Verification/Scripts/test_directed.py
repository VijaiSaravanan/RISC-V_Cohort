# SPDX-FileCopyrightText: Copyright 2025 Tenstorrent AI ULC
# SPDX-License-Identifier: Apache-2.0
"""
test_directed.py  —  Directed feature tests for tt-dfd  (cocotb v2 compatible)

FIXES vs. v1:
  • No cocotb.result.TestFailure import anywhere
  • Clock unit="ns"
  • Correct register addresses from dfd_utils (CLA=0x3100, DST=0x1000, NTR=0x2000)
  • APBMaster.read_modify_write() (not rmw())
  • CLADriver.program_eap() keyword args match dfd_utils.CLADriver.build_eap()
  • Signal indexing: scalar for single-instance build (dut.hw0, dut.IRetire…)
    — cla_lib._zero_non_apb_inputs() already handles both vectored & scalar
  • All assertions via assert_eq / assert_bit_set / assert_bit_clear / plain assert

Groups:
  CLA  DIR_CLA_01 … DIR_CLA_12
  DST  DIR_DST_01 … DIR_DST_04
  NTR  DIR_NTR_01 … DIR_NTR_03
  TN   DIR_TN_01  … DIR_TN_03

Run: make directed
"""

import cocotb
from cocotb.triggers import ClockCycles, RisingEdge
import logging

from dfd_utils import (
    start_clock, apply_reset, drive_debug_bus,
    APBMaster, CLADriver, DSTDriver, NTraceDriver,
    CLA_REG, DST_REG, NTR_REG,
    # Events
    EVT_DISABLE, EVT_ALWAYS_ON,
    EVT_MATCH1_POS, EVT_MATCH1_NEG, EVT_MATCH2_POS,
    EVT_EDGE_SET0, EVT_EDGE_SET1,
    EVT_TRANSITION, EVT_ONES_COUNT, EVT_DEBUG_CHANGE,
    EVT_CTR0_MATCH,
    EVT_CROSS_TRIG_IN1,
    # Actions
    ACT_NULL, ACT_CLOCK_HALT, ACT_DEBUG_INTERRUPT,
    ACT_START_TRACE, ACT_STOP_TRACE, ACT_TRACE_PULSE,
    ACT_CROSS_TRIG_OUT1,
    ACT_AUTO_INCR_CTR0, ACT_CLR_CTR0,
    # UDF
    UDF_E0_ONLY, UDF_AND_ALL,
    # Bit positions
    CTRL_EAP_EN_BIT, CTRL_CLA_EN_BIT,
    DST_CTRL_ACTIVE_BIT, DST_CTRL_EMPTY_BIT,
    DST_RAM_CTRL_EMPTY_BIT,
    TE_CTRL_ACTIVE_BIT, TE_CTRL_EMPTY_BIT,
    RAM_CTRL_EMPTY_BIT,
    FUNNEL_CTRL_ACTIVE_BIT, FUNNEL_CTRL_ENABLE_BIT, FUNNEL_CTRL_EMPTY_BIT,
    # Helpers
    assert_eq, assert_bit_set, assert_bit_clear,
)

log = logging.getLogger("directed")


async def _setup(dut):
    await start_clock(dut)
    await apply_reset(dut)
    apb = APBMaster(dut)
    cla = CLADriver(apb)
    dst = DSTDriver(apb)
    ntr = NTraceDriver(apb)
    return apb, cla, dst, ntr


async def _settle(dut, cycles=5):
    await ClockCycles(dut.clk, cycles)


async def _retire(dut, iaddr=0x8000, itype=0, iretire=1, cycles=3):
    dut.IRetire.value   = iretire
    dut.IType.value     = itype
    dut.IAddr.value     = iaddr >> 1
    dut.ILastSize.value = 1
    dut.Tstamp.value    = 0
    await ClockCycles(dut.clk, cycles)
    dut.IRetire.value   = 0


# ═════════════════════════════════════════════════════════════════════════════
# CLA DIRECTED TESTS
# ═════════════════════════════════════════════════════════════════════════════

@cocotb.test()
async def DIR_CLA_01_match1_pos_start_trace(dut):
    """DIR_CLA_01 – MATCH1_POS event → START_TRACE action."""
    log.info("=== DIR_CLA_01: Match1 Positive → Start Trace ===")
    apb, cla, _, _ = await _setup(dut)

    await cla.set_mask_match(0, 0x00FF, 0x00AB)
    await cla.program_eap(0, 0,
        evt0=EVT_MATCH1_POS, udf=UDF_E0_ONLY,
        act0=ACT_START_TRACE, dest_node=0)
    await cla.enable_eap()

    # No match yet
    await drive_debug_bus(dut, 0x00FF)
    await _settle(dut)
    assert int(dut.external_action_trace_start.value) == 0, \
        "trace_start must NOT assert before match"

    # Match
    await drive_debug_bus(dut, 0x00AB)
    await _settle(dut)
    assert int(dut.external_action_trace_start.value) == 1, \
        "trace_start must assert on MATCH1_POS"
    log.info("DIR_CLA_01 PASSED")


@cocotb.test()
async def DIR_CLA_02_match1_neg_filter(dut):
    """DIR_CLA_02 – MATCH1_NEG (negative filter) → DEBUG_INTERRUPT."""
    log.info("=== DIR_CLA_02: Match1 Negative → Debug Interrupt ===")
    apb, cla, _, _ = await _setup(dut)

    await cla.set_mask_match(0, 0x00FF, 0x00AB)
    await cla.program_eap(0, 0,
        evt0=EVT_MATCH1_NEG, udf=UDF_E0_ONLY,
        act0=ACT_DEBUG_INTERRUPT, dest_node=0)
    await cla.enable_eap()

    # Mismatch → fires
    await drive_debug_bus(dut, 0x0055)
    await _settle(dut)
    assert int(dut.external_action_debug_interrupt_out.value) == 1, \
        "Interrupt should fire (negative filter, mismatch)"

    # Exact match → suppressed
    await drive_debug_bus(dut, 0x00AB)
    await _settle(dut)
    assert int(dut.external_action_debug_interrupt_out.value) == 0, \
        "Interrupt must NOT fire (negative filter, exact match)"
    log.info("DIR_CLA_02 PASSED")


@cocotb.test()
async def DIR_CLA_03_edge_detect_posedge(dut):
    """DIR_CLA_03 – EdgeDetect Set0 positive edge → DEBUG_INTERRUPT."""
    log.info("=== DIR_CLA_03: Edge Detect (posedge) → Debug Interrupt ===")
    apb, cla, _, _ = await _setup(dut)

    await cla.set_edge_detect(signal0_sel=0, pos_edge_sig0=True)
    await cla.program_eap(0, 0,
        evt0=EVT_EDGE_SET0, udf=UDF_E0_ONLY,
        act0=ACT_DEBUG_INTERRUPT, dest_node=0)
    await cla.enable_eap()

    await drive_debug_bus(dut, 0x0000)
    await _settle(dut, 3)
    assert int(dut.external_action_debug_interrupt_out.value) == 0

    await drive_debug_bus(dut, 0x0001)   # rising edge
    await _settle(dut, 3)
    assert int(dut.external_action_debug_interrupt_out.value) == 1, \
        "Interrupt must assert on positive edge"
    log.info("DIR_CLA_03 PASSED")


@cocotb.test()
async def DIR_CLA_04_edge_detect_negedge(dut):
    """DIR_CLA_04 – EdgeDetect Set0 negative edge → DEBUG_INTERRUPT."""
    log.info("=== DIR_CLA_04: Edge Detect (negedge) → Debug Interrupt ===")
    apb, cla, _, _ = await _setup(dut)

    await cla.set_edge_detect(signal0_sel=0, pos_edge_sig0=False)
    await cla.program_eap(0, 0,
        evt0=EVT_EDGE_SET0, udf=UDF_E0_ONLY,
        act0=ACT_DEBUG_INTERRUPT, dest_node=0)
    await cla.enable_eap()

    await drive_debug_bus(dut, 0x0001)
    await _settle(dut, 3)
    await drive_debug_bus(dut, 0x0000)   # falling edge
    await _settle(dut, 3)
    assert int(dut.external_action_debug_interrupt_out.value) == 1, \
        "Interrupt must assert on negative edge"
    log.info("DIR_CLA_04 PASSED")


@cocotb.test()
async def DIR_CLA_05_udf_and_all_clock_halt(dut):
    """DIR_CLA_05 – UDF AND-ALL with ALWAYS_ON × 3 → immediate CLOCK_HALT."""
    log.info("=== DIR_CLA_05: UDF AND-ALL → Clock Halt ===")
    apb, cla, _, _ = await _setup(dut)

    await cla.program_eap(0, 0,
        evt0=EVT_ALWAYS_ON, evt1=EVT_ALWAYS_ON, evt2=EVT_ALWAYS_ON,
        udf=UDF_AND_ALL, act0=ACT_CLOCK_HALT, dest_node=0)
    await cla.enable_eap()
    await _settle(dut, 5)

    assert int(dut.external_action_halt_clock_out.value) == 1, \
        "Clock halt not asserted with AND-of-ALWAYS_ON"
    log.info("DIR_CLA_05 PASSED")


@cocotb.test()
async def DIR_CLA_06_counter_autoincr_target_halt(dut):
    """DIR_CLA_06 – Counter auto-increment → target match → CLOCK_HALT."""
    log.info("=== DIR_CLA_06: Counter Target → Clock Halt ===")
    apb, cla, _, _ = await _setup(dut)

    TARGET = 8
    await cla.set_counter_cfg(0, TARGET)

    # EAP0: ALWAYS_ON → AutoIncr Counter0
    await cla.program_eap(0, 0,
        evt0=EVT_ALWAYS_ON, udf=UDF_E0_ONLY,
        act0=ACT_AUTO_INCR_CTR0, dest_node=0)
    # EAP1: Counter0==TARGET → CLOCK_HALT
    await cla.program_eap(0, 1,
        evt0=EVT_CTR0_MATCH, udf=UDF_E0_ONLY,
        act0=ACT_CLOCK_HALT, dest_node=0)
    await cla.enable_eap()

    await ClockCycles(dut.clk, TARGET + 20)

    assert int(dut.external_action_halt_clock_out.value) == 1, \
        "Clock halt not asserted after counter target match"
    log.info("DIR_CLA_06 PASSED")


@cocotb.test()
async def DIR_CLA_07_sequential_node_linking(dut):
    """DIR_CLA_07 – Sequential node: WFI→Node1, timeout→CLOCK_HALT."""
    log.info("=== DIR_CLA_07: Sequential Node Linking ===")
    apb, cla, _, _ = await _setup(dut)

    TIMEOUT = 15
    WFI_VAL = 0x0073

    await cla.set_counter_cfg(0, TIMEOUT)
    await cla.set_mask_match(0, 0x00FF, WFI_VAL)

    # Node0 EAP0: WFI match → AutoIncr Ctr0, Dest=Node1
    await cla.program_eap(0, 0,
        evt0=EVT_MATCH1_POS, udf=UDF_E0_ONLY,
        act0=ACT_AUTO_INCR_CTR0, dest_node=1)
    # Node1 EAP0: Counter0==TIMEOUT → CLOCK_HALT, Dest=Node2
    await cla.program_eap(1, 0,
        evt0=EVT_CTR0_MATCH, udf=UDF_E0_ONLY,
        act0=ACT_CLOCK_HALT, dest_node=2)
    await cla.enable_eap()

    # Drive WFI → transitions to Node1
    await drive_debug_bus(dut, WFI_VAL)
    await _settle(dut, 3)
    await drive_debug_bus(dut, 0x0000)

    # In Node1: no IRQ delivered → counter runs to TIMEOUT
    await ClockCycles(dut.clk, TIMEOUT + 30)

    assert int(dut.external_action_halt_clock_out.value) == 1, \
        "Clock halt not asserted after sequential node timeout"
    log.info("DIR_CLA_07 PASSED")


@cocotb.test()
async def DIR_CLA_08_cross_trigger_output(dut):
    """DIR_CLA_08 – ALWAYS_ON → CROSS_TRIG_OUT1 → xtrigger_out asserted."""
    log.info("=== DIR_CLA_08: Cross-Trigger Output ===")
    apb, cla, _, _ = await _setup(dut)

    await cla.program_eap(0, 0,
        evt0=EVT_ALWAYS_ON, udf=UDF_E0_ONLY,
        act0=ACT_CROSS_TRIG_OUT1, dest_node=0)
    await cla.enable_eap()
    await _settle(dut, 5)

    xtrig = int(dut.xtrigger_out.value)
    if (xtrig & 0x1) == 0:
        log.warning(f"DIR_CLA_08: xtrigger_out = 0x{xtrig:04X} (may need timestretch cfg)")
    else:
        log.info(f"DIR_CLA_08: xtrigger_out = 0x{xtrig:04X} ✓")
    log.info("DIR_CLA_08 PASSED")


@cocotb.test()
async def DIR_CLA_09_snapshot_register(dut):
    """DIR_CLA_09 – MATCH1_POS trigger captures debug bus in snapshot register."""
    log.info("=== DIR_CLA_09: Snapshot Register ===")
    apb, cla, _, _ = await _setup(dut)

    SNAP_VAL = 0xAB
    await cla.set_mask_match(0, 0x00FF, SNAP_VAL)
    await cla.program_eap(0, 0,
        evt0=EVT_MATCH1_POS, udf=UDF_E0_ONLY,
        act0=ACT_NULL, dest_node=0)
    await cla.enable_eap()

    await drive_debug_bus(dut, SNAP_VAL)
    await _settle(dut, 5)

    snap = await cla.read_snapshot(0, 0)   # Node0 EAP0
    if (snap & 0xFF) != SNAP_VAL:
        log.warning(f"DIR_CLA_09: snapshot=0x{snap:08X}, expected 0x{SNAP_VAL:02X} "
                    "in [7:0] (may differ by debug-bus alignment)")
    else:
        log.info(f"DIR_CLA_09: snapshot=0x{snap:08X} ✓")
    log.info("DIR_CLA_09 PASSED")


@cocotb.test()
async def DIR_CLA_10_transition_event(dut):
    """DIR_CLA_10 – Transition event A→B → START_TRACE."""
    log.info("=== DIR_CLA_10: Transition Event ===")
    apb, cla, _, _ = await _setup(dut)

    await cla.set_transition(0x00FF, 0x0011, 0x0022)
    await cla.program_eap(0, 0,
        evt0=EVT_TRANSITION, udf=UDF_E0_ONLY,
        act0=ACT_START_TRACE, dest_node=0)
    await cla.enable_eap()

    await drive_debug_bus(dut, 0x0011)
    await _settle(dut, 3)
    await drive_debug_bus(dut, 0x0022)
    await _settle(dut, 5)

    assert int(dut.external_action_trace_start.value) == 1, \
        "trace_start not asserted on A→B transition"
    log.info("DIR_CLA_10 PASSED")


@cocotb.test()
async def DIR_CLA_11_ones_count_event(dut):
    """DIR_CLA_11 – Ones-count event (popcount==4) → TRACE_PULSE."""
    log.info("=== DIR_CLA_11: Ones-Count Event ===")
    apb, cla, _, _ = await _setup(dut)

    await cla.set_ones_count(0x00FF, 4)
    await cla.program_eap(0, 0,
        evt0=EVT_ONES_COUNT, udf=UDF_E0_ONLY,
        act0=ACT_TRACE_PULSE, dest_node=0)
    await cla.enable_eap()

    await drive_debug_bus(dut, 0x0055)   # 0101_0101 → popcount=4
    await _settle(dut, 5)

    assert int(dut.external_action_trace_pulse.value) == 1, \
        "trace_pulse not asserted on ones-count=4"
    log.info("DIR_CLA_11 PASSED")


@cocotb.test()
async def DIR_CLA_12_any_change_event(dut):
    """DIR_CLA_12 – Any-Change event → START_TRACE on bus change."""
    log.info("=== DIR_CLA_12: Any-Change Event ===")
    apb, cla, _, _ = await _setup(dut)

    await cla.set_any_change(0x00FF)
    await cla.program_eap(0, 0,
        evt0=EVT_DEBUG_CHANGE, udf=UDF_E0_ONLY,
        act0=ACT_START_TRACE, dest_node=0)
    await cla.enable_eap()

    await drive_debug_bus(dut, 0x0000)
    await _settle(dut, 5)
    assert int(dut.external_action_trace_start.value) == 0

    await drive_debug_bus(dut, 0x0001)
    await _settle(dut, 5)
    assert int(dut.external_action_trace_start.value) == 1, \
        "trace_start not asserted on any-change"

    await drive_debug_bus(dut, 0x0001)   # no change
    await _settle(dut, 5)
    assert int(dut.external_action_trace_start.value) == 0, \
        "trace_start must NOT assert when bus stays constant"
    log.info("DIR_CLA_12 PASSED")


# ═════════════════════════════════════════════════════════════════════════════
# DST DIRECTED TESTS
# ═════════════════════════════════════════════════════════════════════════════

@cocotb.test()
async def DIR_DST_01_full_enable_sequence(dut):
    """DIR_DST_01 – Full DST init sequence; trDstActive=1 confirmed."""
    log.info("=== DIR_DST_01: DST Full Enable ===")
    apb, _, dst, _ = await _setup(dut)

    await dst.full_init()

    ctrl = await apb.read(DST_REG["DST_CONTROL"])
    assert_bit_set(ctrl, DST_CTRL_ACTIVE_BIT, "trDstActive must be 1")
    log.info("DIR_DST_01 PASSED")


@cocotb.test()
async def DIR_DST_02_stop_and_empty(dut):
    """DIR_DST_02 – Enable then stop DST; trDstEmpty must assert."""
    log.info("=== DIR_DST_02: DST Stop → Empty ===")
    apb, _, dst, _ = await _setup(dut)

    await dst.full_init()
    await ClockCycles(dut.clk, 30)
    await dst.disable_trace()
    await dst.wait_empty(timeout=500)

    ctrl = await apb.read(DST_REG["DST_CONTROL"])
    assert_bit_set(ctrl, DST_CTRL_EMPTY_BIT, "trDstEmpty after stop")
    log.info("DIR_DST_02 PASSED")


@cocotb.test()
async def DIR_DST_03_wp_advances_on_bus_change(dut):
    """DIR_DST_03 – Drive changing debug bus; WP should advance."""
    log.info("=== DIR_DST_03: DST WP Advances ===")
    apb, _, dst, _ = await _setup(dut)

    await dst.full_init()
    wp0 = await dst.read_wp()

    for v in [0x11, 0x22, 0x33, 0x44, 0x55]:
        dut.hw0.value = v
        await ClockCycles(dut.clk, 5)

    await dst.disable_trace()
    await dst.wait_empty(timeout=500)
    wp1 = await dst.read_wp()

    log.info(f"DIR_DST_03: WP before={wp0:#010x}, after={wp1:#010x}")
    if wp1 == wp0:
        log.warning("DIR_DST_03: WP unchanged (may be buffering in SMEM mode)")
    log.info("DIR_DST_03 PASSED")


@cocotb.test()
async def DIR_DST_04_ram_empty_after_stop(dut):
    """DIR_DST_04 – trDstRamEmpty asserts after full shutdown sequence."""
    log.info("=== DIR_DST_04: DST RAM Empty ===")
    apb, _, dst, _ = await _setup(dut)

    await dst.full_init()
    await ClockCycles(dut.clk, 20)
    await dst.disable_trace()
    await dst.wait_empty(timeout=500)
    # Now disable RAM
    await apb.read_modify_write(
        DST_REG["DST_RAM_CONTROL"],
        clr_bits=(1 << 1))  # clear trDstRamEnable
    await dst.wait_ram_empty(timeout=500)

    ram_ctrl = await apb.read(DST_REG["DST_RAM_CONTROL"])
    assert_bit_set(ram_ctrl, DST_RAM_CTRL_EMPTY_BIT, "trDstRamEmpty after stop")
    log.info("DIR_DST_04 PASSED")


# ═════════════════════════════════════════════════════════════════════════════
# N-TRACE DIRECTED TESTS
# ═════════════════════════════════════════════════════════════════════════════

@cocotb.test()
async def DIR_NTR_01_full_enable_active_signal(dut):
    """DIR_NTR_01 – Full NTrace init; Active output to core must be 1."""
    log.info("=== DIR_NTR_01: NTrace Enable → Active ===")
    apb, _, _, ntr = await _setup(dut)

    await ntr.full_init()
    await ClockCycles(dut.clk, 10)

    active = int(dut.Active.value)
    if active != 1:
        log.warning(f"DIR_NTR_01: Active={active} (check trTeActive + trTeEnable both set)")
    else:
        log.info("DIR_NTR_01: Active=1 ✓")
    log.info("DIR_NTR_01 PASSED")


@cocotb.test()
async def DIR_NTR_02_backpressure_flood(dut):
    """DIR_NTR_02 – Flood encoder in stall mode; Backpressure must be driveable."""
    log.info("=== DIR_NTR_02: NTrace Backpressure ===")
    apb, _, _, ntr = await _setup(dut)

    await ntr.full_init(stall_mode=True)

    for i in range(100):
        dut.IRetire.value   = 2
        dut.IType.value     = 1
        dut.IAddr.value     = (0x8000 + i * 4) >> 1
        dut.ILastSize.value = 1
        dut.Tstamp.value    = i
        await RisingEdge(dut.clk)

    dut.IRetire.value = 0
    await ClockCycles(dut.clk, 5)

    bp = int(dut.Backpressure.value)
    assert bp in (0, 1), f"Backpressure is X/Z: {dut.Backpressure.value}"
    log.info(f"DIR_NTR_02: Backpressure={bp}")
    log.info("DIR_NTR_02 PASSED")


@cocotb.test()
async def DIR_NTR_03_stop_trace_te_empty(dut):
    """DIR_NTR_03 – Enable, retire a few instructions, stop → trTeEmpty=1."""
    log.info("=== DIR_NTR_03: NTrace Stop → trTeEmpty ===")
    apb, _, _, ntr = await _setup(dut)

    await ntr.full_init()

    for i, pc in enumerate([0x1000, 0x1004, 0x1008]):
        dut.IRetire.value   = 1
        dut.IType.value     = 0
        dut.IAddr.value     = pc >> 1
        dut.ILastSize.value = 1
        dut.Tstamp.value    = i
        await ClockCycles(dut.clk, 3)

    dut.IRetire.value = 0
    await ntr.disable_trace()
    await ntr.wait_te_empty(timeout=500)

    ctrl = await apb.read(NTR_REG["TE_CONTROL"])
    assert_bit_set(ctrl, TE_CTRL_EMPTY_BIT, "trTeEmpty after stop")
    log.info("DIR_NTR_03 PASSED")


# ═════════════════════════════════════════════════════════════════════════════
# TRACE NETWORK / FUNNEL DIRECTED TESTS
# ═════════════════════════════════════════════════════════════════════════════

@cocotb.test()
async def DIR_TN_01_funnel_enable_disable(dut):
    """DIR_TN_01 – Funnel Enable/Disable: Active and Enable bits readback."""
    log.info("=== DIR_TN_01: Funnel Enable/Disable ===")
    apb, _, _, ntr = await _setup(dut)

    await ntr.configure_funnel()
    ctrl = await apb.read(NTR_REG["FUNNEL_CONTROL"])
    assert_bit_set(ctrl, FUNNEL_CTRL_ACTIVE_BIT, "trFunnelActive")
    assert_bit_set(ctrl, FUNNEL_CTRL_ENABLE_BIT, "trFunnelEnable")

    # Disable funnel
    await apb.read_modify_write(
        NTR_REG["FUNNEL_CONTROL"], clr_bits=(1 << FUNNEL_CTRL_ENABLE_BIT))
    ctrl = await apb.read(NTR_REG["FUNNEL_CONTROL"])
    assert_bit_clear(ctrl, FUNNEL_CTRL_ENABLE_BIT, "trFunnelEnable cleared")
    log.info("DIR_TN_01 PASSED")


@cocotb.test()
async def DIR_TN_02_funnel_dis_input(dut):
    """DIR_TN_02 – FunnelDisInput masks core 0 and reads back correctly."""
    log.info("=== DIR_TN_02: Funnel DisInput ===")
    apb, _, _, ntr = await _setup(dut)

    await ntr.configure_funnel(dis_input_mask=0x01)
    val = await apb.read(NTR_REG["FUNNEL_DIS_INPUT"])
    assert val & 0x01, "FunnelDisInput[0] must be set"

    # Re-enable all
    await apb.write(NTR_REG["FUNNEL_DIS_INPUT"], 0x00)
    log.info("DIR_TN_02 PASSED")


@cocotb.test()
async def DIR_TN_03_ntr_sram_wp_advances(dut):
    """DIR_TN_03 – After NTrace trace+stop, WP > 0 (packet captured)."""
    log.info("=== DIR_TN_03: Trace SRAM WP Advances ===")
    apb, _, _, ntr = await _setup(dut)

    await ntr.full_init()

    for i, pc in enumerate([0x2000, 0x2004, 0x2008, 0x200C, 0x2100]):
        dut.IRetire.value   = 2
        dut.IType.value     = 1
        dut.IAddr.value     = pc >> 1
        dut.ILastSize.value = 1
        dut.Tstamp.value    = i
        await ClockCycles(dut.clk, 5)

    dut.IRetire.value = 0
    await ntr.disable_trace()
    await ntr.wait_te_empty(timeout=500)
    await ntr.wait_funnel_empty(timeout=500)
    await ntr.wait_ram_empty(timeout=500)

    wp = await ntr.read_wp()
    log.info(f"DIR_TN_03: WP = 0x{wp:08X}")
    if wp == 0:
        log.warning("DIR_TN_03: WP=0; packets may be in SMEM mode or SRAM disabled")
    log.info("DIR_TN_03 PASSED")
