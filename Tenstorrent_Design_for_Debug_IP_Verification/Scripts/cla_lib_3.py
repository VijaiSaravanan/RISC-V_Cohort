# SPDX-FileCopyrightText: Copyright 2025 Tenstorrent AI ULC
# SPDX-License-Identifier: Apache-2.0
"""
cla_lib.py  —  APB bus driver, CLA register map, and CLA test helpers
for the tt-dfd Core Logic Analyzer verification suite.

All register addresses and bit-field positions are derived directly from
CR_Registers.html (the authoritative hardware register map for the 'cr'
block, offset range 0x3100 - 0x33F8).

Key structural facts that differ from the previous (incorrect) version:
  1. CLA_BASE = 0x3100  (not 0x0)
  2. EAP2/EAP3 of every node live in a NON-CONTIGUOUS region starting at
     0x3248, separate from EAP0/EAP1 (0x3120-0x3158).
  3. SignalMask/Match sets 2 & 3 are also non-contiguous (0x3228-0x3240).
  4. All registers are 64-bit (stride = 8), NOT 32-bit stride.
  5. EAP bit layout is completely different — DestNode is at [1:0], not [39:37].
  6. CTRL_STATUS: EnableEap=bit5, CurrentNode=[1:0], DisGlobal=bit14, DisLocal=bit15.
  7. EAP_STATUS W2C bits are at [47:32] (upper half-word of the 64-bit register).
  8. No counter-clear bits exist in CTRL_STATUS; clearing is done by
     writing the counter's Target field to 0, which lets ResetOnTarget fire.
"""

import cocotb
from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.clock import Clock
import logging

log = logging.getLogger("cla_lib_3")

# ──────────────────────────────────────────────────────────────────────────────
# TOP-LEVEL BASE ADDRESSES
# Derived from CR_Registers.html offset range 0x3100–0x33F8.
# Patch DST_BASE / NTR_BASE to match your build's MMR map.
# ──────────────────────────────────────────────────────────────────────────────
CLA_BASE      = 0x3100          # CLA instance 0  (CR_Registers.html base)
DST_BASE      = 0x1000     # DST instance 0  — patch from your MMR map
NTR_BASE      = 0x2000     # NTrace instance 0 — patch from your MMR map
TIMESYNC_BASE = 0x9200     # TimeSync

