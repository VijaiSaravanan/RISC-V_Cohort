import logging
from pathlib import Path
import shutil

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def copy_listed_files(root_dir, file_list, output_dir):
    """Copy files from file_list to new folders in output_dir."""
    root_path = Path(root_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    for file_name in file_list:
        file_path = root_path / file_name
        if file_path.is_file():
            try:
                new_folder = output_path / file_path.stem
                new_folder.mkdir(exist_ok=True)
                shutil.copy2(file_path, new_folder / file_name)
                logging.info(f"Copied {file_name} to {new_folder}")
            except Exception as e:
                logging.error(f"Error copying {file_name}: {e}")
        else:
            logging.warning(f"File not found: {file_name}")

def main():
    root_dir = "/home/vsysuser/workspace/Assignments/W2"  # Replace with your root directory
    output_dir = "listed_files"   # Replace with your output directory
    file_list = ["extract_zip_files.py", "f8.zip", "f9.zip", "file.txt", "file.doc", "file1.doc"]  # Replace with your file list
    try:
        copy_listed_files(root_dir, file_list, output_dir)
    except Exception as e:
        logging.error(f"Main execution error: {e}")

if __name__ == "__main__":
    main()
