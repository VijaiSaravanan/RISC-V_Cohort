# See LICENSE for license details.

#*****************************************************************************
# bltu_full.S
#-----------------------------------------------------------------------------
#
# Test bltu instruction (branch if less than, unsigned)
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

# 1. 0 < 1 (taken)
    li   x1, 0x00000000
    li   x2, 0x00000001
    bltu x1, x2, bltu_pass_1
    j fail
bltu_pass_1:

# 2. 0xfffffffe < 0xffffffff (taken)
    li   x1, 0xfffffffe
    li   x2, 0xffffffff
    bltu x1, x2, bltu_pass_2
    j fail
bltu_pass_2:

# 3. 0 < 0xffffffff (taken)
    li   x1, 0x00000000
    li   x2, 0xffffffff
    bltu x1, x2, bltu_pass_3
    j fail
bltu_pass_3:

# 4. 1 < 0 (not taken)
    li   x1, 0x00000001
    li   x2, 0x00000000
    bltu x1, x2, bltu_fail_4
bltu_fail_4:

# 5. 0xffffffff < 0xfffffffe (not taken)
    li   x1, 0xffffffff
    li   x2, 0xfffffffe
    bltu x1, x2, bltu_fail_5
bltu_fail_5:

# 6. 0xffffffff < 0x00000000 (not taken)
    li   x1, 0xffffffff
    li   x2, 0x00000000
    bltu x1, x2, bltu_fail_6
bltu_fail_6:

# 7. 0x80000000 < 0x7fffffff (not taken)
    li   x1, 0x80000000
    li   x2, 0x7fffffff
    bltu x1, x2, bltu_fail_7
bltu_fail_7:

# 8-20. Bypass / dependency tests (check forwarding of Src1 and Src2)
    li   x3, 0xf0000000
    li   x4, 0xefffffff
    bltu x3, x4, bltu_fail_8
bltu_fail_8:

    li   x5, 0xf0000000
    li   x6, 0xefffffff
    bltu x5, x6, bltu_fail_9
bltu_fail_9:

    li   x7, 0xf0000000
    li   x8, 0xefffffff
    bltu x7, x8, bltu_fail_10
bltu_fail_10:

    li   x9, 0xf0000000
    li   x10, 0xefffffff
    bltu x9, x10, bltu_fail_11
bltu_fail_11:

    li   x11, 0xf0000000
    li   x12, 0xefffffff
    bltu x11, x12, bltu_fail_12
bltu_fail_12:

    li   x13, 0xf0000000
    li   x14, 0xefffffff
    bltu x13, x14, bltu_fail_13
bltu_fail_13:

# 21. Delay slot test
    li   x1, 1
    bltu x0, x1, bltu_pass_21
    addi x1, x1, 1
    addi x1, x1, 1
    addi x1, x1, 1
    addi x1, x1, 1
bltu_pass_21:
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
