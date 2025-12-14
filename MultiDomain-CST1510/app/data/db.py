# app/data/db.py
"""
Database utilities for CST1510 CW2.

- Creates SQLite database and tables
- Migrates users from Week 7 users.txt
- Loads the 3 domain CSV files into tables
"""

from pathlib import Path
import sqlite3
import pandas as pd

# ---------- Paths ----------

BASE_DIR = Path(__file__).resolve().parents[2]   # project root (Coursework/)
DATA_DIR = BASE_DIR / "DATA"                     # folder that holds CSV and DB
DB_PATH = DATA_DIR / "intelligence.db"           # main SQLite file


def get_connection():
    """Return a new SQLite connection to the project database."""
    # opens a connection to the intelligence.db file
    return sqlite3.connect(DB_PATH)


# ---------- Table creation ----------

def create_tables():
    """Create all required tables if they do not already exist."""
    # use context manager so the connection closes automatically
    with get_connection() as conn:
        cur = conn.cursor()

        # Users table – stores login accounts
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'analyst'
            );
            """
        )

        # Cybersecurity incidents – basic version (not the CSV structure)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS cyber_incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                date TEXT
            );
            """
        )

        # Datasets metadata – basic description of each dataset
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS datasets_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                source TEXT,
                category TEXT,
                size INTEGER
            );
            """
        )

        # IT tickets – simple IT operations ticket table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS it_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                created_date TEXT
            );
            """
        )

        conn.commit()  # save any changes


# ---------- Week 7 → Week 8 migration ----------

def migrate_users_from_file():
    """
    Read users from DATA/users.txt and insert into users table.

    Expected format per line:
        username,hashed_password[,role]

    Bullet-proof handling:
    - Accepts 2 or 3+ columns (role optional)
    - Defaults missing/invalid roles to "analyst"
    - Normalises roles (user -> analyst, uppercase -> lowercase)
    - Skips blank/malformed lines safely
    - Uses INSERT OR IGNORE to avoid duplicates
    """
    users_file = DATA_DIR / "users.txt"
    if not users_file.exists():
        print("[DB] No users.txt found – skipping migration.")
        return

    def normalise_role(raw_role: str) -> str:
        r = (raw_role or "").strip().lower()
        if r in {"admin", "analyst"}:
            return r
        if r in {"user", "users", "viewer"}:
            return "analyst"
        return "analyst"

    with get_connection() as conn:
        cur = conn.cursor()

        with users_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = (line or "").strip()
                if not line:
                    continue

                parts = [p.strip() for p in line.split(",") if p.strip() != ""]

                # Must at least have username + hash
                if len(parts) < 2:
                    print(f"[DB] Skipping malformed line: {line}")
                    continue

                username = parts[0]
                hashed = parts[1]

                # Optional role
                role = normalise_role(parts[2]) if len(parts) >= 3 else "analyst"

                # Basic sanity checks (keeps migration from inserting junk)
                if len(username) < 2:
                    print(f"[DB] Skipping invalid username: {username}")
                    continue

                if not hashed.startswith("$2"):  # bcrypt hashes usually start with $2a/$2b/$2y
                    print(f"[DB] Skipping invalid hash for user {username}")
                    continue

                cur.execute(
                    """
                    INSERT OR IGNORE INTO users (username, password_hash, role)
                    VALUES (?, ?, ?)
                    """,
                    (username, hashed, role),
                )

        conn.commit()

    print("[DB] User migration from users.txt completed.")


# ---------- Load CSVs into domain tables ----------

def load_domain_csvs():
    """
    Load CSV files from DATA/ into the 3 domain tables.
    Uses pandas.to_sql with if_exists='replace' so columns match the CSVs.
    """
    with get_connection() as conn:
        # Cyber incidents
        cyber_csv = DATA_DIR / "cyber_incidents.csv"
        if cyber_csv.exists():
            # read CSV into pandas
            df_cyber = pd.read_csv(cyber_csv)
            # write into cyber_incidents table and replace old data
            df_cyber.to_sql(
                "cyber_incidents", conn, if_exists="replace", index=False
            )
            print("[DB] Loaded cyber_incidents.csv")
        else:
            print("[DB] cyber_incidents.csv not found")

        # Datasets metadata
        datasets_csv = DATA_DIR / "datasets_metadata.csv"
        if datasets_csv.exists():
            df_ds = pd.read_csv(datasets_csv)
            df_ds.to_sql(
                "datasets_metadata", conn, if_exists="replace", index=False
            )
            print("[DB] Loaded datasets_metadata.csv")
        else:
            print("[DB] datasets_metadata.csv not found")

        # IT tickets
        tickets_csv = DATA_DIR / "it_tickets.csv"
        if tickets_csv.exists():
            df_tk = pd.read_csv(tickets_csv)
            df_tk.to_sql(
                "it_tickets", conn, if_exists="replace", index=False
            )
            print("[DB] Loaded it_tickets.csv")
        else:
            print("[DB] it_tickets.csv not found")

        conn.commit()  # commit all table loads