# ──────────────────────────────────────────────────────────────────────────────
# CLA REGISTER MAP  (absolute addresses = CLA_BASE + offset)
#
# All registers are 64-bit; stride = 8 bytes.
# IMPORTANT: EAP0/EAP1 and EAP2/EAP3 of each node are in SEPARATE regions.
# IMPORTANT: SignalMask/Match sets 0-1 and 2-3 are also in SEPARATE regions.
# Refer to CR_Registers.html for authoritative layout.
# ──────────────────────────────────────────────────────────────────────────────
CLA_REG = {
    # ── Counter Config (4 × 64-bit) ──────────────────────────────────────────
    # CDbgClaCounter<0-3>Cfg @ 0x3100, 0x3108, 0x3110, 0x3118
    "COUNTER0_CFG"         : CLA_BASE + 0x000,   # 0x3100
    "COUNTER1_CFG"         : CLA_BASE + 0x008,   # 0x3108
    "COUNTER2_CFG"         : CLA_BASE + 0x010,   # 0x3110
    "COUNTER3_CFG"         : CLA_BASE + 0x018,   # 0x3118

    # ── EAP registers — Node EAP0 and EAP1 (contiguous block) ────────────────
    # CDbgNode<N>Eap<0,1>:  Node0@0x3120/0x3128, Node1@0x3130/0x3138,
    #                       Node2@0x3140/0x3148, Node3@0x3150/0x3158
    "NODE0_EAP0"           : CLA_BASE + 0x020,   # 0x3120
    "NODE0_EAP1"           : CLA_BASE + 0x028,   # 0x3128
    "NODE1_EAP0"           : CLA_BASE + 0x030,   # 0x3130
    "NODE1_EAP1"           : CLA_BASE + 0x038,   # 0x3138
    "NODE2_EAP0"           : CLA_BASE + 0x040,   # 0x3140
    "NODE2_EAP1"           : CLA_BASE + 0x048,   # 0x3148
    "NODE3_EAP0"           : CLA_BASE + 0x050,   # 0x3150
    "NODE3_EAP1"           : CLA_BASE + 0x058,   # 0x3158

    # ── Signal Mask/Match sets 0 & 1 ─────────────────────────────────────────
    # CDbgSignalMask0/Match0 @ 0x3160/0x3168
    # CDbgSignalMask1/Match1 @ 0x3170/0x3178
    "SIGNAL_MASK0"         : CLA_BASE + 0x060,   # 0x3160
    "SIGNAL_MATCH0"        : CLA_BASE + 0x068,   # 0x3168
    "SIGNAL_MASK1"         : CLA_BASE + 0x070,   # 0x3170
    "SIGNAL_MATCH1"        : CLA_BASE + 0x078,   # 0x3178

    # ── Edge Detect Config ────────────────────────────────────────────────────
    # CDbgSignalEdgeDetectCfg @ 0x3180
    "EDGE_DETECT_CFG"      : CLA_BASE + 0x080,   # 0x3180

    # ── EAP Status (64-bit, R/W2C) ────────────────────────────────────────────
    # CDbgEapStatus @ 0x3188
    # Bits [15:0]  = Node0-3 Eap0-3 status (RO, 2 bits per EAP)
    # Bits [31:16] = Reserved
    # Bits [47:32] = W2C clear bits (write 1 to clear corresponding status bit)
    "EAP_STATUS"           : CLA_BASE + 0x088,   # 0x3188

    # ── CLA Control / Status ──────────────────────────────────────────────────
    # CDbgClaCtrlStatus @ 0x3190
    # [1:0]  CurrentNode  (RO)
    # [5]    EnableEap
    # [6]    EnableCla
    # [13:7] ClaChainLoopDelay (reset=0x36)
    # [14]   DisableGlobalClockHalt
    # [15]   DisableLocalClockHalt
    # [63]   ClaLock
    "CTRL_STATUS"          : CLA_BASE + 0x090,   # 0x3190

    # ── Reserved registers (do not use) ──────────────────────────────────────
    # CDbgRsvd0/1/2 @ 0x3198, 0x31A0, 0x31A8  — omitted intentionally

    # ── Transition Event (3 × 64-bit) ────────────────────────────────────────
    # CDbgTransitionMask/FromValue/ToValue @ 0x31B0, 0x31B8, 0x31C0
    "TRANSITION_MASK"      : CLA_BASE + 0x0B0,   # 0x31B0
    "TRANSITION_FROM"      : CLA_BASE + 0x0B8,   # 0x31B8
    "TRANSITION_TO"        : CLA_BASE + 0x0C0,   # 0x31C0

    # ── Ones-Count Event (2 × 64-bit) ────────────────────────────────────────
    # CDbgOnesCountMask/Value @ 0x31C8, 0x31D0
    "ONES_COUNT_MASK"      : CLA_BASE + 0x0C8,   # 0x31C8
    "ONES_COUNT_VALUE"     : CLA_BASE + 0x0D0,   # 0x31D0

    # ── Any-Change Event ─────────────────────────────────────────────────────
    # CDbgAnyChange @ 0x31D8
    "ANY_CHANGE"           : CLA_BASE + 0x0D8,   # 0x31D8

    # ── Debug Bus Snapshots — EAP0/EAP1 of each node ─────────────────────────
    # CDbgSignalSnapshotNode<N>Eap<0,1>:
    #   Node0: 0x31E0, 0x31E8  |  Node1: 0x31F0, 0x31F8
    #   Node2: 0x3200, 0x3208  |  Node3: 0x3210, 0x3218
    "SNAP_N0E0"            : CLA_BASE + 0x0E0,   # 0x31E0
    "SNAP_N0E1"            : CLA_BASE + 0x0E8,   # 0x31E8
    "SNAP_N1E0"            : CLA_BASE + 0x0F0,   # 0x31F0
    "SNAP_N1E1"            : CLA_BASE + 0x0F8,   # 0x31F8
    "SNAP_N2E0"            : CLA_BASE + 0x100,   # 0x3200
    "SNAP_N2E1"            : CLA_BASE + 0x108,   # 0x3208
    "SNAP_N3E0"            : CLA_BASE + 0x110,   # 0x3210
    "SNAP_N3E1"            : CLA_BASE + 0x118,   # 0x3218

    # ── Time Match Event ──────────────────────────────────────────────────────
    # CDbgClaTimeMatch @ 0x3220  (write 0 to deassert)
    "TIME_MATCH"           : CLA_BASE + 0x120,   # 0x3220

    # ── Signal Mask/Match sets 2 & 3 (NON-CONTIGUOUS with sets 0 & 1!) ───────
    # CDbgSignalMask2/Match2 @ 0x3228/0x3230
    # CDbgSignalMask3/Match3 @ 0x3238/0x3240
    "SIGNAL_MASK2"         : CLA_BASE + 0x128,   # 0x3228
    "SIGNAL_MATCH2"        : CLA_BASE + 0x130,   # 0x3230
    "SIGNAL_MASK3"         : CLA_BASE + 0x138,   # 0x3238
    "SIGNAL_MATCH3"        : CLA_BASE + 0x140,   # 0x3240

    # ── EAP registers — Node EAP2 and EAP3 (NON-CONTIGUOUS with EAP0/EAP1!) ─
    # CDbgNode<N>Eap<2,3>:  Node0@0x3248/0x3250, Node1@0x3258/0x3260,
    #                       Node2@0x3268/0x3270,  Node3@0x3278/0x3280
    "NODE0_EAP2"           : CLA_BASE + 0x148,   # 0x3248
    "NODE0_EAP3"           : CLA_BASE + 0x150,   # 0x3250
    "NODE1_EAP2"           : CLA_BASE + 0x158,   # 0x3258
    "NODE1_EAP3"           : CLA_BASE + 0x160,   # 0x3260
    "NODE2_EAP2"           : CLA_BASE + 0x168,   # 0x3268
    "NODE2_EAP3"           : CLA_BASE + 0x170,   # 0x3270
    "NODE3_EAP2"           : CLA_BASE + 0x178,   # 0x3278
    "NODE3_EAP3"           : CLA_BASE + 0x180,   # 0x3280

    # ── Debug Bus Snapshots — EAP2/EAP3 of each node ─────────────────────────
    # CDbgSignalSnapshotNode<N>Eap<2,3>:
    #   Node0: 0x3288, 0x3290  |  Node1: 0x3298, 0x32A0
    #   Node2: 0x32A8, 0x32B0  |  Node3: 0x32B8, 0x32C0
    "SNAP_N0E2"            : CLA_BASE + 0x188,   # 0x3288
    "SNAP_N0E3"            : CLA_BASE + 0x190,   # 0x3290
    "SNAP_N1E2"            : CLA_BASE + 0x198,   # 0x3298
    "SNAP_N1E3"            : CLA_BASE + 0x1A0,   # 0x32A0
    "SNAP_N2E2"            : CLA_BASE + 0x1A8,   # 0x32A8
    "SNAP_N2E3"            : CLA_BASE + 0x1B0,   # 0x32B0
    "SNAP_N3E2"            : CLA_BASE + 0x1B8,   # 0x32B8
    "SNAP_N3E3"            : CLA_BASE + 0x1C0,   # 0x32C0

    # ── Delay Mux Select ─────────────────────────────────────────────────────
    # CDbgSignalDelayMuxSel @ 0x32C8  — Muxselseg0-7 [15:0], 2 bits per lane
    "DELAY_MUX_SEL"        : CLA_BASE + 0x1C8,   # 0x32C8

    # ── Timestamp Sync ────────────────────────────────────────────────────────
    # CDbgClaTimestampsync @ 0x32D0
    "TIMESTAMP_SYNC"       : CLA_BASE + 0x1D0,   # 0x32D0

    # ── Cross-Trigger Timestretch ─────────────────────────────────────────────
    # CDbgClaXtriggerTimestretch @ 0x32D8
    "XTRIGGER_TIMESTRETCH" : CLA_BASE + 0x1D8,   # 0x32D8
}

