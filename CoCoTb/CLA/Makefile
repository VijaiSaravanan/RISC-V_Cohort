TOPLEVEL_LANG = verilog
VERILOG_SOURCES = $(PWD)/cla.v   # path to your Verilog file
TOPLEVEL = cla                    # must match module name
COCOTB_TEST_MODULES = test_cla   # your Python testbench filename without .py
SIM = icarus

include $(shell cocotb-config --makefiles)/Makefile.sim

