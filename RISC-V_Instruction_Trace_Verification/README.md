# RISC-V Trace Verification: Block Level CoCoTb based Verification in Shakthi C-Class Processor
This project performs Instruction Trace Verification on the Shakthi C-Class RISC-V Processor using a Cocotb-based block-level verification environment. The goal is to ensure functional correctness by comparing RTL execution traces against disassembled reference traces of the test program.

## Project Overview
* Block-level functional verification of Shakthi C-Class RISC-V Core
* Simulation-based trace extraction of PC & instruction sequences
* Comparison of RTL-generated trace vs. disassembled reference trace of the test program
* Final results logged in Analysis.csv for evaluation and debugging

## How to Run the Verification
1. Clone the repository
```
   git clone https://github.com/VijaiSaravanan/RISC-V_Cohort/RISC-V_Instruction_Trace_Verification/Scripts.git
```
3. Run the COCOTB test
```
   MODULE=test_c_class TESTCASE= TOPLEVEL=mkTbSoc TOPLEVEL_LANG=verilog "<Simulator>" +rtldump
```
4. Run PC verification script
```
python analyze_pc.py
```
6. Output Results will be available in a csv file.

### 📜 Documentation
📄 Project Report.pdf – Complete workflow, methodology & outcomes
📊 Presentation.ppt – VIVA / Final presentation slides
