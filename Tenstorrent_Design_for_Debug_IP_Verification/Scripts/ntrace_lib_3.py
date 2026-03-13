# SPDX-FileCopyrightText: Copyright 2025 Tenstorrent AI ULC
# SPDX-License-Identifier: Apache-2.0
"""
ntrace_lib.py  —  N-Trace (Instruction Trace) register map and test helpers.

N-Trace Encoder uses the RISC-V Trace Control Interface Specification.
Registers follow trTeControl / trRamControl naming.
Patch NTR_BASE in cla_lib.py if your build uses a different offset.
"""

from cla_lib_3 import APBMaster, NTR_BASE
import logging

log = logging.getLogger("ntrace_lib_3")

# ──────────────────────────────────────────────────────────────────────────────
# NTRACE REGISTER MAP  (offsets from NTR_BASE)
# ──────────────────────────────────────────────────────────────────────────────
NTR_REG = {
    # Trace Encoder (TE) registers — in NTR namespace (0x2000)
    "TE_CONTROL"         : NTR_BASE + 0x000,  # 0x2000: ttrTeControl
    "TE_IMPL"            : NTR_BASE + 0x004,  # 0x2004: trTeImpl (RO)
    "TE_INST_FEATURES"   : NTR_BASE + 0x008,  # 0x2008: trTeInstFeatures (RO)
    "TE_SRC_ID"          : NTR_BASE + 0x00C,  # 0x200C: trTeSrcID

    # NTR RAM sink registers — in TR namespace (decoded at 0x5000 per TR_CSR.pdf)
    # TR CSR: Trramcontrol@0x5000, Trramstartlow@0x5010, Trramwplow@0x5020, etc.
    "RAM_CONTROL"        : 0x5000,
    "RAM_IMPL"           : 0x5004,
    "RAM_START_LOW"      : 0x5010,
    "RAM_START_HIGH"     : 0x5014,
    "RAM_LIMIT_LOW"      : 0x5018,
    "RAM_LIMIT_HIGH"     : 0x501C,
    "RAM_WP_LOW"         : 0x5020,
    "RAM_WP_HIGH"        : 0x5024,
    "RAM_RP_LOW"         : 0x5028,
    "RAM_RP_HIGH"        : 0x502C,
    "RAM_DATA"           : 0x5040,

    # Trace Funnel — in TR namespace (decoded at 0x4000 per TR_CSR.pdf)
    # TR CSR: Trfunnelcontrol@0x4000, Trfunneldisinput@0x4008
    "FUNNEL_CONTROL"     : 0x4000,
    "FUNNEL_IMPL"        : 0x4004,
    "FUNNEL_DIS_INPUT"   : 0x4008,
}

# ──────────────────────────────────────────────────────────────────────────────
# trTeControl bit fields
# ──────────────────────────────────────────────────────────────────────────────
TE_CTRL_ACTIVE_BIT        = 0   # trTeActive
TE_CTRL_ENABLE_BIT        = 1   # trTeEnable
TE_CTRL_INST_TRACING_BIT  = 2   # trTeInstTracing
TE_CTRL_EMPTY_BIT         = 3   # trTeEmpty  (RO)
TE_CTRL_TRIG_ENABLE_BIT   = 11  # trTeInstTriggerEnable  (NTR_CSR: bit 11)
TE_CTRL_STALL_ENA_BIT     = 13  # trTeInstStallEna       (NTR_CSR: bit 13)

# trRamControl bit fields
RAM_CTRL_ACTIVE_BIT       = 0
RAM_CTRL_ENABLE_BIT       = 1
RAM_CTRL_EMPTY_BIT        = 2   # RO
RAM_CTRL_STOP_ON_WRAP_BIT = 8

# Funnel
FUNNEL_CTRL_ACTIVE_BIT    = 0
FUNNEL_CTRL_ENABLE_BIT    = 1
FUNNEL_CTRL_EMPTY_BIT     = 2   # RO