# ──────────────────────────────────────────────────────────────────────────────
# EAP REGISTER BIT-FIELD POSITIONS
#
# 64-bit layout per CR_Registers.html:
#   [1:0]   DestNode            — destination node (2-bit, 4 nodes)
#   [7:2]   Action0             — action 0 select  (6-bit)
#   [13:8]  Action1             — action 1 select  (6-bit)
#   [15:14] LogicalOp           — reserved; program 2'b00 (or per spec 2'b10)
#   [21:16] EventType0          — event 0 select   (6-bit)
#   [27:22] EventType1          — event 1 select   (6-bit)
#   [31:28] CustomAction0       — custom action 0 bit-position (4-bit)
#   [35:32] CustomAction1       — custom action 1 bit-position (4-bit)
#   [36]    CustomAction0Enable — enable custom action 0
#   [37]    CustomAction1Enable — enable custom action 1
#   [43:38] EventType2          — event 2 select   (6-bit)
#   [51:44] Udf                 — 8-bit truth-table for UDF
#   [57:52] Action2             — action 2 select  (6-bit)
#   [63:58] Action3             — action 3 select  (6-bit)
# ──────────────────────────────────────────────────────────────────────────────
EAP_DEST_SHIFT      =  0;  EAP_DEST_MASK      = 0x3    # [1:0]   2-bit
EAP_ACT0_SHIFT      =  2;  EAP_ACT0_MASK      = 0x3F   # [7:2]   6-bit
EAP_ACT1_SHIFT      =  8;  EAP_ACT1_MASK      = 0x3F   # [13:8]  6-bit
EAP_LOGICAL_SHIFT   = 14;  EAP_LOGICAL_MASK   = 0x3    # [15:14] 2-bit (rsvd)
EAP_EVT0_SHIFT      = 16;  EAP_EVT0_MASK      = 0x3F   # [21:16] 6-bit
EAP_EVT1_SHIFT      = 22;  EAP_EVT1_MASK      = 0x3F   # [27:22] 6-bit
EAP_CACT0_SHIFT     = 28;  EAP_CACT0_MASK     = 0xF    # [31:28] 4-bit
EAP_CACT1_SHIFT     = 32;  EAP_CACT1_MASK     = 0xF    # [35:32] 4-bit (in hi32)
EAP_CACT0_EN_BIT    = 36                                # [36]    1-bit
EAP_CACT1_EN_BIT    = 37                                # [37]    1-bit
EAP_EVT2_SHIFT      = 38;  EAP_EVT2_MASK      = 0x3F   # [43:38] 6-bit
EAP_UDF_SHIFT       = 44;  EAP_UDF_MASK       = 0xFF   # [51:44] 8-bit
EAP_ACT2_SHIFT      = 52;  EAP_ACT2_MASK      = 0x3F   # [57:52] 6-bit
EAP_ACT3_SHIFT      = 58;  EAP_ACT3_MASK      = 0x3F   # [63:58] 6-bit

