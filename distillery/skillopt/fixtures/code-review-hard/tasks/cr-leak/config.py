def load_count(path):
    """Return the number of lines in the file at path."""
    f = open(path)
    data = f.read()
    return len(data.splitlines())
