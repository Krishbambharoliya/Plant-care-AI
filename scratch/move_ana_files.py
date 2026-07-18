import os
import shutil

src_dir = r"D:\Project SEM-4\Python Project\ana"
dest_dir = r"D:\Project SEM-4\ana"

# 1. Create destination directory if it doesn't exist
if not os.path.exists(dest_dir):
    os.makedirs(dest_dir)
    print(f"Created destination directory: {dest_dir}")

# 2. Copy all files from src_dir to dest_dir
if os.path.exists(src_dir):
    for filename in os.listdir(src_dir):
        src_file = os.path.join(src_dir, filename)
        dest_file = os.path.join(dest_dir, filename)
        if os.path.isfile(src_file):
            shutil.copy2(src_file, dest_file)
            print(f"Copied: {filename} -> {dest_dir}")

    # 3. Remove src_dir
    shutil.rmtree(src_dir)
    print(f"Successfully removed workspace source directory: {src_dir}")
else:
    print(f"Source directory {src_dir} does not exist.")
