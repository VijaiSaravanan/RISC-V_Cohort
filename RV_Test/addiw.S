# See LICENSE for license details.

#*****************************************************************************
# addiw.S
#-----------------------------------------------------------------------------
#
# Test addiw instruction (32-bit result sign-extended to 64-bit)
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

# 1. Basic addiw small numbers
    li   x1, 1
    addiw x2, x1, 2
    li   x3, 3
    bne  x2, x3, fail

# 2. addiw with zero + immediate
    li   x1, 0
    addiw x2, x1, 0
    li   x3, 0
    bne  x2, x3, fail

# 3. Positive + positive
    li   x1, 10
    addiw x2, x1, 20
    li   x3, 30
    bne  x2, x3, fail

# 4. Positive + negative
    li   x1, 15
    addiw x2, x1, -5
    li   x3, 10
    bne  x2, x3, fail

# 5. Negative + negative
    li   x1, -8
    addiw x2, x1, -12
    li   x3, -20
    bne  x2, x3, fail

# 6. Src1 = dest
    li   x1, 13
    addiw x1, x1, 11
    li   x3, 24
    bne  x1, x3, fail

# 7. Immediate zero
    li   x1, 99
    addiw x2, x1, 0
    li   x3, 99
    bne  x2, x3, fail

# 8. Zero register as src1
    addiw x2, x0, 25
    li   x3, 25
    bne  x2, x3, fail

# 9. Zero register as dest
    li   x1, 15
    addiw x0, x1, 10
    li   x3, 0
    bne  x0, x3, fail

# 10. Large positive 32-bit boundary
    li   x1, 0x7fffffff
    addiw x2, x1, 1
    li   x3, 0xffffffff80000000
    bne  x2, x3, fail

# 11. Large negative 32-bit boundary
    li   x1, -0x80000000
    addiw x2, x1, -1
    li   x3, 0x7fffffff
    bne  x2, x3, fail

# 12. Bypass test
    li   x1, 13
    addiw x2, x1, 11
    addiw x4, x2, 0
    li   x3, 24
    bne  x4, x3, fail

# 13. Dependency chain
    li   x1, 1
    addiw x2, x1, 2
    addiw x3, x2, 2
    addiw x4, x3, 1
    li   x5, 6
    bne  x4, x5, fail

# 14. Mix of positive and negative large imm
    li   x1, 0x7ffffff0
    addiw x2, x1, 0x10
    li   x3, 0x80000000
    bne  x2, x3, fail

# 15. Back-to-back dependency
    li   x1, -1
    addiw x2, x1, -2
    addiw x3, x2, 1
    addiw x4, x3, 0
    li   x5, -2
    bne  x4, x5, fail

# 16. Large positive wrap
    li   x1, 0x7fffffff
    addiw x2, x1, 0x7ff
    li   x3, 0xfffffff800000000
    bne  x2, x3, fail

# 17. Large negative wrap
    li   x1, -0x80000000
    addiw x2, x1, -0x7ff
    li   x3, 0x800007ff
    bne  x2, x3, fail

# 18. Back-to-back dependency chain
    li   x1, 1
    addiw x2, x1, 2
    addiw x3, x2, -1
    addiw x4, x3, 0
    li   x5, 2
    bne  x4, x5, fail

# 19. Zero + negative immediate
    addiw x2, x0, -15
    li   x3, -15
    bne  x2, x3, fail

# 20. Src = dest multiple times
    li   x1, 5
    addiw x1, x1, 10
    addiw x1, x1, -3
    li   x3, 12
    bne  x1, x3, fail

# 21. Max negative + positive
    li   x1, -0x80000000
    addiw x2, x1, 0x7fffffff
    li   x3, -1
    bne  x2, x3, fail

# 22. Min positive + negative
    li   x1, 0x00000001
    addiw x2, x1, -0x2
    li   x3, -1
    bne  x2, x3, fail

# 23. Edge immediate positive
    li   x1, 0x12345678
    addiw x2, x1, 0x7ff
    li   x3, 0x12345d77
    bne  x2, x3, fail

# 24. Edge immediate negative
    li   x1, 0x12345678
    addiw x2, x1, -0x800
    li   x3, 0x12344e78
    bne  x2, x3, fail

# 25. Chain with zero result
    li   x1, 1
    addiw x2, x1, -1
    addiw x3, x2, 0
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
