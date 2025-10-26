#!/usr/bin/env python3
from pathlib import Path
import csv, re, sys

# ==========================================================
#  Detect instruction name and mode automatically
# ==========================================================
instr = sys.argv[1] if len(sys.argv) > 1 else Path.cwd().name
mode = Path.cwd().parent.name   # automatically detect mode folder (p/v/pt/pm)
print(f"🔍 Analyzing instruction: {instr} [Mode: {mode}]")

# ==========================================================
#  File paths
# ==========================================================
csv_file = Path(f"pc_log_{instr}.csv")
rtl_file = Path(f"{instr}.dump") if Path(f"{instr}.dump").exists() else Path("rtl.dump")
dis_file = Path(f"{instr}.disass")

# Individual test report
out_txt = Path(f"missing_instructions_{instr}.txt")
out_csv = Path(f"missing_instruct_{instr}.csv")

# Mode-level aggregated report (stored inside mode folder)
agg_txt = Path(f"../missing_instructions_{mode}.txt")
agg_csv = Path(f"../missing_instructions_{mode}.csv")

# ==========================================================
#  Step 1: Verify CSV exists
# ==========================================================
if not csv_file.exists():
    print(f"❌ No {csv_file} found — run the Cocotb logger first.")
    sys.exit(1)

# ==========================================================
#  Step 2: Load logged PCs from CSV
# ==========================================================
pcs = []
with open(csv_file, encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader, None)
    for row in reader:
        if not row or not row[0].strip():
            continue
        try:
            value = row[0].strip().lower()
            if value.startswith("0x"):
                value = value[2:]
            pcs.append(int(value, 16))
        except ValueError:
            print(f"⚠️ Skipped invalid PC entry: {row[0]}")

print(f"📘 Loaded {len(pcs)} logged PCs from {csv_file}")

# ==========================================================
#  Step 3: Load PC values from RTL dump
# ==========================================================
rtl_pcs = set()
if rtl_file.exists():
    for line in open(rtl_file):
        # Only parse instruction traces (ignore mem writes, etc.)
        if "core" in line and re.search(r"0x[0-9a-fA-F]+", line):
            m = re.search(r"0x[0-9a-fA-F]+", line)
            if m:
                try:
                    rtl_pcs.add(int(m.group(0), 16))
                except ValueError:
                    pass
    print(f"📗 Loaded {len(rtl_pcs)} PCs from {rtl_file}")
else:
    print("⚠️ No rtl.dump found — skipping RTL comparison.")
    sys.exit(0)

# ==========================================================
#  Step 4: Parse disassembly (.disass)
# ==========================================================
pc2inst = {}
pc2label = {}
current_label = None

if dis_file.exists():
    for line in open(dis_file):
        # Detect labels (e.g. 0000000080000138 <reset_vector>:)
        label_match = re.match(r"^\s*[0-9a-fA-F]+\s+<([\w\d_]+)>:", line)
        if label_match:
            current_label = label_match.group(1)
            continue

        # Detect instructions (e.g. 80000000: a09d  j 80000066)
        inst_match = re.match(r"^\s*([0-9a-fA-F]+):\s+[0-9a-fA-F]+\s+(.*)$", line)
        if inst_match:
            pc_addr = int(inst_match.group(1), 16)
            instruction = inst_match.group(2).strip()
            pc2inst[pc_addr] = instruction
            if current_label:
                pc2label[pc_addr] = current_label

    print(f"📄 Loaded disassembly ({len(pc2inst)} instructions, {len(set(pc2label.values()))} labels)")
else:
    print("⚠️ No disassembly file found. Instructions will be marked as 'Not found'.")

# ==========================================================
#  Step 5: Find missing PCs
# ==========================================================
missing = [p for p in pcs if p not in rtl_pcs]
print(f"📊 Logged {len(pcs)} PCs, {len(missing)} missing in RTL dump.")

# ==========================================================
#  Step 6A: Write individual test report (TXT)
# ==========================================================
with open(out_txt, "w") as f:
    f.write("Missing PC (Hex) | Label (Context) | Instruction\n")
    f.write("=" * 100 + "\n")
    if not missing:
        f.write("✅ No missing PCs — all matched with RTL dump.\n")
    else:
        for pc in missing:
            inst = pc2inst.get(pc, "Not found in disassembly")
            label = pc2label.get(pc, "No label")
            f.write(f"{hex(pc):<18} {label:<20} {inst}\n")

print(f"📄 Missing PC report saved → {out_txt}")

# ==========================================================
#  Step 6B: Write individual test report (CSV)
# ==========================================================
with open(out_csv, "w", newline="") as csv_out:
    writer = csv.writer(csv_out)
    writer.writerow(["Missing PC (Hex)", "Label (Context)", "Instruction"])
    if not missing:
        writer.writerow(["✅ No missing PCs — all matched with RTL dump", "", ""])
    else:
        for pc in missing:
            inst = pc2inst.get(pc, "Not found in disassembly")
            label = pc2label.get(pc, "No label")
            writer.writerow([hex(pc), label, inst])

print(f"📘 Missing PC CSV report saved → {out_csv}")

# ==========================================================
#  Step 7: Append to mode-level aggregated report (inside mode folder)
# ==========================================================
new_file = not agg_csv.exists()

with open(agg_txt, "a") as f:
    f.write(f"\n{'='*120}\n")
    f.write(f"📁 Instruction: {instr} | Mode: {mode}\n")
    f.write(f"{'='*120}\n")
    if not missing:
        f.write("✅ No missing PCs — all matched with RTL dump.\n")
    else:
        for pc in missing:
            inst = pc2inst.get(pc, "Not found in disassembly")
            label = pc2label.get(pc, "No label")
            f.write(f"{hex(pc):<18} {label:<20} {inst}\n")

print(f"🧾 Updated mode-level TXT report → {agg_txt}")

with open(agg_csv, "a", newline="") as agg_out:
    writer = csv.writer(agg_out)
    if new_file:
        writer.writerow(["Instruction", "Mode", "Missing PC (Hex)", "Label (Context)", "Instruction"])
    if not missing:
        writer.writerow([instr, mode, "✅ No missing PCs", "", ""])
    else:
        for pc in missing:
            inst = pc2inst.get(pc, "Not found in disassembly")
            label = pc2label.get(pc, "No label")
            writer.writerow([instr, mode, hex(pc), label, inst])

print(f"🧾 Updated mode-level CSV report → {agg_csv}")
