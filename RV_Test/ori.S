# See LICENSE for license details.

#*****************************************************************************
# ori.S
#-----------------------------------------------------------------------------
#
# Test ori instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

#-------------------------------------------------------------
# 1. Basic logical tests
#-------------------------------------------------------------
# TEST 1
    li x1, 0xffffffffff00ff00
    ori x2, x1, 0x0f0f
    li x3, 0xffffffffffffff0f
    bne x2, x3, fail

# TEST 2
    li x1, 0x000000000ff00ff0
    ori x2, x1, 0x00f
    li x3, 0x000000000ff00ff0
    bne x2, x3, fail

# TEST 3
    li x1, 0x0000000000ff00ff
    ori x2, x1, 0x70f
    li x3, 0x0000000000ff07ff
    bne x2, x3, fail

# TEST 4
    li x1, 0xfffffffff00ff00f
    ori x2, x1, 0x0f0
    li x3, 0xfffffffff00ff0ff
    bne x2, x3, fail

#-------------------------------------------------------------
# 2. Source = Destination tests
#-------------------------------------------------------------
# TEST 5 - SRC1 = DEST
    li x4, 0xff00ff00
    ori x4, x4, 0x0f0
    li x3, 0xff00fff0
    bne x4, x3, fail

#-------------------------------------------------------------
# 3. Bypassing tests
#-------------------------------------------------------------
# TEST 6 - Dest bypass
    li x5, 0x000000000ff00ff0
    ori x6, x5, 0x0f0
    ori x7, x6, 0x0f0
    li x3, 0x000000000ff00ff0
    bne x7, x3, fail

# TEST 7 - Src1 bypass
    li x8, 0x0000000000ff00ff
    ori x9, x8, 0xf0f
    ori x10, x9, 0x70f
    li x3, 0xffffffffffffffff
    bne x10, x3, fail

# TEST 8 - Zero source
    ori x11, x0, 0x0f0
    li x3, 0x0f0
    bne x11, x3, fail

# TEST 9 - Zero destination (writes ignored for x0)
    ori x0, x0, 0x70f
    li x12, 0
    bne x0, x12, fail

#-------------------------------------------------------------
# 4. Edge cases
#-------------------------------------------------------------
# TEST 10 - All ones
    li x13, -1
    ori x14, x13, 0x0
    li x3, -1
    bne x14, x3, fail

# TEST 11 - All zeros
    li x15, 0
    ori x16, x15, 0
    beq x16, x0, ok

# TEST 12 - Negative immediate
    li x17, -0x12345678
    ori x18, x17, 0x876
    li x3, -0x1234480
    bne x18, x3, fail

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
