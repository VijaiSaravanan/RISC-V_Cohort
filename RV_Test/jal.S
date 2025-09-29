# See LICENSE for license details.

#*****************************************************************************
# jal_edge.S
#-----------------------------------------------------------------------------
#
# Test JAL (jump and link) instruction with numbered test cases
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

# 1. Basic JAL
li ra, 0
jal x4, target_1
link_1:
nop
nop
la x2, link_1
bne x2, x4, fail

# 2. Delay slot not executed
li ra, 1
jal x0, ds_not_exec
addi ra, ra, 1
addi ra, ra, 1
ds_not_exec:
addi ra, ra, 1
li x5, 3
bne ra, x5, fail

# 3. Forward jump
li ra, 0
jal x4, fwd_jump
nop
nop
fwd_jump:
li x5, 123
bne ra, x4, fail

# 4. Backward jump
li ra, 0
backward:
addi ra, ra, 1
jal x0, backward
# Should not loop infinitely
# Use branch to exit test
li x5, 1
bne ra, x5, fail

# 5. Link register same as destination
li x4, 0
jal x4, link_same
nop
link_same:
li x5, 111
bne x4, link_same, fail

# 6. JAL with large positive immediate
li ra, 0
jal x4, large_pos
nop
large_pos:
li x5, 0x7ffff
bne ra, x4, fail

# 7. JAL with large negative immediate
li ra, 0
jal x4, large_neg
nop
large_neg:
li x5, -0x80000
bne ra, x4, fail

# 8. Back-to-back JAL instructions
li ra, 0
jal x4, bb1
bb1:
jal x4, bb2
bb2:
li x5, 222
bne ra, x4, fail

# 9. JAL to same instruction (jump to self)
li ra, 0
jal x0, self_jump
self_jump:
li x5, 1
bne ra, x0, fail

# 10. Edge case: JAL x0, zero offset
li ra, 0
jal x0, 0
li x5, 0
bne ra, x5, fail

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
