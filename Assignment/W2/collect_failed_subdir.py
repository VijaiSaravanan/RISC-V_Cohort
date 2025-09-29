import logging
from pathlib import Path
import shutil
import argparse

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def collect_failed_subdirectories(root_dir, output_dir="failed_subdirectories", copy_status_only=False):
    """Copy subdirectories containing STATUS_FAILED file to output_dir and optionally copy STATUS_FAILED file to root_dir/failed_subdirectories."""
    root_path = Path(root_dir).resolve()
    output_path = Path(output_dir).resolve()
    output_path.mkdir(exist_ok=True)

    # Create failed_subdirectories in root_dir if copy_status_only is True
    status_only_dir = root_path / "failed_subdirectories"
    if copy_status_only:
        status_only_dir.mkdir(exist_ok=True)

    logging.info(f"Searching for subdirectories with STATUS_FAILED in {root_path}")
    found = False
    for subdir in root_path.rglob("*"):
        if subdir.is_dir():
            status_file = subdir / "STATUS_FAILED"
            if status_file.is_file():
                found = True
                try:
                    # Copy entire subdirectory to output_dir
                    dest_dir = output_path / subdir.name
                    shutil.copytree(subdir, dest_dir, dirs_exist_ok=True)
                    logging.info(f"Copied subdirectory {subdir.name} to {dest_dir}")

                    # If copy_status_only is True, copy STATUS_FAILED file to root_dir/failed_subdirectories
                    if copy_status_only:
                        dest_status_file = status_only_dir / f"{subdir.name}_STATUS_FAILED"
                        shutil.copy2(status_file, dest_status_file)
                        logging.info(f"Copied STATUS_FAILED from {subdir.name} to {dest_status_file}")
                except Exception as e:
                    logging.error(f"Error processing subdirectory {subdir.name}: {e}")

    if not found:
        logging.warning(f"No subdirectories with STATUS_FAILED found in {root_path}")

def main():
    parser = argparse.ArgumentParser(description="Copy subdirectories with STATUS_FAILED file and optionally copy STATUS_FAILED file to root_dir/failed_subdirectories.")
    parser.add_argument("--copy-status-only", action="store_true", help="Copy only the STATUS_FAILED file to root_dir/failed_subdirectories")
    parser.add_argument("--root-dir", default=".", help="Root directory to search for STATUS_FAILED files")
    parser.add_argument("--output-dir", default="failed_subdirectories", help="Output directory for copied subdirectories")
    args = parser.parse_args()

    try:
        root_path = Path(args.root_dir)
        if not root_path.exists():
            logging.error(f"Root directory does not exist: {args.root_dir}")
            return
        collect_failed_subdirectories(args.root_dir, args.output_dir, args.copy_status_only)
    except Exception as e:
        logging.error(f"Main execution error: {e}")

if __name__ == "__main__":
    main()
