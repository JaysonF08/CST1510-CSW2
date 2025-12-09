# pages/1_Login.py

import streamlit as st

from app.data.users import (
    validate_username,
    validate_password,
    register_user,
    login_user,
)
from app.data import db

st.set_page_config(page_title="Cybersecurity Login", page_icon="🔒")

# Ensure tables exist (safe to call multiple times)
if "db_initialised" not in st.session_state:
    db.create_tables()
    db.migrate_users_from_file()
    st.session_state["db_initialised"] = True

st.title("Login Page")
st.write("A secure login page.")


# --------- Menu: Login or Register ---------
mode = st.radio(
    "Select an option:",
    ("Login", "Register a new user"),
    horizontal=True,
)

# Session state to remember login status
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = None


# --------- REGISTER SECTION ---------
if mode == "Register a new user":
    st.subheader("Create a new account")

    new_username = st.text_input("Username")
    new_password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

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
                    success = register_user(new_username, new_password)
                    if success:
                        st.success("User registered successfully! You can now login.")
                    else:
                        st.error("That username already exists. Please choose another one.")


# --------- LOGIN SECTION ---------
if mode == "Login":
    st.subheader("Login to your account")

    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pass")

    if st.button("Login"):
        if not username or not password:
            st.error("Please enter both username and password.")
        else:
            ok = login_user(username, password)
            if ok:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.success(f"Welcome, {username}!")

                # In Week 9, navigate to your Cyber dashboard page
                st.info("Redirecting to Cybersecurity dashboard...")
                st.switch_page("pages/2_Cybersecurity.py")
            else:
                st.error("Invalid username or password.")


# Sidebar status
if st.session_state["logged_in"]:
    st.sidebar.success(f"Logged in as: {st.session_state['username']}")
else:
    st.sidebar.warning("Not logged in.")
