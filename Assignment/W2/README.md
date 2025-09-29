## Week 2
It contains Python codes for File and Directory Handling and common Automation tasks.

### P1: Extract ZIP Files
File name: extract_zip_files.py
This python code searches all directories and its sub-directories for .zip files. If found, it unzips in its location itself. If any .zip file is corrupted, it is not extracted and it is skipped to continue the search. In this program, root directory is represented using '.' .
Run the .py file by placing it in the root directory.

### P2: Copy Listed Files
File name: copy_listed_files.py
This Python file contains a list instantiated to store a number of file names. Each file name is searched in the sub-directories and co-directories in which the python file is present. If a file in the list is found, output directory is created with a name 'listed_files' and the corresponding files are copied to the output directory within the directory named as the listed file name.
Run the .py file by placing it in the root directory.

### P3: Collect Failed Sub-directories
File name: collect_failed_subdir.py
This Python program searches for a file named as 'STATUS_FAILED'. If found, it copies the contents of the directory into a new directory in the root directory.
Run the .py file by placing it in the root directory.

### P4: Copy Matching Directories
File name: copy_match_dir.py
In this code, a prefix name 'f' is searched recursively throughout the directory. If a directory is found with this prefix, then that directory is copied to a new direcotry named with the prefix.
Run the .py file by placing it in the root directory.

### P5: Rename and Copy Co-directories
File name: rename_copy.py
This code, renames .elf file in dut sub-directory to match the co-directory name. It skips if any 'ref' directory is found and copies entire co-directory to a destination directory.
Run the .py file by placing it in the root directory.
