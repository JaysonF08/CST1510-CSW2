# app/data/users.py
"""
User-related functions:

- bcrypt hashing / verification
- username & password validation
- register_user()  (writes to DB + keeps users.txt in sync)
- login_user()     (checks DB with bcrypt)
"""

from pathlib import Path
import bcrypt

from .db import get_connection, DATA_DIR, create_tables


USER_FILE = DATA_DIR / "users.txt"


# ---------- Hashing helpers ----------

def hash_password(plain_text_password: str) -> str:
    """Return bcrypt hash (as UTF-8 string) for a plain-text password."""
    password_bytes = plain_text_password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_text_password: str, stored_hash: str) -> bool:
    """Check if plain_text_password matches stored_hash (bcrypt)."""
    pw_bytes = plain_text_password.encode("utf-8")
    hash_bytes = stored_hash.encode("utf-8")
    return bcrypt.checkpw(pw_bytes, hash_bytes)


# ---------- Validation helpers ----------

def validate_username(username: str):
    username = username.strip()
    if not username:
        return False, "Username cannot be empty."
    if " " in username:
        return False, "Username cannot contain spaces."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    return True, "OK"


def validate_password(password: str):
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    return True, "OK"


# ---------- DB helpers ----------

def get_user_by_username(username: str):
    """Return (id, username, password_hash, role) or None."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, username, password_hash, role
            FROM users
            WHERE username = ?
            """,
            (username,),
        )
        return cur.fetchone()


def register_user(username: str, password: str, role: str = "analyst") -> bool:
    """
    Register a new user in the database.

    Returns True if created, False if username already exists.
    Also keeps DATA/users.txt updated for Week 7 evidence.
    """
    create_tables()  # ensure table exists
    username = username.strip()

    # 1. Check if user already exists
    if get_user_by_username(username) is not None:
        return False

    # 2. Hash password
    pw_hash = hash_password(password)

    # 3. Insert into DB
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (username, password_hash, role)
            VALUES (?, ?, ?)
            """,
            (username, pw_hash, role),
        )
        conn.commit()

    # 4. Append to users.txt (optional but nice for showing Week 7 → Week 8)
    USER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with USER_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{username},{pw_hash},{role}\n")

    return True


def login_user(username: str, password: str) -> bool:
    """
    Check credentials against SQLite database.
    Returns True if login successful, False otherwise.
    """
    create_tables()  # safe if called multiple times
    username = username.strip()

    row = get_user_by_username(username)
    if row is None:
        return False

    stored_hash = row[2]  # (id, username, password_hash, role)
    return verify_password(password, stored_hash)
