def find_user(conn, name):
    """Look up a single user row by name."""
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE name = '" + name + "'"
    cursor.execute(query)
    return cursor.fetchone()
