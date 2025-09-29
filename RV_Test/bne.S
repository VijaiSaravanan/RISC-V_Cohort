# See LICENSE for license details.

#*****************************************************************************
# bne.S
#-----------------------------------------------------------------------------
#
# Test bne instruction (branch if not equal)
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

# 1. 0 != 1 (taken)
    li   x1, 0
    li   x2, 1
    bne  x1, x2, bne_pass_1
    j fail
bne_pass_1:

# 2. 1 != 0 (taken)
    li   x1, 1
    li   x2, 0
    bne  x1, x2, bne_pass_2
    j fail
bne_pass_2:

# 3. -1 != 1 (taken)
    li   x1, -1
    li   x2, 1
    bne  x1, x2, bne_pass_3
    j fail
bne_pass_3:

# 4. 1 != -1 (taken)
    li   x1, 1
    li   x2, -1
    bne  x1, x2, bne_pass_4
    j fail
bne_pass_4:

# 5. 0 != 0 (not taken)
    li   x1, 0
    li   x2, 0
    bne  x1, x2, bne_fail_5
bne_fail_5:

# 6. 1 != 1 (not taken)
    li   x1, 1
    li   x2, 1
    bne  x1, x2, bne_fail_6
bne_fail_6:

# 7. -1 != -1 (not taken)
    li   x1, -1
    li   x2, -1
    bne  x1, x2, bne_fail_7
bne_fail_7:

# 8-20. Bypass / dependency tests
    li   x3, 0
    li   x4, 0
    bne  x3, x4, bne_fail_8
bne_fail_8:

    li   x5, 0
    li   x6, 0
    bne  x5, x6, bne_fail_9
bne_fail_9:

    li   x7, 0
    li   x8, 0
    bne  x7, x8, bne_fail_10
bne_fail_10:

    li   x9, 0
    li   x10, 0
    bne  x9, x10, bne_fail_11
bne_fail_11:

    li   x11, 0
    li   x12, 0
    bne  x11, x12, bne_fail_12
bne_fail_12:

    li   x13, 0
    li   x14, 0
    bne  x13, x14, bne_fail_13
bne_fail_13:

# 21. Delay slot test
    li   x1, 1
    bne  x1, x0, bne_pass_21
    addi x1, x1, 1
    addi x1, x1, 1
    addi x1, x1, 1
    addi x1, x1, 1
bne_pass_21:
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
