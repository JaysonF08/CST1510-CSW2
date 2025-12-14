# app/data/users.py
"""
User-related functions:

- bcrypt hashing / verification
- username & password validation
- register_user()  (writes to DB + keeps users.txt in sync)
- authenticate_user() (returns (ok, role))
- ensure_seed_admin() (creates/repairs the seed admin)
"""

from pathlib import Path
import re
import bcrypt

from .db import get_connection, DATA_DIR, create_tables

# Path to users.txt (Week 7 evidence file)
USER_FILE = DATA_DIR / "users.txt"

# -----------------------------
# SEED ADMIN (Option B)
# -----------------------------
SEED_ADMIN_USERNAME = "JaysonF"
SEED_ADMIN_PASSWORD = "Jayson@2008"
SEED_ADMIN_ROLE = "admin"


# ---------- Hashing helpers ----------

def hash_password(plain_text_password: str) -> str:
    """Turn a normal password into a secure bcrypt hash."""
    password_bytes = plain_text_password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_text_password: str, stored_hash: str) -> bool:
    """Check if a plain password matches the saved bcrypt hash."""
    pw_bytes = plain_text_password.encode("utf-8")
    hash_bytes = stored_hash.encode("utf-8")
    return bcrypt.checkpw(pw_bytes, hash_bytes)


# ---------- Validation helpers ----------

def validate_username(username: str):
    """
    Rules:
    - must be at least 2 characters
    - no spaces
    - only letters, numbers, underscore
    """
    username = (username or "").strip()

    if len(username) < 2:
        return False, "Username must be at least 2 characters."
    if " " in username:
        return False, "Username cannot contain spaces."
    if not re.fullmatch(r"[A-Za-z0-9_]+", username):
        return False, "Username can only contain letters, numbers, and underscore (_)."

    return True, "OK"


def validate_password(password: str):
    """
    Rules:
    - minimum 5 characters
    - at least 1 number
    - at least 1 special character (e.g., @ # ! $)
    - at least 1 letter
    """
    password = password or ""

    if len(password) < 5:
        return False, "Password must be at least 5 characters."
    if not any(ch.isdigit() for ch in password):
        return False, "Password must contain at least 1 number."
    if not any(ch.isalpha() for ch in password):
        return False, "Password must contain at least 1 letter."
    if not any(not ch.isalnum() for ch in password):
        return False, "Password must contain at least 1 special character (e.g., @, #, !)."

    return True, "OK"


# ---------- DB helpers ----------

def get_user_by_username(username: str):
    """Get a user from the DB. Returns row or None if not found."""
    username = (username or "").strip()
    if not username:
        return None

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
        return cur.fetchone()  # (id, username, password_hash, role) or None


def authenticate_user(username: str, password: str):
    """
    Returns: (ok: bool, role: str|None)
    """
    create_tables()
    username = (username or "").strip()

    row = get_user_by_username(username)
    if row is None:
        return False, None

    stored_hash = row[2]
    role = row[3]

    if verify_password(password, stored_hash):
        return True, role

    return False, None


def login_user(username: str, password: str) -> bool:
    """Backwards-compatible: returns True/False only."""
    ok, _ = authenticate_user(username, password)
    return ok


def is_admin_credentials(username: str, password: str) -> bool:
    """Used for Option B: only admins can authorize admin registration."""
    ok, role = authenticate_user(username, password)
    return ok and (role == "admin")


def _userfile_has_username(username: str) -> bool:
    """Check users.txt contains username (first column)."""
    if not USER_FILE.exists():
        return False

    try:
        for line in USER_FILE.read_text(encoding="utf-8").splitlines():
            parts = [p.strip() for p in line.split(",")]
            if parts and parts[0] == username:
                return True
    except Exception:
        return False

    return False


def ensure_seed_admin() -> None:
    """
    Bullet-proof seed admin:
    - If missing => creates it
    - If exists with wrong password/role => updates it to the correct values
    Also syncs users.txt as evidence.
    """
    create_tables()

    desired_hash = hash_password(SEED_ADMIN_PASSWORD)
    existing = get_user_by_username(SEED_ADMIN_USERNAME)

    with get_connection() as conn:
        cur = conn.cursor()

        if existing is None:
            cur.execute(
                """
                INSERT INTO users (username, password_hash, role)
                VALUES (?, ?, ?)
                """,
                (SEED_ADMIN_USERNAME, desired_hash, SEED_ADMIN_ROLE),
            )
        else:
            cur.execute(
                """
                UPDATE users
                SET password_hash = ?, role = ?
                WHERE username = ?
                """,
                (desired_hash, SEED_ADMIN_ROLE, SEED_ADMIN_USERNAME),
            )

        conn.commit()

    # Keep users.txt in sync (evidence file)
    USER_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not _userfile_has_username(SEED_ADMIN_USERNAME):
        row = get_user_by_username(SEED_ADMIN_USERNAME)
        if row is not None:
            pw_hash = row[2]
            with USER_FILE.open("a", encoding="utf-8") as f:
                f.write(f"{SEED_ADMIN_USERNAME},{pw_hash},{SEED_ADMIN_ROLE}\n")


def register_user(username: str, password: str, role: str = "analyst") -> bool:
    """
    Create a new user in the DB.
    Returns True when successful, False if username already exists.
    Also updates users.txt for coursework requirements.
    """
    create_tables()

    username = (username or "").strip()
    role = (role or "analyst").strip().lower()

    if role not in {"analyst", "admin"}:
        role = "analyst"

    if get_user_by_username(username) is not None:
        return False

    pw_hash = hash_password(password)

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

    USER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with USER_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{username},{pw_hash},{role}\n")

    return True