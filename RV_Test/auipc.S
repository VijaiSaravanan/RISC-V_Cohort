# See LICENSE for license details.

#*****************************************************************************
# auipc.S
#-----------------------------------------------------------------------------
#
# Test auipc instruction
#

#include "riscv_test.h"
#include "test_macros.h"

RVTEST_RV64U
RVTEST_CODE_BEGIN

#-------------------------------------------------------------
# Basic AUIPC tests with positive and negative offsets
#-------------------------------------------------------------

  # Test 1: Positive offset
  TEST_CASE(2, a0, 10000, \
    .align 3; \
    lla a0, 1f + 10000; \
    jal a1, 1f; \
    1: sub a0, a0, a1; \
  )

  # Test 2: Negative offset
  TEST_CASE(3, a0, -10000, \
    .align 3; \
    lla a0, 1f - 10000; \
    jal a1, 1f; \
    1: sub a0, a0, a1; \
  )

#-------------------------------------------------------------
# AUIPC with zero offset
#-------------------------------------------------------------

  TEST_CASE(4, a0, 0, \
    .align 3; \
    auipc a0, 0; \
    jal a1, 1f; \
    1: sub a0, a0, a1; \
  )

#-------------------------------------------------------------
# AUIPC with max positive 20-bit immediate
#-------------------------------------------------------------

  TEST_CASE(5, a0, 0xFFFFF000, \
    .align 3; \
    auipc a0, 0xFFFFF; \
    slli a0, a0, 12; \
    jal a1, 1f; \
    1: sub a0, a0, a1; \
  )

#-------------------------------------------------------------
# AUIPC with src=dest
#-------------------------------------------------------------

  li a2, 0x1234
  auipc a2, 0x10
  auipc a2, 0x20       # overwrite dest immediately

#-------------------------------------------------------------
# AUIPC with multiple dependent instructions
#-------------------------------------------------------------

  auipc a3, 0x10
  auipc a4, 0x20
  add a5, a3, a4       # dependent sum check

#-------------------------------------------------------------
# Edge case: AUIPC with signed negative immediate
#-------------------------------------------------------------

  auipc a6, -1          # -1 in 20-bit signed immediate
  addi a6, a6, 0x1000   # adjust to expected result

#-------------------------------------------------------------
# AUIPC chain dependency
#-------------------------------------------------------------

  auipc a7, 0x5
  auipc t0, 0xA
  add t1, a7, t0

TEST_PASSFAIL

RVTEST_CODE_END

.data
RVTEST_DATA_BEGIN

  TEST_DATA

RVTEST_DATA_END
