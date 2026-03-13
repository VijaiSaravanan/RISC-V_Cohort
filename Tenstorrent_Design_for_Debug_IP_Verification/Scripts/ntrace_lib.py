# SPDX-FileCopyrightText: Copyright 2025 Tenstorrent AI ULC
# SPDX-License-Identifier: Apache-2.0
"""
ntrace_lib.py  —  N-Trace (Instruction Trace) register map and test helpers.

N-Trace Encoder uses the RISC-V Trace Control Interface Specification.
Registers follow trTeControl / trRamControl naming.
Patch NTR_BASE in cla_lib.py if your build uses a different offset.

Updates based on tt-dfd PDF (pp. 18–24 N-trace overview, pp. 26–27 programming sequence):
  - Absolute offsets aligned to CDbgNtraceControl=0x2000 (base=0x2000 + 0x000).
  - Added full programming sequence: activate (trTeActive=1 readback), config RAM/sink/filters/funnel/format/sync, enable (trTeEnable=1).
  - Added configure_filters() for Trteinstfilters[15:0]/privilege (p.21–22).
  - Added set_format() for Trteformat[26:24]=0x1 basic (p.20).
  - Added disable_and_flush() with empty poll (p.27).
  - Retained/enhanced stall_mode in enable_trace().
  - Added retry on slverr in activate (up to 3).
  - Import ClockCycles for retry delay.
"""

from cocotb.triggers import ClockCycles
from cla_lib import APBMaster, NTR_BASE  # Import NTR_BASE from cla_lib
import logging

log = logging.getLogger("ntrace_lib")

# ──────────────────────────────────────────────────────────────────────────────
# NTRACE REGISTER MAP  (absolute addresses = NTR_BASE + offset)
# Names follow the spec's N-trace equivalents (trTe*, trRam*, trFunnel*).
# Aligned to PDF pp.18–24: CDbgNtraceControl=0x2000, Trramcontrol=0x2010, etc. (cr_4b block).
# ──────────────────────────────────────────────────────────────────────────────
NTR_REG = {
    # CDbgNtraceControl (mirrors trTeControl) @ 0x2000
    "TE_CONTROL"         : NTR_BASE + 0x000,  # trTeControl

    # CDbgNtraceImpl (read-only) @ 0x2004
    "TE_IMPL"            : NTR_BASE + 0x004,

    # CDbgNtraceInstFeatures (read-only) @ 0x2008
    "TE_INST_FEATURES"   : NTR_BASE + 0x008,

    # CDbgNtraceSrcID @ 0x200C
    "TE_SRC_ID"          : NTR_BASE + 0x00C,

    # CDbgNtraceRamControl @ 0x2010
    "RAM_CONTROL"        : NTR_BASE + 0x010,

    # CDbgNtraceRamImpl (read-only) @ 0x2014
    "RAM_IMPL"           : NTR_BASE + 0x014,

    # RAM address range @ 0x2020–0x202C
    "RAM_START_LOW"      : NTR_BASE + 0x020,
    "RAM_START_HIGH"     : NTR_BASE + 0x024,
    "RAM_LIMIT_LOW"      : NTR_BASE + 0x028,
    "RAM_LIMIT_HIGH"     : NTR_BASE + 0x02C,

    # Write pointer / read pointer @ 0x2030–0x203C
    "RAM_WP_LOW"         : NTR_BASE + 0x030,
    "RAM_WP_HIGH"        : NTR_BASE + 0x034,
    "RAM_RP_LOW"         : NTR_BASE + 0x038,
    "RAM_RP_HIGH"        : NTR_BASE + 0x03C,

    # Sync mode @ 0x2040–0x2044
    "SYNC_MODE"          : NTR_BASE + 0x040,
    "SYNC_MAX"           : NTR_BASE + 0x044,

    # Data readout (SRAM mode) @ 0x2050
    "RAM_DATA"           : NTR_BASE + 0x050,

    # Filters (Trteinstfilters[15:0], Trtefiltermatchprivilege) @ 0x2058–0x205C
    "INST_FILTERS"       : NTR_BASE + 0x058,
    "FILTER_PRIVILEGE"   : NTR_BASE + 0x05C,

    # Funnel control @ 0x2060–0x2068
    "FUNNEL_CONTROL"     : NTR_BASE + 0x060,  # trFunnelControl
    "FUNNEL_IMPL"        : NTR_BASE + 0x064,  # trFunnelImpl (RO)
    "FUNNEL_DIS_INPUT"   : NTR_BASE + 0x068,  # trFunnelDisInput

    # CDbgNtraceFormat @ 0x206C (encoder format)
    "TE_FORMAT"          : NTR_BASE + 0x06C,
}

