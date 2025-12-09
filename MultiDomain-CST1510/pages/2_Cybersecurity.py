# pages/2_Cybersecurity.py

import streamlit as st
from app.data import db

st.set_page_config(page_title="Cybersecurity Dashboard", page_icon="🛡️", layout="wide")

st.title("Cybersecurity Dashboard")

# Optional: guard – only show if logged in
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("You must be logged in to view this page.")
    if st.button("Go to Login"):
        st.switch_page("pages/1_Login.py")
else:
    st.success(f"Welcome, {st.session_state['username']}! 🎉")
    st.write("This is where your Cybersecurity charts and incident analysis will go.")
