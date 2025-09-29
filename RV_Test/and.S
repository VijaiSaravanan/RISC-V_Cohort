# See LICENSE for license details.

#*****************************************************************************
# and.S
#-----------------------------------------------------------------------------
#
# Test and instruction (bitwise AND)
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

# 1. Basic AND
    li   x1, 0x0f0f0f0f
    li   x2, 0xff00ff00
    and  x3, x1, x2
    li   x4, 0x0f000f00
    bne  x3, x4, fail

# 2. AND different pattern
    li   x1, 0x0ff00ff0
    li   x2, 0xf0f0f0f0
    and  x3, x1, x2
    li   x4, 0x00f000f0
    bne  x3, x4, fail

# 3. AND alternating bits
    li   x1, 0x00ff00ff
    li   x2, 0x0f0f0f0f
    and  x3, x1, x2
    li   x4, 0x000f000f
    bne  x3, x4, fail

# 4. AND edge pattern
    li   x1, 0xf00ff00f
    li   x2, 0xf0f0f0f0
    and  x3, x1, x2
    li   x4, 0xf000f000
    bne  x3, x4, fail

# 5. Src1 = dest
    li   x1, 0xff00ff00
    li   x2, 0x0f0f0f0f
    and  x1, x1, x2
    li   x3, 0x0f000f00
    bne  x1, x3, fail

# 6. Src2 = dest
    li   x1, 0x0ff00ff0
    li   x2, 0xf0f0f0f0
    and  x2, x1, x2
    li   x3, 0x00f000f0
    bne  x2, x3, fail

# 7. Src1 = Src2 = dest
    li   x1, 0xff00ff00
    and  x1, x1, x1
    li   x2, 0xff00ff00
    bne  x1, x2, fail

# 8. AND with zero src1
    li   x2, 0xff00ff00
    and  x3, x0, x2
    li   x4, 0
    bne  x3, x4, fail

# 9. AND with zero src2
    li   x1, 0x00ff00ff
    and  x3, x1, x0
    li   x4, 0
    bne  x3, x4, fail

# 10. AND with zero dest
    li   x1, 0x12345678
    li   x2, 0x87654321
    and  x0, x1, x2
    li   x3, 0
    bne  x0, x3, fail

# 11. All ones AND
    li   x1, -1
    li   x2, 0x0f0f0f0f
    and  x3, x1, x2
    li   x4, 0x0f0f0f0f
    bne  x3, x4, fail

# 12. All zeros AND
    li   x1, 0
    li   x2, 0xffffffff
    and  x3, x1, x2
    li   x4, 0
    bne  x3, x4, fail

# 13. Complement pattern
    li   x1, 0xaaaaaaaa
    li   x2, 0x55555555
    and  x3, x1, x2
    li   x4, 0
    bne  x3, x4, fail

# 14. Bypass test
    li   x1, 0x0f0f0f0f
    li   x2, 0xff00ff00
    and  x3, x1, x2
    and  x4, x3, x0
    li   x5, 0x0f000f00
    bne  x4, x5, fail

# 15. Dependency chain
    li   x1, 0xff00ff00
    li   x2, 0x0f0f0f0f
    and  x3, x1, x2
    and  x4, x3, x2
    and  x5, x4, x1
    li   x6, 0x0f000f00
    bne  x5, x6, fail

# 16. Edge pattern
    li   x1, 0x12345678
    li   x2, 0x87654321
    and  x3, x1, x2
    li   x4, 0x02244220
    bne  x3, x4, fail

# 17. Src1 = zero, src2 = zero
    and  x3, x0, x0
    li   x4, 0
    bne  x3, x4, fail

# 18. Src1 = dest multiple times
    li   x1, 0x0f0f0f0f
    and  x1, x1, 0xff00ff00
    and  x1, x1, 0x0ff00ff0
    li   x2, 0x0f000f00
    bne  x1, x2, fail

# 19. Src2 = dest multiple times
    li   x1, 0x0f0f0f0f
    li   x2, 0xff00ff00
    and  x2, x1, x2
    and  x2, x1, x2
    li   x3, 0x0f000f00
    bne  x2, x3, fail

# 20. Zero + pattern
    and  x2, x0, 0x12345678
    li   x3, 0
    bne  x2, x3, fail

# 21. Src1 = all ones
    li   x1, -1
    li   x2, 0x87654321
    and  x3, x1, x2
    li   x4, 0x87654321
    bne  x3, x4, fail

# 22. Src2 = all ones
    li   x1, 0x12345678
    li   x2, -1
    and  x3, x1, x2
    li   x4, 0x12345678
    bne  x3, x4, fail

# 23. Src1 = Src2 edge
    li   x1, 0x55555555
    li   x2, 0x55555555
    and  x3, x1, x2
    li   x4, 0x55555555
    bne  x3, x4, fail

# 24. Edge pattern 2
    li   x1, 0xabcdef12
    li   x2, 0x12345678
    and  x3, x1, x2
    li   x4, 0x02245612
    bne  x3, x4, fail

# 25. Chain with zero result
    li   x1, 0xff00ff00
    li   x2, 0x00ff00ff
    and  x3, x1, x2
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
