import streamlit as st
import psycopg2
import pandas as pd
from datetime import date

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
    if not conn: return [], []
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            data = cur.fetchall()
            cols = [desc[0] for desc in cur.description] if cur.description else []
            return data, cols
    except Exception as e:
        st.error(f"Query Error: {e}")
        return [], []
    finally:
        if conn:
            conn.close()

def execute_update(query, params=None):
    """Executes an UPDATE or INSERT query and commits the transaction."""
    conn = get_connection()
    if not conn: return False
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
            return True
    except Exception as e:
        st.error(f"Database Error: {e}")
        return False
    finally:
        if conn:
            conn.close()

# -----------------------------------------------------------------------------
# Page UI & Logic
# -----------------------------------------------------------------------------
st.title("📦 Fulfill Requests (Work-Study To-Do List)")
st.markdown("Review pending mailing requests below, gather the required materials, and mark them as completed once packed.")

st.divider()

# 1. Query all pending mailings
pending_query = """
    SELECT 
        m.id, 
        c.first_name || ' ' || c.last_name AS counselor_name, 
        m.destination_address, 
        m.requested_arrival_date
    FROM mailings m
    JOIN counselors c ON m.counselor_id = c.id
    WHERE m.status = 'Pending'
    ORDER BY m.requested_arrival_date ASC;
"""
pending_requests, _ = fetch_data(pending_query)

# 2. Check if there are pending requests
if not pending_requests:
    st.success("🎉 Awesome job! There are currently no pending mailing requests. You are all caught up.")
else:
    # 3. Iterate through each pending request and create an expander
    for request in pending_requests:
        m_id, counselor_name, address, needed_by = request
        
        # Expander header shows the most critical info at a glance
        with st.expander(f"📮 Send to {counselor_name} (Need by: {needed_by})", expanded=False):
            st.markdown(f"**Destination Address:**\n{address}")
            
            # Fetch the specific items requested for this mailing
            items_query = """
                SELECT 
                    mat.item_name AS "Material", 
                    mat.category AS "Category", 
                    mi.quantity_sent AS "Quantity to Pack"
                FROM mailing_items mi
                JOIN materials mat ON mi.material_id = mat.id
                WHERE mi.mailing_id = %s;
            """
            items_data, item_cols = fetch_data(items_query, (m_id,))
            
            st.markdown("**Materials to Pack:**")
            if items_data:
                df_items = pd.DataFrame(items_data, columns=item_cols)
                st.dataframe(df_items, use_container_width=True, hide_index=True)
            else:
                st.warning("No specific materials listed for this request.")
            
            # 4. Form to mark the request as completed
            # Notice the key arguments: they MUST be dynamic so each form is unique
            with st.form(key=f"fulfill_form_{m_id}"):
                completion_date = st.date_input(
                    "Date Completed", 
                    value=date.today(), 
                    key=f"date_{m_id}"
                )
                
                submit = st.form_submit_button("Mark as Completed", type="primary")
                
                if submit:
                    update_query = """
                        UPDATE mailings 
                        SET status = 'Completed', completion_date = %s 
                        WHERE id = %s
                    """
                    success = execute_update(update_query, (completion_date, m_id))
                    
                    if success:
                        st.success("Request marked as completed!")
                        st.rerun() # Refresh the page to remove the fulfilled item