# ──────────────────────────────────────────────────────────────────────────────
# CTRL_STATUS REGISTER BIT FIELDS  (CDbgClaCtrlStatus @ 0x3190)
#
# [1:0]   CurrentNode          (RO)  — active node index
# [5]     EnableEap                  — set after EAP programming is complete
# [6]     EnableCla                  — master CLA enable
# [13:7]  ClaChainLoopDelay          — reset default = 0x36
# [14]    DisableGlobalClockHalt     — suppress halt_clock_out
# [15]    DisableLocalClockHalt      — suppress halt_clock_local_out
# [63]    ClaLock                    — lock register writes
# ──────────────────────────────────────────────────────────────────────────────
CTRL_CURRENT_NODE_SHIFT  = 0    # [1:0]
CTRL_CURRENT_NODE_MASK   = 0x3  # 2-bit (4 nodes)
CTRL_EAP_EN_BIT          = 5    # EnableEap
CTRL_CLA_EN_BIT          = 6    # EnableCla
CTRL_DIS_GLOBAL_HALT_BIT = 14   # DisableGlobalClockHalt
CTRL_DIS_LOCAL_HALT_BIT  = 15   # DisableLocalClockHalt

# ──────────────────────────────────────────────────────────────────────────────
# COUNTER CONFIG REGISTER BIT FIELDS  (CDbgClaCounter<N>Cfg)
#
# [15:0]  Counter       — current counter value (writeable to reset)
# [31:16] Target        — match target
# [32]    ResetOnTarget — if set, counter resets to 0 when Counter==Target
# [47:33] UpperCounter  — upper bits of counter
# [62:48] UpperTarget   — upper bits of target
# [63]    Rsvd
# ──────────────────────────────────────────────────────────────────────────────
CTR_COUNTER_SHIFT      =  0;  CTR_COUNTER_MASK      = 0xFFFF
CTR_TARGET_SHIFT       = 16;  CTR_TARGET_MASK       = 0xFFFF
CTR_RESET_ON_TGT_BIT   = 32

# ──────────────────────────────────────────────────────────────────────────────
# EVENT SELECT CODES  (Table from spec page 6 / CR_Registers.html EventType field)
# ──────────────────────────────────────────────────────────────────────────────
EVT_DISABLE             = 0x00
EVT_ALWAYS_ON           = 0x01
EVT_MATCH1_POS          = 0x02
EVT_MATCH1_NEG          = 0x03
EVT_MATCH2_POS          = 0x04
EVT_MATCH2_NEG          = 0x05
EVT_EDGE_SET0           = 0x06
EVT_EDGE_SET1           = 0x07
EVT_TRANSITION          = 0x08
EVT_CROSS_TRIG_IN1      = 0x09
EVT_CROSS_TRIG_IN2      = 0x0A
EVT_ONES_COUNT          = 0x0B
EVT_DEBUG_CHANGE        = 0x0C
EVT_CORE_TIME_MATCH     = 0x0F
EVT_CTR0_MATCH          = 0x10
EVT_CTR0_OVERFLOW       = 0x11
EVT_CTR0_BELOW          = 0x12
EVT_CTR1_MATCH          = 0x13
EVT_CTR1_OVERFLOW       = 0x14
EVT_CTR1_BELOW          = 0x15
EVT_CTR2_MATCH          = 0x16
EVT_CTR2_OVERFLOW       = 0x17
EVT_CTR2_BELOW          = 0x18
EVT_CTR3_MATCH          = 0x19
EVT_CTR3_OVERFLOW       = 0x1A
EVT_CTR3_BELOW          = 0x1B

