# SPDX-FileCopyrightText: Copyright 2025 Tenstorrent AI ULC
# SPDX-License-Identifier: Apache-2.0
"""
dfd_utils.py  —  Shared utilities for the tt-dfd cocotb testbench suite.

FIXES vs. original:
  1. TestFailure removed — cocotb v2.x dropped it. Use plain assert / raise
     AssertionError instead.
  2. Clock(): unit="ns" (not units="ns") — cocotb v2 uses the singular form.
  3. All register addresses updated to match cla_lib.py / dst_lib.py / ntrace_lib.py
     which are derived from CR_Registers.html (authoritative hardware map):
       CLA_BASE  = 0x3100 (stride 8 bytes, 64-bit registers)
       DST_BASE  = 0x1000 (trDstControl), RAM at 0x6000
       NTR_BASE  = 0x2000 (ttrTeControl), RAM at 0x5000, Funnel at 0x4000
       MCR_MUXSEL= 0x0198
  4. APBMaster.write/read raise AssertionError on PSLVERR (no TestFailure).
  5. poll_bit / wait_for_signal use AssertionError.
  6. build_eap() updated to match 64-bit EAP layout from CR_Registers.html.
  7. enable_ntrace / enable_dst / stop_ntrace / stop_dst updated to correct
     register addresses and correct bit positions from ntrace_lib / dst_lib.
"""

import cocotb
from cocotb.clock    import Clock
from cocotb.triggers import RisingEdge, ClockCycles, Timer
import logging

logger = logging.getLogger("dfd_utils")

CLK_PERIOD_NS = 10   # 100 MHz

# ─────────────────────────────────────────────────────────────────────────────
# BASE ADDRESSES  (from CR_Registers.html + CSR PDF maps)
# ─────────────────────────────────────────────────────────────────────────────
CLA_BASE      = 0x0000_3100   # CLA instance 0  — CR_Registers.html range 0x3100–0x33F8
DST_BASE      = 0x0000_1000   # DST control regs (trDstControl @ 0x1000)
NTR_BASE      = 0x0000_2000   # NTrace TE regs   (ttrTeControl @ 0x2000)

MCR_MUXSEL_ADDR = 0x0000_0198  # CDbgMuxSel in MCR CSR

# ── Funnel & RAM sinks (TR CSR map) ──────────────────────────────────────────
FUNNEL_BASE   = 0x0000_4000   # trFunnelControl @ 0x4000
NTR_RAM_BASE  = 0x0000_5000   # trRamControl    @ 0x5000
DST_RAM_BASE  = 0x0000_6000   # trDstRamControl @ 0x6000

