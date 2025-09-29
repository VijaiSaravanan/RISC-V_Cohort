# See LICENSE for license details.

#*****************************************************************************
# ld_st.S
#-----------------------------------------------------------------------------
#
# Test load and store instructions with numbered test cases
#

#include "riscv_test.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

#-------------------------------------------------------------
# Test 2: sb + lb signed byte
#-------------------------------------------------------------
li   TESTNUM, 2
li   x5, -35          # 0xffffffffffffffdd
la   x1, tdat
sb   x5, 0(x1)
lb   x2, 0(x1)
li   x3, -35
bne  x2, x3, fail

#-------------------------------------------------------------
# Test 3: sb + lb signed byte
#-------------------------------------------------------------
li   TESTNUM, 3
li   x5, -51
sb   x5, 1(x1)
lb   x2, 1(x1)
li   x3, -51
bne  x2, x3, fail

#-------------------------------------------------------------
# Test 4: sb + lb signed byte
#-------------------------------------------------------------
li   TESTNUM, 4
li   x5, -52
sb   x5, 2(x1)
lb   x2, 2(x1)
li   x3, -52
bne  x2, x3, fail

#-------------------------------------------------------------
# Test 5: sb + lb signed byte
#-------------------------------------------------------------
li   TESTNUM, 5
li   x5, -68
sb   x5, 3(x1)
lb   x2, 3(x1)
li   x3, -68
bne  x2, x3, fail

#-------------------------------------------------------------
# Test 6: sb + lb signed byte
#-------------------------------------------------------------
li   TESTNUM, 6
li   x5, -69
sb   x5, 4(x1)
lb   x2, 4(x1)
li   x3, -69
bne  x2, x3, fail

#-------------------------------------------------------------
# Test 7: sb + lb signed byte
#-------------------------------------------------------------
li   TESTNUM, 7
li   x5, -85
sb   x5, 5(x1)
lb   x2, 5(x1)
li   x3, -85
bne  x2, x3, fail

#-------------------------------------------------------------
# Test 8: sb + lb signed byte (positive)
#-------------------------------------------------------------
li   TESTNUM, 8
li   x5, 0x33
sb   x5, 0(x1)
lb   x2, 0(x1)
li   x3, 0x33
bne  x2, x3, fail

#-------------------------------------------------------------
# Test 9: sb + lb signed byte (positive)
#-------------------------------------------------------------
li   TESTNUM, 9
li   x5, 0x23
sb   x5, 1(x1)
lb   x2, 1(x1)
li   x3, 0x23
bne  x2, x3, fail

#-------------------------------------------------------------
# Test 10: sb + lb signed byte
#-------------------------------------------------------------
li   TESTNUM, 10
li   x5, 0x22
sb   x5, 2(x1)
lb   x2, 2(x1)
li   x3, 0x22
bne  x2, x3, fail

#-------------------------------------------------------------
# Test 11: sb + lb signed byte
#-------------------------------------------------------------
li   TESTNUM, 11
li   x5, 0x12
sb   x5, 3(x1)
lb   x2, 3(x1)
li   x3, 0x12
bne  x2, x3, fail

#-------------------------------------------------------------
# Test 12: sb + lb signed byte
#-------------------------------------------------------------
li   TESTNUM, 12
li   x5, 0x11
sb   x5, 4(x1)
lb   x2, 4(x1)
li   x3, 0x11
bne  x2, x3, fail

#-------------------------------------------------------------
# Test 13: sb + lb signed byte
#-------------------------------------------------------------
li   TESTNUM, 13
li   x5, 0x01
sb   x5, 5(x1)
lb   x2, 5(x1)
li   x3, 0x01
bne  x2, x3, fail

#-------------------------------------------------------------
# Test 14-19: sb + lbu unsigned byte
#-------------------------------------------------------------
li   TESTNUM, 14
li   x5, 0x33
sb   x5, 0(x1)
lbu  x2, 0(x1)
li   x3, 0x33
bne  x2, x3, fail

li   TESTNUM, 15
li   x5, 0x23
sb   x5, 1(x1)
lbu  x2, 1(x1)
li   x3, 0x23
bne  x2, x3, fail

li   TESTNUM, 16
li   x5, 0x22
sb   x5, 2(x1)
lbu  x2, 2(x1)
li   x3, 0x22
bne  x2, x3, fail

li   TESTNUM, 17
li   x5, 0x12
sb   x5, 3(x1)
lbu  x2, 3(x1)
li   x3, 0x12
bne  x2, x3, fail

li   TESTNUM, 18
li   x5, 0x11
sb   x5, 4(x1)
lbu  x2, 4(x1)
li   x3, 0x11
bne  x2, x3, fail

li   TESTNUM, 19
li   x5, 0x01
sb   x5, 5(x1)
lbu  x2, 5(x1)
li   x3, 0x01
bne  x2, x3, fail

#-------------------------------------------------------------
# Further tests for sw/lw, sh/lh, sd/ld (RV64) omitted for brevity
# Use the same pattern: load immediate, store, load back, verify
#-------------------------------------------------------------

pass:
li a0, 1
ecall

fail:
li a0, 0
ecall

RVTEST_CODE_END

.data
RVTEST_DATA_BEGIN

tdat:
    .rept 64
    .word 0xdeadbeef
    .endr

RVTEST_DATA_END