# ──────────────────────────────────────────────────────────────────────────────
# CDbgNtraceControl bit fields  (mirrors trTeControl; PDF p.19)
# ──────────────────────────────────────────────────────────────────────────────
TE_CTRL_ACTIVE_BIT        = 0   # trTeActive
TE_CTRL_ENABLE_BIT        = 1   # trTeEnable
TE_CTRL_EMPTY_BIT         = 3   # trTeEmpty  (RO)
TE_CTRL_TRIG_ENABLE_BIT   = 8   # trTeTriggerEnable
TE_CTRL_STALL_ENA_BIT     = 9   # trTeStallEna (stall mode p.21)

# CDbgNtraceRamControl bit fields (PDF p.23)
RAM_CTRL_ACTIVE_BIT       = 0   # trRamActive
RAM_CTRL_ENABLE_BIT       = 1   # trRamEnable
RAM_CTRL_EMPTY_BIT        = 2   # trRamEmpty  (RO)
RAM_CTRL_STOP_ON_WRAP_BIT = 8   # trRamStopOnWrap

# Funnel bit fields (PDF p.23)
FUNNEL_CTRL_ACTIVE_BIT    = 0   # trFunnelActive
FUNNEL_CTRL_ENABLE_BIT    = 1   # trFunnelEnable
FUNNEL_CTRL_EMPTY_BIT     = 2   # trFunnelEmpty  (RO)

# CDbgNtraceFormat bit fields (PDF p.20 Trteformat[26:24])
TE_FORMAT_SHIFT           = 24  # Encoder format
TE_FORMAT_BASIC           = 0x1  # Basic mode (reset/default)

# ──────────────────────────────────────────────────────────────────────────────
# HART2TE interface IType encoding  (RISC-V N-Trace spec, PDF pp.19–20)
# ──────────────────────────────────────────────────────────────────────────────
ITYPE_NOTAKEN     = 0
ITYPE_EXCEPTION   = 1
ITYPE_INTERRUPT   = 2
ITYPE_ERET        = 3
ITYPE_NON_RETURN  = 4
ITYPE_CALL        = 5
ITYPE_JUMP        = 6
ITYPE_RETURN      = 7


