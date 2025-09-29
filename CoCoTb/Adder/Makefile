TOPLEVEL_LANG = verilog
VERILOG_SOURCES = $(PWD)/adder.v
TOPLEVEL = adder
MODULE = test_adder   # Python testbench file name (without .py)

SIM = icarus   # or verilator, questa, vcs, etc.

include $(shell cocotb-config --makefiles)/Makefile.sim
