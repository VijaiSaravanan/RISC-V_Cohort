import logging
from pathlib import Path
import shutil

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def copy_matching_directories(root_dir, dest_dir, prefix="f"):
    """Copy subdirectories starting with prefix to dest_dir."""
    root_path = Path(root_dir).resolve()
    dest_path = Path(dest_dir).resolve()
    dest_path.mkdir(exist_ok=True)
    logging.info(f"Searching for subdirectories starting with '{prefix}' in {root_path}")

    found = False
    for subdir in root_path.rglob("*"):
        if subdir.is_dir() and subdir.name.startswith(prefix):
            found = True
            try:
                dest_subdir = dest_path / subdir.name
                shutil.copytree(subdir, dest_subdir, dirs_exist_ok=True)
                logging.info(f"Copied subdirectory {subdir.name} to {dest_subdir}")
            except Exception as e:
                logging.error(f"Error copying subdirectory {subdir.name}: {e}")

    if not found:
        logging.warning(f"No subdirectories starting with '{prefix}' found in {root_path}")

def main():
    root_dir = "."  # Replace with your root directory
    dest_dir = "f"  # Replace with your destination directory
    try:
        if not Path(root_dir).exists():
            logging.error(f"Root directory does not exist: {root_dir}")
            return
        copy_matching_directories(root_dir, dest_dir)
    except Exception as e:
        logging.error(f"Main execution error: {e}")

if __name__ == "__main__":
    main()
