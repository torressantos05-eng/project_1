import streamlit as st
import psycopg2
import pandas as pd

# -----------------------------------------------------------------------------
# Database Helper Function
# -----------------------------------------------------------------------------
def execute_query(query, params=None, fetch=False):
    """
    Executes a query, handles the connection gracefully, and optionally fetches data.
    """
    conn = None
    try:
        # Open connection
        conn = psycopg2.connect(st.secrets["DB_URL"])
        with conn.cursor() as cur:
            cur.execute(query, params)
            
            if fetch:
                result = cur.fetchall()
                # Get column names from the cursor description
                columns = [desc[0] for desc in cur.description] if cur.description else []
                conn.commit()
                return result, columns
            
            conn.commit()
            return True, None
    except Exception as e:
        st.error(f"Database Error: {e}")
        return None, None
    finally:
        # Ensure connection is closed even if an error occurs
        if conn is not None:
            conn.close()

# -----------------------------------------------------------------------------
# 1. Page Title
# -----------------------------------------------------------------------------
st.title("Manage Counselors")

# -----------------------------------------------------------------------------
# 2. Add Counselor Form
# -----------------------------------------------------------------------------
st.header("Add New Counselor", divider="gray")

with st.form("add_counselor_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("First Name *")
        email = st.text_input("Email *")
    with col2:
        last_name = st.text_input("Last Name *")
        territory = st.text_input("Territory")
        
    submitted = st.form_submit_button("Add Counselor")

    if submitted:
        # Validation
        if not first_name.strip() or not last_name.strip() or not email.strip():
            st.error("First Name, Last Name, and Email are required fields.")
        elif "@" not in email:
            st.error("Please enter a valid email address containing an '@' symbol.")
        else:
            # Parameterized Insert
            insert_query = """
                INSERT INTO counselors (first_name, last_name, email, territory)
                VALUES (%s, %s, %s, %s)
            """
            success, _ = execute_query(insert_query, (first_name, last_name, email, territory))
            
            if success:
                st.success(f"Counselor '{first_name} {last_name}' added successfully!")
                st.rerun() # Refresh the page to update the table

# -----------------------------------------------------------------------------
# 3. Current Counselors Table
# -----------------------------------------------------------------------------
st.header("Current Counselors", divider="gray")

select_all_query = "SELECT id, first_name, last_name, email, territory, is_active FROM counselors ORDER BY id;"
data, columns = execute_query(select_all_query, fetch=True)

if data:
    df = pd.DataFrame(data, columns=columns)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No counselors found in the database.")
    df = pd.DataFrame() # Empty dataframe to prevent errors below

# -----------------------------------------------------------------------------
# 4. Update & Delete Counselor
# -----------------------------------------------------------------------------
if not df.empty:
    st.header("Modify Existing Counselor", divider="gray")
    
    # Create a dictionary for the selectbox mapping "ID - Name" to the row data
    counselor_dict = {f"ID: {row[0]} | {row[1]} {row[2]}": row for row in data}
    
    selected_option = st.selectbox(
        "Select a counselor to modify:", 
        options=["-- Select a Counselor --"] + list(counselor_dict.keys())
    )

    if selected_option != "-- Select a Counselor --":
        # Extract the selected counselor's current data
        selected_row = counselor_dict[selected_option]
        c_id, c_fname, c_lname, c_email, c_territory, c_active = selected_row
        
        # Use tabs to separate Edit and Delete actions cleanly
        tab_edit, tab_delete = st.tabs(["✏️ Edit Counselor", "🗑️ Delete Counselor"])
        
        # --- EDIT TAB ---
        with tab_edit:
            with st.form("edit_counselor_form"):
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    new_fname = st.text_input("First Name", value=c_fname)
                    new_email = st.text_input("Email", value=c_email)
                with e_col2:
                    new_lname = st.text_input("Last Name", value=c_lname)
                    new_territory = st.text_input("Territory", value=c_territory if c_territory else "")
                
                new_active = st.checkbox("Active Counselor", value=c_active)
                
                update_submitted = st.form_submit_button("Update Counselor")
                
                if update_submitted:
                    if not new_fname.strip() or not new_lname.strip() or not new_email.strip():
                        st.error("First Name, Last Name, and Email cannot be blank.")
                    elif "@" not in new_email:
                        st.error("Please enter a valid email address.")
                    else:
                        update_query = """
                            UPDATE counselors
                            SET first_name = %s, last_name = %s, email = %s, territory = %s, is_active = %s
                            WHERE id = %s
                        """
                        success, _ = execute_query(
                            update_query, 
                            (new_fname, new_lname, new_email, new_territory, new_active, c_id)
                        )
                        if success:
                            st.success("Counselor updated successfully!")
                            st.rerun()

        # --- DELETE TAB ---
        with tab_delete:
            st.warning(f"**Warning:** You are about to permanently delete the record for **{c_fname} {c_lname}**.")
            
            # Explicit confirmation step
            confirm_delete = st.checkbox("I understand the consequences and confirm I want to delete this counselor.")
            
            if st.button("Delete Counselor", type="primary"):
                if confirm_delete:
                    delete_query = "DELETE FROM counselors WHERE id = %s"
                    success, _ = execute_query(delete_query, (c_id,))
                    if success:
                        st.success("Counselor deleted successfully!")
                        st.rerun()
                else:
                    st.error("You must check the confirmation box to proceed with deletion.")