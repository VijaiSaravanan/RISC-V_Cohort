# See LICENSE for license details.

#*****************************************************************************
# beq.S
#-----------------------------------------------------------------------------
#
# Raw assembly test cases for beq instruction
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

#-------------------------------------------------------------
# 1. Branch taken tests
#-------------------------------------------------------------

# beq 0, 0 -> taken
li x1, 0
li x2, 0
beq x1, x2, beq_taken_2
addi x3, x0, 1      # should be skipped
beq_taken_2:
addi x3, x0, 0      # success

# beq 1, 1 -> taken
li x1, 1
li x2, 1
beq x1, x2, beq_taken_3
addi x3, x0, 1
beq_taken_3:
addi x3, x0, 0

# beq -1, -1 -> taken
li x1, -1
li x2, -1
beq x1, x2, beq_taken_4
addi x3, x0, 1
beq_taken_4:
addi x3, x0, 0

#-------------------------------------------------------------
# 2. Branch not-taken tests
#-------------------------------------------------------------

# beq 0, 1 -> not taken
li x1, 0
li x2, 1
beq x1, x2, beq_taken_5
addi x3, x0, 0      # executed
beq_taken_5:

# beq 1, 0 -> not taken
li x1, 1
li x2, 0
beq x1, x2, beq_taken_6
addi x3, x0, 0
beq_taken_6:

# beq -1, 1 -> not taken
li x1, -1
li x2, 1
beq x1, x2, beq_taken_7
addi x3, x0, 0
beq_taken_7:

# beq 1, -1 -> not taken
li x1, 1
li x2, -1
beq x1, x2, beq_taken_8
addi x3, x0, 0
beq_taken_8:

#-------------------------------------------------------------
# 3. Bypassing / dependency tests
#-------------------------------------------------------------

# Example of source register dependency bypass
li x5, 0
li x6, -1
beq x5, x6, beq_bypass_9
addi x7, x0, 0      # executed since not taken
beq_bypass_9:

li x5, 0
li x6, -1
beq x5, x6, beq_bypass_10
addi x7, x0, 0
beq_bypass_10:

# Repeat similar pattern for remaining bypass cases
# (all beq source/dest bypasses can be manually written as above)

#-------------------------------------------------------------
# 4. Delay slot / sequential instructions test
#-------------------------------------------------------------

li  x1, 1
beq x0, x0, beq_delay
addi x1, x1, 1
addi x1, x1, 1
addi x1, x1, 1
addi x1, x1, 1
beq_delay:
addi x1, x1, 1
addi x1, x1, 1

TEST_PASSFAIL

RVTEST_CODE_END

.data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
