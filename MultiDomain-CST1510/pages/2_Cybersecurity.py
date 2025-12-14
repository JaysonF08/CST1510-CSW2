# pages/2_Cybersecurity.py

import streamlit as st
import pandas as pd
import plotly.express as px

from app.data.db import (
    get_connection,
    get_all_cyber_incidents,
    create_cyber_incident,
    update_cyber_incident,
    delete_cyber_incident,
)


# PAGE CONFIG

st.set_page_config(page_title="Cybersecurity Dashboard", layout="wide")
st.session_state["current_page"] = "Cybersecurity"


# ACCESS CONTROL

if not st.session_state.get("logged_in", False):
    st.warning("Please log in to access the Cybersecurity dashboard.")
    st.switch_page("pages/1_Login.py")


# SIDEBAR

with st.sidebar:
    st.write(f"User: {st.session_state.get('username')} ({st.session_state.get('role')})")
    if st.button("Logout", key="logout_button_cyber"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.session_state["role"] = None
        st.switch_page("pages/1_Login.py")


# CUSTOM STYLES (force chip color + remove dark corners)

st.markdown(
    """
<style>
/* ---------- MULTISELECT CHIP COLOR (FORCE BLUE) ---------- */
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
  background-color: rgba(90, 120, 255, 0.18) !important;
  border: 1px solid rgba(90, 120, 255, 0.55) !important;
  color: #dfe7ff !important;
  border-radius: 8px !important;
}
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] * {
  color: #dfe7ff !important;
}
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] svg {
  fill: #dfe7ff !important;
}

/* ---------- REMOVE DARK “CORNER” SHADE AROUND MULTISELECT ---------- */
div[data-testid="stMultiSelect"] div[role="combobox"] {
  background: rgba(90, 120, 255, 0.07) !important;
  border: 1px solid rgba(90, 120, 255, 0.28) !important;
  box-shadow: none !important;
}
div[data-testid="stMultiSelect"] div[role="combobox"]:focus-within {
  border: 1px solid rgba(90, 120, 255, 0.55) !important;
  box-shadow: none !important;
}
div[data-testid="stMultiSelect"] div[role="listbox"] {
  background: rgba(20, 22, 30, 0.98) !important;
  border: 1px solid rgba(90, 120, 255, 0.25) !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# HEADER

st.title("Cybersecurity Dashboard")
st.info(f"Logged in as: **{st.session_state.get('username', 'Unknown')}**")


# BUTTONS (centered)

btn_left, btn_mid, btn_right = st.columns([1, 3, 1])
with btn_mid:
    b1, b2 = st.columns(2)

    if "show_cyber_explain" not in st.session_state:
        st.session_state["show_cyber_explain"] = False

    with b1:
        if st.button("Explain this dashboard", use_container_width=True, key="btn_explain"):
            st.session_state["show_cyber_explain"] = not st.session_state["show_cyber_explain"]

    with b2:
        if st.button("Go to AI Assistant", use_container_width=True, key="btn_go_ai"):
            st.switch_page("pages/6_AI_Assistant.py")


# EXPLANATION (no emojis)

if st.session_state.get("show_cyber_explain", False):
    st.markdown(
        """
## What’s going on in this dashboard?

This page is basically the **control centre** for cyber incidents.

- You can **filter incidents** by severity, category, status, and date.
- The metrics at the top give you a quick snapshot of what’s happening.
- The **category vs severity** chart shows how serious different threats are.
- The trend chart helps spot spikes (months where incidents jump).
- The **bottleneck** section shows which category is slowing things down.
- At the bottom, you can **create, update, delete, or view incidents** directly from the database.

**What to look for:**
- A spike = the month with the most incidents.
- A bottleneck = the category with the most unresolved incidents.
        """
    )

st.markdown("---")


# LOAD DATA

@st.cache_data(show_spinner=False)
def load_incidents():
    # Prefer DB; fallback to CSV
    try:
        with get_connection() as conn:
            df_db = pd.read_sql("SELECT * FROM cyber_incidents", conn)
        if not df_db.empty:
            return df_db
    except Exception:
        pass

    # Fallback
    return pd.read_csv("DATA/cyber_incidents.csv")


df = load_incidents()
if df.empty:
    st.error("No incident data found in the cyber_incidents table or CSV.")
    st.stop()

# Ensure timestamp column exists and is valid
if "timestamp" not in df.columns:
    st.error("Your data needs a 'timestamp' column.")
    st.stop()

df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
df = df.dropna(subset=["timestamp"])

st.markdown("---")


# FILTERS

st.subheader("Filters")
st.caption("Use the filters below to update the metrics and charts.")

with st.expander("Filter incidents", expanded=True):
    c1, c2, c3 = st.columns(3)

    severities = sorted(df["severity"].dropna().unique()) if "severity" in df.columns else []
    categories = sorted(df["category"].dropna().unique()) if "category" in df.columns else []
    statuses = sorted(df["status"].dropna().unique()) if "status" in df.columns else []

    selected_sev = c1.multiselect("Severity", severities, default=severities, key="flt_sev")
    selected_cat = c2.multiselect("Category", categories, default=categories, key="flt_cat")
    selected_status = c3.multiselect("Status", statuses, default=statuses, key="flt_status")

    min_d = df["timestamp"].dt.date.min()
    max_d = df["timestamp"].dt.date.max()
    date_range = st.date_input("Date range", (min_d, max_d), key="flt_dates")

# Filter safely (only apply if columns exist)
filtered_df = df.copy()
if "severity" in filtered_df.columns and selected_sev:
    filtered_df = filtered_df[filtered_df["severity"].isin(selected_sev)]
if "category" in filtered_df.columns and selected_cat:
    filtered_df = filtered_df[filtered_df["category"].isin(selected_cat)]
if "status" in filtered_df.columns and selected_status:
    filtered_df = filtered_df[filtered_df["status"].isin(selected_status)]

filtered_df = filtered_df[
    (filtered_df["timestamp"].dt.date >= date_range[0])
    & (filtered_df["timestamp"].dt.date <= date_range[1])
].copy()

if filtered_df.empty:
    st.warning("No incidents match the selected filters.")
    st.stop()

st.markdown("---")


# KPI METRICS

st.subheader("Key incident metrics")

unresolved_statuses = ["open", "in progress", "investigating", "new"]

total_incidents = len(filtered_df)
unresolved_count = (
    filtered_df[filtered_df["status"].astype(str).str.lower().isin(unresolved_statuses)].shape[0]
    if "status" in filtered_df.columns
    else 0
)
high_crit_count = (
    filtered_df[filtered_df["severity"].astype(str).str.lower().isin(["high", "critical"])].shape[0]
    if "severity" in filtered_df.columns
    else 0
)
high_crit_pct = (high_crit_count / total_incidents * 100) if total_incidents else 0
top_category = filtered_df["category"].mode()[0] if "category" in filtered_df.columns and not filtered_df["category"].empty else "N/A"

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total incidents", total_incidents)
k2.metric("Unresolved incidents", unresolved_count)
k3.metric("High/Critical (%)", f"{high_crit_pct:.1f}%")
k4.metric("Most common category", top_category)

st.markdown("---")


# CATEGORY vs SEVERITY

st.subheader("Category vs Severity")

if "category" in filtered_df.columns and "severity" in filtered_df.columns:
    cat_sev_counts = (
        filtered_df.groupby(["category", "severity"])
        .size()
        .reset_index(name="count")
    )

    fig_cat_sev = px.bar(
        cat_sev_counts,
        x="category",
        y="count",
        color="severity",
        barmode="group",
        title="Incident counts by category and severity",
        labels={"category": "Category", "count": "Number of incidents", "severity": "Severity"},
    )
    st.plotly_chart(fig_cat_sev, use_container_width=True)
else:
    st.info("Not enough columns to show Category vs Severity chart.")

st.markdown("---")


# THREAT TREND — Top 3 + Other

st.subheader("Threat trend (spike detection)")

if "category" in filtered_df.columns:
    trend_df = filtered_df.copy()
    trend_df["month"] = trend_df["timestamp"].dt.to_period("M").dt.to_timestamp()

    top_cats = trend_df["category"].value_counts().head(3).index.tolist()
    trend_df["category_grouped"] = trend_df["category"].where(trend_df["category"].isin(top_cats), "Other")

    trend_counts = (
        trend_df.groupby(["month", "category_grouped"])
        .size()
        .reset_index(name="count")
    )

    fig_trend = px.line(
        trend_counts,
        x="month",
        y="count",
        color="category_grouped",
        markers=True,
        title="Monthly incident counts (Top categories + Other)",
        labels={"month": "Month", "count": "Incident count", "category_grouped": "Category"},
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    if not trend_counts.empty:
        peak_row = trend_counts.loc[trend_counts["count"].idxmax()]
        st.info(
            f"Highest spike: **{int(peak_row['count'])}** incident(s) in **{peak_row['month'].strftime('%Y-%m')}** "
            f"(mostly from **{peak_row['category_grouped']}**)."
        )
else:
    st.info("Not enough columns to show the trend chart.")

st.markdown("---")


# BOTTLENECK

st.subheader("Response bottleneck (unresolved backlog)")

if "status" in filtered_df.columns and "category" in filtered_df.columns:
    backlog_df = filtered_df[filtered_df["status"].astype(str).str.lower().isin(unresolved_statuses)].copy()
    if backlog_df.empty:
        st.success("No unresolved incidents right now.")
    else:
        backlog_counts = backlog_df["category"].value_counts()
        st.bar_chart(backlog_counts)
        st.warning(f"Bottleneck: **{backlog_counts.idxmax()}** ({int(backlog_counts.max())} unresolved incidents)")
else:
    st.info("Not enough columns to calculate bottlenecks.")

st.markdown("---")


# CRUD

st.header("Incident management (CRUD)")
st.caption("Create, update, delete, and review cyber incidents stored in the database.")

tabs = st.tabs(["Create", "Update", "Delete", "View table"])

# Helper (so delete/table refresh immediately)
def refresh_everything():
    st.cache_data.clear()

# CREATE
with tabs[0]:
    st.subheader("Create a new incident")

    with st.form("create_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            d = st.date_input("Date", value=pd.Timestamp.today().date(), key="create_date")
        with c2:
            t = st.time_input("Time", value=pd.Timestamp.now().time(), key="create_time")

        sev = st.selectbox("Severity", ["Low", "Medium", "High", "Critical"], key="create_sev")
        cat = st.selectbox(
            "Category",
            ["Phishing", "Malware", "Misconfiguration", "DDoS", "Unauthorized Access"],
            key="create_cat",
        )
        status = st.selectbox("Status", ["Open", "In Progress", "Resolved", "Closed"], key="create_status")
        desc = st.text_area("Description", key="create_desc")

        submitted = st.form_submit_button("Create incident")

    if submitted:
        if not desc.strip():
            st.error("Please add a short description.")
        else:
            ts = pd.Timestamp.combine(d, t).isoformat()
            new_id = create_cyber_incident(ts, sev, cat, status, desc.strip())
            st.success(f"Incident created (ID: {new_id}).")
            refresh_everything()

# UPDATE (allowed for all users)
with tabs[1]:
    st.subheader("Update an existing incident")

    if st.button("Refresh incidents", key="refresh_update"):
        refresh_everything()

    all_inc = get_all_cyber_incidents(limit=None)
    if all_inc is None or all_inc.empty:
        st.info("No incidents available to update.")
    else:
        options = all_inc["incident_id"].astype(str) + " - " + all_inc["category"].astype(str)
        pick = st.selectbox("Select incident", options, key="upd_pick")

        inc_id = int(pick.split("-")[0].strip())
        row = all_inc[all_inc["incident_id"] == inc_id].iloc[0]

        # Current values as a clean 1-row table (requested change)
        with st.expander("Current values", expanded=False):
            current_df = pd.DataFrame([{
                "Incident ID": int(row["incident_id"]),
                "Timestamp": str(row["timestamp"]),
                "Severity": row["severity"],
                "Category": row["category"],
                "Status": row["status"],
                "Description": row["description"],
            }])
            st.dataframe(current_df, use_container_width=True, hide_index=True)

        new_sev = st.selectbox("Severity", ["(no change)", "Low", "Medium", "High", "Critical"], key="upd_sev")
        new_cat = st.selectbox(
            "Category",
            ["(no change)", "Phishing", "Malware", "Misconfiguration", "DDoS", "Unauthorized Access"],
            key="upd_cat",
        )
        new_status = st.selectbox("Status", ["(no change)", "Open", "In Progress", "Resolved", "Closed"], key="upd_status")
        new_desc = st.text_area(
            "Description (optional)",
            placeholder="Only type if you want to overwrite the description.",
            key="upd_desc",
        )

        if st.button("Update incident", key="upd_btn"):
            kwargs = {}
            if new_sev != "(no change)":
                kwargs["severity"] = new_sev
            if new_cat != "(no change)":
                kwargs["category"] = new_cat
            if new_status != "(no change)":
                kwargs["status"] = new_status
            if new_desc.strip():
                kwargs["description"] = new_desc.strip()

            if not kwargs:
                st.warning("No changes selected.")
            else:
                ok = update_cyber_incident(inc_id, **kwargs)
                if ok:
                    st.success("Incident updated.")
                    refresh_everything()
                else:
                    st.error("Update failed. Check database or logs.")

# DELETE (admin-only)
with tabs[2]:
    st.subheader("Delete an incident")

    if st.button("Refresh incidents", key="refresh_delete"):
        refresh_everything()

    user_role = (st.session_state.get("role") or "").lower()
    if user_role != "admin":
        st.warning("Delete is admin-only.")
    else:
        all_inc = get_all_cyber_incidents(limit=None)
        if all_inc is None or all_inc.empty:
            st.info("No incidents available to delete.")
        else:
            options = all_inc["incident_id"].astype(str) + " - " + all_inc["category"].astype(str)
            pick = st.selectbox("Select incident to delete", options, key="del_pick")

            inc_id = int(pick.split("-")[0].strip())
            st.warning(f"You are about to permanently delete incident {inc_id}.")
            confirm = st.checkbox("Yes, delete this incident.", key="del_confirm")

            if st.button("Delete incident", key="del_btn", disabled=not confirm):
                ok = delete_cyber_incident(inc_id)
                if ok:
                    st.success("Incident deleted.")
                    refresh_everything()
                else:
                    st.error("Delete failed. Check database or logs.")

# VIEW TABLE
with tabs[3]:
    st.subheader("Cyber incidents (database)")

    if st.button("Refresh table", key="refresh_table"):
        refresh_everything()

    table_df = get_all_cyber_incidents(limit=500)
    if table_df is None or table_df.empty:
        st.info("No incidents found in the database yet.")
    else:
        st.dataframe(table_df, use_container_width=True, hide_index=True)