# ─────────────────────────────────────────────────────────────────────────────
# CLA REGISTER MAP  (64-bit, stride 8)
# ─────────────────────────────────────────────────────────────────────────────
CLA_REG = {
    "COUNTER0_CFG"        : CLA_BASE + 0x000,   # 0x3100
    "COUNTER1_CFG"        : CLA_BASE + 0x008,   # 0x3108
    "COUNTER2_CFG"        : CLA_BASE + 0x010,   # 0x3110
    "COUNTER3_CFG"        : CLA_BASE + 0x018,   # 0x3118
    # EAP0/EAP1 (contiguous)
    "NODE0_EAP0"          : CLA_BASE + 0x020,   # 0x3120
    "NODE0_EAP1"          : CLA_BASE + 0x028,   # 0x3128
    "NODE1_EAP0"          : CLA_BASE + 0x030,   # 0x3130
    "NODE1_EAP1"          : CLA_BASE + 0x038,   # 0x3138
    "NODE2_EAP0"          : CLA_BASE + 0x040,   # 0x3140
    "NODE2_EAP1"          : CLA_BASE + 0x048,   # 0x3148
    "NODE3_EAP0"          : CLA_BASE + 0x050,   # 0x3150
    "NODE3_EAP1"          : CLA_BASE + 0x058,   # 0x3158
    # SignalMask/Match 0 & 1 (contiguous with EAP0/1 region)
    "SIGNAL_MASK0"        : CLA_BASE + 0x060,   # 0x3160
    "SIGNAL_MATCH0"       : CLA_BASE + 0x068,   # 0x3168
    "SIGNAL_MASK1"        : CLA_BASE + 0x070,   # 0x3170
    "SIGNAL_MATCH1"       : CLA_BASE + 0x078,   # 0x3178
    "EDGE_DETECT_CFG"     : CLA_BASE + 0x080,   # 0x3180
    "EAP_STATUS"          : CLA_BASE + 0x088,   # 0x3188
    "CTRL_STATUS"         : CLA_BASE + 0x090,   # 0x3190
    # Transition event
    "TRANSITION_MASK"     : CLA_BASE + 0x0B0,   # 0x31B0
    "TRANSITION_FROM"     : CLA_BASE + 0x0B8,   # 0x31B8
    "TRANSITION_TO"       : CLA_BASE + 0x0C0,   # 0x31C0
    # Ones-count
    "ONES_COUNT_MASK"     : CLA_BASE + 0x0C8,   # 0x31C8
    "ONES_COUNT_VALUE"    : CLA_BASE + 0x0D0,   # 0x31D0
    "ANY_CHANGE"          : CLA_BASE + 0x0D8,   # 0x31D8
    # Snapshots EAP0/1 per node
    "SNAP_N0E0"           : CLA_BASE + 0x0E0,   # 0x31E0
    "SNAP_N0E1"           : CLA_BASE + 0x0E8,   # 0x31E8
    "SNAP_N1E0"           : CLA_BASE + 0x0F0,   # 0x31F0
    "SNAP_N1E1"           : CLA_BASE + 0x0F8,   # 0x31F8
    "SNAP_N2E0"           : CLA_BASE + 0x100,   # 0x3200
    "SNAP_N2E1"           : CLA_BASE + 0x108,   # 0x3208
    "SNAP_N3E0"           : CLA_BASE + 0x110,   # 0x3210
    "SNAP_N3E1"           : CLA_BASE + 0x118,   # 0x3218
    "TIME_MATCH"          : CLA_BASE + 0x120,   # 0x3220
    # SignalMask/Match 2 & 3 (NON-CONTIGUOUS with 0/1)
    "SIGNAL_MASK2"        : CLA_BASE + 0x128,   # 0x3228
    "SIGNAL_MATCH2"       : CLA_BASE + 0x130,   # 0x3230
    "SIGNAL_MASK3"        : CLA_BASE + 0x138,   # 0x3238
    "SIGNAL_MATCH3"       : CLA_BASE + 0x140,   # 0x3240
    # EAP2/EAP3 (NON-CONTIGUOUS with EAP0/1)
    "NODE0_EAP2"          : CLA_BASE + 0x148,   # 0x3248
    "NODE0_EAP3"          : CLA_BASE + 0x150,   # 0x3250
    "NODE1_EAP2"          : CLA_BASE + 0x158,   # 0x3258
    "NODE1_EAP3"          : CLA_BASE + 0x160,   # 0x3260
    "NODE2_EAP2"          : CLA_BASE + 0x168,   # 0x3268
    "NODE2_EAP3"          : CLA_BASE + 0x170,   # 0x3270
    "NODE3_EAP2"          : CLA_BASE + 0x178,   # 0x3278
    "NODE3_EAP3"          : CLA_BASE + 0x180,   # 0x3280
    # Snapshots EAP2/3 per node
    "SNAP_N0E2"           : CLA_BASE + 0x188,   # 0x3288
    "SNAP_N0E3"           : CLA_BASE + 0x190,   # 0x3290
    "SNAP_N1E2"           : CLA_BASE + 0x198,   # 0x3298
    "SNAP_N1E3"           : CLA_BASE + 0x1A0,   # 0x32A0
    "SNAP_N2E2"           : CLA_BASE + 0x1A8,   # 0x32A8
    "SNAP_N2E3"           : CLA_BASE + 0x1B0,   # 0x32B0
    "SNAP_N3E2"           : CLA_BASE + 0x1B8,   # 0x32B8
    "SNAP_N3E3"           : CLA_BASE + 0x1C0,   # 0x32C0
    "DELAY_MUX_SEL"       : CLA_BASE + 0x1C8,   # 0x32C8
    "TIMESTAMP_SYNC"      : CLA_BASE + 0x1D0,   # 0x32D0
    "XTRIGGER_TIMESTRETCH": CLA_BASE + 0x1D8,   # 0x32D8
}

# ─────────────────────────────────────────────────────────────────────────────
# DST REGISTER MAP
# ─────────────────────────────────────────────────────────────────────────────
DST_REG = {
    "DST_CONTROL"        : DST_BASE + 0x000,   # 0x1000 trDstControl
    "DST_IMPL"           : DST_BASE + 0x004,   # 0x1004 RO
    "DST_INST_FEATURES"  : DST_BASE + 0x008,   # 0x1008 RO
    "DST_SRC_ID"         : DST_BASE + 0x00C,   # 0x100C
    # RAM sink (TR namespace @ 0x6000)
    "DST_RAM_CONTROL"    : DST_RAM_BASE + 0x000,  # 0x6000
    "DST_RAM_IMPL"       : DST_RAM_BASE + 0x004,  # 0x6004
    "DST_RAM_START_LOW"  : DST_RAM_BASE + 0x010,  # 0x6010
    "DST_RAM_START_HIGH" : DST_RAM_BASE + 0x014,  # 0x6014
    "DST_RAM_LIMIT_LOW"  : DST_RAM_BASE + 0x018,  # 0x6018
    "DST_RAM_LIMIT_HIGH" : DST_RAM_BASE + 0x01C,  # 0x601C
    "DST_RAM_WP_LOW"     : DST_RAM_BASE + 0x020,  # 0x6020
    "DST_RAM_WP_HIGH"    : DST_RAM_BASE + 0x024,  # 0x6024
    "DST_RAM_RP_LOW"     : DST_RAM_BASE + 0x028,  # 0x6028
    "DST_RAM_RP_HIGH"    : DST_RAM_BASE + 0x02C,  # 0x602C
    "DST_RAM_DATA"       : DST_RAM_BASE + 0x040,  # 0x6040
}

