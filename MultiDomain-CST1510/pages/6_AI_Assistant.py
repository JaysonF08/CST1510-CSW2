# pages/6_AI_Assistant.py

from pathlib import Path
import sqlite3
import pandas as pd
import streamlit as st

from app.api_utils import ai_generate_sql



# PAGE CONFIG
st.set_page_config(page_title="AI Assistant", layout="wide")
st.session_state["current_page"] = "AI Assistant"


# ACCESS CONTROL
if not st.session_state.get("logged_in", False):
    st.warning("Please log in to access the AI Assistant.")
    st.switch_page("pages/1_Login.py")



# DB PATH (safe path)
BASE_DIR = Path(__file__).resolve().parents[1]  # project root
DB_PATH = BASE_DIR / "DATA" / "intelligence.db"


# TABLES
ALL_TABLES = ["cyber_incidents", "it_tickets", "datasets_metadata"]


def tables_for_mode(mode: str) -> list[str]:
    if mode == "Cybersecurity":
        return ["cyber_incidents"]
    if mode == "IT Operations":
        return ["it_tickets"]
    if mode == "Data Science":
        return ["datasets_metadata"]
    return ALL_TABLES


def run_select_query(sql: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(sql, conn)
    finally:
        conn.close()


def format_quick_answer(df: pd.DataFrame) -> str | None:
    if df is None or df.empty:
        return None
    if df.shape[0] == 1 and df.shape[1] == 1:
        return f"Answer: {df.iat[0, 0]}"
    return None


# SIDEBAR
with st.sidebar:
    st.subheader("AI Assistant settings")

    domain_mode = st.selectbox(
        "Domain focus",
        ["All domains", "Cybersecurity", "IT Operations", "Data Science"],
        index=0,
        key="ai_domain_mode",
    )

    show_sql = st.toggle("Show SQL query", value=False, key="ai_show_sql")
    show_table = st.toggle("Show table results", value=True, key="ai_show_table")

    # If user changes domain, we can optionally clear chat so it feels like it worked
    if "last_domain_mode" not in st.session_state:
        st.session_state["last_domain_mode"] = domain_mode

    if domain_mode != st.session_state["last_domain_mode"]:
        # auto-clear chat when domain changes (makes it feel responsive)
        st.session_state.pop("ai_messages", None)
        st.session_state["last_domain_mode"] = domain_mode
        st.rerun()

    if st.button("Clear chat", use_container_width=True, key="ai_clear_chat"):
        st.session_state.pop("ai_messages", None)
        st.rerun()

    st.divider()

    if st.button("Logout", use_container_width=True, key="logout_ai"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.switch_page("pages/1_Login.py")


# HEADER
st.title("AI Assistant")
st.caption(f"Domain focus: {st.session_state.get('ai_domain_mode', 'All domains')}")
st.caption(f"Logged in as: {st.session_state.get('username', 'Unknown')}")


# CHAT HISTORY
if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = [
        {
            "role": "assistant",
            "content": (
                "Ask me something about your data.\n\n"
                "Examples:\n"
                "- How many critical incidents are there?\n"
                "- Show open IT tickets by priority\n"
                "- What are the newest datasets?"
            ),
        }
    ]

for msg in st.session_state.ai_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# CHAT INPUT
user_question = st.chat_input("Type your question here...")

if user_question:
    # Store and show user message
    st.session_state.ai_messages.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    # Assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                allowed_tables = tables_for_mode(st.session_state.get("ai_domain_mode", "All domains"))

                sql, explanation = ai_generate_sql(
                    question=user_question,
                    allowed_tables=allowed_tables,
                )

                df = run_select_query(sql)
                quick = format_quick_answer(df)

                reply_parts = []
                if explanation:
                    reply_parts.append(explanation)

                if quick:
                    reply_parts.append(quick)
                else:
                    reply_parts.append(f"I found {len(df)} row(s).")

                reply_text = "\n\n".join(reply_parts)
                st.markdown(reply_text)

                if show_sql:
                    st.code(sql, language="sql")

                if show_table:
                    if df is None or df.empty:
                        st.info("No matching records were found.")
                    else:
                        st.dataframe(df, use_container_width=True)

                st.session_state.ai_messages.append({"role": "assistant", "content": reply_text})

            except Exception as e:
                err = str(e)

                if "RESOURCE_EXHAUSTED" in err or "429" in err:
                    err = (
                        "Gemini API rate limit / quota was hit.\n\n"
                        "Try:\n"
                        "- Wait 30–60 seconds and ask again\n"
                        "- Ask a shorter question\n"
                        "- Avoid clicking too fast"
                    )

                st.error(err)
                st.session_state.ai_messages.append({"role": "assistant", "content": err})