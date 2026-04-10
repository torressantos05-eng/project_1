import streamlit as st
import psycopg2
import pandas as pd
from datetime import date

# -----------------------------------------------------------------------------
# Database Connection Helper
# -----------------------------------------------------------------------------
def get_connection():
    """Returns a psycopg2 connection using Streamlit secrets."""
    try:
        return psycopg2.connect(st.secrets["DB_URL"])
    except Exception as e:
        st.error(f"Failed to connect to the database: {e}")
        return None

# Helper to run simple fetch queries
def fetch_data(query, params=None):
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
        conn.close()

# -----------------------------------------------------------------------------
# Page UI & Logic
# -----------------------------------------------------------------------------
st.title("Request a Mailing")

# 1. Fetch Active Counselors
counselor_data, _ = fetch_data("SELECT id, first_name, last_name FROM counselors WHERE is_active = true ORDER BY last_name, first_name;")
counselor_options = {f"{row[1]} {row[2]} (ID: {row[0]})": row[0] for row in counselor_data}

# 2. Fetch Available Materials
materials_data, _ = fetch_data("SELECT id, item_name, quantity_in_stock FROM materials WHERE quantity_in_stock > 0 ORDER BY item_name;")
material_options = {row[1]: {"id": row[0], "stock": row[2]} for row in materials_data}

st.header("New Mailing Request", divider="gray")

# Check if we have the necessary reference data to proceed
if not counselor_options:
    st.warning("No active counselors found. Please add or activate a counselor first.")
elif not material_options:
    st.warning("No materials currently in stock.")
else:
    # -------------------------------------------------------------------------
    # 3. Dynamic Request "Form" (Using standard inputs for dynamic reactivity)
    # -------------------------------------------------------------------------
    selected_counselor = st.selectbox("Select Counselor *", options=["-- Select --"] + list(counselor_options.keys()))
    destination_address = st.text_area("Destination Address *")
    requested_arrival_date = st.date_input("Requested Arrival Date *", min_value=date.today())
    
    selected_materials = st.multiselect("Select Materials Needed *", options=list(material_options.keys()))
    
    # Dynamically generate number inputs based on selections
    quantities = {}
    if selected_materials:
        st.markdown("**Specify Quantities:**")
        for mat in selected_materials:
            stock = material_options[mat]["stock"]
            # Enforce max value based on stock
            quantities[mat] = st.number_input(f"{mat} (Max: {stock})", min_value=0, max_value=stock, value=0, step=1)

    submitted = st.button("Submit Request", type="primary")

    if submitted:
        # 4. Validation
        if selected_counselor == "-- Select --":
            st.error("Please select a counselor.")
        elif not destination_address.strip():
            st.error("Destination address cannot be blank.")
        elif not selected_materials:
            st.error("Please select at least one material.")
        elif sum(quantities.values()) == 0:
            st.error("At least one selected material must have a quantity greater than 0.")
        else:
            # 5. Database Insertion (Transaction)
            counselor_id = counselor_options[selected_counselor]
            
            conn = get_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        # Insert into mailings and return the new ID
                        insert_mailing_sql = """
                            INSERT INTO mailings (counselor_id, destination_address, requested_arrival_date, status)
                            VALUES (%s, %s, %s, 'Pending')
                            RETURNING id;
                        """
                        cur.execute(insert_mailing_sql, (counselor_id, destination_address.strip(), requested_arrival_date))
                        new_mailing_id = cur.fetchone()[0]

                        # Insert into mailing_items for each valid selection
                        insert_item_sql = """
                            INSERT INTO mailing_items (mailing_id, material_id, quantity_sent)
                            VALUES (%s, %s, %s);
                        """
                        for mat, qty in quantities.items():
                            if qty > 0:
                                mat_id = material_options[mat]["id"]
                                cur.execute(insert_item_sql, (new_mailing_id, mat_id, qty))
                        
                        # Commit the transaction
                        conn.commit()
                        st.success("Mailing request submitted successfully!")
                        st.rerun() # Refresh to clear inputs and update the table below
                
                except Exception as e:
                    conn.rollback() # Rollback on failure
                    st.error(f"Failed to submit request: {e}")
                finally:
                    conn.close()

# -----------------------------------------------------------------------------
# 6. Recent Mailing Requests Table
# -----------------------------------------------------------------------------
st.header("Recent Mailing Requests", divider="gray")

recent_mailings_query = """
    SELECT 
        m.id AS "Mailing ID",
        c.first_name || ' ' || c.last_name AS "Counselor",
        m.destination_address AS "Destination",
        m.requested_arrival_date AS "Needed By",
        m.status AS "Status"
    FROM mailings m
    JOIN counselors c ON m.counselor_id = c.id
    ORDER BY m.id DESC
    LIMIT 20;
"""

recent_data, columns = fetch_data(recent_mailings_query)

if recent_data:
    df_recent = pd.DataFrame(recent_data, columns=columns)
    st.dataframe(df_recent, use_container_width=True, hide_index=True)
else:
    st.info("No mailing requests found.")