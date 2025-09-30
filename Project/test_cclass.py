import os
import random
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


async def print_info(dut):
      while True:
        print("the pc value is : ", hex(dut.soc.soc.ccore_0.riscv_etrace_ingress_port_iaddr.value))
        for i in range(0,5): 
            await RisingEdge(dut.CLK)
    
    
@cocotb.test()
async def test_cclass(dut):
    
    clock = Clock(dut.CLK, 100, units="ns")  # Create a 10us period clock on port clk
    # Start the clock. Start it low to avoid issues on the first RisingEdge
    cocotb.start_soon(clock.start(start_high=False))
    cocotb.start_soon(print_info(dut))
    dut.RST_N.value = 0
    for i in range(0,400): 
        await RisingEdge(dut.CLK)
    
    dut.RST_N.value = 1
    dut._log.info('Incrementing')
    for i in range(0,185):
        await RisingEdge(dut.CLK)
    
    await Timer(8,units="ns")

