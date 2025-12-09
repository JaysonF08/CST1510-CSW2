# auth_functions.py

import bcrypt
import os

USER_DATA_FILE = "users.txt"


def hash_password(plain_text_password):
    # Hashing the plain text using bcrypt.
    pass_bytes = plain_text_password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pass_bytes, salt)
    return hashed_password


def verify_password(plain_text_password, hashed_password):
    # If user already exists, this checks whether the plain text matched with the stored hash.
    pass_bytes = plain_text_password.encode("utf-8")
    return bcrypt.checkpw(pass_bytes, hashed_password)


def register_user(username, password):
    """Registers a new user by saving username and hashed password to users.txt."""

    # Check if username already exists
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                parts = line.split(",", 1)
                saved_username = parts[0]

                if saved_username == username:
                    # Username already taken
                    return False
    except FileNotFoundError:
        # File doesn't exist yet – that's fine, we'll create it
        pass

    # Hash the password
    hashed_password = hash_password(password)
    # Convert bytes to string so we can store it in the text file
    hashed_password_str = hashed_password.decode("utf-8")

    # Append new user to the file
    with open(USER_DATA_FILE, "a", encoding="utf-8") as f:
        f.write(f"{username},{hashed_password_str}\n")

    return True


def login_user(username, password):
    """Checks if the username + password combination is valid."""
    if not os.path.exists(USER_DATA_FILE):
        return False

    with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            parts = line.split(",", 1)   # [saved_username, hashed_password_str]
            saved_username = parts[0]
            saved_hashed_password_str = parts[1]

            if saved_username == username:
                # Convert stored hash (string) back to bytes
                stored_hash_bytes = saved_hashed_password_str.encode("utf-8")
                if verify_password(password, stored_hash_bytes):
                    return True
                else:
                    return False

    # Username not found
    return False


def validate_username(username):
    """Basic checks for username strength."""
    if len(username) < 3:
        return False, "Username must be at least 3 characters long."

    if " " in username:
        return False, "Username cannot contain spaces."

    if not username.isalnum():
        return False, "Username can only contain letters and numbers."

    return True, ""


def validate_password(password):
    """Basic checks for password strength."""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."

    if not any(ch.isdigit() for ch in password):
        return False, "Password must contain at least one number."

    if not any(ch.isalpha() for ch in password):
        return False, "Password must contain at least one letter."

    return True, ""