# Optional quick test
if __name__ == "__main__":
    create_tables()
    migrate_users_from_file()
    load_domain_csvs()
    print("[DB] Setup complete.")

# ----------------- CYBER INCIDENTS CRUD HELPERS -----------------


def get_all_cyber_incidents(limit: int | None = 200):
    """
    Return recent cyber incidents as a pandas DataFrame.
    Used by dashboards + CRUD forms.
    """
    # open connection and read from cyber_incidents table
    conn = get_connection()
    query = "SELECT * FROM cyber_incidents ORDER BY timestamp DESC"
    if limit:
        # limit how many rows we read (for performance)
        query += f" LIMIT {int(limit)}"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def _get_next_incident_id() -> int:
    """Internal helper: get next incident_id based on current max."""
    # get all incidents so we can see the current max ID
    df = get_all_cyber_incidents(limit=None)
    if "incident_id" in df.columns and not df["incident_id"].isna().all():
        try:
            # convert to int and add 1 for the next ID
            return int(df["incident_id"].astype(int).max()) + 1
        except Exception:
            pass
    # fallback if the column is missing or weird – start from 1000
    return 1000


def create_cyber_incident(
    timestamp: str,
    severity: str,
    category: str,
    status: str,
    description: str,
) -> int:
    """
    Insert a new cyber incident.
    Returns the incident_id that was created.
    """
    # get the next free incident_id
    new_id = _get_next_incident_id()

    conn = get_connection()
    cur = conn.cursor()
    # insert a brand new row into cyber_incidents
    cur.execute(
        """
        INSERT INTO cyber_incidents
            (incident_id, timestamp, severity, category, status, description)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (new_id, timestamp, severity, category, status, description),
    )
    conn.commit()
    conn.close()
    return new_id  # send the new id back to the caller


def update_cyber_incident(
    incident_id: int,
    severity: str | None = None,
    category: str | None = None,
    status: str | None = None,
    description: str | None = None,
) -> bool:
    """
    Update selected fields for a given incident_id.
    Returns True if a row was updated.
    """
    # build the SET part of the UPDATE dynamically
    fields = []
    values: list[str] = []

    if severity is not None:
        fields.append("severity = ?")
        values.append(severity)
    if category is not None:
        fields.append("category = ?")
        values.append(category)
    if status is not None:
        fields.append("status = ?")
        values.append(status)
    if description is not None:
        fields.append("description = ?")
        values.append(description)

    # if no fields are changed, just stop
    if not fields:
        return False  # nothing to update

    # last value is always the incident_id for the WHERE clause
    values.append(int(incident_id))

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"""
        UPDATE cyber_incidents
        SET {", ".join(fields)}
        WHERE incident_id = ?
        """,
        values,
    )
    conn.commit()
    updated = cur.rowcount > 0  # True if at least one row changed
    conn.close()
    return updated


def delete_cyber_incident(incident_id: int) -> bool:
    """
    Delete an incident by incident_id.
    Returns True if a row was deleted.
    """
    conn = get_connection()
    cur = conn.cursor()
    # delete the row that matches this incident_id
    cur.execute(
        "DELETE FROM cyber_incidents WHERE incident_id = ?",
        (int(incident_id),),
    )
    conn.commit()
    deleted = cur.rowcount > 0  # True if a row was actually removed
    conn.close()
    return deleted

def query_df(sql: str):
    """
    Execute a SELECT query and return results as a pandas DataFrame.
    Used by the AI Assistant.
    """
    conn = get_connection()
    try:
        df = pd.read_sql_query(sql, conn)
        return df
    finally:
        conn.close()