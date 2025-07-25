import os

# The path to the problematic file inside the Vercel build environment,
# which we found in the deployment error log.
file_to_patch = '/var/task/pollinations/__init__.py'

def patch_file(file_path):
    """
    Finds the get_latest() call in the specified file and comments it out.
    """
    print(f"Attempting to patch file: {file_path}")
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}. Cannot apply patch.")
        return

    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()

        if any("# get_latest()" in line for line in lines):
            print("Patch has already been applied. Exiting.")
            return

        with open(file_path, 'w') as f:
            for line in lines:
                # Find the exact line that calls the function and comment it out
                if "get_latest()" in line and not line.strip().startswith('#'):
                    f.write("# " + line)
                    print(f"Successfully commented out line: {line.strip()}")
                else:
                    f.write(line)
        print("File patching was successful.")
    except Exception as e:
        print(f"An unexpected error occurred while patching the file: {e}")

if __name__ == "__main__":
    patch_file(file_to_patch)
