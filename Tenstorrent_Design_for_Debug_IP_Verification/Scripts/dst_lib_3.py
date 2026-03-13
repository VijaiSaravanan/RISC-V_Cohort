# SPDX-FileCopyrightText: Copyright 2025 Tenstorrent AI ULC
# SPDX-License-Identifier: Apache-2.0
"""
dst_lib.py  —  Debug Signal Trace register map and test helpers.

DST reuses the RISC-V Trace Control Interface register layout.
Register addresses are derived from the spec Table (pages 24-26) and the
dfd_dst_csr_pkg.sv naming.  Patch DST_BASE if your build differs.
"""

from cla_lib_3 import APBMaster, DST_BASE
import logging

log = logging.getLogger("dst_lib_3")

# ──────────────────────────────────────────────────────────────────────────────
# DST REGISTER MAP  (offsets from DST_BASE)
# Names follow the spec's DST equivalents of Trace Control registers
# ──────────────────────────────────────────────────────────────────────────────
DST_REG = {
    # trDstControl — in DST namespace (0x1000)
    "DST_CONTROL"         : DST_BASE + 0x000,  # 0x1000: trDstControl
    "DST_IMPL"            : DST_BASE + 0x004,  # 0x1004: trDstImpl (RO)
    "DST_INST_FEATURES"   : DST_BASE + 0x008,  # 0x1008: trDstInstFeatures (RO)
    "DST_SRC_ID"          : DST_BASE + 0x00C,  # 0x100C: trDstSrcID

    # trDstRam* — in TR namespace (decoded at 0x6000 per TR_CSR.pdf)
    # TR CSR: Trdstramcontrol@0x6000, Trdstramstartlow@0x6010, etc.
    "DST_RAM_CONTROL"     : 0x6000,
    "DST_RAM_IMPL"        : 0x6004,
    "DST_RAM_START_LOW"   : 0x6010,
    "DST_RAM_START_HIGH"  : 0x6014,
    "DST_RAM_LIMIT_LOW"   : 0x6018,
    "DST_RAM_LIMIT_HIGH"  : 0x601C,
    "DST_RAM_WP_LOW"      : 0x6020,
    "DST_RAM_WP_HIGH"     : 0x6024,
    "DST_RAM_RP_LOW"      : 0x6028,
    "DST_RAM_RP_HIGH"     : 0x602C,
    "DST_RAM_DATA"        : 0x6040,
}

# ──────────────────────────────────────────────────────────────────────────────
# trDstControl bit fields  (mirrors trTeControl)
# ──────────────────────────────────────────────────────────────────────────────
DST_CTRL_ACTIVE_BIT          = 0   # trDstActive
DST_CTRL_ENABLE_BIT          = 1   # trDstEnable
DST_CTRL_INST_TRACING_BIT    = 2   # trDstInstTracing
DST_CTRL_EMPTY_BIT           = 3   # trDstEmpty  (read-only)
DST_CTRL_TRIG_ENABLE_BIT     = 8   # trDstInstTriggerEnable

# trDstRamControl bit fields
DST_RAM_CTRL_ACTIVE_BIT      = 0   # trDstRamActive
DST_RAM_CTRL_ENABLE_BIT      = 1   # trDstRamEnable
DST_RAM_CTRL_EMPTY_BIT       = 2   # trDstRamEmpty  (read-only)
DST_RAM_CTRL_MODE_SHIFT      = 4   # trDstRamMode   (SRAM=0, SMEM=1)
DST_RAM_CTRL_STOP_ON_WRAP    = 8   # trDstRamStopOnWrap


