# pages/4_Data_Science.py

import streamlit as st
import pandas as pd
import altair as alt
import sqlite3
import time

from app.data.db import get_connection

# Page setup for Streamlit
st.set_page_config(
    page_title="Data Science Dashboard",
    layout="wide",
)

# Custom CSS to style multiselect chips to match the design used in other pages
st.markdown(
    """
    <style>
    /* Multiselect "chips" style */
    span[data-baseweb="tag"] {
        background-color: rgba(76, 111, 255, 0.14) !important;
        border: 1px solid rgba(76, 111, 255, 0.75) !important;
        color: rgba(226, 232, 255, 1) !important;
        border-radius: 10px !important;
        font-weight: 500 !important;
    }
    span[data-baseweb="tag"] span {
        color: rgba(226, 232, 255, 1) !important;
    }
    span[data-baseweb="tag"] svg {
        fill: rgba(226, 232, 255, 1) !important;
    }

    /* Slight spacing adjustment for a cleaner layout */
    div[data-baseweb="tag"] {
        margin-right: 6px !important;
        margin-bottom: 6px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Track current page in session state
st.session_state["current_page"] = "Data Science"

# Redirect user if not logged in
if not st.session_state.get("logged_in", False):
    st.switch_page("pages/1_Login.py")

# Extra safety check to prevent unauthenticated access
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("You must log in to view this page.")
    st.info("Go to the Login page in the sidebar and sign in first.")
    st.stop()

# Sidebar logout button
with st.sidebar:
    if st.button("Logout", key="logout_button"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.switch_page("pages/1_Login.py")


@st.cache_data
def load_metadata():
    # Load dataset metadata from the database, fallback to CSV if needed
    try:
        with get_connection() as conn:
            df = pd.read_sql_query("SELECT * FROM datasets_metadata", conn)
        if df.empty:
            df = pd.read_csv("DATA/datasets_metadata.csv")
    except Exception:
        df = pd.read_csv("DATA/datasets_metadata.csv")

    # Convert upload_date to datetime
    df["upload_date"] = pd.to_datetime(df["upload_date"], errors="coerce")

    # Ensure numeric columns are actually numeric
    for col in ["rows", "columns", "dataset_id"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Clean up text-based columns
    for col in ["name", "uploaded_by"]:
        if col in df.columns:
            df[col] = df[col].astype(str).fillna("").str.strip()

    return df


def db_execute(query: str, params: tuple = (), retries: int = 6, sleep_s: float = 0.35):
    # Helper function to safely execute database write queries
    last_err = None
    for _ in range(retries):
        try:
            with get_connection() as conn:
                try:
                    # Improve concurrency handling
                    conn.execute("PRAGMA journal_mode=WAL;")
                    conn.execute("PRAGMA busy_timeout = 3000;")
                except Exception:
                    pass
                conn.execute(query, params)
                conn.commit()
            return True, None
        except sqlite3.OperationalError as e:
            last_err = str(e)
            # Retry if the database is locked or busy
            if "locked" in last_err.lower() or "busy" in last_err.lower():
                time.sleep(sleep_s)
                continue
            return False, last_err
        except Exception as e:
            return False, str(e)
    return False, last_err or "Database is locked/busy. Try again."


def set_flash(scope: str, level: str, message: str):
    # Store flash messages in session state
    st.session_state["flash_msg"] = {
        "scope": scope,
        "level": level,
        "message": message,
    }


def show_flash(scope: str):
    # Display flash messages for a specific CRUD action
    msg = st.session_state.get("flash_msg")
    if not msg:
        return

    if msg.get("scope") != scope:
        return

    level = msg.get("level", "info")
    text = msg.get("message", "")

    if level == "success":
        st.success(text)
    elif level == "error":
        st.error(text)
    elif level == "warning":
        st.warning(text)
    else:
        st.info(text)

    # Clear message after showing
    st.session_state["flash_msg"] = None


# Load dataset metadata
df = load_metadata()

# Stop page if no data is available
if df.empty:
    st.error("No dataset metadata found in the database or CSV.")
    st.stop()

# Page title
st.title("Data Science Dashboard")

# Display logged-in user info
username = st.session_state.get("username", "Unknown")
role = st.session_state.get("role", "user")

st.info(f"Logged in as: {username} ({role})")

# Button to navigate to AI Assistant
AI_ASSISTANT_PAGE = "pages/6_AI_Assistant.py"
c_btn1, c_btn2, c_btn3 = st.columns([3, 2, 3])
with c_btn2:
    if st.button("Go to AI Assistant", use_container_width=True, key="go_ai_assistant"):
        st.switch_page(AI_ASSISTANT_PAGE)

st.markdown("---")

# Page description
st.write(
    "This page analyses dataset metadata such as size, upload activity, "
    "contributors and how fresh each dataset is."
)

st.markdown("---")

# High-level dataset metrics
total_datasets = len(df)

largest_rows = int(df["rows"].max()) if df["rows"].notna().any() else 0
largest_dataset = df.loc[df["rows"].idxmax(), "name"] if df["rows"].notna().any() else "N/A"

if df["upload_date"].notna().any():
    newest_idx = df["upload_date"].idxmax()
    newest_dataset = df.loc[newest_idx, "name"]
    newest_date = df.loc[newest_idx, "upload_date"].date()
else:
    newest_dataset = "N/A"
    newest_date = "N/A"

uploader_counts = df["uploaded_by"].value_counts()
top_contributor = uploader_counts.index[0] if not uploader_counts.empty else "N/A"
top_contrib_count = int(uploader_counts.iloc[0]) if not uploader_counts.empty else 0

# Display metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total datasets", total_datasets)
col2.metric("Largest dataset (rows)", f"{largest_rows:,}", largest_dataset)
col3.metric("Most active uploader", top_contributor, f"{top_contrib_count} datasets")
col4.metric("Newest dataset", newest_dataset, str(newest_date))

st.markdown("---")

# Filtering section
st.subheader("Filters")
st.caption("Use the filters below to update the metrics and charts (not the database itself).")

with st.expander("Filter datasets", expanded=True):
    vis_df = df.copy()

    uploader_list = sorted([x for x in vis_df["uploaded_by"].dropna().unique().tolist() if str(x).strip() != ""])
    name_list = sorted([x for x in vis_df["name"].dropna().unique().tolist() if str(x).strip() != ""])

    min_u = vis_df["upload_date"].min()
    max_u = vis_df["upload_date"].max()

    c1, c2, c3 = st.columns([2, 2, 2])

    with c1:
        sel_uploaders = st.multiselect(
            "Uploaded by",
            options=uploader_list,
            default=uploader_list,
            key="ds_vis_uploader"
        )

    with c2:
        sel_names = st.multiselect(
            "Dataset name",
            options=name_list,
            default=name_list,
            key="ds_vis_names"
        )

    with c3:
        date_rng = None
        if pd.isna(min_u) or pd.isna(max_u):
            st.info("No valid upload dates found for date filtering.")
        else:
            date_rng = st.date_input(
                "Upload date range",
                value=(min_u.date(), max_u.date()),
                key="ds_vis_dates"
            )

# Apply selected filters
if sel_uploaders:
    vis_df = vis_df[vis_df["uploaded_by"].isin(sel_uploaders)]
if sel_names:
    vis_df = vis_df[vis_df["name"].isin(sel_names)]
if date_rng and isinstance(date_rng, (tuple, list)) and len(date_rng) == 2:
    start_d, end_d = date_rng
    vis_df = vis_df[
        (vis_df["upload_date"].dt.date >= start_d) &
        (vis_df["upload_date"].dt.date <= end_d)
    ]

# Remove rows with missing size info
vis_df = vis_df.dropna(subset=["rows", "columns"])

if vis_df.empty:
    st.warning("No rows match your filters. Adjust the filters to see charts.")
    st.stop()

st.markdown("---")

# Dataset size chart
st.subheader("Dataset Size Overview")
st.write("Datasets ordered by number of rows:")

top_n = st.slider(
    "Number of largest datasets to display",
    min_value=3,
    max_value=min(25, len(vis_df)),
    value=min(10, len(vis_df)),
    key="ds_top_n"
)

size_vis = (
    vis_df[["name", "rows"]]
    .sort_values("rows", ascending=False)
    .head(top_n)
)

size_chart = (
    alt.Chart(size_vis)
    .mark_bar()
    .encode(
        y=alt.Y("name:N", sort="-x", title="Dataset"),
        x=alt.X("rows:Q", title="Rows"),
        tooltip=[
            alt.Tooltip("name:N", title="Dataset"),
            alt.Tooltip("rows:Q", title="Rows", format=",")
        ],
    )
    .properties(height=40 * len(size_vis) + 80)
)

st.altair_chart(size_chart, use_container_width=True)

if not size_vis.empty:
    st.info(
        f"Largest dataset in this view: {size_vis.iloc[0]['name']} with {int(size_vis.iloc[0]['rows']):,} rows."
    )

st.markdown("---")

# Dataset complexity chart
st.subheader("Dataset Complexity (Columns per Dataset)")

st.write(
    "This compares how many columns each dataset has (more columns usually means more features). "
    "Colour shows who uploaded the dataset."
)

bar_df = (
    vis_df[["name", "columns", "rows", "uploaded_by", "upload_date"]]
    .dropna(subset=["name", "columns"])
    .sort_values("columns", ascending=False)
)

complex_bar = (
    alt.Chart(bar_df)
    .mark_bar()
    .encode(
        x=alt.X("name:N", sort="-y", title="Dataset"),
        y=alt.Y("columns:Q", title="Number of columns"),
        color=alt.Color("uploaded_by:N", title="Uploaded by"),
        tooltip=[
            alt.Tooltip("name:N", title="Dataset"),
            alt.Tooltip("columns:Q", title="Columns"),
            alt.Tooltip("rows:Q", title="Rows", format=","),
            alt.Tooltip("uploaded_by:N", title="Uploaded by"),
            alt.Tooltip("upload_date:T", title="Upload date"),
        ],
    )
    .properties(height=420)
)

st.altair_chart(complex_bar, use_container_width=True)

st.markdown("---")

# Contributor analysis
st.subheader("Contributor Breakdown")

contrib = (
    vis_df.groupby("uploaded_by")
    .size()
    .reset_index(name="datasets")
    .sort_values("datasets", ascending=False)
)

contrib["percent"] = (contrib["datasets"] / contrib["datasets"].sum()) * 100

contrib_chart = (
    alt.Chart(contrib)
    .mark_bar()
    .encode(
        y=alt.Y("uploaded_by:N", sort="-x", title="Uploader"),
        x=alt.X("datasets:Q", title="Datasets uploaded"),
        tooltip=[
            alt.Tooltip("uploaded_by:N", title="Uploader"),
            alt.Tooltip("datasets:Q", title="Datasets"),
            alt.Tooltip("percent:Q", title="Percent", format=".1f"),
        ],
    )
    .properties(height=220)
)

st.altair_chart(contrib_chart, use_container_width=True)

if not contrib.empty:
    st.info(
        f"Top contributor in this view: {contrib.iloc[0]['uploaded_by']} "
        f"with {int(contrib.iloc[0]['datasets'])} datasets ({float(contrib.iloc[0]['percent']):.1f}%)."
    )

st.markdown("---")

# CRUD section for dataset metadata
st.subheader("Dataset Metadata (CRUD)")

tab_create, tab_update, tab_delete, tab_view = st.tabs(["Create", "Update", "Delete", "View Table"])

# CREATE tab
with tab_create:
    show_flash("create")
    st.caption("Add a new dataset record into the database (datasets_metadata).")

    current_ids = df["dataset_id"].dropna().astype(int).tolist() if "dataset_id" in df.columns else []
    next_id = (max(current_ids) + 1) if current_ids else 1

    create_status = st.empty()

    with st.form("ds_create_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            dataset_id = st.number_input("Dataset ID", min_value=1, value=int(next_id), step=1)
            name = st.text_input("Dataset name")
            uploaded_by = st.text_input("Uploaded by (username)")
        with c2:
            rows_val = st.number_input("Rows", min_value=0, value=0, step=1)
            cols_val = st.number_input("Columns", min_value=0, value=0, step=1)
            upload_date = st.date_input("Upload date")

        submitted = st.form_submit_button("Create dataset")

    if submitted:
        create_status.info("Saving dataset...")
        if not str(name).strip():
            create_status.empty()
            st.error("Dataset name cannot be empty.")
        elif not str(uploaded_by).strip():
            create_status.empty()
            st.error("Uploaded by cannot be empty.")
        else:
            ok, err = db_execute(
                """
                INSERT INTO datasets_metadata (dataset_id, name, rows, columns, uploaded_by, upload_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    int(dataset_id),
                    str(name).strip(),
                    int(rows_val),
                    int(cols_val),
                    str(uploaded_by).strip(),
                    str(upload_date),
                )
            )
            create_status.empty()
            if ok:
                load_metadata.clear()
                set_flash("create", "success", "Dataset created successfully.")
                st.rerun()
            else:
                st.error(f"Create failed: {err}")

