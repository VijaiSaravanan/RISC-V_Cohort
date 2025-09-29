# See LICENSE for license details.

#*****************************************************************************
# lui.S
#-----------------------------------------------------------------------------
#
# Test LUI instruction with edge cases
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

  #-------------------------------------------------------------
  # Basic tests
  #-------------------------------------------------------------

  # Test 2: LUI with zero immediate
  li   TESTNUM, 2
  lui  x1, 0x00000
  li   x2, 0x0000000000000000
  bne  x1, x2, fail

  # Test 3: LUI with max immediate (0xFFFFF)
  li   TESTNUM, 3
  lui  x1, 0xfffff
  sra  x1, x1, 1       # normalize for signed comparison
  li   x2, 0xfffffffffffff800
  bne  x1, x2, fail

  # Test 4: LUI with intermediate value (0x7FFFF)
  li   TESTNUM, 4
  lui  x1, 0x7ffff
  sra  x1, x1, 20
  li   x2, 0x00000000000007ff
  bne  x1, x2, fail

  # Test 5: LUI with sign-bit set (0x80000)
  li   TESTNUM, 5
  lui  x1, 0x80000
  sra  x1, x1, 20
  li   x2, 0xfffffffffffff800
  bne  x1, x2, fail

  # Test 6: LUI writing to x0 (should not modify x0)
  li   TESTNUM, 6
  lui  x0, 0x80000
  li   x2, 0
  bne  x0, x2, fail

  #-------------------------------------------------------------
  # Edge Cases
  #-------------------------------------------------------------

  # Test 7: LUI with smallest positive non-zero immediate
  li   TESTNUM, 7
  lui  x1, 0x00001
  li   x2, 0x0000000000001000
  bne  x1, x2, fail

  # Test 8: LUI combined with ADDI resulting in negative number
  li   TESTNUM, 8
  lui  x1, 0x80000
  addi x1, x1, -1
  li   x2, 0xfffffffffffff000
  bne  x1, x2, fail

  # Test 9: LUI with all zeros and ADDI positive
  li   TESTNUM, 9
  lui  x1, 0x0
  addi x1, x1, 1234
  li   x2, 1234
  bne  x1, x2, fail

  # Test 10: LUI with max immediate and ADDI negative
  li   TESTNUM, 10
  lui  x1, 0xfffff
  addi x1, x1, -4096
  li   x2, 0xfffffffffffff000
  bne  x1, x2, fail

  # Test 11: LUI mid-range with ADDI overflow
  li   TESTNUM, 11
  lui  x1, 0x7ffff
  addi x1, x1, 4095
  li   x2, 0x000000000000ffff
  bne  x1, x2, fail

  TEST_PASSFAIL

RVTEST_CODE_END

.data
RVTEST_DATA_BEGIN

TEST_DATA

RVTEST_DATA_END
