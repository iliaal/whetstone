import os


def safe_write(path, data):
    """Write data to path only if the file does not already exist."""
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(data)
        return True
    return False