# ──────────────────────────────────────────────────────────────────────────────
# ACTION SELECT CODES  (Table from spec pages 7-8 / CR_Registers.html Action field)
# ──────────────────────────────────────────────────────────────────────────────
ACT_NULL                = 0x00
ACT_CLOCK_HALT          = 0x01
ACT_DEBUG_INTERRUPT     = 0x02
ACT_START_TRACE         = 0x04
ACT_STOP_TRACE          = 0x05
ACT_TRACE_PULSE         = 0x06
ACT_CROSS_TRIG_OUT1     = 0x07
ACT_CROSS_TRIG_OUT2     = 0x08
ACT_INCR_CTR0           = 0x10
ACT_CLR_CTR0            = 0x11
ACT_AUTO_INCR_CTR0      = 0x12
ACT_STOP_AUTO_CTR0      = 0x13
ACT_INCR_CTR1           = 0x14
ACT_CLR_CTR1            = 0x15
ACT_AUTO_INCR_CTR1      = 0x16
ACT_STOP_AUTO_CTR1      = 0x17
ACT_INCR_CTR2           = 0x18
ACT_CLR_CTR2            = 0x19
ACT_AUTO_INCR_CTR2      = 0x1A
ACT_STOP_AUTO_CTR2      = 0x1B
ACT_INCR_CTR3           = 0x1C
ACT_CLR_CTR3            = 0x1D
ACT_AUTO_INCR_CTR3      = 0x1E
ACT_STOP_AUTO_CTR3      = 0x1F

# ──────────────────────────────────────────────────────────────────────────────
# UDF (User Defined Function) 8-bit truth-table constants
#
# The 8-bit UDF field is indexed as UDF[{E2,E1,E0}].
# UDF bit N = result when the 3-event combination equals N.
# ──────────────────────────────────────────────────────────────────────────────
UDF_AND_ALL      = 0x80   # fires only when E2=1 AND E1=1 AND E0=1
UDF_OR_ANY       = 0xFE   # fires when any of E0,E1,E2 is active (not all-zero)
UDF_ALWAYS       = 0xFF   # fires always (including when all events are 0)
UDF_E0_ONLY      = 0xAA   # fires when E0 active, regardless of E1/E2
UDF_E1_ONLY      = 0xCC   # fires when E1 active, regardless of E0/E2
UDF_E2_ONLY      = 0xF0   # fires when E2 active, regardless of E0/E1
UDF_E1_AND_E0    = 0x88   # fires when (E1 AND E0)
UDF_SPEC_EXAMPLE = 0xEC   # (E2 AND E1) OR E0  — truth-table example from spec p.9