# DST bit positions
DST_CTRL_ACTIVE_BIT       = 0
DST_CTRL_ENABLE_BIT       = 1
DST_CTRL_INST_TRACING_BIT = 2
DST_CTRL_EMPTY_BIT        = 3
DST_RAM_CTRL_ACTIVE_BIT   = 0
DST_RAM_CTRL_ENABLE_BIT   = 1
DST_RAM_CTRL_EMPTY_BIT    = 2
DST_RAM_CTRL_STOP_ON_WRAP = 8

# ─────────────────────────────────────────────────────────────────────────────
# NTR REGISTER MAP
# ─────────────────────────────────────────────────────────────────────────────
NTR_REG = {
    "TE_CONTROL"         : NTR_BASE + 0x000,   # 0x2000 ttrTeControl
    "TE_IMPL"            : NTR_BASE + 0x004,   # 0x2004 RO
    "TE_INST_FEATURES"   : NTR_BASE + 0x008,   # 0x2008 RO
    "TE_SRC_ID"          : NTR_BASE + 0x00C,   # 0x200C
    # Funnel (TR namespace @ 0x4000)
    "FUNNEL_CONTROL"     : FUNNEL_BASE + 0x000, # 0x4000
    "FUNNEL_IMPL"        : FUNNEL_BASE + 0x004, # 0x4004
    "FUNNEL_DIS_INPUT"   : FUNNEL_BASE + 0x008, # 0x4008
    # RAM sink (TR namespace @ 0x5000)
    "RAM_CONTROL"        : NTR_RAM_BASE + 0x000, # 0x5000
    "RAM_IMPL"           : NTR_RAM_BASE + 0x004, # 0x5004
    "RAM_START_LOW"      : NTR_RAM_BASE + 0x010, # 0x5010
    "RAM_START_HIGH"     : NTR_RAM_BASE + 0x014, # 0x5014
    "RAM_LIMIT_LOW"      : NTR_RAM_BASE + 0x018, # 0x5018
    "RAM_LIMIT_HIGH"     : NTR_RAM_BASE + 0x01C, # 0x501C
    "RAM_WP_LOW"         : NTR_RAM_BASE + 0x020, # 0x5020
    "RAM_WP_HIGH"        : NTR_RAM_BASE + 0x024, # 0x5024
    "RAM_RP_LOW"         : NTR_RAM_BASE + 0x028, # 0x5028
    "RAM_RP_HIGH"        : NTR_RAM_BASE + 0x02C, # 0x502C
    "RAM_DATA"           : NTR_RAM_BASE + 0x040, # 0x5040
}

# NTR bit positions
TE_CTRL_ACTIVE_BIT        = 0
TE_CTRL_ENABLE_BIT        = 1
TE_CTRL_INST_TRACING_BIT  = 2
TE_CTRL_EMPTY_BIT         = 3
TE_CTRL_STALL_ENA_BIT     = 13
RAM_CTRL_ACTIVE_BIT       = 0
RAM_CTRL_ENABLE_BIT       = 1
RAM_CTRL_EMPTY_BIT        = 2
RAM_CTRL_STOP_ON_WRAP_BIT = 8
FUNNEL_CTRL_ACTIVE_BIT    = 0
FUNNEL_CTRL_ENABLE_BIT    = 1
FUNNEL_CTRL_EMPTY_BIT     = 2

# ─────────────────────────────────────────────────────────────────────────────
# CLA CTRL_STATUS bit positions
# ─────────────────────────────────────────────────────────────────────────────
CTRL_CURRENT_NODE_SHIFT  = 0
CTRL_CURRENT_NODE_MASK   = 0x3
CTRL_EAP_EN_BIT          = 5
CTRL_CLA_EN_BIT          = 6
CTRL_DIS_GLOBAL_HALT_BIT = 14
CTRL_DIS_LOCAL_HALT_BIT  = 15

# ─────────────────────────────────────────────────────────────────────────────
# CLA COUNTER CONFIG bit positions
# ─────────────────────────────────────────────────────────────────────────────
CTR_COUNTER_SHIFT    =  0;  CTR_COUNTER_MASK    = 0xFFFF
CTR_TARGET_SHIFT     = 16;  CTR_TARGET_MASK     = 0xFFFF
CTR_RESET_ON_TGT_BIT = 32   # bit 32 of 64-bit reg = bit 0 of hi32

