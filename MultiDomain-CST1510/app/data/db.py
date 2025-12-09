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
DATA_DIR = BASE_DIR / "DATA"
DB_PATH = DATA_DIR / "intelligence.db"           # main SQLite file


def get_connection():
    """Return a new SQLite connection to the project database."""
    return sqlite3.connect(DB_PATH)


# ---------- Table creation ----------

def create_tables():
    """Create all required tables if they do not already exist."""
    with get_connection() as conn:
        cur = conn.cursor()

        # Users table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user'
            );
            """
        )

        # Cybersecurity incidents
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

        # Datasets metadata
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

        # IT tickets
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

        conn.commit()


# ---------- Week 7 → Week 8 migration ----------

def migrate_users_from_file():
    """
    Read users from DATA/users.txt and insert into users table.

    Expected format per line:
        username,hashed_password[,role]
    """
    users_file = DATA_DIR / "users.txt"
    if not users_file.exists():
        print("[DB] No users.txt found – skipping migration.")
        return

    with get_connection() as conn:
        cur = conn.cursor()

        with users_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                parts = [p.strip() for p in line.split(",")]
                if len(parts) == 2:
                    username, hashed = parts
                    role = "user"
                elif len(parts) >= 3:
                    username, hashed, role = parts[0], parts[1], parts[2]
                else:
                    print(f"[DB] Skipping malformed line: {line}")
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
            df_cyber = pd.read_csv(cyber_csv)
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

        conn.commit()


# Optional quick test
if __name__ == "__main__":
    create_tables()
    migrate_users_from_file()
    load_domain_csvs()
    print("[DB] Setup complete.")