# UPDATE tab
with tab_update:
    show_flash("update")
    st.caption("Edit an existing dataset record.")

    update_status = st.empty()

    latest_df = load_metadata().copy()
    latest_df = latest_df.dropna(subset=["dataset_id"]).copy()
    latest_df["dataset_id"] = latest_df["dataset_id"].astype(int)

    if latest_df.empty:
        st.info("No datasets found to update.")
    else:
        options = latest_df.apply(lambda r: f"{int(r['dataset_id'])} — {r['name']}", axis=1).tolist()
        choice = st.selectbox("Select a dataset to update", options=options, key="ds_update_choice")

        chosen_id = int(choice.split("—")[0].strip())
        row = latest_df[latest_df["dataset_id"] == chosen_id].iloc[0]

        with st.form("ds_update_form", clear_on_submit=False):
            c1, c2 = st.columns(2)
            with c1:
                new_name = st.text_input("Dataset name", value=str(row["name"]))
                new_uploaded_by = st.text_input("Uploaded by", value=str(row["uploaded_by"]))
            with c2:
                new_rows = st.number_input(
                    "Rows",
                    min_value=0,
                    value=int(row["rows"]) if pd.notna(row["rows"]) else 0,
                    step=1
                )
                new_cols = st.number_input(
                    "Columns",
                    min_value=0,
                    value=int(row["columns"]) if pd.notna(row["columns"]) else 0,
                    step=1
                )

                current_date = pd.to_datetime(row["upload_date"], errors="coerce")
                date_default = current_date.date() if pd.notna(current_date) else pd.Timestamp.today().date()
                new_date = st.date_input("Upload date", value=date_default)

            updated = st.form_submit_button("Update dataset")

        if updated:
            update_status.info("Saving changes...")
            if not str(new_name).strip():
                update_status.empty()
                st.error("Dataset name cannot be empty.")
            elif not str(new_uploaded_by).strip():
                update_status.empty()
                st.error("Uploaded by cannot be empty.")
            else:
                ok, err = db_execute(
                    """
                    UPDATE datasets_metadata
                    SET name = ?, rows = ?, columns = ?, uploaded_by = ?, upload_date = ?
                    WHERE dataset_id = ?
                    """,
                    (
                        str(new_name).strip(),
                        int(new_rows),
                        int(new_cols),
                        str(new_uploaded_by).strip(),
                        str(new_date),
                        int(chosen_id),
                    )
                )
                update_status.empty()
                if ok:
                    load_metadata.clear()
                    set_flash("update", "success", "Dataset updated successfully.")
                    st.rerun()
                else:
                    st.error(f"Update failed: {err}")

