import logging
from pathlib import Path
import zipfile
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_zip_files(root_dir):
    """Recursively extract all .zip files into the same directory where they are located."""
    root_path = Path(root_dir).resolve()
    logging.info(f"Searching for .zip files in {root_path}")
    zip_files = list(root_path.rglob('*.zip'))  # Recursive search for .zip files

    if not zip_files:
        logging.warning(f"No .zip files found in {root_path}")
        return

    for zip_path in zip_files:
        try:
            # Get directory contents before extraction
            extract_dir = zip_path.parent
            before_items = set(extract_dir.iterdir())

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Log ZIP contents
                zip_contents = zip_ref.namelist()
                logging.info(f"Contents of {zip_path.resolve()}: {zip_contents}")

                # Check if ZIP is empty
                if not zip_contents:
                    logging.warning(f"ZIP file is empty: {zip_path.resolve()}")
                    continue

                zip_ref.testzip()  # Check for corruption
                logging.info(f"Attempting to extract {zip_path.resolve()} to {extract_dir.resolve()}")
                zip_ref.extractall(extract_dir)

                # Verify extraction (files and directories)
                time.sleep(0.1)  # Brief delay for filesystem updates
                after_items = set(extract_dir.iterdir())
                new_items = after_items - before_items

                if new_items:
                    logging.info(f"Extracted {zip_path.resolve()} to {extract_dir.resolve()}: {[item.name for item in new_items]}")
                else:
                    logging.warning(f"No new files or directories extracted from {zip_path.resolve()}. Existing items may have been overwritten.")
        except zipfile.BadZipFile:
            logging.warning(f"Skipping corrupted ZIP file: {zip_path.resolve()}")
        except PermissionError as e:
            logging.error(f"Permission error extracting {zip_path.resolve()}: {e}")
        except Exception as e:
            logging.error(f"Error extracting {zip_path.resolve()}: {e}")

def main():
    root_dir = "."  # Absolute path to your directory
    try:
        if not Path(root_dir).exists():
            logging.error(f"Root directory does not exist: {root_dir}")
            return
        extract_zip_files(root_dir)
    except Exception as e:
        logging.error(f"Main execution error: {e}")

if __name__ == "__main__":
    main()