# ──────────────────────────────────────────────────────────────────────────────
# APB DRIVER CLASS
# ──────────────────────────────────────────────────────────────────────────────
class APBMaster:
    """
    Minimal APB3 master for cocotb.
    Drives: paddr, psel, penable, pwrite, pwdata, pstrb
    Reads:  pready, prdata, pslverr
    """
    def __init__(self, dut, clk_period_ns=10):
        self.dut = dut
        self.clk_period_ns = clk_period_ns

    async def _wait_ready(self, timeout_cycles=100):
        """Spin on pready for up to timeout_cycles clock edges."""
        for _ in range(timeout_cycles):
            await RisingEdge(self.dut.clk)
            if self.dut.pready.value == 1:
                return
        raise TimeoutError("APB pready never asserted")

    async def write(self, addr, data, strb=0xF):
        """Perform a single 32-bit APB write transaction."""
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
            log.warning(f"APB SLVERR on write addr=0x{addr:08X} data=0x{data:08X}")
        dut.psel.value    = 0
        dut.penable.value = 0
        dut.pwrite.value  = 0
        await RisingEdge(dut.clk)

    async def read(self, addr):
        """Perform a single 32-bit APB read and return the data value."""
        dut = self.dut
        dut.paddr.value   = addr
        dut.pwrite.value  = 0
        dut.psel.value    = 1
        dut.penable.value = 0
        await RisingEdge(dut.clk)
        dut.penable.value = 1
        await self._wait_ready()
        data = int(dut.prdata.value)
        if dut.pslverr.value == 1:
            log.warning(f"APB SLVERR on read addr=0x{addr:08X}")
        dut.psel.value    = 0
        dut.penable.value = 0
        await RisingEdge(dut.clk)
        return data

    async def read64(self, addr):
        """Read a 64-bit register as two consecutive 32-bit APB reads."""
        lo = await self.read(addr)
        hi = await self.read(addr + 4)
        return (hi << 32) | lo

    async def write64(self, addr, data):
        """Write a 64-bit register as two consecutive 32-bit APB writes."""
        await self.write(addr,     data & 0xFFFF_FFFF)
        await self.write(addr + 4, (data >> 32) & 0xFFFF_FFFF)

    async def read_modify_write(self, addr, set_bits=0, clr_bits=0):
        """32-bit RMW: read → clear clr_bits → set set_bits → write."""
        val = await self.read(addr)
        val = (val & ~clr_bits) | set_bits
        await self.write(addr, val)
        return val

    async def read_modify_write64(self, addr, set_bits=0, clr_bits=0):
        """64-bit RMW across two APB transactions."""
        val = await self.read64(addr)
        val = (val & ~clr_bits) | set_bits
        await self.write64(addr, val)
        return val

    async def poll_field(self, addr, mask, expected, timeout_cycles=2000):
        """Poll register at addr until (reg & mask) == expected."""
        for _ in range(timeout_cycles):
            val = await self.read(addr)
            if (val & mask) == expected:
                return val
            await ClockCycles(self.dut.clk, 1)
        raise TimeoutError(
            f"poll_field timeout: addr=0x{addr:X} mask=0x{mask:X} "
            f"expected=0x{expected:X}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# CLA DRIVER  —  high-level CLA programming layer built on APBMaster
# ──────────────────────────────────────────────────────────────────────────────
class CLADriver:
    """High-level CLA programming layer built on APBMaster."""

    def __init__(self, apb: APBMaster):
        self.apb = apb

    # ── EAP helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def build_eap(evt0=EVT_DISABLE, evt1=EVT_ALWAYS_ON, evt2=EVT_ALWAYS_ON, udf=UDF_E0_ONLY, act0=ACT_NULL, act1=ACT_NULL, act2=ACT_NULL, act3=ACT_NULL, dest_node=0, cact0=0, cact0_en=False, cact1=0, cact1_en=False):
        """
        Build a 64-bit EAP register value from CR_Registers.html field layout.

        Field layout (all fields sized and positioned per CR_Registers.html):
          [1:0]   DestNode
          [7:2]   Action0
          [13:8]  Action1
          [15:14] LogicalOp (reserved, left as 0)
          [21:16] EventType0
          [27:22] EventType1
          [31:28] CustomAction0 (4-bit bit-position selector)
          [35:32] CustomAction1 (4-bit bit-position selector)
          [36]    CustomAction0Enable
          [37]    CustomAction1Enable
          [43:38] EventType2
          [51:44] Udf (8-bit truth table)
          [57:52] Action2
          [63:58] Action3

        Returns (lo32, hi32) for two consecutive 32-bit APB writes.
        """
        val  = (dest_node & EAP_DEST_MASK)  << EAP_DEST_SHIFT
        val |= (act0      & EAP_ACT0_MASK)  << EAP_ACT0_SHIFT
        val |= (act1      & EAP_ACT1_MASK)  << EAP_ACT1_SHIFT
        # [15:14] LogicalOp — leave as 0 (reserved, no spec mandate to write 2'b10)
        # [15:14] LogicalOp — MUST be 2'b10 per spec (ttdfd.pdf p.9).
        # Value 0 = always-fire (ignores UDF/events); value 2 = UDF-gated mode.
        # All other values are reserved. Leaving this 0 causes every EAP to
        # fire unconditionally every cycle regardless of event conditions.
        val |= (0x2 & EAP_LOGICAL_MASK) << EAP_LOGICAL_SHIFT
        val |= (evt0      & EAP_EVT0_MASK)  << EAP_EVT0_SHIFT
        val |= (evt1      & EAP_EVT1_MASK)  << EAP_EVT1_SHIFT
        val |= (cact0     & EAP_CACT0_MASK) << EAP_CACT0_SHIFT
        val |= (cact1     & EAP_CACT1_MASK) << EAP_CACT1_SHIFT
        if cact0_en:
            val |= (1 << EAP_CACT0_EN_BIT)
        if cact1_en:
            val |= (1 << EAP_CACT1_EN_BIT)
        val |= (evt2      & EAP_EVT2_MASK)  << EAP_EVT2_SHIFT
        val |= (udf       & EAP_UDF_MASK)   << EAP_UDF_SHIFT
        val |= (act2      & EAP_ACT2_MASK)  << EAP_ACT2_SHIFT
        val |= (act3      & EAP_ACT3_MASK)  << EAP_ACT3_SHIFT

        lo32 = val & 0xFFFF_FFFF
        hi32 = (val >> 32) & 0xFFFF_FFFF
        return lo32, hi32

    async def program_eap(self, node, eap_idx, **kwargs):
        """
        Program a single EAP register (64-bit via two 32-bit APB writes).
        node in [0..3], eap_idx in [0..3].
        Keyword args are forwarded directly to build_eap().
        """
        reg_name  = f"NODE{node}_EAP{eap_idx}"
        base_addr = CLA_REG[reg_name]
        lo32, hi32 = self.build_eap(**kwargs)
        await self.apb.write(base_addr,     lo32)   # bits [31:0]
        await self.apb.write(base_addr + 4, hi32)   # bits [63:32]

    async def activate(self):
        """Set EnableCla (bit 6) in CTRL_STATUS — master CLA output enable.
        Required for external actions (trace_start, halt, interrupt) to route
        to the output pins. Call before or alongside enable_eap()."""
        await self.apb.read_modify_write(
            CLA_REG["CTRL_STATUS"],
            set_bits=(1 << CTRL_CLA_EN_BIT)
        )

    async def set_mux_sel(self, sel):
        """Write CDbgMuxSel (MCR CSR @ 0x0198) to select which hw lane feeds
        the CLA/DST debug bus. sel=0 selects hw0 (default)."""
        MCR_MUXSEL_ADDR = 0x0000_0198  # CDbgMuxSel in MCR CSR
        await self.apb.write(MCR_MUXSEL_ADDR, sel & 0xFFFF_FFFF)

    async def enable_eap(self):
        """Set EnableEap (bit 5) AND EnableCla (bit 6) in CTRL_STATUS.
        EnableEap gates EAP evaluation; EnableCla routes external actions
        (trace_start, halt_clock, debug_interrupt) to the output pins.
        Both must be set for EAP-triggered external outputs to work."""
        await self.apb.read_modify_write(
            CLA_REG["CTRL_STATUS"],
            set_bits=(1 << CTRL_EAP_EN_BIT) | (1 << CTRL_CLA_EN_BIT)
        )

    async def disable_eap(self):
        """Clear EnableEap (bit 5) in CTRL_STATUS."""
        await self.apb.read_modify_write(
            CLA_REG["CTRL_STATUS"],
            clr_bits=(1 << CTRL_EAP_EN_BIT)
        )

    async def get_current_node(self):
        """
        Read current active node from CTRL_STATUS[1:0].
        Returns an integer in [0..3].
        """
        val = await self.apb.read(CLA_REG["CTRL_STATUS"])
        return (val >> CTRL_CURRENT_NODE_SHIFT) & CTRL_CURRENT_NODE_MASK

    async def clear_counter(self, idx):
        """
        Reset CLA counter <idx> to zero by writing Counter[15:0] = 0 and
        Target[31:16] = 0 in the lower 32 bits of the Counter Config register.

        Note: There are NO counter-clear bits in CDbgClaCtrlStatus (the old
        CTRL_CLR_CTR* constants were incorrect). The hardware clears the
        counter when it equals the Target and ResetOnTarget is set; writing
        Target=0 with ResetOnTarget=1 achieves an immediate software clear.
        """
        addr = CLA_REG[f"COUNTER{idx}_CFG"]
        # Write lower 32 bits: Counter=0, Target=0
        await self.apb.write(addr, 0x0000_0000)
        # Write upper 32 bits: ResetOnTarget=1 (bit 0 of hi32 = bit 32 overall)
        await self.apb.write(addr + 4, 0x0000_0001)

    async def set_mask_match(self, set_idx, mask, match):
        """
        Program debug signal mask/match set (0..3).
        Note: sets 0-1 and sets 2-3 are in non-contiguous address regions.
        """
        await self.apb.write(CLA_REG[f"SIGNAL_MASK{set_idx}"],  mask  & 0xFFFF_FFFF)
        await self.apb.write(CLA_REG[f"SIGNAL_MATCH{set_idx}"], match & 0xFFFF_FFFF)

    async def set_edge_detect(self, signal0_sel, pos_edge_sig0,
                              signal1_sel=0, pos_edge_sig1=True):
        """
        Program CDbgSignalEdgeDetectCfg.
        Field layout per CR_Registers.html:
          [5:0]  Signal0Select    — debug bus signal index for edge set 0
          [6]    PosEdgeSignal0   — 1 = positive edge, 0 = negative edge
          [12:7] Signal1Select    — debug bus signal index for edge set 1
          [13]   PosEdgeSignal1   — 1 = positive edge, 0 = negative edge
        """
        val  = (signal0_sel & 0x3F)
        val |= (1 if pos_edge_sig0 else 0) << 6
        val |= (signal1_sel & 0x3F)        << 7
        val |= (1 if pos_edge_sig1 else 0) << 13
        await self.apb.write(CLA_REG["EDGE_DETECT_CFG"], val)

    async def set_transition(self, mask, from_val, to_val):
        """Program transition event registers (all 64-bit, lower 32 bits used)."""
        await self.apb.write(CLA_REG["TRANSITION_MASK"], mask    & 0xFFFF_FFFF)
        await self.apb.write(CLA_REG["TRANSITION_FROM"], from_val & 0xFFFF_FFFF)
        await self.apb.write(CLA_REG["TRANSITION_TO"],   to_val   & 0xFFFF_FFFF)

    async def set_ones_count(self, mask, value):
        """Program ones-count event registers."""
        await self.apb.write(CLA_REG["ONES_COUNT_MASK"],  mask  & 0xFFFF_FFFF)
        await self.apb.write(CLA_REG["ONES_COUNT_VALUE"], value & 0xFFFF_FFFF)

    async def set_any_change(self, mask):
        """Program any-change event mask register."""
        await self.apb.write(CLA_REG["ANY_CHANGE"], mask & 0xFFFF_FFFF)

    async def set_counter_cfg(self, idx, target):
        """
        Program counter target for counter idx (0..3).
        Writes Target[31:16] into the lower 32 bits of the Counter Config reg.
        Counter[15:0] is left as 0 (reset value).
        """
        addr = CLA_REG[f"COUNTER{idx}_CFG"]
        lo32 = (target & CTR_TARGET_MASK) << CTR_TARGET_SHIFT
        await self.apb.write(addr, lo32)

    async def clear_eap_status(self):
        """
        Write-to-clear EAP status register.
        W2C bits are at [47:32] (the lower 16 bits of the upper 32-bit word).
        Writing 0xFFFF to that half-word clears all 16 status bits.
        """
        # Lower word (bits [31:0]) — status is RO, write has no effect
        await self.apb.write(CLA_REG["EAP_STATUS"],     0x0000_0000)
        # Upper word (bits [63:32]) — bits [15:0] of this word = bits [47:32] overall
        await self.apb.write(CLA_REG["EAP_STATUS"] + 4, 0x0000_FFFF)

    async def read_eap_status(self):
        """Read the lower 32 bits of EAP_STATUS (contains all 16 status bits)."""
        return await self.apb.read(CLA_REG["EAP_STATUS"])

    async def read_snapshot(self, node, eap_idx):
        """Read debug bus snapshot register for given node/eap (lower 32 bits)."""
        key = f"SNAP_N{node}E{eap_idx}"
        return await self.apb.read(CLA_REG[key])

    async def set_time_match(self, value):
        """Program CDbgClaTimeMatch. Write 0 to deassert the time-match event."""
        await self.apb.write(CLA_REG["TIME_MATCH"], value & 0xFFFF_FFFF)

    async def reset_cla(self):
        """
        Full software reset sequence:
          1. Disable EAP
          2. Clear all four counters
          3. Clear EAP status
          4. Deassert time-match
        """
        await self.disable_eap()
        for i in range(4):
            await self.clear_counter(i)
        await self.clear_eap_status()
        await self.set_time_match(0)


# ──────────────────────────────────────────────────────────────────────────────
# CLOCK & RESET HELPERS
# ──────────────────────────────────────────────────────────────────────────────
async def start_clock(dut, period_ns=10):
    """Start the DUT clock."""
    cocotb.start_soon(Clock(dut.clk, period_ns, unit="ns").start())


async def apply_reset(dut, cycles=20):
    """
    Assert all resets active-low for `cycles` clocks, then release.
    Also de-asserts all APB and non-APB inputs to safe idle state.
    """
    dut.reset_n.value              = 0
    dut.reset_n_warm_ovrride.value = 0
    dut.cold_reset_n.value         = 0
    # APB idle
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


def _zero_non_apb_inputs(dut):
    """Drive all non-APB DUT inputs to a safe zero / idle state."""
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
        pass   # Ports that don't exist for a given build variant are silently skipped


async def drive_debug_bus(dut, value, instance=0):
    """
    Drive the debug bus with `value`.

    The debug bus is assembled by the dfd_mux_sel block from hw0..hw15,
    where each hw<N> is 8-bits wide (8-bit lane).
    hw0 → debug_bus[ 7: 0]  (lane 0)
    hw1 → debug_bus[15: 8]  (lane 1)
    hw2 → debug_bus[23:16]  (lane 2)
    ... etc.

    This function drives hw0 (bits [7:0]) and hw1 (bits [15:8]) to cover
    a full 16-bit value, matching SignalMask/Match sets 0 and 1 which
    operate on debug_bus[63:0].

    For tests that exercise mask/match on bits above 15, drive additional
    hw<N> lanes directly in the test body.
    """
    dut.hw0.value = (value >> 0) & 0xFF   # debug_bus[7:0]
    dut.hw1.value = (value >> 8) & 0xFF   # debug_bus[15:8]


# ──────────────────────────────────────────────────────────────────────────────
# ASSERTION HELPERS
# ──────────────────────────────────────────────────────────────────────────────
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