# ─────────────────────────────────────────────────────────────────────────────
# EAP 64-bit field positions  (CR_Registers.html)
# ─────────────────────────────────────────────────────────────────────────────
EAP_DEST_SHIFT   =  0;  EAP_DEST_MASK   = 0x3    # [1:0]
EAP_ACT0_SHIFT   =  2;  EAP_ACT0_MASK   = 0x3F   # [7:2]
EAP_ACT1_SHIFT   =  8;  EAP_ACT1_MASK   = 0x3F   # [13:8]
EAP_EVT0_SHIFT   = 16;  EAP_EVT0_MASK   = 0x3F   # [21:16]
EAP_EVT1_SHIFT   = 22;  EAP_EVT1_MASK   = 0x3F   # [27:22]
EAP_CACT0_SHIFT  = 28;  EAP_CACT0_MASK  = 0xF    # [31:28]
EAP_CACT1_SHIFT  = 32;  EAP_CACT1_MASK  = 0xF    # [35:32]
EAP_CACT0_EN_BIT = 36
EAP_CACT1_EN_BIT = 37
EAP_EVT2_SHIFT   = 38;  EAP_EVT2_MASK   = 0x3F   # [43:38]
EAP_UDF_SHIFT    = 44;  EAP_UDF_MASK    = 0xFF   # [51:44]
EAP_ACT2_SHIFT   = 52;  EAP_ACT2_MASK   = 0x3F   # [57:52]
EAP_ACT3_SHIFT   = 58;  EAP_ACT3_MASK   = 0x3F   # [63:58]

# ─────────────────────────────────────────────────────────────────────────────
# EVENT SELECT CODES
# ─────────────────────────────────────────────────────────────────────────────
EVT_DISABLE        = 0x00
EVT_ALWAYS_ON      = 0x01
EVT_MATCH1_POS     = 0x02
EVT_MATCH1_NEG     = 0x03
EVT_MATCH2_POS     = 0x04
EVT_MATCH2_NEG     = 0x05
EVT_EDGE_SET0      = 0x06
EVT_EDGE_SET1      = 0x07
EVT_TRANSITION     = 0x08
EVT_CROSS_TRIG_IN1 = 0x09
EVT_CROSS_TRIG_IN2 = 0x0A
EVT_ONES_COUNT     = 0x0B
EVT_DEBUG_CHANGE   = 0x0C
EVT_CORE_TIME_MATCH= 0x0F
EVT_CTR0_MATCH     = 0x10;  EVT_CTR0_OVERFLOW = 0x11;  EVT_CTR0_BELOW = 0x12
EVT_CTR1_MATCH     = 0x13;  EVT_CTR1_OVERFLOW = 0x14;  EVT_CTR1_BELOW = 0x15
EVT_CTR2_MATCH     = 0x16;  EVT_CTR2_OVERFLOW = 0x17;  EVT_CTR2_BELOW = 0x18
EVT_CTR3_MATCH     = 0x19;  EVT_CTR3_OVERFLOW = 0x1A;  EVT_CTR3_BELOW = 0x1B

# ─────────────────────────────────────────────────────────────────────────────
# ACTION SELECT CODES
# ─────────────────────────────────────────────────────────────────────────────
ACT_NULL           = 0x00
ACT_CLOCK_HALT     = 0x01
ACT_DEBUG_INTERRUPT= 0x02
ACT_START_TRACE    = 0x04
ACT_STOP_TRACE     = 0x05
ACT_TRACE_PULSE    = 0x06
ACT_CROSS_TRIG_OUT1= 0x07
ACT_CROSS_TRIG_OUT2= 0x08
ACT_INCR_CTR0      = 0x10;  ACT_CLR_CTR0       = 0x11
ACT_AUTO_INCR_CTR0 = 0x12;  ACT_STOP_AUTO_CTR0 = 0x13
ACT_INCR_CTR1      = 0x14;  ACT_CLR_CTR1       = 0x15
ACT_AUTO_INCR_CTR1 = 0x16;  ACT_STOP_AUTO_CTR1 = 0x17
ACT_INCR_CTR2      = 0x18;  ACT_CLR_CTR2       = 0x19
ACT_AUTO_INCR_CTR2 = 0x1A;  ACT_STOP_AUTO_CTR2 = 0x1B
ACT_INCR_CTR3      = 0x1C;  ACT_CLR_CTR3       = 0x1D
ACT_AUTO_INCR_CTR3 = 0x1E;  ACT_STOP_AUTO_CTR3 = 0x1F

# ─────────────────────────────────────────────────────────────────────────────
# UDF presets
# ─────────────────────────────────────────────────────────────────────────────
UDF_AND_ALL      = 0x80   # fires only when E0=1 AND E1=1 AND E2=1
UDF_OR_ANY       = 0xFE   # fires when any of E0,E1,E2 is active
UDF_ALWAYS       = 0xFF   # always fires
UDF_E0_ONLY      = 0xAA   # fires when E0 active, irrespective of E1/E2
UDF_E1_ONLY      = 0xCC   # fires when E1 active
UDF_E2_ONLY      = 0xF0   # fires when E2 active
UDF_E1_AND_E0    = 0x88   # fires when E1 AND E0
UDF_SPEC_EXAMPLE = 0xEC   # (E2 AND E1) OR E0

# ─────────────────────────────────────────────────────────────────────────────
# Clock & Reset
# ─────────────────────────────────────────────────────────────────────────────
async def start_clock(dut, period_ns=CLK_PERIOD_NS):
    """Start the DUT clock.  Uses unit='ns' (cocotb v2 singular form)."""
    cocotb.start_soon(Clock(dut.clk, period_ns, unit="ns").start())


