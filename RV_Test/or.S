# See LICENSE for license details.

#*****************************************************************************
# or.S
#-----------------------------------------------------------------------------
#
# Test or instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

#-------------------------------------------------------------
# 1. Basic logical tests
#-------------------------------------------------------------
# TEST 1
    li x1, 0xff00ff00
    li x2, 0x0f0f0f0f
    or x3, x1, x2
    li x4, 0xff0fff0f
    bne x3, x4, fail

# TEST 2
    li x1, 0x0ff00ff0
    li x2, 0xf0f0f0f0
    or x3, x1, x2
    li x4, 0xfff0fff0
    bne x3, x4, fail

# TEST 3
    li x1, 0x00ff00ff
    li x2, 0x0f0f0f0f
    or x3, x1, x2
    li x4, 0x0fff0fff
    bne x3, x4, fail

# TEST 4
    li x1, 0xf00ff00f
    li x2, 0xf0f0f0f0
    or x3, x1, x2
    li x4, 0xf0fff0ff
    bne x3, x4, fail

#-------------------------------------------------------------
# 2. Source = Destination tests
#-------------------------------------------------------------
# TEST 5 - SRC1 = DEST
    li x1, 0xff00ff00
    li x2, 0x0f0f0f0f
    or x1, x1, x2
    li x4, 0xff0fff0f
    bne x1, x4, fail

# TEST 6 - SRC2 = DEST
    li x1, 0xff00ff00
    li x2, 0x0f0f0f0f
    or x2, x1, x2
    li x4, 0xff0fff0f
    bne x2, x4, fail

# TEST 7 - SRC1 = SRC2 = DEST
    li x1, 0x00ff00ff
    or x1, x1, x1
    li x4, 0x00ff00ff
    bne x1, x4, fail

#-------------------------------------------------------------
# 3. Bypassing tests (simulate pipeline hazards)
#-------------------------------------------------------------
# TEST 8 - Dest bypass
    li x5, 0x0f0f0f0f
    li x6, 0xf0f0f0f0
    or x7, x5, x6
    or x8, x7, x5      # x7 used immediately
    li x4, 0xffffffff
    bne x8, x4, fail

# TEST 9 - Src1 bypass
    li x9, 0x12345678
    li x10, 0x87654321
    or x11, x9, x10
    or x12, x11, x10   # x11 used immediately
    li x4, 0x97755779
    bne x12, x4, fail

# TEST 10 - Src2 bypass
    li x13, 0x11111111
    li x14, 0x22222222
    or x15, x13, x14
    or x16, x13, x15   # x15 used immediately
    li x4, 0x33333333
    bne x16, x4, fail

#-------------------------------------------------------------
# 4. Zero source tests
#-------------------------------------------------------------
# TEST 11 - Both sources zero
    li x17, 0
    li x18, 0
    or x19, x17, x18
    beq x19, x0, ok

# TEST 12 - SRC1 zero
    li x20, 0
    li x21, 0xdeadbeef
    or x22, x20, x21
    li x4, 0xdeadbeef
    bne x22, x4, fail

# TEST 13 - SRC2 zero
    li x23, 0xdeadbeef
    li x24, 0
    or x25, x23, x24
    li x4, 0xdeadbeef
    bne x25, x4, fail

#-------------------------------------------------------------
# 5. Edge case tests
#-------------------------------------------------------------
# TEST 14 - All ones
    li x26, -1          # 0xffffffffffffffff
    li x27, 0
    or x28, x26, x27
    li x4, -1
    bne x28, x4, fail

# TEST 15 - All zeros
    li x29, 0
    li x30, 0
    or x31, x29, x30
    beq x31, x0, ok

# TEST 16 - Negative numbers
    li x1, -0x12345678
    li x2, 0x12345678
    or x3, x1, x2
    li x4, -1
    bne x3, x4, fail

ok:
    li a0, 1
    ecall                  # exit success

fail:
    li a0, 0
    ecall                  # exit failure

RVTEST_CODE_END

  .data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