class DSTDriver:
    """High-level DST programming layer."""

    def __init__(self, apb: APBMaster):
        self.apb = apb

    async def release_reset(self):
        """Step 1: Set trDstActive = 1 and read it back."""
        await self.apb.read_modify_write(
            DST_REG["DST_CONTROL"],
            set_bits=(1 << DST_CTRL_ACTIVE_BIT)
        )
        val = await self.apb.read(DST_REG["DST_CONTROL"])
        assert (val >> DST_CTRL_ACTIVE_BIT) & 1, \
            "DST_CONTROL.trDstActive did not read back 1"

    async def configure_sram(self, start=0, limit=0x7FFF,
                             stop_on_wrap=True):
        """Configure the RAM sink in SRAM mode."""
        # RAM active
        await self.apb.read_modify_write(
            DST_REG["DST_RAM_CONTROL"],
            set_bits=(1 << DST_RAM_CTRL_ACTIVE_BIT)
        )
        # Mode = SRAM (0)
        await self.apb.read_modify_write(
            DST_REG["DST_RAM_CONTROL"],
            clr_bits=(1 << DST_RAM_CTRL_MODE_SHIFT)
        )
        # StopOnWrap
        if stop_on_wrap:
            await self.apb.read_modify_write(
                DST_REG["DST_RAM_CONTROL"],
                set_bits=(1 << DST_RAM_CTRL_STOP_ON_WRAP)
            )
        # Address range
        await self.apb.write(DST_REG["DST_RAM_START_LOW"],  start  & 0xFFFF_FFFF)
        await self.apb.write(DST_REG["DST_RAM_START_HIGH"], (start >> 32) & 0xFFFF_FFFF)
        await self.apb.write(DST_REG["DST_RAM_LIMIT_LOW"],  limit  & 0xFFFF_FFFF)
        await self.apb.write(DST_REG["DST_RAM_LIMIT_HIGH"], (limit >> 32) & 0xFFFF_FFFF)
        # Clear WP/RP
        await self.apb.write(DST_REG["DST_RAM_WP_LOW"],  0)
        await self.apb.write(DST_REG["DST_RAM_WP_HIGH"], 0)
        await self.apb.write(DST_REG["DST_RAM_RP_LOW"],  0)
        await self.apb.write(DST_REG["DST_RAM_RP_HIGH"], 0)
        # Enable RAM
        await self.apb.read_modify_write(
            DST_REG["DST_RAM_CONTROL"],
            set_bits=(1 << DST_RAM_CTRL_ENABLE_BIT)
        )

    async def enable_trace(self):
        """Enable DST tracing: set Enable and InstTracing bits."""
        await self.apb.read_modify_write(
            DST_REG["DST_CONTROL"],
            set_bits=(1 << DST_CTRL_ENABLE_BIT) | (1 << DST_CTRL_INST_TRACING_BIT)
        )

    async def disable_trace(self):
        """Disable DST tracing: clear Enable bit."""
        await self.apb.read_modify_write(
            DST_REG["DST_CONTROL"],
            clr_bits=(1 << DST_CTRL_ENABLE_BIT)
        )

    async def wait_empty(self, timeout=2000):
        """Poll until trDstEmpty = 1."""
        await self.apb.poll_field(
            DST_REG["DST_CONTROL"],
            mask=(1 << DST_CTRL_EMPTY_BIT),
            expected=(1 << DST_CTRL_EMPTY_BIT),
            timeout_cycles=timeout
        )

    async def wait_ram_empty(self, timeout=2000):
        """Poll until trDstRamEmpty = 1."""
        await self.apb.poll_field(
            DST_REG["DST_RAM_CONTROL"],
            mask=(1 << DST_RAM_CTRL_EMPTY_BIT),
            expected=(1 << DST_RAM_CTRL_EMPTY_BIT),
            timeout_cycles=timeout
        )

    async def read_wp(self):
        """Return the write pointer (64-bit)."""
        lo = await self.apb.read(DST_REG["DST_RAM_WP_LOW"])
        hi = await self.apb.read(DST_REG["DST_RAM_WP_HIGH"])
        return (hi << 32) | lo

    async def read_rp(self):
        """Return the read pointer (64-bit)."""
        lo = await self.apb.read(DST_REG["DST_RAM_RP_LOW"])
        hi = await self.apb.read(DST_REG["DST_RAM_RP_HIGH"])
        return (hi << 32) | lo

    async def full_init(self):
        """Full DST initialization sequence per spec Programming Guide."""
        await self.release_reset()
        await self.configure_sram()
        await self.enable_trace()
