# See LICENSE for license details.

#*****************************************************************************
# lh.S
#-----------------------------------------------------------------------------
#
# Test lh instruction with explicit numbered test cases
#

#include "riscv_test.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

#-------------------------------------------------------------
# Test 2: Basic load 1
#-------------------------------------------------------------
li   TESTNUM, 2
la   x1, tdat
lh   x5, 0(x1)
li   x2, 0x00000000000000ff
bne  x5, x2, fail

#-------------------------------------------------------------
# Test 3: Basic load 2
#-------------------------------------------------------------
li   TESTNUM, 3
lh   x5, 2(x1)
li   x2, 0xffffffffffffff00
bne  x5, x2, fail

#-------------------------------------------------------------
# Test 4: Basic load 3
#-------------------------------------------------------------
li   TESTNUM, 4
lh   x5, 4(x1)
li   x2, 0x0000000000000ff0
bne  x5, x2, fail

#-------------------------------------------------------------
# Test 5: Basic load 4
#-------------------------------------------------------------
li   TESTNUM, 5
lh   x5, 6(x1)
li   x2, 0xfffffffffffff00f
bne  x5, x2, fail

#-------------------------------------------------------------
# Test 6: Load with negative offset
#-------------------------------------------------------------
li   TESTNUM, 6
la   x1, tdat4
lh   x5, -6(x1)
li   x2, 0x00000000000000ff
bne  x5, x2, fail

#-------------------------------------------------------------
# Test 7: Load with negative offset
#-------------------------------------------------------------
li   TESTNUM, 7
lh   x5, -4(x1)
li   x2, 0xffffffffffffff00
bne  x5, x2, fail

#-------------------------------------------------------------
# Test 8: Load with negative offset
#-------------------------------------------------------------
li   TESTNUM, 8
lh   x5, -2(x1)
li   x2, 0x0000000000000ff0
bne  x5, x2, fail

#-------------------------------------------------------------
# Test 9: Load with negative offset
#-------------------------------------------------------------
li   TESTNUM, 9
lh   x5, 0(x1)
li   x2, 0xfffffffffffff00f
bne  x5, x2, fail

#-------------------------------------------------------------
# Test 10: Load with negative base
#-------------------------------------------------------------
li   TESTNUM, 10
la   x1, tdat
addi x1, x1, -32
lh   x5, 32(x1)
li   x2, 0x00000000000000ff
bne  x5, x2, fail

#-------------------------------------------------------------
# Test 11: Load with unaligned base
#-------------------------------------------------------------
li   TESTNUM, 11
la   x1, tdat
addi x1, x1, -5
lh   x5, 7(x1)
li   x2, 0xffffffffffffff00
bne  x5, x2, fail

#-------------------------------------------------------------
# Test 12-17: Destination/Src1 bypassing
#-------------------------------------------------------------
li   TESTNUM, 12
la   x1, tdat2
lh   x5, 2(x1)
li   x2, 0x0000000000000ff0
bne  x5, x2, fail

li   TESTNUM, 13
la   x1, tdat3
lh   x5, 2(x1)
li   x2, 0xfffffffffffff00f
bne  x5, x2, fail

li   TESTNUM, 14
la   x1, tdat1
lh   x5, 2(x1)
li   x2, 0xffffffffffffff00
bne  x5, x2, fail

li   TESTNUM, 15
la   x1, tdat2
lh   x5, 2(x1)
li   x2, 0x0000000000000ff0
bne  x5, x2, fail

li   TESTNUM, 16
la   x1, tdat3
lh   x5, 2(x1)
li   x2, 0xfffffffffffff00f
bne  x5, x2, fail

li   TESTNUM, 17
la   x1, tdat1
lh   x5, 2(x1)
li   x2, 0xffffffffffffff00
bne  x5, x2, fail

#-------------------------------------------------------------
# Test 18: Write-after-write hazard
#-------------------------------------------------------------
li   TESTNUM, 18
la   x1, tdat
lh   x2, 0(x1)
li   x2, 2
li   x3, 2
bne  x2, x3, fail

#-------------------------------------------------------------
# Test 19: Write-after-write hazard with nop
#-------------------------------------------------------------
li   TESTNUM, 19
la   x1, tdat
lh   x2, 0(x1)
nop
li   x2, 2
li   x3, 2
bne  x2, x3, fail

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
tdat1:  .half 0x00ff
tdat2:  .half 0xff00
tdat3:  .half 0x0ff0
tdat4:  .half 0xf00f

RVTEST_DATA_END
