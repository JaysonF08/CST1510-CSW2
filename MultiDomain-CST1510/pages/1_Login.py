# pages/1_Login.py

import streamlit as st

from app.data.users import (
    validate_username,
    validate_password,
    register_user,
    authenticate_user,
    is_admin_credentials,
    ensure_seed_admin,
)

from app.data import db

st.set_page_config(page_title="Cybersecurity Login", layout="wide")
st.session_state["current_page"] = "Login"


# INIT DB + MIGRATION

if "db_initialised" not in st.session_state:
    db.create_tables()
    db.migrate_users_from_file()
    st.session_state["db_initialised"] = True

# Always run seed (safe + fixes Streamlit session not re-running it)
ensure_seed_admin()

st.title("Login Page")
st.write("A secure login page.")

mode = st.radio(
    "Select an option:",
    ("Login", "Register a new user"),
    horizontal=True,
)

# global session auth state
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = None
if "role" not in st.session_state:
    st.session_state["role"] = None



# REGISTER

if mode == "Register a new user":
    st.subheader("Create a new account")

    st.info(
        "Username rules:\n"
        "- at least 2 characters\n"
        "- no spaces\n"
        "- only letters/numbers/underscore\n\n"
        "Password rules:\n"
        "- minimum 5 characters\n"
        "- at least 1 letter\n"
        "- at least 1 number\n"
        "- at least 1 special character (e.g., @, #, !)"
    )

    new_username = st.text_input("Username")
    new_password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    st.markdown("**Role:**")
    register_as_admin = st.checkbox("Register as admin")

    admin_ok = True
    admin_user = ""
    admin_pass = ""

    if register_as_admin:
        st.warning("Admin registration needs an existing admin to approve it.")
        admin_user = st.text_input("Existing admin username")
        admin_pass = st.text_input("Existing admin password", type="password")

        if admin_user and admin_pass:
            admin_ok = is_admin_credentials(admin_user, admin_pass)
        else:
            admin_ok = False

    if st.button("Register"):
        if not new_username or not new_password or not confirm_password:
            st.error("Please fill in all the fields.")
        else:
            is_valid_user, user_msg = validate_username(new_username)
            if not is_valid_user:
                st.error(user_msg)
            else:
                is_valid_pass, pass_msg = validate_password(new_password)
                if not is_valid_pass:
                    st.error(pass_msg)
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    role = "admin" if register_as_admin else "analyst"

                    if role == "admin" and not admin_ok:
                        st.error("Admin approval failed. Use a valid existing admin login.")
                    else:
                        success = register_user(new_username, new_password, role=role)
                        if success:
                            st.success(f"User registered as **{role}**. You can now login.")
                        else:
                            st.error("That username already exists. Please choose another one.")



# LOGIN

if mode == "Login":
    st.subheader("Login to your account")

    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pass")

    if st.button("Login"):
        if not username or not password:
            st.error("Please enter both username and password.")
        else:
            ok, role = authenticate_user(username, password)
            if ok:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.session_state["role"] = role

                st.success(f"Welcome, {username}!")
                st.switch_page("pages/2_Cybersecurity.py")
            else:
                st.error("Invalid username or password.")


# sidebar status
if st.session_state.get("logged_in"):
    st.sidebar.success(
        f"Logged in as: {st.session_state.get('username')} ({st.session_state.get('role')})"
    )
else:
    st.sidebar.warning("Not logged in.")