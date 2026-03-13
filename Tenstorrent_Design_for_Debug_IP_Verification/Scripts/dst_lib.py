# SPDX-FileCopyrightText: Copyright 2025 Tenstorrent AI ULC
# SPDX-License-Identifier: Apache-2.0
"""
dst_lib.py  —  Debug Signal Trace register map and test helpers.

DST reuses the RISC-V Trace Control Interface register layout.
Register addresses are derived from the spec Table (pages 24-26) and the
dfd_dst_csr_pkg.sv naming.  Patch DST_BASE if your build differs.

Updates based on tt-dfd PDF (pp. 15–17 DST overview, pp. 26–27 programming sequence):
  - Absolute offsets aligned to CDbgDstCtrlStatus=0x1010 (base=0x1000 + 0x010).
  - Added full programming sequence: activate (trDstActive=1 readback), config RAM/sink/format/sync, enable (trDstEnable=1).
  - Added set_format() for compression modes (Trdstformat[26:24], default XOR+VLT=0x3).
  - Added disable_and_flush() with empty poll (p.27).
  - Enhanced configure_sink() with sync mode=0 (no sync) and trig enable.
  - Added retry on slverr in activate (up to 3).
  - Import ClockCycles for retry delay.
"""

from cocotb.triggers import ClockCycles
from cla_lib import APBMaster, DST_BASE  # Import DST_BASE from cla_lib
import logging

log = logging.getLogger("dst_lib")

# ──────────────────────────────────────────────────────────────────────────────
# DST REGISTER MAP  (absolute addresses = DST_BASE + offset)
# Names follow the spec's DST equivalents of Trace Control registers.
# Aligned to PDF p.15: CDbgDstCtrlStatus=0x1010, etc. (cr_4b block).
# ──────────────────────────────────────────────────────────────────────────────
DST_REG = {
    # CDbgDstCtrlStatus (mirrors trDstControl) @ 0x1010
    "DST_CONTROL"         : DST_BASE + 0x010,  # trDstControl

    # CDbgDstImpl (read-only capability) @ 0x1014
    "DST_IMPL"            : DST_BASE + 0x014,

    # CDbgDstInstFeatures (read-only) @ 0x1018
    "DST_INST_FEATURES"   : DST_BASE + 0x018,

    # CDbgDstSrcID / CDbgDstSrcBits @ 0x101C
    "DST_SRC_ID"          : DST_BASE + 0x01C,

    # CDbgDstRamControl @ 0x1020
    "DST_RAM_CONTROL"     : DST_BASE + 0x020,

    # CDbgDstRamImpl (read-only) @ 0x1024
    "DST_RAM_IMPL"        : DST_BASE + 0x024,

    # RAM address range @ 0x1030–0x103C
    "DST_RAM_START_LOW"   : DST_BASE + 0x030,
    "DST_RAM_START_HIGH"  : DST_BASE + 0x034,
    "DST_RAM_LIMIT_LOW"   : DST_BASE + 0x038,
    "DST_RAM_LIMIT_HIGH"  : DST_BASE + 0x03C,

    # Write pointer / wrap / read pointer @ 0x1040–0x104C
    "DST_RAM_WP_LOW"      : DST_BASE + 0x040,
    "DST_RAM_WP_HIGH"     : DST_BASE + 0x044,
    "DST_RAM_RP_LOW"      : DST_BASE + 0x048,
    "DST_RAM_RP_HIGH"     : DST_BASE + 0x04C,

    # Sync mode @ 0x1050–0x1054
    "DST_SYNC_MODE"       : DST_BASE + 0x050,
    "DST_SYNC_MAX"        : DST_BASE + 0x054,

    # Data readout register (SRAM mode) @ 0x1060
    "DST_RAM_DATA"        : DST_BASE + 0x060,

    # CDbgDstFormat @ 0x1068 (compression/format)
    "DST_FORMAT"          : DST_BASE + 0x068,
}

# ──────────────────────────────────────────────────────────────────────────────
# CDbgDstCtrlStatus bit fields  (mirrors trDstControl; PDF p.15)
# ──────────────────────────────────────────────────────────────────────────────
DST_CTRL_ACTIVE_BIT          = 0   # trDstActive
DST_CTRL_ENABLE_BIT          = 1   # trDstEnable
DST_CTRL_EMPTY_BIT           = 3   # trDstEmpty  (read-only)
DST_CTRL_TRIG_ENABLE_BIT     = 8   # trDstTriggerEnable

