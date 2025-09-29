# See LICENSE for license details.

#*****************************************************************************
# fence_i_edge.S
#-----------------------------------------------------------------------------
#
# Test fence.i instruction and self-modifying code with edge cases
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

# 1. Simple I-cache flush
li a3, 111
lh a0, insn
lh a1, insn+2
sh a0, mod1, t0
sh a1, mod1+2, t0
fence.i
la t1, mod1
jalr t1
li a5, 444
bne a3, a5, fail

# 2. Prefetcher hit
li a4, 100
1: addi a4, a4, -1
   bnez a4, 1b
lh a0, insn
lh a1, insn+2
sh a0, mod2, t0
sh a1, mod2+2, t0
fence.i
la t1, mod2
jalr t1
li a5, 777
bne a3, a5, fail

# 3. Consecutive modifications
lh a0, insn
lh a1, insn+2
sh a0, mod3, t0
sh a1, mod3+2, t0
lh a0, insn
lh a1, insn+2
sh a0, mod4, t0
sh a1, mod4+2, t0
fence.i
la t1, mod3
jalr t1
la t1, mod4
jalr t1
li a5, 1234
bne a3, a5, fail

# 4. Branch target modified
lh a0, insn
lh a1, insn+2
sh a0, mod_branch, t0
sh a1, mod_branch+2, t0
fence.i
jal mod_branch
li a5, 888
bne a3, a5, fail

# 5. Large alignment offsets
.align 6
lh a0, insn
lh a1, insn+2
sh a0, mod_align, t0
sh a1, mod_align+2, t0
fence.i
la t1, mod_align
jalr t1
li a5, 999
bne a3, a5, fail

# 6. Zero-length modification
lh a0, insn
lh a1, insn+2
sh a0, mod_same, t0
sh a1, mod_same+2, t0
fence.i
la t1, mod_same
jalr t1
li a5, 333
bne a3, a5, fail

# 7. Immediate extreme positive
lh a0, insn
lh a1, insn+2
sh a0, mod_imm_pos, t0
sh a1, mod_imm_pos+2, t0
fence.i
la t1, mod_imm_pos
jalr t1
li a5, 0x7fff
bne a3, a5, fail

# 8. Immediate extreme negative
lh a0, insn
lh a1, insn+2
sh a0, mod_imm_neg, t0
sh a1, mod_imm_neg+2, t0
fence.i
la t1, mod_imm_neg
jalr t1
li a5, -0x8000
bne a3, a5, fail

# 9. Jump into modified instruction
lh a0, insn
lh a1, insn+2
sh a0, mod_jmp, t0
sh a1, mod_jmp+2, t0
fence.i
jal mod_jmp
li a5, 555
bne a3, a5, fail

# 10. Back-to-back dependent modifications
lh a0, insn
lh a1, insn+2
sh a0, mod_dep1, t0
sh a1, mod_dep1+2, t0
lh a0, insn
lh a1, insn+2
sh a0, mod_dep2, t0
sh a1, mod_dep2+2, t0
fence.i
la t1, mod_dep1
jalr t1
la t1, mod_dep2
jalr t1
li a5, 2000
bne a3, a5, fail

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

insn:
  addi a3, a3, 333

2: addi a3, a3, 222
jalr a5, t1, 0

3: addi a3, a3, 555
jalr a5, t1, 0

RVTEST_DATA_END
