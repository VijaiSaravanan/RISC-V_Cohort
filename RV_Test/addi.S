# See LICENSE for license details.

#*****************************************************************************
# addi.S
#-----------------------------------------------------------------------------
#
# Test addi instruction.
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

# 1. Basic addi small numbers
    li   x1, 1
    addi x2, x1, 2        # 1 + 2 = 3
    li   x3, 3
    bne  x2, x3, fail

# 2. addi with zero + immediate
    li   x1, 0
    addi x2, x1, 0        # 0 + 0 = 0
    li   x3, 0
    bne  x2, x3, fail

# 3. Positive + positive immediate
    li   x1, 10
    addi x2, x1, 20       # 10 + 20 = 30
    li   x3, 30
    bne  x2, x3, fail

# 4. Positive + negative immediate
    li   x1, 15
    addi x2, x1, -5       # 15 + (-5) = 10
    li   x3, 10
    bne  x2, x3, fail

# 5. Negative base + negative imm
    li   x1, -8
    addi x2, x1, -12      # -8 + (-12) = -20
    li   x3, -20
    bne  x2, x3, fail

# 6. Src1 = dest
    li   x1, 13
    addi x1, x1, 11       # 13 + 11 = 24
    li   x3, 24
    bne  x1, x3, fail

# 7. Immediate zero
    li   x1, 99
    addi x2, x1, 0        # 99 + 0 = 99
    li   x3, 99
    bne  x2, x3, fail

# 8. Zero register as src1
    addi x2, x0, 25       # 0 + 25 = 25
    li   x3, 25
    bne  x2, x3, fail

# 9. Zero register as dest
    li   x1, 15
    addi x0, x1, 10       # discard result
    li   x3, 0
    bne  x0, x3, fail     # must remain 0

# 10. Large positive boundary
    li   x1, 0x7fffffff
    addi x2, x1, 1        # 2147483647 + 1 = 2147483648
    li   x3, 0x80000000
    bne  x2, x3, fail

# 11. Large negative boundary
    li   x1, -0x80000000
    addi x2, x1, -1       # -2147483648 + (-1) = -2147483649
    li   x3, -2147483649
    bne  x2, x3, fail

# 12. Bypass test
    li   x1, 13
    addi x2, x1, 11       # 24
    addi x4, x2, 0        # use immediately
    li   x3, 24
    bne  x4, x3, fail

# 13. Dependency chain
    li   x1, 1
    addi x2, x1, 2        # 3
    addi x3, x2, 2        # 5
    addi x4, x3, 1        # 6
    li   x5, 6
    bne  x4, x5, fail

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
