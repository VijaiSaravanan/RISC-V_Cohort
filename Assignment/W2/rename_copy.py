import logging
from pathlib import Path
import shutil
import argparse

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def rename_and_copy_codirectories(root_dir, dest_dir="codir_copies"):
    """Rename .elf files in dut subdirectories and copy co-directories to dest_dir, skipping ref subdirectories."""
    root_path = Path(root_dir).resolve()
    dest_path = Path(dest_dir).resolve()
    dest_path.mkdir(exist_ok=True)
    logging.info(f"Searching for co-directories with dut subdirectory in {root_path}")

    found = False
    # Iterate only through direct subdirectories (co-directories)
    for codir in root_path.iterdir():
        if codir.is_dir():
            dut_dir = codir / "dut"
            if dut_dir.is_dir():
                found = True
                try:
                    # Rename .elf files in dut subdirectory
                    for elf_file in dut_dir.glob("*.elf"):
                        new_elf_name = f"{codir.name}.elf"
                        new_elf_path = dut_dir / new_elf_name
                        try:
                            elf_file.rename(new_elf_path)
                            logging.info(f"Renamed {elf_file.name} to {new_elf_name} in {dut_dir}")
                        except Exception as e:
                            logging.error(f"Error renaming {elf_file.name} in {dut_dir}: {e}")

                    # Copy co-directory to destination, excluding ref subdirectory
                    def ignore_ref(dir, names):
                        return ["ref"] if "ref" in names else []

                    dest_codir = dest_path / codir.name
                    shutil.copytree(codir, dest_codir, ignore=ignore_ref, dirs_exist_ok=True)
                    logging.info(f"Copied co-directory {codir.name} to {dest_codir}")
                except Exception as e:
                    logging.error(f"Error processing co-directory {codir.name}: {e}")

    if not found:
        logging.warning(f"No co-directories with dut subdirectory found in {root_path}")

def main():
    parser = argparse.ArgumentParser(description="Rename .elf files in dut subdirectories and copy co-directories to destination, skipping ref subdirectories.")
    parser.add_argument("--root-dir", default=".", help="Root directory to search for co-directories")
    parser.add_argument("--dest-dir", default="codir_copies", help="Destination directory for copied co-directories")
    args = parser.parse_args()

    try:
        root_path = Path(args.root_dir)
        if not root_path.exists():
            logging.error(f"Root directory does not exist: {args.root_dir}")
            return
        rename_and_copy_codirectories(args.root_dir, args.dest_dir)
    except Exception as e:
        logging.error(f"Main execution error: {e}")

if __name__ == "__main__":
    main()
