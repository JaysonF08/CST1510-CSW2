# app.py

import streamlit as st
from app.data import db  # database functions

# page settings
st.set_page_config(
    page_title="Multi-Domain Intelligence Platform",
    layout="wide",
    page_icon="🔒",  # tab icon
)


# Initialise the database once per session
if "db_initialised" not in st.session_state:
    db.create_tables()             # create all required tables
    db.migrate_users_from_file()   # move users.txt data into the DB (if available)
    db.load_domain_csvs()          # load CSV files into DB (cyber, IT, metadata)
    st.session_state["db_initialised"] = True


# Sidebar logout button
# Only show when user is logged in and not on Login page
current_page = st.session_state.get("current_page", "")

if st.session_state.get("logged_in", False) and current_page != "Login":
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.success("You have been logged out.")
        st.switch_page("pages/1_Login.py")


# Landing page
st.title("Multi-Domain Intelligence Platform")

st.write(
    """
This web application brings together three main domains:

- Cybersecurity: incident trends, phishing analysis, backlog issues  
- IT Operations: ticket priorities, resolution times, team workload  
- Data Science: dataset analysis, contributors, dataset size and freshness  
- User Analytics: user roles and account insights  

Use the sidebar on the left to navigate between different dashboards.
"""
)