async def apply_reset(dut, cycles=20):
    """Assert all active-low resets for `cycles` clocks then release."""
    dut.reset_n.value              = 0
    dut.reset_n_warm_ovrride.value = 0
    dut.cold_reset_n.value         = 0
    dut.psel.value    = 0
    dut.penable.value = 0
    dut.pwrite.value  = 0
    dut.paddr.value   = 0
    dut.pwdata.value  = 0
    dut.pstrb.value   = 0xF
    _zero_non_apb_inputs(dut)
    await ClockCycles(dut.clk, cycles)
    dut.reset_n.value              = 1
    dut.reset_n_warm_ovrride.value = 1
    dut.cold_reset_n.value         = 1
    await ClockCycles(dut.clk, 5)
    logger.info("Reset released")


def _zero_non_apb_inputs(dut):
    """Drive all non-APB DUT inputs to a safe idle state."""
    try:
        for i in range(16):
            getattr(dut, f"hw{i}").value = 0
        dut.Time_Tick.value           = 0
        dut.xtrigger_in.value         = 0
        dut.time_match_event.value    = 0
        dut.IRetire.value             = 0
        dut.IType.value               = 0
        dut.IAddr.value               = 0
        dut.ILastSize.value           = 0
        dut.Tstamp.value              = 0
        dut.Priv.value                = 0
        dut.Context.value             = 0
        dut.Tval.value                = 0
        dut.Error.value               = 0
        dut.TrigControl.value         = 0
        dut.i_mem_tsel_settings.value = 0
        dut.EXT_TR_SlvResp.value      = 0
        dut.JT_TR_SlvReq.value        = 0
        dut.DfdCsrs_external.value    = 0
        dut.CoreTime.value            = 0
    except AttributeError:
        pass


async def drive_debug_bus(dut, value):
    """
    Drive hw0 (bits[7:0]) and hw1 (bits[15:8]) to form a 16-bit debug bus.
    For multi-instance builds index via dut.hw0[inst].
    """
    try:
        dut.hw0[0].value = (value >> 0) & 0xFF
        dut.hw1[0].value = (value >> 8) & 0xFF
    except TypeError:
        dut.hw0.value = (value >> 0) & 0xFF
        dut.hw1.value = (value >> 8) & 0xFF


