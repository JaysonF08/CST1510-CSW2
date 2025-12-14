# app/api_utils.py

from __future__ import annotations

import re
import streamlit as st
from google import genai


# GEMINI CONFIG
def _get_gemini_client() -> tuple[genai.Client, str]:
    """
    Reads Gemini API key + model from .streamlit/secrets.toml

    [gemini]
    API_KEY = "..."
    MODEL = "gemini-2.5-flash"
    """
    if "gemini" not in st.secrets:
        raise RuntimeError("Missing [gemini] section in .streamlit/secrets.toml")

    api_key = st.secrets["gemini"].get("API_KEY", "").strip()
    model = st.secrets["gemini"].get("MODEL", "gemini-2.5-flash").strip()

    if not api_key:
        raise RuntimeError("Missing Gemini API key")

    client = genai.Client(api_key=api_key)
    return client, model


# DATABASE SCHEMA
TABLE_SCHEMAS = {
    "cyber_incidents": {
        "columns": ["incident_id", "timestamp", "severity", "category", "status", "description"],
        "backlog_column": "category",
        "status_column": "status",
    },
    "it_tickets": {
        "columns": ["ticket_id", "created_at", "priority", "status", "assigned_to", "description"],
        "backlog_column": "priority",
        "status_column": "status",
    },
    "datasets_metadata": {
        "columns": ["dataset_id", "dataset_name", "domain", "owner", "created_at", "description"],
        "backlog_column": None,  # not applicable
        "status_column": None,
    },
}



# SAFETY: SELECT / WITH ONLY
_SELECT_OR_WITH_RE = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)
_FORBIDDEN_RE = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|truncate|attach|detach|pragma)\b",
    re.IGNORECASE,
)

def enforce_select_only(sql: str) -> str:
    if not sql or not sql.strip():
        raise ValueError("AI did not return a SQL query.")

    sql_clean = sql.strip().rstrip(";").strip()

    if not _SELECT_OR_WITH_RE.match(sql_clean):
        raise ValueError("Only SELECT / WITH queries are allowed.")

    if _FORBIDDEN_RE.search(sql_clean):
        raise ValueError("Query contains forbidden SQL keywords.")

    if ";" in sql_clean:
        raise ValueError("Multiple SQL statements are not allowed.")

    return sql_clean


# MAIN AI FUNCTION
def ai_generate_sql(
    question: str,
    allowed_tables: list[str],
) -> tuple[str, str]:
    """
    Generates:
    - SQLite SELECT/WITH query
    - Short natural explanation
    """

    client, model = _get_gemini_client()

    # Build schema description for prompt
    schema_lines = []
    for table in allowed_tables:
        cols = ", ".join(TABLE_SCHEMAS[table]["columns"])
        schema_lines.append(f"- {table}({cols})")

    schema_text = "\n".join(schema_lines)

    system_prompt = f"""
You are a simple AI assistant for a university Streamlit dashboard (Week 10 level).

Your task:
- Generate ONE SQLite SELECT (or WITH) query
- Use ONLY the tables and columns listed below
- Then explain the result in natural language

Database schema:
{schema_text}

Rules:
- Output EXACTLY two lines:
  SQL: <SQLite SELECT or WITH query>
  EXPLAIN: <1–3 sentence friendly explanation>
- Never invent columns
- Never query tables outside the allowed list
- For counts or summaries, prefer COUNT(*)
- Use LOWER() for case-insensitive text filters
- If the question is unclear, show a small preview using LIMIT 5
"""

    user_prompt = f"User question: {question}"

    response = client.models.generate_content(
        model=model,
        contents=[system_prompt, user_prompt],
    )

    text = (response.text or "").strip()

    sql_line = ""
    explain_line = ""

    for line in text.splitlines():
        if line.lower().startswith("sql:"):
            sql_line = line.split(":", 1)[1].strip()
        elif line.lower().startswith("explain:"):
            explain_line = line.split(":", 1)[1].strip()

    if not sql_line:
        raise ValueError("AI did not return a valid SQL statement.")

    sql_line = enforce_select_only(sql_line)

    if not explain_line:
        explain_line = "Here’s what I found based on your data."

    return sql_line, explain_line