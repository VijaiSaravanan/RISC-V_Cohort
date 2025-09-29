import glob
import os
import pandas as pd
from collections import defaultdict

def parse_extensions_from_filename(filename):
    # Extract base filename without extension
    base = os.path.splitext(os.path.basename(filename))[0]
    # Remove 'rv_', 'rv32_', or 'rv64_' prefix
    if base.startswith('rv64_'):
        base = base[5:]
    elif base.startswith('rv32_'):
        base = base[5:]
    elif base.startswith('rv_'):
        base = base[3:]
    # Split by '_' to get extensions
    extensions = base.split('_')
    # Normalize extensions
    normalized = []
    for ext in extensions:
        # Preserve case for Z* extensions (e.g., Zbkb, Zfh)
        if ext.lower().startswith('z'):
            normalized.append(ext.capitalize())  # e.g., zbkb -> Zbkb, zfh -> Zfh
        else:
            ext = ext.upper()
            if ext == 'I':
                normalized.append('RV32I')  # Assume 'i' means RV32I
            elif ext == 'M':
                normalized.append('M')
            elif ext == 'A':
                normalized.append('A')
            elif ext == 'F':
                normalized.append('F')
            elif ext == 'D':
                normalized.append('D')
            elif ext == 'C':
                normalized.append('C')
            else:
                normalized.append(ext)  # Keep unknown extensions as-is
    return normalized

def parse_instructions(directory):
    # Check if directory exists
    if not os.path.exists(directory):
        print(f"Error: Directory '{directory}' does not exist.")
        return defaultdict(int), defaultdict(list)

    # Dictionary to store extension counts
    extension_counts = defaultdict(int)
    # Dictionary to store instructions and their extensions
    instruction_extensions = defaultdict(list)

    # Find all files in the extensions directory
    files = glob.glob(os.path.join(directory, "*"))
    if not files:
        print(f"Warning: No files found in '{directory}'.")

    for file_path in files:
        # Skip if not a file
        if not os.path.isfile(file_path):
            continue

        # Get extensions from filename
        extensions = parse_extensions_from_filename(file_path)
        if not extensions:
            continue

        try:
            with open(file_path, 'r') as file:
                for line in file:
                    # Skip empty lines, comments, or quadrant headers
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    # Extract instruction name (first word after optional $pseudo_op)
                    parts = line.split()
                    if not parts:
                        continue
                    instr_name = parts[0]
                    if instr_name.startswith('$pseudo_op'):
                        if len(parts) < 2:
                            continue
                        # Handle pseudo-op format (e.g., "$pseudo_op rv64_zbp::shfli")
                        instr_name = parts[1].split('::')[-1] if '::' in parts[1] else parts[1]

                    # Store instruction and its extensions
                    instruction_extensions[instr_name].extend(extensions)
                    # Count instruction for each extension
                    for ext in extensions:
                        extension_counts[ext] += 1
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    return extension_counts, instruction_extensions

def main():
    # Directory containing opcode files
    directory = "riscv-opcodes/extensions"

    # Parse instructions and count extensions
    extension_counts, instruction_extensions = parse_instructions(directory)

    # Exit if no instructions were found
    if not instruction_extensions:
        print("No instructions found. Exiting.")
        return

    # Print instruction list with extensions
    print("\nInstructions and Their Extensions")
    print("-" * 35)
    print(f"{'Instruction':<20} | {'Extensions'}")
    print("-" * 35)
    for instr, exts in sorted(instruction_extensions.items()):
        # Remove duplicates while preserving order
        unique_exts = sorted(set(exts))
        print(f"{instr:<20} | {', '.join(unique_exts)}")

    # Print extension count table
    print("\nExtension | Instruction Count")
    print("-" * 30)
    for ext, count in sorted(extension_counts.items()):
        print(f"{ext:<9} | {count}")

    # Create DataFrame and save to CSV
    df = pd.DataFrame(sorted(extension_counts.items()), columns=["Extension", "Instruction Count"])
    df.to_csv("extension_counts.csv", index=False)
    print("\nExtension counts saved to 'extension_counts.csv'")

if __name__ == "__main__":
    main()

