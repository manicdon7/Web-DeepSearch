import importlib.util
import os

def apply_patch():
    """
    Finds the installed 'pollinations' package and comments out the
    faulty get_latest() call in its __init__.py file.
    """
    try:
        # Dynamically find the location of the installed package
        spec = importlib.util.find_spec("pollinations")
        if spec is None or spec.origin is None:
            print("Error: Could not find the 'pollinations' package location.")
            exit(1) # Exit with an error code to fail the build

        file_to_patch = spec.origin
        print(f"Found 'pollinations' __init__.py at: {file_to_patch}")

        with open(file_to_patch, 'r') as f:
            lines = f.readlines()

        # Check if the file is already patched to avoid redundant edits
        if any("# get_latest()" in line for line in lines):
            print("Patch appears to be already applied. No action needed.")
            return

        # Rewrite the file with the faulty line commented out
        patched = False
        with open(file_to_patch, 'w') as f:
            for line in lines:
                if "get_latest()" in line and not line.strip().startswith('#'):
                    f.write("# " + line)
                    print(f"Success: Commented out line: '{line.strip()}'")
                    patched = True
                else:
                    f.write(line)
        
        if not patched:
            print("Warning: The line 'get_latest()' was not found in the file.")
        
        print("Patching process completed.")

    except Exception as e:
        print(f"An unexpected error occurred during the patching process: {e}")
        exit(1) # Exit with an error code

if __name__ == "__main__":
    apply_patch()