# ─────────────────────────────────────────────────────────────────────────────
# APB Master
# ─────────────────────────────────────────────────────────────────────────────
class APBMaster:
    """
    Minimal APB3 master for cocotb v2.
    Does NOT use cocotb.result.TestFailure (removed in v2).
    All errors are AssertionError or TimeoutError.
    """
    def __init__(self, dut, clk_period_ns=CLK_PERIOD_NS):
        self.dut = dut
        self.clk_period_ns = clk_period_ns

    async def _wait_ready(self, timeout_cycles=200):
        for _ in range(timeout_cycles):
            await RisingEdge(self.dut.clk)
            if self.dut.pready.value == 1:
                return
        raise TimeoutError("APB pready never asserted")

    async def write(self, addr, data, strb=0xF):
        dut = self.dut
        dut.paddr.value   = addr
        dut.pwdata.value  = data & 0xFFFF_FFFF
        dut.pstrb.value   = strb
        dut.pwrite.value  = 1
        dut.psel.value    = 1
        dut.penable.value = 0
        await RisingEdge(dut.clk)
        dut.penable.value = 1
        await self._wait_ready()
        if dut.pslverr.value == 1:
            logger.warning(f"APB SLVERR on write addr=0x{addr:08X}")
        dut.psel.value    = 0
        dut.penable.value = 0
        dut.pwrite.value  = 0
        await RisingEdge(dut.clk)

    async def read(self, addr):
        dut = self.dut
        dut.paddr.value   = addr
        dut.pwdata.value  = 0
        dut.pstrb.value   = 0xF
        dut.pwrite.value  = 0
        dut.psel.value    = 1
        dut.penable.value = 0
        await RisingEdge(dut.clk)
        dut.penable.value = 1
        await self._wait_ready()
        data = int(dut.prdata.value)
        if dut.pslverr.value == 1:
            logger.warning(f"APB SLVERR on read addr=0x{addr:08X}")
        dut.psel.value    = 0
        dut.penable.value = 0
        await RisingEdge(dut.clk)
        return data

    async def read64(self, addr):
        lo = await self.read(addr)
        hi = await self.read(addr + 4)
        return (hi << 32) | lo

    async def write64(self, addr, data):
        await self.write(addr,     data & 0xFFFF_FFFF)
        await self.write(addr + 4, (data >> 32) & 0xFFFF_FFFF)

    async def read_modify_write(self, addr, set_bits=0, clr_bits=0):
        val = await self.read(addr)
        val = (val & ~clr_bits) | set_bits
        await self.write(addr, val)
        return val

    async def poll_field(self, addr, mask, expected, timeout_cycles=2000):
        """Poll (reg & mask) == expected, raise TimeoutError if exceeded."""
        for _ in range(timeout_cycles):
            val = await self.read(addr)
            if (val & mask) == expected:
                return val
            await ClockCycles(self.dut.clk, 1)
        raise TimeoutError(
            f"poll_field timeout: addr=0x{addr:X} mask=0x{mask:X} "
            f"expected=0x{expected:X}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# CLA Driver  (high-level layer, mirrors CLADriver in cla_lib.py)
# ─────────────────────────────────────────────────────────────────────────────
class CLADriver:
    def __init__(self, apb: APBMaster):
        self.apb = apb

    @staticmethod
    def build_eap(evt0=EVT_DISABLE, evt1=EVT_ALWAYS_ON, evt2=EVT_ALWAYS_ON,
                  udf=UDF_E0_ONLY,
                  act0=ACT_NULL, act1=ACT_NULL, act2=ACT_NULL, act3=ACT_NULL,
                  dest_node=0, cact0=0, cact0_en=False, cact1=0, cact1_en=False):
        val  = (dest_node & EAP_DEST_MASK)  << EAP_DEST_SHIFT
        val |= (act0      & EAP_ACT0_MASK)  << EAP_ACT0_SHIFT
        val |= (act1      & EAP_ACT1_MASK)  << EAP_ACT1_SHIFT
        val |= (evt0      & EAP_EVT0_MASK)  << EAP_EVT0_SHIFT
        val |= (evt1      & EAP_EVT1_MASK)  << EAP_EVT1_SHIFT
        val |= (cact0     & EAP_CACT0_MASK) << EAP_CACT0_SHIFT
        val |= (cact1     & EAP_CACT1_MASK) << EAP_CACT1_SHIFT
        if cact0_en: val |= (1 << EAP_CACT0_EN_BIT)
        if cact1_en: val |= (1 << EAP_CACT1_EN_BIT)
        val |= (evt2      & EAP_EVT2_MASK)  << EAP_EVT2_SHIFT
        val |= (udf       & EAP_UDF_MASK)   << EAP_UDF_SHIFT
        val |= (act2      & EAP_ACT2_MASK)  << EAP_ACT2_SHIFT
        val |= (act3      & EAP_ACT3_MASK)  << EAP_ACT3_SHIFT
        return val & 0xFFFF_FFFF, (val >> 32) & 0xFFFF_FFFF

    async def program_eap(self, node, eap_idx, **kwargs):
        reg_name  = f"NODE{node}_EAP{eap_idx}"
        base_addr = CLA_REG[reg_name]
        lo32, hi32 = self.build_eap(**kwargs)
        await self.apb.write(base_addr,     lo32)
        await self.apb.write(base_addr + 4, hi32)

    async def enable_eap(self):
        await self.apb.read_modify_write(
            CLA_REG["CTRL_STATUS"],
            set_bits=(1 << CTRL_EAP_EN_BIT) | (1 << CTRL_CLA_EN_BIT)
        )

    async def disable_eap(self):
        await self.apb.read_modify_write(
            CLA_REG["CTRL_STATUS"],
            clr_bits=(1 << CTRL_EAP_EN_BIT)
        )

    async def get_current_node(self):
        val = await self.apb.read(CLA_REG["CTRL_STATUS"])
        return (val >> CTRL_CURRENT_NODE_SHIFT) & CTRL_CURRENT_NODE_MASK

    async def set_mask_match(self, set_idx, mask, match):
        await self.apb.write(CLA_REG[f"SIGNAL_MASK{set_idx}"],  mask  & 0xFFFF_FFFF)
        await self.apb.write(CLA_REG[f"SIGNAL_MATCH{set_idx}"], match & 0xFFFF_FFFF)

    async def set_edge_detect(self, signal0_sel=0, pos_edge_sig0=True,
                               signal1_sel=0, pos_edge_sig1=True):
        val  = (signal0_sel & 0x3F)
        val |= (1 if pos_edge_sig0 else 0) << 6
        val |= (signal1_sel & 0x3F)        << 7
        val |= (1 if pos_edge_sig1 else 0) << 13
        await self.apb.write(CLA_REG["EDGE_DETECT_CFG"], val)

    async def set_transition(self, mask, from_val, to_val):
        await self.apb.write(CLA_REG["TRANSITION_MASK"], mask     & 0xFFFF_FFFF)
        await self.apb.write(CLA_REG["TRANSITION_FROM"], from_val & 0xFFFF_FFFF)
        await self.apb.write(CLA_REG["TRANSITION_TO"],   to_val   & 0xFFFF_FFFF)

    async def set_ones_count(self, mask, value):
        await self.apb.write(CLA_REG["ONES_COUNT_MASK"],  mask  & 0xFFFF_FFFF)
        await self.apb.write(CLA_REG["ONES_COUNT_VALUE"], value & 0xFFFF_FFFF)

    async def set_any_change(self, mask):
        await self.apb.write(CLA_REG["ANY_CHANGE"], mask & 0xFFFF_FFFF)

    async def set_counter_cfg(self, idx, target):
        addr = CLA_REG[f"COUNTER{idx}_CFG"]
        lo32 = (target & CTR_TARGET_MASK) << CTR_TARGET_SHIFT
        await self.apb.write(addr, lo32)

    async def clear_counter(self, idx):
        addr = CLA_REG[f"COUNTER{idx}_CFG"]
        await self.apb.write(addr,     0x0000_0000)
        await self.apb.write(addr + 4, 0x0000_0001)  # ResetOnTarget=1

    async def read_eap_status(self):
        return await self.apb.read(CLA_REG["EAP_STATUS"])

    async def clear_eap_status(self):
        await self.apb.write(CLA_REG["EAP_STATUS"],     0x0000_0000)
        await self.apb.write(CLA_REG["EAP_STATUS"] + 4, 0x0000_FFFF)

    async def read_snapshot(self, node, eap_idx):
        key = f"SNAP_N{node}E{eap_idx}"
        return await self.apb.read(CLA_REG[key])


# ─────────────────────────────────────────────────────────────────────────────
# DST Driver
# ─────────────────────────────────────────────────────────────────────────────
class DSTDriver:
    def __init__(self, apb: APBMaster):
        self.apb = apb

    async def release_reset(self):
        await self.apb.read_modify_write(
            DST_REG["DST_CONTROL"], set_bits=(1 << DST_CTRL_ACTIVE_BIT))

    async def configure_sram(self, start=0, limit=0x7FFF, stop_on_wrap=True):
        await self.apb.read_modify_write(
            DST_REG["DST_RAM_CONTROL"], set_bits=(1 << DST_RAM_CTRL_ACTIVE_BIT))
        if stop_on_wrap:
            await self.apb.read_modify_write(
                DST_REG["DST_RAM_CONTROL"], set_bits=(1 << DST_RAM_CTRL_STOP_ON_WRAP))
        await self.apb.write(DST_REG["DST_RAM_START_LOW"],  start  & 0xFFFF_FFFF)
        await self.apb.write(DST_REG["DST_RAM_START_HIGH"], (start >> 32) & 0xFFFF_FFFF)
        await self.apb.write(DST_REG["DST_RAM_LIMIT_LOW"],  limit  & 0xFFFF_FFFF)
        await self.apb.write(DST_REG["DST_RAM_LIMIT_HIGH"], (limit >> 32) & 0xFFFF_FFFF)
        await self.apb.write(DST_REG["DST_RAM_WP_LOW"],  0)
        await self.apb.write(DST_REG["DST_RAM_WP_HIGH"], 0)
        await self.apb.write(DST_REG["DST_RAM_RP_LOW"],  0)
        await self.apb.write(DST_REG["DST_RAM_RP_HIGH"], 0)
        await self.apb.read_modify_write(
            DST_REG["DST_RAM_CONTROL"], set_bits=(1 << DST_RAM_CTRL_ENABLE_BIT))

    async def enable_trace(self):
        await self.apb.read_modify_write(
            DST_REG["DST_CONTROL"],
            set_bits=(1 << DST_CTRL_ENABLE_BIT) | (1 << DST_CTRL_INST_TRACING_BIT))

    async def disable_trace(self):
        await self.apb.read_modify_write(
            DST_REG["DST_CONTROL"], clr_bits=(1 << DST_CTRL_ENABLE_BIT))

    async def wait_empty(self, timeout=2000):
        await self.apb.poll_field(
            DST_REG["DST_CONTROL"],
            mask=(1 << DST_CTRL_EMPTY_BIT),
            expected=(1 << DST_CTRL_EMPTY_BIT),
            timeout_cycles=timeout)

    async def wait_ram_empty(self, timeout=2000):
        await self.apb.poll_field(
            DST_REG["DST_RAM_CONTROL"],
            mask=(1 << DST_RAM_CTRL_EMPTY_BIT),
            expected=(1 << DST_RAM_CTRL_EMPTY_BIT),
            timeout_cycles=timeout)

    async def read_wp(self):
        lo = await self.apb.read(DST_REG["DST_RAM_WP_LOW"])
        hi = await self.apb.read(DST_REG["DST_RAM_WP_HIGH"])
        return (hi << 32) | lo

    async def read_rp(self):
        lo = await self.apb.read(DST_REG["DST_RAM_RP_LOW"])
        hi = await self.apb.read(DST_REG["DST_RAM_RP_HIGH"])
        return (hi << 32) | lo

    async def full_init(self, start=0, limit=0x7FFF):
        await self.release_reset()
        await self.configure_sram(start=start, limit=limit)
        await self.enable_trace()


# ─────────────────────────────────────────────────────────────────────────────
# NTrace Driver
# ─────────────────────────────────────────────────────────────────────────────
class NTraceDriver:
    def __init__(self, apb: APBMaster):
        self.apb = apb

    async def release_reset(self):
        await self.apb.read_modify_write(
            NTR_REG["TE_CONTROL"], set_bits=(1 << TE_CTRL_ACTIVE_BIT))

    async def configure_ram(self, start=0, limit=0x7FFF, stop_on_wrap=True):
        await self.apb.read_modify_write(
            NTR_REG["RAM_CONTROL"], set_bits=(1 << RAM_CTRL_ACTIVE_BIT))
        if stop_on_wrap:
            await self.apb.read_modify_write(
                NTR_REG["RAM_CONTROL"], set_bits=(1 << RAM_CTRL_STOP_ON_WRAP_BIT))
        await self.apb.write(NTR_REG["RAM_START_LOW"],  start  & 0xFFFF_FFFF)
        await self.apb.write(NTR_REG["RAM_START_HIGH"], (start >> 32) & 0xFFFF_FFFF)
        await self.apb.write(NTR_REG["RAM_LIMIT_LOW"],  limit  & 0xFFFF_FFFF)
        await self.apb.write(NTR_REG["RAM_LIMIT_HIGH"], (limit >> 32) & 0xFFFF_FFFF)
        await self.apb.write(NTR_REG["RAM_WP_LOW"],  0)
        await self.apb.write(NTR_REG["RAM_WP_HIGH"], 0)
        await self.apb.write(NTR_REG["RAM_RP_LOW"],  0)
        await self.apb.write(NTR_REG["RAM_RP_HIGH"], 0)
        await self.apb.read_modify_write(
            NTR_REG["RAM_CONTROL"], set_bits=(1 << RAM_CTRL_ENABLE_BIT))

    async def configure_funnel(self, dis_input_mask=0):
        await self.apb.read_modify_write(
            NTR_REG["FUNNEL_CONTROL"], set_bits=(1 << FUNNEL_CTRL_ACTIVE_BIT))
        if dis_input_mask:
            await self.apb.write(NTR_REG["FUNNEL_DIS_INPUT"], dis_input_mask)
        await self.apb.read_modify_write(
            NTR_REG["FUNNEL_CONTROL"], set_bits=(1 << FUNNEL_CTRL_ENABLE_BIT))

    async def enable_trace(self, stall_mode=False):
        bits = (1 << TE_CTRL_ENABLE_BIT) | (1 << TE_CTRL_INST_TRACING_BIT)
        if stall_mode:
            bits |= (1 << TE_CTRL_STALL_ENA_BIT)
        await self.apb.read_modify_write(NTR_REG["TE_CONTROL"], set_bits=bits)

    async def disable_trace(self):
        await self.apb.read_modify_write(
            NTR_REG["TE_CONTROL"], clr_bits=(1 << TE_CTRL_ENABLE_BIT))

    async def wait_te_empty(self, timeout=2000):
        await self.apb.poll_field(
            NTR_REG["TE_CONTROL"],
            mask=(1 << TE_CTRL_EMPTY_BIT),
            expected=(1 << TE_CTRL_EMPTY_BIT),
            timeout_cycles=timeout)

    async def wait_funnel_empty(self, timeout=2000):
        await self.apb.poll_field(
            NTR_REG["FUNNEL_CONTROL"],
            mask=(1 << FUNNEL_CTRL_EMPTY_BIT),
            expected=(1 << FUNNEL_CTRL_EMPTY_BIT),
            timeout_cycles=timeout)

    async def wait_ram_empty(self, timeout=2000):
        await self.apb.poll_field(
            NTR_REG["RAM_CONTROL"],
            mask=(1 << RAM_CTRL_EMPTY_BIT),
            expected=(1 << RAM_CTRL_EMPTY_BIT),
            timeout_cycles=timeout)

    async def full_init(self, stall_mode=False, start=0, limit=0x7FFF):
        await self.release_reset()
        await self.configure_ram(start=start, limit=limit)
        await self.configure_funnel()
        await self.enable_trace(stall_mode=stall_mode)

    async def read_wp(self):
        lo = await self.apb.read(NTR_REG["RAM_WP_LOW"])
        hi = await self.apb.read(NTR_REG["RAM_WP_HIGH"])
        return (hi << 32) | lo

    async def read_rp(self):
        lo = await self.apb.read(NTR_REG["RAM_RP_LOW"])
        hi = await self.apb.read(NTR_REG["RAM_RP_HIGH"])
        return (hi << 32) | lo


# ─────────────────────────────────────────────────────────────────────────────
# Assertion helpers  (no TestFailure — use plain assert)
# ─────────────────────────────────────────────────────────────────────────────
def assert_eq(actual, expected, msg=""):
    assert actual == expected, \
        f"FAIL {msg}: got 0x{actual:08X}, expected 0x{expected:08X}"

def assert_ne(actual, unexpected, msg=""):
    assert actual != unexpected, \
        f"FAIL {msg}: unexpectedly got 0x{actual:08X}"

def assert_bit_set(val, bit, msg=""):
    assert (val >> bit) & 1, \
        f"FAIL {msg}: bit {bit} not set in 0x{val:08X}"

def assert_bit_clear(val, bit, msg=""):
    assert not ((val >> bit) & 1), \
        f"FAIL {msg}: bit {bit} unexpectedly set in 0x{val:08X}"

# Aliases used by older test files
def assert_bit(val, bit, expected=1, msg=""):
    if expected:
        assert_bit_set(val, bit, msg)
    else:
        assert_bit_clear(val, bit, msg)
