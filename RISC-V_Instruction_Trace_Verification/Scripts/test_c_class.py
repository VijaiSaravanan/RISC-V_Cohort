import os
import csv
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

# Automatically name CSV file based on test folder name
instr_name = Path.cwd().name
csv_file = f"pc_log_{instr_name}.csv"


async def log_pc_to_csv(dut):
    """Continuously log unique PC values into a CSV file."""
    seen_pcs = set()  # Track already-logged PCs

    # Create CSV and write header
    with open(csv_file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["PC_Value (Hex)"])

        while True:
            # Read PC value
            pc_value = int(dut.soc.soc.ccore_0.riscv_etrace_ingress_port_iaddr.value)

            # Log only if it's new
            if pc_value not in seen_pcs:
                seen_pcs.add(pc_value)
                writer.writerow([hex(pc_value)])
                f.flush()
                print(f"Logged PC: {hex(pc_value)}")

            # Wait 5 clock cycles
            for _ in range(1):
                await RisingEdge(dut.CLK)


@cocotb.test()
async def test_c_class(dut):
    """Main testbench to drive clock, reset, and monitor PC values."""

    # Create a 100 ns clock
    clock = Clock(dut.CLK, 100, units="ns")
    cocotb.start_soon(clock.start(start_high=False))

    # Start PC logger
    cocotb.start_soon(log_pc_to_csv(dut))
    await RisingEdge(dut.CLK)
    # Apply reset
    dut.RST_N.value = 0
    for _ in range(400):
        await RisingEdge(dut.CLK)

    # Release reset
    dut.RST_N.value = 1
    dut._log.info("Reset released, starting simulation...")

    # Run simulation
    for _ in range(185):
        await RisingEdge(dut.CLK)

    # Small delay before ending
    await Timer(20, units="ns")
    dut._log.info(f"Simulation finished. PC log saved to {csv_file}")

