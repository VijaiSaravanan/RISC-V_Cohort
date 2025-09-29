# See LICENSE for license details.

#*****************************************************************************
# bgeu.S
#-----------------------------------------------------------------------------
#
# Test bgeu instruction (branch if greater than or equal, unsigned)
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

# 1. Zero >= Zero
    li   x1, 0x00000000
    li   x2, 0x00000000
    bgeu x1, x2, bgeu_pass_1
    j fail
bgeu_pass_1:

# 2. One >= One
    li   x1, 0x00000001
    li   x2, 0x00000001
    bgeu x1, x2, bgeu_pass_2
    j fail
bgeu_pass_2:

# 3. Max unsigned >= Max unsigned
    li   x1, 0xffffffff
    li   x2, 0xffffffff
    bgeu x1, x2, bgeu_pass_3
    j fail
bgeu_pass_3:

# 4. Small > Zero
    li   x1, 0x00000001
    li   x2, 0x00000000
    bgeu x1, x2, bgeu_pass_4
    j fail
bgeu_pass_4:

# 5. Max > Max-1
    li   x1, 0xffffffff
    li   x2, 0xfffffffe
    bgeu x1, x2, bgeu_pass_5
    j fail
bgeu_pass_5:

# 6. Max > Zero
    li   x1, 0xffffffff
    li   x2, 0x00000000
    bgeu x1, x2, bgeu_pass_6
    j fail
bgeu_pass_6:

# 7. Zero < One (not taken)
    li   x1, 0x00000000
    li   x2, 0x00000001
    bgeu x1, x2, bgeu_fail_7
bgeu_fail_7:

# 8. Max-1 < Max (not taken)
    li   x1, 0xfffffffe
    li   x2, 0xffffffff
    bgeu x1, x2, bgeu_fail_8
bgeu_fail_8:

# 9. Zero < Max (not taken)
    li   x1, 0x00000000
    li   x2, 0xffffffff
    bgeu x1, x2, bgeu_fail_9
bgeu_fail_9:

# 10. 0x7fffffff < 0x80000000 (not taken)
    li   x1, 0x7fffffff
    li   x2, 0x80000000
    bgeu x1, x2, bgeu_fail_10
bgeu_fail_10:

# 11. Dependency chain
    li   x3, 0x1000
    li   x4, 0x0fff
    bgeu x3, x4, bgeu_pass_11
    j fail
bgeu_pass_11:

# 12. Src1 = dest bypass
    li   x5, 0xefffffff
    li   x6, 0xf0000000
    bgeu x5, x6, bgeu_pass_12
    j fail
bgeu_pass_12:

# 13. Src2 = dest bypass
    li   x7, 0x12345678
    li   x8, 0x12345678
    bgeu x7, x8, bgeu_pass_13
    j fail
bgeu_pass_13:

# 14. Src1 = zero
    li   x1, 0x00000000
    li   x2, 0x00000000
    bgeu x1, x2, bgeu_pass_14
    j fail
bgeu_pass_14:

# 15. Src2 = zero, Src1 > zero
    li   x1, 0x1
    li   x2, 0x0
    bgeu x1, x2, bgeu_pass_15
    j fail
bgeu_pass_15:

# 16. Backward branch (taken)
    li   x1, 0x10
    li   x2, 0x10
    bgeu x1, x2, bgeu_pass_16
    j fail
bgeu_pass_16:

# 17. Forward branch (not taken)
    li   x1, 0x5
    li   x2, 0x10
    bgeu x1, x2, bgeu_fail_17
bgeu_fail_17:

# 18. Max unsigned Src1, small Src2
    li   x1, 0xffffffff
    li   x2, 0x00000001
    bgeu x1, x2, bgeu_pass_18
    j fail
bgeu_pass_18:

# 19. Max-1 < Max
    li   x1, 0xfffffffe
    li   x2, 0xffffffff
    bgeu x1, x2, bgeu_fail_19
bgeu_fail_19:

# 20. Zero Src1, Max Src2
    li   x1, 0x00000000
    li   x2, 0xffffffff
    bgeu x1, x2, bgeu_fail_20
bgeu_fail_20:

# 21. Back-to-back branches with dependency
    li   x9, 0xabcdef01
    li   x10, 0xabcdef00
    bgeu x9, x10, bgeu_pass_21
    j fail
bgeu_pass_21:

# 22. Edge unsigned wraparound
    li   x11, 0xffffffff
    li   x12, 0x00000000
    bgeu x11, x12, bgeu_pass_22
    j fail
bgeu_pass_22:

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