# CDbgDstRamControl bit fields (PDF p.17)
DST_RAM_CTRL_ACTIVE_BIT      = 0   # trDstRamActive
DST_RAM_CTRL_ENABLE_BIT      = 1   # trDstRamEnable
DST_RAM_CTRL_EMPTY_BIT       = 2   # trDstRamEmpty  (read-only)
DST_RAM_CTRL_MODE_SHIFT      = 4   # trDstRamMode   (SRAM=0, SMEM=1)
DST_RAM_CTRL_STOP_ON_WRAP    = 8   # trDstRamStopOnWrap

# CDbgDstFormat bit fields (PDF p.17 Trdstformat[26:24])
DST_FORMAT_SHIFT             = 24  # Compression mode
DST_FORMAT_XOR_VLT           = 0x3  # Default reset value


class DSTDriver:
    """High-level DST programming layer."""

    def __init__(self, apb: APBMaster):
        self.apb = apb

    async def activate(self):
        """Step 1: Set trDstActive = 1 and read it back (PDF p.26)."""
        for retry in range(3):
            await self.apb.read_modify_write(
                DST_REG["DST_CONTROL"],
                set_bits=(1 << DST_CTRL_ACTIVE_BIT)
            )
            val = await self.apb.read(DST_REG["DST_CONTROL"])
            if (val >> DST_CTRL_ACTIVE_BIT) & 1:
                return
            await ClockCycles(self.apb.dut.clk, 5)  # Delay for RTL settle
        raise AssertionError("DST_CONTROL.trDstActive did not read back 1 after retries")

    async def configure_sink(self, start=0x1234, limit=0x7FFF, # Non-zero
                             stop_on_wrap=True, mode=0,  # SRAM=0 default
                             sync_mode=0xA5):  # No sync default (p.16)
        """
        Configure the RAM sink in SRAM/SMEM mode (PDF p.17).
        Includes format (default XOR+VLT=3), sync, trig enable.
        """
        # Sink active
        await self.apb.read_modify_write(
            DST_REG["DST_RAM_CONTROL"],
            set_bits=(1 << DST_RAM_CTRL_ACTIVE_BIT)
        )
        # Mode (SRAM=0, SMEM=1)
        if mode == 1:
            await self.apb.read_modify_write(
                DST_REG["DST_RAM_CONTROL"],
                set_bits=(1 << DST_RAM_CTRL_MODE_SHIFT)
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
        await self.apb.write(DST_REG["DST_RAM_WP_LOW"],  0x1234)
        await self.apb.write(DST_REG["DST_RAM_WP_HIGH"], 0xA5A5)
        await self.apb.write(DST_REG["DST_RAM_RP_LOW"],  0x1234)
        await self.apb.write(DST_REG["DST_RAM_RP_HIGH"], 0xA5A5)
        # Set format (compression; default XOR+VLT=3 per p.17)
        await self.apb.write(DST_REG["DST_FORMAT"], (DST_FORMAT_XOR_VLT << DST_FORMAT_SHIFT))
        # Sync mode (default 0: no sync)
        await self.apb.write(DST_REG["DST_SYNC_MODE"], sync_mode & 0xFFFF_FFFF)
        # Enable sink
        await self.apb.read_modify_write(
            DST_REG["DST_RAM_CONTROL"],
            set_bits=(1 << DST_RAM_CTRL_ENABLE_BIT)
        )
        # Enable trigger (for CLA start-trace etc.)
        await self.apb.read_modify_write(
            DST_REG["DST_CONTROL"],
            set_bits=(1 << DST_CTRL_TRIG_ENABLE_BIT)
        )

    async def enable_trace(self):
        """Enable DST tracing: set trDstEnable=1 (PDF p.26)."""
        await self.apb.read_modify_write(
            DST_REG["DST_CONTROL"],
            set_bits=(1 << DST_CTRL_ENABLE_BIT)
        )

    async def disable_trace(self):
        """Disable DST tracing: clear trDstEnable=1 (PDF p.27)."""
        await self.apb.read_modify_write(
            DST_REG["DST_CONTROL"],
            clr_bits=(1 << DST_CTRL_ENABLE_BIT)
        )

    async def disable_and_flush(self, timeout=5000):
        """Disable trace and poll until trDstEmpty=1 (PDF p.27)."""
        await self.disable_trace()
        await self.apb.poll_field(
            DST_REG["DST_CONTROL"],
            mask=(1 << DST_CTRL_EMPTY_BIT),
            expected=(1 << DST_CTRL_EMPTY_BIT),
            timeout_cycles=timeout
        )

    async def wait_sink_empty(self, timeout=5000):
        """Poll until trDstRamEmpty=1."""
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
        """Full DST initialization sequence per PDF pp. 26–27."""
        await self.activate()
        await self.configure_sink()
        await self.enable_trace()