class NTraceDriver:
    """High-level N-Trace (Instruction Trace) programming layer."""

    def __init__(self, apb: APBMaster):
        self.apb = apb

    async def activate(self):
        """Step 1: Set trTeActive = 1 and read it back (PDF p.26)."""
        for retry in range(3):
            await self.apb.read_modify_write(
                NTR_REG["TE_CONTROL"],
                set_bits=(1 << TE_CTRL_ACTIVE_BIT)
            )
            val = await self.apb.read(NTR_REG["TE_CONTROL"])
            if (val >> TE_CTRL_ACTIVE_BIT) & 1:
                return
            await ClockCycles(self.apb.dut.clk, 5)  # Delay for RTL settle
        raise AssertionError("TE_CONTROL.trTeActive did not read back 1 after retries")

    async def configure_sink(self, start=0x1234, limit=0x7FFF, # Non-zero
                             stop_on_wrap=True, sync_mode=0xA5):  # No sync default (p.20)
        """
        Configure the RAM sink (PDF p.23).
        Includes format (basic=1), sync.
        """
        # Sink active
        await self.apb.read_modify_write(
            NTR_REG["RAM_CONTROL"],
            set_bits=(1 << RAM_CTRL_ACTIVE_BIT)
        )
        # StopOnWrap
        if stop_on_wrap:
            await self.apb.read_modify_write(
                NTR_REG["RAM_CONTROL"],
                set_bits=(1 << RAM_CTRL_STOP_ON_WRAP_BIT)
            )
        # Address range
        await self.apb.write(NTR_REG["RAM_START_LOW"],  start  & 0xFFFF_FFFF)
        await self.apb.write(NTR_REG["RAM_START_HIGH"], (start >> 32) & 0xFFFF_FFFF)
        await self.apb.write(NTR_REG["RAM_LIMIT_LOW"],  limit  & 0xFFFF_FFFF)
        await self.apb.write(NTR_REG["RAM_LIMIT_HIGH"], (limit >> 32) & 0xFFFF_FFFF)
        # Clear WP/RP
        await self.apb.write(NTR_REG["RAM_WP_LOW"],  0x1234)
        await self.apb.write(NTR_REG["RAM_WP_HIGH"], 0xA5A5)
        await self.apb.write(NTR_REG["RAM_RP_LOW"],  0x1234)
        await self.apb.write(NTR_REG["RAM_RP_HIGH"], 0xA5A5)
        # Set format (basic=1 per p.20)
        await self.apb.write(NTR_REG["TE_FORMAT"], (TE_FORMAT_BASIC << TE_FORMAT_SHIFT))
        # Sync mode (default 0: no sync)
        await self.apb.write(NTR_REG["SYNC_MODE"], sync_mode & 0xFFFF_FFFF)
        # Enable sink
        await self.apb.read_modify_write(
            NTR_REG["RAM_CONTROL"],
            set_bits=(1 << RAM_CTRL_ENABLE_BIT)
        )

    async def configure_filters(self, inst_filters=0xFFFF,  # All instructions (p.21)
                                match_privilege=0xA5):  # Match any privilege (p.22)
        """
        Configure instruction filters and privilege matching (PDF pp.21–22).
        Trteinstfilters[15:0]: bitmask for instruction types.
        Trtefiltermatchprivilege: 0=all, 1=user-only, etc.
        """
        await self.apb.write(NTR_REG["INST_FILTERS"], inst_filters & 0xFFFF_FFFF)
        await self.apb.write(NTR_REG["FILTER_PRIVILEGE"], match_privilege & 0xFFFF_FFFF)

    async def configure_funnel(self, dis_input_mask=0xA5):
        """Configure trace funnel (PDF p.23)."""
        await self.apb.read_modify_write(
            NTR_REG["FUNNEL_CONTROL"],
            set_bits=(1 << FUNNEL_CTRL_ACTIVE_BIT)
        )
        if dis_input_mask:
            await self.apb.write(NTR_REG["FUNNEL_DIS_INPUT"], dis_input_mask & 0xFFFF_FFFF)
        await self.apb.read_modify_write(
            NTR_REG["FUNNEL_CONTROL"],
            set_bits=(1 << FUNNEL_CTRL_ENABLE_BIT)
        )

    async def enable_trace(self, stall_mode=False):
        """Enable N-Trace: set trTeEnable=1 + TriggerEnable (PDF p.26; stall p.21)."""
        bits = (1 << TE_CTRL_ENABLE_BIT) | (1 << TE_CTRL_TRIG_ENABLE_BIT)
        if stall_mode:
            bits |= (1 << TE_CTRL_STALL_ENA_BIT)
        await self.apb.read_modify_write(NTR_REG["TE_CONTROL"], set_bits=bits)

    async def disable_trace(self):
        """Disable N-Trace: clear trTeEnable (PDF p.27)."""
        await self.apb.read_modify_write(
            NTR_REG["TE_CONTROL"],
            clr_bits=(1 << TE_CTRL_ENABLE_BIT)
        )

    async def disable_and_flush(self, timeout=5000):
        """Disable trace and poll until trTeEmpty=1 (PDF p.27)."""
        await self.disable_trace()
        await self.apb.poll_field(
            NTR_REG["TE_CONTROL"],
            mask=(1 << TE_CTRL_EMPTY_BIT),
            expected=(1 << TE_CTRL_EMPTY_BIT),
            timeout_cycles=timeout
        )

    async def wait_sink_empty(self, timeout=5000):
        """Poll until trRamEmpty=1."""
        await self.apb.poll_field(
            NTR_REG["RAM_CONTROL"],
            mask=(1 << RAM_CTRL_EMPTY_BIT),
            expected=(1 << RAM_CTRL_EMPTY_BIT),
            timeout_cycles=timeout
        )

    async def wait_funnel_empty(self, timeout=5000):
        """Poll until trFunnelEmpty=1."""
        await self.apb.poll_field(
            NTR_REG["FUNNEL_CONTROL"],
            mask=(1 << FUNNEL_CTRL_EMPTY_BIT),
            expected=(1 << FUNNEL_CTRL_EMPTY_BIT),
            timeout_cycles=timeout
        )

    async def full_init(self, stall_mode=False, inst_filters=0xFFFF,
                        match_privilege=0xA5, dis_input_mask=0xA5):
        """
        Full N-Trace init sequence per PDF pp. 26–27:
        active → sink/config → filters → funnel → enable.
        """
        await self.activate()
        await self.configure_sink()
        await self.configure_filters(inst_filters=inst_filters,
                                     match_privilege=match_privilege)
        await self.configure_funnel(dis_input_mask=dis_input_mask)
        await self.enable_trace(stall_mode=stall_mode)

    async def read_wp(self):
        """Return the write pointer (64-bit)."""
        lo = await self.apb.read(NTR_REG["RAM_WP_LOW"])
        hi = await self.apb.read(NTR_REG["RAM_WP_HIGH"])
        return (hi << 32) | lo

    async def read_rp(self):
        """Return the read pointer (64-bit)."""
        lo = await self.apb.read(NTR_REG["RAM_RP_LOW"])
        hi = await self.apb.read(NTR_REG["RAM_RP_HIGH"])
        return (hi << 32) | lo