# DELETE tab
with tab_delete:
    show_flash("delete")
    st.caption("Delete a dataset record (admins only).")

    delete_status = st.empty()

    if st.session_state.get("role") != "admin":
        st.warning("Only administrators can delete datasets.")
    else:
        latest_df = load_metadata().copy()
        latest_df = latest_df.dropna(subset=["dataset_id"]).copy()
        latest_df["dataset_id"] = latest_df["dataset_id"].astype(int)

        if latest_df.empty:
            st.info("No datasets found to delete.")
        else:
            options = latest_df.apply(lambda r: f"{int(r['dataset_id'])} — {r['name']}", axis=1).tolist()
            choice = st.selectbox("Select a dataset to delete", options=options, key="ds_delete_choice")
            chosen_id = int(choice.split("—")[0].strip())

            confirm = st.checkbox(
                "I understand this will permanently delete the selected dataset.",
                key="ds_delete_confirm"
            )

            if st.button("Delete dataset", disabled=not confirm, key="ds_delete_btn"):
                delete_status.info("Deleting dataset...")
                ok, err = db_execute(
                    "DELETE FROM datasets_metadata WHERE dataset_id = ?",
                    (int(chosen_id),)
                )
                delete_status.empty()
                if ok:
                    load_metadata.clear()
                    set_flash("delete", "success", "Dataset deleted successfully.")
                    st.rerun()
                else:
                    st.error(f"Delete failed: {err}")

# VIEW tab
with tab_view:
    st.caption("View the dataset metadata table (this is the Data Science table).")

    load_metadata.clear()
    latest_df = load_metadata().copy()

    if "dataset_id" in latest_df.columns:
        latest_df = latest_df.sort_values(["dataset_id"], ascending=True)

    st.dataframe(latest_df, use_container_width=True, height=420)