# ──────────────────────────────────────────────────────────────────────────────
# HART2TE interface IType encoding  (RISC-V N-Trace spec)
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

    async def release_reset(self):
        """Set trTeActive = 1 and read back."""
        await self.apb.read_modify_write(
            NTR_REG["TE_CONTROL"],
            set_bits=(1 << TE_CTRL_ACTIVE_BIT)
        )
        val = await self.apb.read(NTR_REG["TE_CONTROL"])
        assert (val >> TE_CTRL_ACTIVE_BIT) & 1, \
            "TE_CONTROL.trTeActive did not read back 1"

    async def configure_ram(self, start=0, limit=0x7FFF,
                            stop_on_wrap=True):
        """Configure RAM sink for N-Trace."""
        await self.apb.read_modify_write(
            NTR_REG["RAM_CONTROL"],
            set_bits=(1 << RAM_CTRL_ACTIVE_BIT)
        )
        if stop_on_wrap:
            await self.apb.read_modify_write(
                NTR_REG["RAM_CONTROL"],
                set_bits=(1 << RAM_CTRL_STOP_ON_WRAP_BIT)
            )
        await self.apb.write(NTR_REG["RAM_START_LOW"],  start  & 0xFFFF_FFFF)
        await self.apb.write(NTR_REG["RAM_START_HIGH"], (start >> 32) & 0xFFFF_FFFF)
        await self.apb.write(NTR_REG["RAM_LIMIT_LOW"],  limit  & 0xFFFF_FFFF)
        await self.apb.write(NTR_REG["RAM_LIMIT_HIGH"], (limit >> 32) & 0xFFFF_FFFF)
        await self.apb.write(NTR_REG["RAM_WP_LOW"],  0)
        await self.apb.write(NTR_REG["RAM_WP_HIGH"], 0)
        await self.apb.write(NTR_REG["RAM_RP_LOW"],  0)
        await self.apb.write(NTR_REG["RAM_RP_HIGH"], 0)
        await self.apb.read_modify_write(
            NTR_REG["RAM_CONTROL"],
            set_bits=(1 << RAM_CTRL_ENABLE_BIT)
        )

    async def configure_funnel(self, dis_input_mask=0):
        """Configure trace funnel."""
        await self.apb.read_modify_write(
            NTR_REG["FUNNEL_CONTROL"],
            set_bits=(1 << FUNNEL_CTRL_ACTIVE_BIT)
        )
        if dis_input_mask:
            await self.apb.write(NTR_REG["FUNNEL_DIS_INPUT"], dis_input_mask)
        await self.apb.read_modify_write(
            NTR_REG["FUNNEL_CONTROL"],
            set_bits=(1 << FUNNEL_CTRL_ENABLE_BIT)
        )

    async def enable_trace(self, stall_mode=False):
        """Enable N-Trace: set Enable + InstTracing (RMW)."""
        bits = (1 << TE_CTRL_ENABLE_BIT) | (1 << TE_CTRL_INST_TRACING_BIT)
        if stall_mode:
            bits |= (1 << TE_CTRL_STALL_ENA_BIT)
        await self.apb.read_modify_write(NTR_REG["TE_CONTROL"], set_bits=bits)

    async def disable_trace(self):
        """Clear Enable bit (RMW)."""
        await self.apb.read_modify_write(
            NTR_REG["TE_CONTROL"],
            clr_bits=(1 << TE_CTRL_ENABLE_BIT)
        )

    async def wait_te_empty(self, timeout=2000):
        """Poll until trTeEmpty = 1."""
        await self.apb.poll_field(
            NTR_REG["TE_CONTROL"],
            mask=(1 << TE_CTRL_EMPTY_BIT),
            expected=(1 << TE_CTRL_EMPTY_BIT),
            timeout_cycles=timeout
        )

    async def wait_funnel_empty(self, timeout=2000):
        """Poll until trFunnelEmpty = 1."""
        await self.apb.poll_field(
            NTR_REG["FUNNEL_CONTROL"],
            mask=(1 << FUNNEL_CTRL_EMPTY_BIT),
            expected=(1 << FUNNEL_CTRL_EMPTY_BIT),
            timeout_cycles=timeout
        )

    async def wait_ram_empty(self, timeout=2000):
        """Poll until trRamEmpty = 1."""
        await self.apb.poll_field(
            NTR_REG["RAM_CONTROL"],
            mask=(1 << RAM_CTRL_EMPTY_BIT),
            expected=(1 << RAM_CTRL_EMPTY_BIT),
            timeout_cycles=timeout
        )

    async def full_init(self, stall_mode=False):
        """Full N-Trace init: active → RAM → funnel → encoder enable."""
        await self.release_reset()
        await self.configure_ram()
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
