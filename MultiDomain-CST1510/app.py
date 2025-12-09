# app.py
import streamlit as st

from app.data import db

st.set_page_config(
    page_title="Multi-Domain Intelligence Platform",
    layout="wide",
    page_icon="📊",
)

# Initialise DB once per session
if "db_initialised" not in st.session_state:
    db.create_tables()
    db.migrate_users_from_file()
    # You can delay CSV loading until dashboards, if you like
    st.session_state["db_initialised"] = True

st.title("Multi-Domain Intelligence Platform")
st.write(
    "Welcome! This app provides dashboards for Cybersecurity, "
    "Data Science, and IT Operations."
)

st.markdown("### Start here")

if st.button("Go to Login Page"):
    st.switch_page("pages/1_Login.py")
