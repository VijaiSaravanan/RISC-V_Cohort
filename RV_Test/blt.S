# See LICENSE for license details.

#*****************************************************************************
# blt_full.S
#-----------------------------------------------------------------------------
#
# Test blt instruction (branch if less than, signed)
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

# 1. 0 < 1 (taken)
    li   x1, 0
    li   x2, 1
    blt  x1, x2, blt_pass_1
    j fail
blt_pass_1:

# 2. -1 < 1 (taken)
    li   x1, -1
    li   x2, 1
    blt  x1, x2, blt_pass_2
    j fail
blt_pass_2:

# 3. -2 < -1 (taken)
    li   x1, -2
    li   x2, -1
    blt  x1, x2, blt_pass_3
    j fail
blt_pass_3:

# 4. 1 < 0 (not taken)
    li   x1, 1
    li   x2, 0
    blt  x1, x2, blt_fail_4
blt_fail_4:

# 5. 1 < -1 (not taken)
    li   x1, 1
    li   x2, -1
    blt  x1, x2, blt_fail_5
blt_fail_5:

# 6. -1 < -2 (not taken)
    li   x1, -1
    li   x2, -2
    blt  x1, x2, blt_fail_6
blt_fail_6:

# 7. 1 < -2 (not taken)
    li   x1, 1
    li   x2, -2
    blt  x1, x2, blt_fail_7
blt_fail_7:

# 8-20. Bypassing / dependency tests
# (check forwarding of Src1 and Src2 through pipeline)
    li   x3, 0
    li   x4, -1
    blt  x3, x4, blt_fail_8
blt_fail_8:

    li   x5, 0
    li   x6, -1
    blt  x5, x6, blt_fail_9
blt_fail_9:

    li   x7, 0
    li   x8, -1
    blt  x7, x8, blt_fail_10
blt_fail_10:

    li   x9, 0
    li   x10, -1
    blt  x9, x10, blt_fail_11
blt_fail_11:

    li   x11, 0
    li   x12, -1
    blt  x11, x12, blt_fail_12
blt_fail_12:

    li   x13, 0
    li   x14, -1
    blt  x13, x14, blt_fail_13
blt_fail_13:

# 21. Delay slot test
    li   x1, 1
    blt  x0, x1, blt_pass_21
    addi x1, x1, 1
    addi x1, x1, 1
    addi x1, x1, 1
    addi x1, x1, 1
blt_pass_21:
    addi x1, x1, 1
    addi x1, x1, 1

# --- End of tests ---
pass:
    li a0, 1
    ecall

fail:
    li a0, 0
    ecall

RVTEST_CODE_END

.data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
