# See LICENSE for license details.

#*****************************************************************************
# lbu.S
#-----------------------------------------------------------------------------
#
# Test lbu instruction with numbered test cases in assembly
#

#include "riscv_test.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

#-------------------------------------------------------------
# Test 2: Load unsigned byte 0xff from tdat[0]
#-------------------------------------------------------------
li   TESTNUM, 2
la   x2, tdat
lbu  x3, 0(x2)
li   x4, 0xff
bne  x3, x4, fail

#-------------------------------------------------------------
# Test 3: Load 0 from tdat[1]
#-------------------------------------------------------------
li   TESTNUM, 3
lbu  x3, 1(x2)
li   x4, 0
bne  x3, x4, fail

#-------------------------------------------------------------
# Test 4: Load 0xf0 from tdat[2]
#-------------------------------------------------------------
li   TESTNUM, 4
lbu  x3, 2(x2)
li   x4, 0xf0
bne  x3, x4, fail

#-------------------------------------------------------------
# Test 5: Load 0x0f from tdat[3]
#-------------------------------------------------------------
li   TESTNUM, 5
lbu  x3, 3(x2)
li   x4, 0x0f
bne  x3, x4, fail

#-------------------------------------------------------------
# Test 6: Negative offset - Load 0xff from tdat4[-3]
#-------------------------------------------------------------
li   TESTNUM, 6
la   x2, tdat4
lbu  x3, -3(x2)
li   x4, 0xff
bne  x3, x4, fail

#-------------------------------------------------------------
# Test 7: Negative offset - Load 0 from tdat4[-2]
#-------------------------------------------------------------
li   TESTNUM, 7
lbu  x3, -2(x2)
li   x4, 0x00
bne  x3, x4, fail

#-------------------------------------------------------------
# Test 8: Negative offset - Load 0xf0 from tdat4[-1]
#-------------------------------------------------------------
li   TESTNUM, 8
lbu  x3, -1(x2)
li   x4, 0xf0
bne  x3, x4, fail

#-------------------------------------------------------------
# Test 9: Negative offset - Load 0x0f from tdat4[0]
#-------------------------------------------------------------
li   TESTNUM, 9
lbu  x3, 0(x2)
li   x4, 0x0f
bne  x3, x4, fail

#-------------------------------------------------------------
# Test 10: Negative base - Load 0xff
#-------------------------------------------------------------
li   TESTNUM, 10
la   x1, tdat
addi x1, x1, -32
lbu  x5, 32(x1)
li   x6, 0xff
bne  x5, x6, fail

#-------------------------------------------------------------
# Test 11: Unaligned base - Load 0
#-------------------------------------------------------------
li   TESTNUM, 11
la   x1, tdat
addi x1, x1, -6
lbu  x5, 7(x1)
li   x6, 0
bne  x5, x6, fail

#-------------------------------------------------------------
# Test 12: Dest bypass test - Load 0xf0 from tdat2[1]
#-------------------------------------------------------------
li   TESTNUM, 12
la   x1, tdat2
lbu  x3, 1(x1)
li   x4, 0xf0
bne  x3, x4, fail

#-------------------------------------------------------------
# Test 13: Dest bypass test - Load 0x0f from tdat3[1]
#-------------------------------------------------------------
li   TESTNUM, 13
la   x1, tdat3
lbu  x3, 1(x1)
li   x4, 0x0f
bne  x3, x4, fail

#-------------------------------------------------------------
# Test 14: Dest bypass test - Load 0 from tdat1[1]
#-------------------------------------------------------------
li   TESTNUM, 14
la   x1, tdat1
lbu  x3, 1(x1)
li   x4, 0x00
bne  x3, x4, fail

#-------------------------------------------------------------
# Test 15: Src1 bypass test - Load 0xf0 from tdat2[1]
#-------------------------------------------------------------
li   TESTNUM, 15
la   x1, tdat2
lbu  x3, 1(x1)
li   x4, 0xf0
bne  x3, x4, fail

#-------------------------------------------------------------
# Test 16: Src1 bypass test - Load 0x0f from tdat3[1]
#-------------------------------------------------------------
li   TESTNUM, 16
la   x1, tdat3
lbu  x3, 1(x1)
li   x4, 0x0f
bne  x3, x4, fail

#-------------------------------------------------------------
# Test 17: Src1 bypass test - Load 0 from tdat1[1]
#-------------------------------------------------------------
li   TESTNUM, 17
la   x1, tdat1
lbu  x3, 1(x1)
li   x4, 0x00
bne  x3, x4, fail

#-------------------------------------------------------------
# Test 18: Write-after-write hazard
#-------------------------------------------------------------
li   TESTNUM, 18
la   x5, tdat
lbu  x2, 0(x5)
li   x2, 2

#-------------------------------------------------------------
# Test 19: Write-after-write hazard with nop
#-------------------------------------------------------------
li   TESTNUM, 19
la   x5, tdat
lbu  x2, 0(x5)
nop
li   x2, 2

#-------------------------------------------------------------
# End of tests
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

tdat:   .byte 0xff, 0x00, 0xf0, 0x0f
tdat1:  .byte 0xff
tdat2:  .byte 0x00
tdat3:  .byte 0xf0
tdat4:  .byte 0x0f

RVTEST_DATA_END
