# See LICENSE for license details.

#*****************************************************************************
# andi.S
#-----------------------------------------------------------------------------
#
# Test andi instruction (bitwise AND with immediate)
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

# 1. Basic ANDI
    li   x1, 0xff00ff00
    andi x3, x1, 0xf0f
    li   x4, 0x00000f00
    bne  x3, x4, fail

# 2. ANDI different pattern
    li   x1, 0x0ff00ff0
    andi x3, x1, 0x0f0
    li   x4, 0x000000f0
    bne  x3, x4, fail

# 3. ANDI alternating bits
    li   x1, 0x00ff00ff
    andi x3, x1, 0x70f
    li   x4, 0x0000000f
    bne  x3, x4, fail

# 4. ANDI edge pattern
    li   x1, 0xf00ff00f
    andi x3, x1, 0x0f0
    li   x4, 0x00000000
    bne  x3, x4, fail

# 5. Src1 = dest
    li   x1, 0xff00ff00
    andi x1, x1, 0x0f0
    li   x2, 0x00000f00
    bne  x1, x2, fail

# 6. Bypass dest = 0 cycles
    li   x1, 0x0ff00ff0
    andi x3, x1, 0x70f
    andi x4, x3, 0x0f0
    li   x5, 0x00000700
    bne  x4, x5, fail

# 7. Dependency chain
    li   x1, 0x00ff00ff
    andi x3, x1, 0x0f0
    andi x4, x3, 0x00f
    andi x5, x4, 0x0f0
    li   x6, 0x00000000
    bne  x5, x6, fail

# 8. Src1 = zero
    andi x3, x0, 0x0f0
    li   x4, 0
    bne  x3, x4, fail

# 9. Immediate = zero
    li   x1, 0x12345678
    andi x3, x1, 0
    li   x4, 0
    bne  x3, x4, fail

# 10. All ones ANDI
    li   x1, -1
    andi x3, x1, 0x0f0
    li   x4, 0x0f0
    bne  x3, x4, fail

# 11. Src1 = all ones
    li   x1, -1
    andi x3, x1, 0x70f
    li   x4, 0x70f
    bne  x3, x4, fail

# 12. Immediate = all ones (12-bit sign-extended)
    li   x1, 0x123
    andi x3, x1, 0xfff
    li   x4, 0x123
    bne  x3, x4, fail

# 13. Src1 = dest repeated
    li   x1, 0x0ff00ff0
    andi x1, x1, 0x70f
    andi x1, x1, 0x0f0
    li   x2, 0x00000700
    bne  x1, x2, fail

# 14. Bypass src1
    li   x1, 0xff00ff00
    andi x3, x1, 0xf0f
    andi x4, x1, 0x0f0
    li   x5, 0x00000f00
    bne  x4, x5, fail

# 15. Src1 = zero + immediate
    andi x3, x0, 0x123
    li   x4, 0
    bne  x3, x4, fail

# 16. Src1 = all ones + negative immediate
    li   x1, -1
    andi x3, x1, -0x7
    li   x4, 0xfffffffffffffff9
    bne  x3, x4, fail

# 17. Immediate edge pattern
    li   x1, 0xabcdef12
    andi x3, x1, 0x123
    li   x4, 0x102
    bne  x3, x4, fail

# 18. Chain with zero result
    li   x1, 0xff00ff00
    andi x3, x1, 0x00ff00ff
    li   x4, 0
    bne  x3, x4, fail

# 19. Back-to-back dependency
    li   x1, 0x12345678
    andi x3, x1, 0x0f0
    andi x4, x3, 0x00f
    andi x5, x4, 0x0f0
    li   x6, 0
    bne  x5, x6, fail

# 20. Src1 = dest multiple times
    li   x1, 0x0f0f0f0f
    andi x1, x1, 0xff0
    andi x1, x1, 0x0f0
    li   x2, 0x00000f00
    bne  x1, x2, fail

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