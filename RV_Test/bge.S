# See LICENSE for license details.

#*****************************************************************************
# bge.S
#-----------------------------------------------------------------------------
#
# Test bge instruction (branch if greater than or equal)
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

# 1. bge 0 >= 0
    li   x1, 0
    li   x2, 0
    bge  x1, x2, bge_pass_1
    li   x3, 1
bge_pass_1:
    li   x3, 0
    bne  x3, x0, fail

# 2. bge 1 >= 1
    li   x1, 1
    li   x2, 1
    bge  x1, x2, bge_pass_2
    li   x3, 1
bge_pass_2:
    li   x3, 0
    bne  x3, x0, fail

# 3. bge -1 >= -1
    li   x1, -1
    li   x2, -1
    bge  x1, x2, bge_pass_3
    li   x3, 1
bge_pass_3:
    li   x3, 0
    bne  x3, x0, fail

# 4. bge 1 >= 0
    li   x1, 1
    li   x2, 0
    bge  x1, x2, bge_pass_4
    li   x3, 1
bge_pass_4:
    li   x3, 0
    bne  x3, x0, fail

# 5. bge 1 >= -1
    li   x1, 1
    li   x2, -1
    bge  x1, x2, bge_pass_5
    li   x3, 1
bge_pass_5:
    li   x3, 0
    bne  x3, x0, fail

# 6. bge -1 >= -2
    li   x1, -1
    li   x2, -2
    bge  x1, x2, bge_pass_6
    li   x3, 1
bge_pass_6:
    li   x3, 0
    bne  x3, x0, fail

# 7. bge 0 >= 1 -> not taken
    li   x1, 0
    li   x2, 1
    bge  x1, x2, bge_fail_7
    li   x3, 0
bge_fail_7:

# 8. bge -1 >= 1 -> not taken
    li   x1, -1
    li   x2, 1
    bge  x1, x2, bge_fail_8
    li   x3, 0
bge_fail_8:

# 9. bge -2 >= -1 -> not taken
    li   x1, -2
    li   x2, -1
    bge  x1, x2, bge_fail_9
    li   x3, 0
bge_fail_9:

# 10. bge -2 >= 1 -> not taken
    li   x1, -2
    li   x2, 1
    bge  x1, x2, bge_fail_10
    li   x3, 0
bge_fail_10:

# 11. Src1 = dest
    li   x1, 5
    bge  x1, x2, bge_pass_11
    li   x1, 1
bge_pass_11:
    li   x3, 0
    bne  x3, x0, fail

# 12. Dependency chain
    li   x5, 3
    li   x6, 2
    bge  x5, x6, bge_pass_12
    li   x7, 1
bge_pass_12:
    li   x7, 0
    bne  x7, x0, fail

# 13. Src1 = zero
    li   x1, 0
    li   x2, 0
    bge  x1, x2, bge_pass_13
    li   x3, 1
bge_pass_13:
    li   x3, 0
    bne  x3, x0, fail

# 14. Src2 = zero
    li   x1, 1
    li   x2, 0
    bge  x1, x2, bge_pass_14
    li   x3, 1
bge_pass_14:
    li   x3, 0
    bne  x3, x0, fail

# 15. Negative numbers
    li   x1, -3
    li   x2, -5
    bge  x1, x2, bge_pass_15
    li   x3, 1
bge_pass_15:
    li   x3, 0
    bne  x3, x0, fail

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
