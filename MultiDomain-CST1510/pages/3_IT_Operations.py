# pages/3_IT_Operations.py

import streamlit as st
import pandas as pd
from datetime import date

from app.data.db import get_connection

# PAGE CONFIG (must be first Streamlit call)
# Sets the page name/layout and also helps Streamlit load it properly
st.set_page_config(page_title="IT Operations Dashboard", layout="wide")
st.session_state["current_page"] = "IT Operations"

# ACCESS CONTROL
# If the user is not logged in, send them back to the login page
if not st.session_state.get("logged_in", False):
    st.switch_page("pages/1_Login.py")

# Pull user info from session state (role is used to check admin permissions)
username = st.session_state.get("username", "Unknown")
role = (st.session_state.get("role") or "analyst").lower()
is_admin = role == "admin"

# SIDEBAR
# Logout clears session state and sends the user back to login
with st.sidebar:
    if st.button("Logout", key="logout_button_itops"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.session_state["role"] = None
        st.switch_page("pages/1_Login.py")

# CUSTOM STYLES (match Cyber look)
# CSS to make the multiselect filters look consistent with the Cybersecurity page
st.markdown(
    """
<style>
/* MULTISELECT CHIP COLOR (FORCE BLUE) */
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
  background-color: rgba(90, 120, 255, 0.18) !important;
  border: 1px solid rgba(90, 120, 255, 0.55) !important;
  color: #dfe7ff !important;
  border-radius: 8px !important;
}
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] * { color: #dfe7ff !important; }
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] svg { fill: #dfe7ff !important; }

/* REMOVE DARK CORNER SHADE AROUND MULTISELECT */
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
# Title and a small logged-in message so it's clear who is using the dashboard
st.title("IT Operations Dashboard")
st.info(f"Logged in as: **{username} ({role})**")

# Quick button to jump to the AI Assistant page
btn_left, btn_mid, btn_right = st.columns([2, 3, 2])
with btn_mid:
    if st.button("Go to AI Assistant", use_container_width=True, key="btn_go_ai_itops"):
        st.switch_page("pages/6_AI_Assistant.py")

st.markdown("---")

# DB HELPERS
# These functions keep all database CRUD queries in one place so the UI code stays cleaner
def get_all_tickets_db() -> pd.DataFrame:
    # Gets all tickets from the database ordered by newest first
    with get_connection() as conn:
        return pd.read_sql("SELECT * FROM it_tickets ORDER BY created_at DESC", conn)

def create_ticket_db(
    ticket_id: int,
    created_at: str,
    priority: str,
    status: str,
    assigned_to: str,
    description: str,
    resolution_time_hours: float,
) -> bool:
    # Inserts a new ticket into the it_tickets table
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO it_tickets
                (ticket_id, priority, description, status, assigned_to, created_at, resolution_time_hours)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (ticket_id, priority, description, status, assigned_to, created_at, resolution_time_hours),
            )
            conn.commit()
        return True
    except Exception:
        # If insert fails (like duplicate ID), return False so the UI can show an error
        return False

def update_ticket_db(ticket_id: int, **fields) -> bool:
    # Updates a ticket, but only allows certain fields (so random keys can't break the SQL)
    allowed = {"priority", "description", "status", "assigned_to", "created_at", "resolution_time_hours"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        return False

    # Build the SET part dynamically depending on what the user changed
    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    params = list(fields.values()) + [ticket_id]

    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"UPDATE it_tickets SET {set_clause} WHERE ticket_id = ?", params)
            conn.commit()
        return True
    except Exception:
        return False

def delete_ticket_db(ticket_id: int) -> bool:
    # Deletes a ticket from the database using ticket_id
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM it_tickets WHERE ticket_id = ?", (ticket_id,))
            conn.commit()
        return True
    except Exception:
        return False

def delete_ticket_anywhere(ticket_id: int) -> bool:
    # Tries to delete from DB first, and if that fails it tries to remove it from the CSV as backup
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM it_tickets WHERE ticket_id = ?", (ticket_id,))
            conn.commit()
            if cur.rowcount and cur.rowcount > 0:
                return True
    except Exception:
        pass

    try:
        # Fallback delete from the CSV file (only used if DB deletion didn't work)
        df_csv = pd.read_csv("DATA/it_tickets.csv")
        df_csv["ticket_id"] = pd.to_numeric(df_csv["ticket_id"], errors="coerce")
        before = len(df_csv)
        df_csv = df_csv[df_csv["ticket_id"] != ticket_id]
        after = len(df_csv)

        if after < before:
            df_csv.to_csv("DATA/it_tickets.csv", index=False)
            return True

        return False
    except Exception:
        return False

# DATA NORMALISATION + MERGE (CSV + DB)
# This part makes sure the data is in a consistent format, then merges CSV + DB into one dataset
def normalize_ticket_df(df_any: pd.DataFrame) -> pd.DataFrame:
    # If no data, return an empty dataframe with the columns we expect
    if df_any is None or df_any.empty:
        return pd.DataFrame(
            columns=[
                "ticket_id",
                "priority",
                "description",
                "status",
                "assigned_to",
                "created_at",
                "resolution_time_hours",
            ]
        )

    df_any = df_any.copy()
    # Ensure all required columns exist (so the rest of the code doesn't crash)
    for col in ["ticket_id", "priority", "description", "status", "assigned_to", "created_at", "resolution_time_hours"]:
        if col not in df_any.columns:
            df_any[col] = None

    # Force ticket_id to be numeric and clean out invalid rows
    df_any["ticket_id"] = pd.to_numeric(df_any["ticket_id"], errors="coerce")
    df_any = df_any.dropna(subset=["ticket_id"])
    df_any["ticket_id"] = df_any["ticket_id"].astype(int)

    # Convert created_at to datetime (and drop rows with invalid dates)
    df_any["created_at"] = pd.to_datetime(df_any["created_at"], errors="coerce")
    df_any = df_any.dropna(subset=["created_at"])

    # Ensure resolution time is numeric (default 0 if missing)
    df_any["resolution_time_hours"] = pd.to_numeric(df_any["resolution_time_hours"], errors="coerce").fillna(0.0)

    # Clean up text fields so filtering/grouping works properly
    for col in ["priority", "description", "status", "assigned_to"]:
        df_any[col] = df_any[col].astype(str).fillna("").str.strip()

    return df_any

@st.cache_data(show_spinner=False)
def load_csv_tickets(path: str) -> pd.DataFrame:
    # Loads the CSV and normalises it so it matches the DB format
    try:
        return normalize_ticket_df(pd.read_csv(path))
    except Exception:
        return normalize_ticket_df(pd.DataFrame())

def build_full_dataset() -> pd.DataFrame:
    # Combine CSV + DB into one dataset (DB updates overwrite CSV where IDs match)
    df_csv = load_csv_tickets("DATA/it_tickets.csv")

    try:
        df_db = normalize_ticket_df(get_all_tickets_db())
    except Exception:
        df_db = normalize_ticket_df(pd.DataFrame())

    # If both are empty, just return an empty normalised df
    if df_csv.empty and df_db.empty:
        return normalize_ticket_df(pd.DataFrame())

    if df_csv.empty:
        df_full = df_db.copy()
    elif df_db.empty:
        df_full = df_csv.copy()
    else:
        # Use ticket_id as index so we can update matching records easily
        csv_idx = df_csv.set_index("ticket_id")
        db_idx = df_db.set_index("ticket_id")

        # DB version overwrites CSV version for matching ticket_ids
        csv_idx.update(db_idx)

        # Add DB-only rows that don't exist in CSV
        combined = pd.concat([csv_idx, db_idx[~db_idx.index.isin(csv_idx.index)]], axis=0)
        df_full = combined.reset_index()

    # Sort newest first for display
    df_full = df_full.sort_values("created_at", ascending=False).reset_index(drop=True)
    return df_full

def refresh_everything():
    # Clears Streamlit cache so new CRUD changes show up instantly
    st.cache_data.clear()

# Build the full dataset used for filters, charts, and CRUD
df_full = build_full_dataset()
if df_full.empty:
    st.error("No ticket data found (CSV and database are both empty).")
    st.stop()

# Get unique values for filters (fallback lists are used if dataset is missing values)
priorities_all = sorted([p for p in df_full["priority"].dropna().unique().tolist() if p]) or ["Low", "Medium", "High", "Critical"]
statuses_all = sorted([s for s in df_full["status"].dropna().unique().tolist() if s]) or ["Open", "In Progress", "Resolved", "Closed", "Waiting for User"]
agents_all = sorted([a for a in df_full["assigned_to"].dropna().unique().tolist() if a]) or ["IT_Support_A", "IT_Support_B", "IT_Support_C"]

# FILTERS + ANALYTICS (never blocks CRUD)
# Filters only affect charts/metrics, they do not delete/edit anything
st.subheader("Filters")
st.caption("Use the filters below to update the metrics and charts.")

with st.expander("Filter tickets", expanded=True):
    c1, c2, c3 = st.columns(3)

    sel_priority = c1.multiselect("Priority", priorities_all, default=priorities_all, key="flt_it_pri")
    sel_status = c2.multiselect("Status", statuses_all, default=statuses_all, key="flt_it_status")
    sel_agent = c3.multiselect("Assigned to", agents_all, default=agents_all, key="flt_it_agent")

    # Date range filter uses the created_at field
    min_date = df_full["created_at"].dt.date.min() or date.today()
    max_date = df_full["created_at"].dt.date.max() or date.today()
    date_range = st.date_input("Created date range", (min_date, max_date), key="flt_it_dates")

# Apply all filters to build the dataset used by charts/metrics
filtered_df = df_full[
    df_full["priority"].isin(sel_priority)
    & df_full["status"].isin(sel_status)
    & df_full["assigned_to"].isin(sel_agent)
    & (df_full["created_at"].dt.date >= date_range[0])
    & (df_full["created_at"].dt.date <= date_range[1])
].copy()

st.markdown("---")

# If filtered_df is empty, hide charts/metrics but still allow CRUD below
if filtered_df.empty:
    st.warning("No tickets match the selected filters. Charts/metrics are hidden, but CRUD still works.")
else:
    st.subheader("Key Ticket Metrics")

    # Basic dashboard numbers
    total_tickets = len(filtered_df)
    open_statuses = ["open", "in progress", "new", "waiting for user"]
    open_tickets = filtered_df[filtered_df["status"].astype(str).str.lower().isin(open_statuses)].shape[0]

    # Only use resolved/closed tickets for resolution time calculation
    resolved_df = filtered_df[filtered_df["status"].astype(str).str.lower().isin(["resolved", "closed"])].copy()
    avg_resolution = float(resolved_df["resolution_time_hours"].mean()) if not resolved_df.empty else 0.0

    # Most active agent in the filtered dataset
    top_agent = filtered_df["assigned_to"].value_counts().idxmax() if not filtered_df.empty else "N/A"

    # Show metrics in a 4-column layout
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total tickets", total_tickets)
    k2.metric("Open tickets", open_tickets)
    k3.metric("Avg. resolution time (hrs)", f"{avg_resolution:.1f}")
    k4.metric("Busiest support agent", top_agent)

    st.markdown("---")

    # Status bar chart (counts per status)
    st.subheader("Ticket status overview")
    st.bar_chart(filtered_df["status"].value_counts().to_frame("Ticket Count"))

    st.markdown("---")

    # Priority bar chart (counts per priority)
    st.subheader("Priority distribution")
    st.bar_chart(filtered_df["priority"].value_counts().to_frame("Ticket Count"))

    st.markdown("---")

    # Average resolution time grouped by priority (only for resolved tickets)
    st.subheader("Average resolution time by priority")
    if not resolved_df.empty:
        by_p = resolved_df.groupby("priority")["resolution_time_hours"].mean().to_frame("Avg Resolution Time (hrs)")
        by_p = by_p.sort_values("Avg Resolution Time (hrs)", ascending=False)
        st.bar_chart(by_p)
        st.info(f"Slowest to resolve: {by_p.index[0]} (avg {float(by_p.iloc[0,0]):.1f} hours).")
    else:
        st.info("No resolved tickets in the filtered data to analyse resolution time.")

    st.markdown("---")

    # Active tickets by agent (to help spot workload bottlenecks)
    st.subheader("Active tickets by support agent")
    active_statuses = ["open", "in progress", "waiting for user"]
    active = filtered_df[filtered_df["status"].astype(str).str.lower().isin(active_statuses)]
    if active.empty:
        st.info("There are no active tickets for any agent in the filtered data.")
    else:
        by_agent = active.groupby("assigned_to")["ticket_id"].count().to_frame("Active Tickets").sort_values("Active Tickets", ascending=False)
        st.bar_chart(by_agent)
        st.warning(f"Potential bottleneck: {by_agent.index[0]} has {int(by_agent.iloc[0,0])} active tickets.")

st.markdown("---")

# CRUD (Cyber-style, stable selection, messages persist)
# This section lets the user manage tickets (create/update/delete) without leaving the page
st.header("Ticket management (CRUD)")
st.caption("Create, update, delete, and review IT tickets stored in the database.")

# Store which CRUD tab is selected so it doesn't jump around on rerun
if "it_crud_tab" not in st.session_state:
    st.session_state["it_crud_tab"] = "Create"

# Store messages per tab so the success/error text stays after reruns
if "it_crud_msg" not in st.session_state:
    st.session_state["it_crud_msg"] = {"Create": None, "Update": None, "Delete": None}

def set_msg(tab: str, kind: str, text: str):
    # Save a message for the tab (used after a CRUD action)
    st.session_state["it_crud_msg"][tab] = (kind, text)

def show_msg(tab: str):
    # Display the message for the current tab if one exists
    msg = st.session_state["it_crud_msg"].get(tab)
    if not msg:
        return
    kind, text = msg
    if kind == "success":
        st.success(text)
    elif kind == "error":
        st.error(text)
    else:
        st.warning(text)

def load_db_now() -> pd.DataFrame:
    # Reload tickets directly from the DB (used for update choices)
    try:
        return normalize_ticket_df(get_all_tickets_db())
    except Exception:
        return normalize_ticket_df(pd.DataFrame())

def next_ticket_id(df_any: pd.DataFrame) -> int:
    # Suggest the next ticket ID based on the current max
    try:
        return int(pd.to_numeric(df_any["ticket_id"], errors="coerce").max()) + 1
    except Exception:
        return 1

# Tab selection (radio keeps it clean and simple)
st.session_state["it_crud_tab"] = st.radio(
    "",
    ["Create", "Update", "Delete", "View table"],
    horizontal=True,
    key="it_crud_tab_radio",
)

tab = st.session_state["it_crud_tab"]

if tab == "Create":
    show_msg("Create")
    st.subheader("Create a new ticket")

    # Use both full dataset and DB dataset to generate a safe next ID
    db_now = load_db_now()
    suggested_id = next_ticket_id(pd.concat([df_full, db_now], ignore_index=True))

    with st.form("it_create_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            ticket_id = st.number_input("Ticket ID", min_value=1, value=int(suggested_id), step=1)
        with c2:
            created_date = st.date_input("Created date", value=pd.Timestamp.today().date())

        priority = st.selectbox("Priority", ["Low", "Medium", "High", "Critical"])
        status = st.selectbox("Status", ["Open", "In Progress", "Resolved", "Closed", "Waiting for User"])
        assigned_to = st.selectbox("Assigned to", agents_all)

        resolution_time_hours = st.number_input("Resolution time (hours)", min_value=0.0, value=0.0, step=1.0)
        description = st.text_area("Description")

        submitted = st.form_submit_button("Create ticket")

    if submitted:
        # Require a description so blank tickets don't get created
        if not str(description).strip():
            set_msg("Create", "error", "Please add a short description.")
        else:
            ok = create_ticket_db(
                int(ticket_id),
                pd.Timestamp(created_date).isoformat(),
                str(priority),
                str(status),
                str(assigned_to),
                str(description).strip(),
                float(resolution_time_hours),
            )
            if ok:
                set_msg("Create", "success", f"Ticket created (ID: {int(ticket_id)}).")
                refresh_everything()
                st.rerun()
            else:
                set_msg("Create", "error", "Create failed. Ticket ID might already exist.")

elif tab == "Update":
    show_msg("Update")
    st.subheader("Update an existing ticket")

    db_now = load_db_now()
    if db_now.empty:
        st.info("No tickets available to update (database is empty).")
    else:
        # Build the dropdown using ID + priority + status so it’s easier to identify tickets
        options = db_now["ticket_id"].astype(str) + " - " + db_now["priority"].astype(str) + " - " + db_now["status"].astype(str)
        pick = st.selectbox("Select ticket", options, key="it_update_pick")
        ticket_id = int(pick.split("-")[0].strip())

        row = db_now[db_now["ticket_id"] == ticket_id].iloc[0]

        # Quick view of current values before changing anything
        with st.expander("Current values", expanded=True):
            show_row = row[
                ["ticket_id", "created_at", "priority", "status", "assigned_to", "resolution_time_hours", "description"]
            ].to_frame("Value")
            show_row.index = ["Ticket ID", "Created At", "Priority", "Status", "Assigned To", "Resolution Time (hrs)", "Description"]
            st.dataframe(show_row, use_container_width=True)

        # Using “(no change)” makes it easy to update only what you want
        new_priority = st.selectbox("Priority", ["(no change)", "Low", "Medium", "High", "Critical"])
        new_status = st.selectbox("Status", ["(no change)", "Open", "In Progress", "Resolved", "Closed", "Waiting for User"])
        new_assigned = st.selectbox("Assigned to", ["(no change)"] + agents_all)

        new_res_time = st.text_input("Resolution time (hours) (optional)", placeholder="Only type if you want to overwrite.")
        new_desc = st.text_area("Description (optional)", placeholder="Only type if you want to overwrite the description.")

        if st.button("Update ticket"):
            kwargs = {}

            # Only add fields if the user picked a new value
            if new_priority != "(no change)":
                kwargs["priority"] = new_priority
            if new_status != "(no change)":
                kwargs["status"] = new_status
            if new_assigned != "(no change)":
                kwargs["assigned_to"] = new_assigned
            if str(new_desc).strip():
                kwargs["description"] = str(new_desc).strip()
            if str(new_res_time).strip():
                try:
                    kwargs["resolution_time_hours"] = float(str(new_res_time).strip())
                except ValueError:
                    set_msg("Update", "error", "Resolution time must be a number.")
                    kwargs = None

            if kwargs is None:
                pass
            elif not kwargs:
                set_msg("Update", "warning", "No changes selected.")
            else:
                ok = update_ticket_db(ticket_id, **kwargs)
                if ok:
                    set_msg("Update", "success", f"Ticket updated (ID: {ticket_id}).")
                    refresh_everything()
                    st.rerun()
                else:
                    set_msg("Update", "error", "Update failed. Check DB schema.")

elif tab == "Delete":
    # Delete is restricted to admins only
    if not is_admin:
        st.warning("Only admin users can delete tickets.")
    else:
        show_msg("Delete")
        st.subheader("Delete a ticket")

        # Uses the combined dataset so tickets are visible even if they came from CSV originally
        del_source = df_full.copy()
        if del_source.empty:
            st.info("No tickets available to delete.")
        else:
            options = (
                del_source["ticket_id"].astype(str)
                + " - " + del_source["priority"].astype(str)
                + " - " + del_source["status"].astype(str)
            )
            pick = st.selectbox("Select ticket to delete", options, key="it_delete_pick")
            ticket_id = int(pick.split("-")[0].strip())

            # Confirmation so users don't delete by accident
            st.warning(f"You are about to permanently delete ticket {ticket_id}.")
            confirm = st.checkbox("Yes, delete this ticket.")

            if st.button("Delete ticket", disabled=not confirm):
                ok = delete_ticket_anywhere(ticket_id)
                if ok:
                    set_msg("Delete", "success", f"Ticket deleted (ID: {ticket_id}).")
                    refresh_everything()
                    st.rerun()
                else:
                    set_msg("Delete", "error", "Delete failed. Ticket not found or file is locked.")

else:
    # Simple view mode for the full merged dataset (CSV + DB)
    st.subheader("IT tickets (full dataset)")
    st.dataframe(df_full, use_container_width=True, height=520)