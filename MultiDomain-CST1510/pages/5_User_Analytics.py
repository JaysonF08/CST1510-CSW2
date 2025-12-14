# pages/5_User_Analytics.py

import streamlit as st
import pandas as pd
from app.data.db import get_connection

# track current page
st.session_state["current_page"] = "User Analytics"

# stop access if user is not logged in
if not st.session_state.get("logged_in", False):
    st.switch_page("pages/1_Login.py")

# sidebar logout button
with st.sidebar:
    if st.button("Logout", key="logout_button"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.switch_page("pages/1_Login.py")

# page settings
st.set_page_config(
    page_title="User Analytics",
    layout="wide",
)

# page title
st.title("User Analytics")

# second login guard
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("You must log in to view this page.")
    st.info("Go to the Login page in the sidebar and sign in first.")
    st.stop()

st.success(f"Welcome, {st.session_state['username']}!")


# LOAD USER DATA
try:
    with get_connection() as conn:
        users_df = pd.read_sql("SELECT id, username, role FROM users", conn)
except Exception:
    st.error("Could not load users from the database.")
    st.stop()

if users_df.empty:
    st.warning("No user records found.")
    st.stop()


# KPI SUMMARY CARDS
st.markdown("### User Metrics")

total_users = len(users_df)
role_counts = users_df["role"].value_counts()

num_admins = role_counts.get("admin", 0)
top_role = role_counts.idxmax() if not role_counts.empty else "N/A"

c1, c2, c3 = st.columns(3)
c1.metric("Total users", total_users)
c2.metric("Number of admins", num_admins)
c3.metric("Most common role", top_role)

st.markdown("---")


# ROLE FILTER + BAR CHART
st.subheader("Users by Role")

roles = sorted(users_df["role"].unique())
sel_roles = st.multiselect("Filter by role", roles, default=roles)

filtered_users = users_df[users_df["role"].isin(sel_roles)]

if filtered_users.empty:
    st.warning("No users match the selected roles.")
    st.stop()

role_counts_filtered = (
    filtered_users["role"]
    .value_counts()
    .to_frame("User Count")
    .sort_values("User Count", ascending=False)
)

st.write("User count per role (bar chart):")
st.bar_chart(role_counts_filtered)

st.markdown("---")


# USER TABLE
st.subheader("User List")

st.dataframe(
    filtered_users[["id", "username", "role"]].sort_values("username"),
    use_container_width=True,
)
