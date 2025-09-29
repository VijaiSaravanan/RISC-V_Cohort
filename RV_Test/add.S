# See LICENSE for license details.

#*****************************************************************************
# add.S
#-----------------------------------------------------------------------------
#
# Test add instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  # 1. Basic add small numbers
    li   x1, 1
    li   x2, 2
    add  x3, x1, x2       # 1 + 2 = 3
    li   x4, 3
    bne  x3, x4, fail

# 2. Add zero + zero
    li   x1, 0
    li   x2, 0
    add  x3, x1, x2       # 0 + 0 = 0
    li   x4, 0
    bne  x3, x4, fail

# 3. Add positive + positive
    li   x1, 10
    li   x2, 20
    add  x3, x1, x2       # 10 + 20 = 30
    li   x4, 30
    bne  x3, x4, fail

# 4. Add positive + negative
    li   x1, 15
    li   x2, -5
    add  x3, x1, x2       # 15 + (-5) = 10
    li   x4, 10
    bne  x3, x4, fail

# 5. Add negative + negative
    li   x1, -8
    li   x2, -12
    add  x3, x1, x2       # -20
    li   x4, -20
    bne  x3, x4, fail

# 6. Add with src1 = dest
    li   x1, 13
    li   x2, 11
    add  x1, x1, x2       # x1 = 24
    li   x4, 24
    bne  x1, x4, fail

# 7. Add with src2 = dest
    li   x1, 14
    li   x2, 11
    add  x2, x1, x2       # x2 = 25
    li   x4, 25
    bne  x2, x4, fail

# 8. Add with both src1 and src2 same
    li   x1, 7
    add  x1, x1, x1       # 7 + 7 = 14
    li   x4, 14
    bne  x1, x4, fail

# 9. Add zero register as src1
    li   x2, 15
    add  x3, x0, x2       # 0 + 15 = 15
    li   x4, 15
    bne  x3, x4, fail

# 10. Add zero register as src2
    li   x1, 32
    add  x3, x1, x0       # 32 + 0 = 32
    li   x4, 32
    bne  x3, x4, fail

# 11. Add with zero register as dest
    li   x1, 10
    li   x2, 20
    add  x0, x1, x2       # discard result
    li   x4, 0
    bne  x0, x4, fail     # must remain 0

# 12. Large positive values (no overflow in 64-bit)
    li   x1, 0x7fffffff
    li   x2, 1
    add  x3, x1, x2       # 2147483647 + 1 = 2147483648
    li   x4, 0x80000000
    bne  x3, x4, fail

# 13. Large negative values
    li   x1, -0x80000000
    li   x2, -1
    add  x3, x1, x2
    li   x4, -2147483649
    bne  x3, x4, fail

# 14. Bypass test (dest used immediately)
    li   x1, 13
    li   x2, 11
    add  x3, x1, x2       # x3 = 24
    add  x5, x3, x0       # use x3 immediately
    li   x4, 24
    bne  x5, x4, fail

# 15. Back-to-back dependency chain
    li   x1, 1
    li   x2, 2
    add  x3, x1, x2       # 3
    add  x4, x3, x2       # 5
    add  x5, x4, x1       # 6
    li   x6, 6
    bne  x5, x6, fail

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
