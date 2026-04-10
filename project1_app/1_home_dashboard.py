# pages/1_Home_Dashboard.py

import streamlit as st
import psycopg2
import psycopg2.extras
from datetime import date

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Home Dashboard", page_icon="📬", layout="wide")

# ── DB connection helper ───────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    """Create (and cache) a single psycopg2 connection for the session."""
    try:
        conn = psycopg2.connect(st.secrets["DB_URL"])
        return conn
    except psycopg2.OperationalError as e:
        st.error(f"⚠️ Could not connect to the database: {e}")
        st.stop()

def run_query(sql: str, params=None):
    """Run a SELECT and return rows as a list of dicts. Re-raises on error."""
    conn = get_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return cur.fetchall()

# ── Page header ───────────────────────────────────────────────────────────────
st.title("📬 Recruitment Travel — Home Dashboard")
st.markdown(
    """
    Welcome to the **Recruitment Travel** management system. Use this dashboard
    to monitor mailing requests, track inventory levels, and manage counselor
    territories — all in one place.
    """
)
st.divider()

# ── Metric cards ──────────────────────────────────────────────────────────────
try:
    pending_rows   = run_query("SELECT COUNT(*) AS n FROM mailings WHERE status = 'Pending'")
    completed_rows = run_query("SELECT COUNT(*) AS n FROM mailings WHERE status = 'Completed'")
    low_stock_rows = run_query("SELECT COUNT(*) AS n FROM materials WHERE quantity_in_stock < 50")

    pending_count   = pending_rows[0]["n"]   if pending_rows   else 0
    completed_count = completed_rows[0]["n"] if completed_rows else 0
    low_stock_count = low_stock_rows[0]["n"] if low_stock_rows else 0

except Exception as e:
    st.error(f"⚠️ Failed to load metrics: {e}")
    pending_count = completed_count = low_stock_count = 0

col1, col2, col3 = st.columns(3)

col1.metric(
    label="📋 Total Pending Requests",
    value=pending_count,
    help="Mailings currently waiting to be fulfilled.",
)
col2.metric(
    label="✅ Packages Sent",
    value=completed_count,
    help="Mailings that have been marked Completed.",
)
col3.metric(
    label="⚠️ Low Stock Alerts",
    value=low_stock_count,
    help="Materials with fewer than 50 units remaining.",
)

st.divider()

# ── Recent mailing requests table ─────────────────────────────────────────────
st.subheader("🕐 10 Most Recent Mailing Requests")

RECENT_MAILINGS_SQL = """
    SELECT
        c.last_name                                  AS "Counselor",
        m.destination_address                        AS "Destination Address",
        TO_CHAR(m.requested_arrival_date, 'Mon DD, YYYY') AS "Requested Arrival",
        m.status                                     AS "Status"
    FROM   mailings   m
    JOIN   counselors c ON c.id = m.counselor_id
    ORDER  BY m.id DESC
    LIMIT  10;
"""

try:
    rows = run_query(RECENT_MAILINGS_SQL)

    if rows:
        # Convert list-of-dicts to a plain list-of-dicts Streamlit can render
        st.dataframe(
            data=[dict(r) for r in rows],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No mailing requests found yet.")

except Exception as e:
    st.error(f"⚠️ Failed to load recent mailings: {e}")