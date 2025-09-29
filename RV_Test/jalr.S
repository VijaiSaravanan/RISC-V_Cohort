# See LICENSE for license details.

#*****************************************************************************
# jalr_edge.S
#-----------------------------------------------------------------------------
#
# Test JALR (jump and link register) instruction with numbered test cases
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

# 1. Basic JALR
li t0, 0
la t1, target_1
jalr t0, t1, 0
link_1:
nop
nop
la t2, link_1
bne t0, t2, fail

# 2. JALR rs = rd (link register same as target)
li t0, 0
la t1, target_2
jalr t0, t0, 0
link_2:
nop
nop
la t2, link_2
bne t0, t2, fail

# 3. Delay slot not executed
li t0, 1
la t1, ds_not_exec
jr t1
addi t0, t0, 1
addi t0, t0, 1
ds_not_exec:
addi t0, t0, 1
li x5, 4
bne t0, x5, fail

# 4. Forward jump
li t0, 0
la t1, fwd_jump
jalr t0, t1, 0
nop
fwd_jump:
li x5, 10
bne t0, t1, fail

# 5. Backward jump
li t0, 0
backward:
addi t0, t0, 1
jalr x0, backward, 0
# Should not loop infinitely
li x5, 1
bne t0, x5, fail

# 6. JALR with large positive offset
li t0, 0
la t1, large_pos
jalr t0, t1, 4096
nop
large_pos:
li x5, 0x7fff
bne t0, t1, fail

# 7. JALR with large negative offset
li t0, 0
la t1, large_neg
jalr t0, t1, -4096
nop
large_neg:
li x5, -0x8000
bne t0, t1, fail

# 8. Back-to-back JALR
li t0, 0
la t1, bb1
jalr t0, t1, 0
bb1:
jalr t0, bb2, 0
bb2:
li x5, 222
bne t0, t1, fail

# 9. JALR to same instruction (self-loop)
li t0, 0
jalr x0, self_jump, 0
self_jump:
li x5, 1
bne t0, x0, fail

# 10. Edge case: JALR x0, zero offset
li t0, 0
jalr x0, t0, 0
li x5, 0
bne t0, x5, fail

# 11. Bypassing test: src1 -> rd in 0 cycles
TEST_JALR_SRC1_BYPASS(11, 0, jalr)

# 12. Bypassing test: src1 -> rd in 1 cycle
TEST_JALR_SRC1_BYPASS(12, 1, jalr)

# 13. Bypassing test: src1 -> rd in 2 cycles
TEST_JALR_SRC1_BYPASS(13, 2, jalr)

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
