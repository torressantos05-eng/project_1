import streamlit as st
import psycopg2
import pandas as pd

# -----------------------------------------------------------------------------
# Database Helper Functions
# -----------------------------------------------------------------------------
def get_connection():
    """Returns a psycopg2 connection using Streamlit secrets."""
    try:
        return psycopg2.connect(st.secrets["DB_URL"])
    except Exception as e:
        st.error(f"Failed to connect to the database: {e}")
        return None

def fetch_data(query, params=None):
    """Executes a SELECT query and returns the data and column names."""
    conn = get_connection()
    if not conn:
        return [], []
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            data = cur.fetchall()
            cols = [desc[0] for desc in cur.description] if cur.description else []
            return data, cols
    except Exception as e:
        st.error(f"Database Query Error: {e}")
        return [], []
    finally:
        if conn:
            conn.close()

def get_single_value(query):
    """Helper to fetch a single scalar value (like a COUNT)."""
    data, _ = fetch_data(query)
    if data and data[0]:
        return data[0][0]
    return 0

# -----------------------------------------------------------------------------
# 1. Page Title & Welcome
# -----------------------------------------------------------------------------
st.title("📦 Recruitment Travel Dashboard")
st.markdown("Welcome to the Recruitment Travel mailing management system. Here is a high-level overview of current mailing requests and active personnel.")

st.divider()

# -----------------------------------------------------------------------------
# 2. Key Metrics
# -----------------------------------------------------------------------------
# Fetch counts from the database
pending_query = "SELECT COUNT(*) FROM mailings WHERE status = 'Pending';"
completed_query = "SELECT COUNT(*) FROM mailings WHERE status = 'Completed';"
active_counselors_query = "SELECT COUNT(*) FROM counselors WHERE is_active = true;"

total_pending = get_single_value(pending_query)
total_sent = get_single_value(completed_query)
total_active = get_single_value(active_counselors_query)

# Display metrics in 3 columns
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Pending Requests", total_pending)
with col2:
    st.metric("Packages Sent", total_sent)
with col3:
    st.metric("Total Active Counselors", total_active)

# -----------------------------------------------------------------------------
# 3. Recent Mailing Requests Table
# -----------------------------------------------------------------------------
st.subheader("Recent Mailing Requests")

recent_mailings_query = """
    SELECT 
        c.last_name AS "Counselor",
        m.destination_address AS "Destination",
        m.requested_arrival_date AS "Needed By",
        m.status AS "Status"
    FROM mailings m
    JOIN counselors c ON m.counselor_id = c.id
    ORDER BY m.id DESC
    LIMIT 10;
"""

recent_data, columns = fetch_data(recent_mailings_query)

if recent_data:
    df_recent = pd.DataFrame(recent_data, columns=columns)
    
    # Optional: Apply some basic styling to the dataframe
    st.dataframe(
        df_recent, 
        use_container_width=True, 
        hide_index=True
    )
else:
    st.info("No recent mailing requests found in the system.")
