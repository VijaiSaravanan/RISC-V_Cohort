# See LICENSE for license details.

#*****************************************************************************
# lw.S
#-----------------------------------------------------------------------------
#
# Test LW instruction with edge cases
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Basic tests
  #-------------------------------------------------------------

  # Test 2: LW from base address offset 0
  li   TESTNUM, 2
  la   x1, tdat
  lw   x5, 0(x1)
  li   x2, 0x0000000000ff00ff
  bne  x5, x2, fail

  # Test 3: LW from base + 4
  li   TESTNUM, 3
  lw   x5, 4(x1)
  li   x2, 0xffffffffff00ff00
  bne  x5, x2, fail

  # Test 4: LW from base + 8
  li   TESTNUM, 4
  lw   x5, 8(x1)
  li   x2, 0x000000000ff00ff0
  bne  x5, x2, fail

  # Test 5: LW from base + 12
  li   TESTNUM, 5
  lw   x5, 12(x1)
  li   x2, 0xfffffffff00ff00f
  bne  x5, x2, fail

  #-------------------------------------------------------------
  # Test with negative offset
  #-------------------------------------------------------------

  li   TESTNUM, 6
  lw   x5, -12(x1)
  li   x2, 0x0000000000ff00ff
  bne  x5, x2, fail

  li   TESTNUM, 7
  lw   x5, -8(x1)
  li   x2, 0xffffffffff00ff00
  bne  x5, x2, fail

  li   TESTNUM, 8
  lw   x5, -4(x1)
  li   x2, 0x000000000ff00ff0
  bne  x5, x2, fail

  li   TESTNUM, 9
  lw   x5, 0(x1)
  li   x2, 0xfffffffff00ff00f
  bne  x5, x2, fail

  #-------------------------------------------------------------
  # Test with negative base
  #-------------------------------------------------------------

  li   TESTNUM, 10
  addi x1, x1, -32
  lw   x5, 32(x1)
  li   x2, 0x0000000000ff00ff
  bne  x5, x2, fail

  #-------------------------------------------------------------
  # Test with unaligned base
  #-------------------------------------------------------------

  li   TESTNUM, 11
  addi x1, x1, -3
  lw   x5, 7(x1)
  li   x2, 0xffffffffff00ff00
  bne  x5, x2, fail

  #-------------------------------------------------------------
  # Bypassing tests
  #-------------------------------------------------------------

  li   TESTNUM, 12
  lw   x5, 4(x1)
  li   x2, 0x000000000ff00ff0
  bne  x5, x2, fail

  li   TESTNUM, 13
  lw   x5, 4(x1)
  li   x2, 0xfffffffff00ff00f
  bne  x5, x2, fail

  li   TESTNUM, 14
  lw   x5, 4(x1)
  li   x2, 0xffffffffff00ff00
  bne  x5, x2, fail

  #-------------------------------------------------------------
  # Test write-after-write hazard
  #-------------------------------------------------------------

  li   TESTNUM, 15
  lw   x2, 0(x1)
  li   x2, 2
  li   TESTNUM, 16
  lw   x2, 0(x1)
  nop
  li   x2, 2

  #-------------------------------------------------------------
  # Edge Cases
  #-------------------------------------------------------------

  # Test 17: LW from last word in memory (simulate end of data)
  li   TESTNUM, 17
  la   x1, tdat
  lw   x5, 20(x1)
  li   x2, 0xdeadbeef   # Expecting known pattern
  bne  x5, x2, fail

  # Test 18: LW with misaligned address
  li   TESTNUM, 18
  addi x1, x1, 1
  lw   x5, 0(x1)
  # This may raise misaligned load exception in some RV32/64 implementations

  TEST_PASSFAIL

RVTEST_CODE_END

.data
RVTEST_DATA_BEGIN

TEST_DATA

tdat:
tdat1:  .word 0x00ff00ff
tdat2:  .word 0xff00ff00
tdat3:  .word 0x0ff00ff0
tdat4:  .word 0xf00ff00f
tdat5:  .word 0xdeadbeef      # Edge case pattern

RVTEST_DATA_END
