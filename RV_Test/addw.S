# See LICENSE for license details.

#*****************************************************************************
# addw.S
#-----------------------------------------------------------------------------
#
# Test addw instruction (32-bit result sign-extended to 64-bit)
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

# 1. Basic addw small numbers
    li   x1, 1
    addw x2, x1, 2
    li   x3, 3
    bne  x2, x3, fail

# 2. addw with zero + zero
    li   x1, 0
    addw x2, x1, 0
    li   x3, 0
    bne  x2, x3, fail

# 3. Positive + positive
    li   x1, 10
    addw x2, x1, 20
    li   x3, 30
    bne  x2, x3, fail

# 4. Positive + negative
    li   x1, 15
    addw x2, x1, -5
    li   x3, 10
    bne  x2, x3, fail

# 5. Negative + negative
    li   x1, -8
    addw x2, x1, -12
    li   x3, -20
    bne  x2, x3, fail

# 6. Src1 = dest
    li   x1, 13
    addw x1, x1, 11
    li   x3, 24
    bne  x1, x3, fail

# 7. Src2 = dest
    li   x1, 14
    addw x2, x1, 11
    li   x3, 25
    bne  x2, x3, fail

# 8. Src1 = Src2 = dest
    li   x1, 7
    addw x1, x1, x1
    li   x3, 14
    bne  x1, x3, fail

# 9. Zero register as src1
    li   x2, 15
    addw x3, x0, x2
    li   x4, 15
    bne  x3, x4, fail

# 10. Zero register as src2
    li   x1, 32
    addw x3, x1, x0
    li   x4, 32
    bne  x3, x4, fail

# 11. Zero register as dest
    li   x1, 10
    li   x2, 20
    addw x0, x1, x2
    li   x3, 0
    bne  x0, x3, fail

# 12. Large positive wrap
    li   x1, 0x7fffffff
    addw x2, x1, 1
    li   x3, 0xffffffff80000000
    bne  x2, x3, fail

# 13. Large negative wrap
    li   x1, -0x80000000
    addw x2, x1, -1
    li   x3, 0x7fffffff
    bne  x2, x3, fail

# 14. Bypass test
    li   x1, 13
    addw x2, x1, 11
    addw x4, x2, x0
    li   x3, 24
    bne  x4, x3, fail

# 15. Dependency chain
    li   x1, 1
    addw x2, x1, 2
    addw x3, x2, 2
    addw x4, x3, 1
    li   x5, 6
    bne  x4, x5, fail

# 16. Large positive wrap-around
    li   x1, 0x7fffffff
    addw x2, x1, 0x7fffffff
    li   x3, -2
    bne  x2, x3, fail

# 17. Large negative wrap-around
    li   x1, -0x80000000
    addw x2, x1, -0x80000000
    li   x3, 0
    bne  x2, x3, fail

# 18. Back-to-back dependency chain
    li   x1, 1
    addw x2, x1, 2
    addw x3, x2, -1
    addw x4, x3, 0
    li   x5, 2
    bne  x4, x5, fail

# 19. Zero + negative
    addw x2, x0, -15
    li   x3, -15
    bne  x2, x3, fail

# 20. Src = dest multiple times
    li   x1, 5
    addw x1, x1, 10
    addw x1, x1, -3
    li   x3, 12
    bne  x1, x3, fail

# 21. Max negative + positive
    li   x1, -0x80000000
    addw x2, x1, 0x7fffffff
    li   x3, -1
    bne  x2, x3, fail

# 22. Min positive + negative
    li   x1, 0x00000001
    addw x2, x1, -0x2
    li   x3, -1
    bne  x2, x3, fail

# 23. Edge positive
    li   x1, 0x12345678
    addw x2, x1, 0x7fff
    li   x3, 0x1234c577
    bne  x2, x3, fail

# 24. Edge negative
    li   x1, 0x12345678
    addw x2, x1, -0x8000
    li   x3, 0x1233d678
    bne  x2, x3, fail

# 25. Chain with zero result
    li   x1, 1
    addw x2, x1, -1
    addw x3, x2, 0
    li   x4, 0
    bne  x3, x4, fail

# --- End of tests ---
pass:
    li   a0, 1
    ecall

fail:
    li   a0, 0
    ecall

RVTEST_CODE_END

.data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
