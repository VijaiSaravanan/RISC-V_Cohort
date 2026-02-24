TOPLEVEL_LANG = verilog
SIM           = verilator

TOPLEVEL      = dfd_top
COCOTB_TEST_MODULES = test_csr
# ------------------------------------------------------------
# Source files provided via filelist
# ------------------------------------------------------------
# VERILOG_SOURCES intentionally empty
# Using tt_dfd.f instead
EXTRA_ARGS += -f tt_dfd.f
# ------------------------------------------------------------
# Verilator optimization & compatibility flags
# ------------------------------------------------------------
EXTRA_ARGS += --no-timing --public-flat-rw -O3 --x-assign fast --x-initial fast --noassert --bbox-sys --autoflush --threads 1 --output-split 20000 --output-split-ctrace 10000

EXTRA_ARGS += -Wno-STMTDLY -Wno-UNOPTFLAT -Wno-WIDTH -Wno-lint -Wno-COMBDLY -Wno-INITIALDLY -Wno-WIDTHCONCAT -Wno-SPLITVAR
# ------------------------------------------------------------
# Waveform generation (VCD)
# ------------------------------------------------------------
WAVES = 1
# ------------------------------------------------------------
# Include Cocotb build system
# ------------------------------------------------------------
include $(shell cocotb-config --makefiles)/Makefile.sim
