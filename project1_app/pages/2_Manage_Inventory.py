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
        conn = psycopg2.connect(st.secrets["DB_URL"])
        with conn.cursor() as cur:
            cur.execute(query, params)
            
            if fetch:
                result = cur.fetchall()
                columns = [desc[0] for desc in cur.description] if cur.description else []
                conn.commit()
                return result, columns
            
            conn.commit()
            return True, None
    except Exception as e:
        st.error(f"Database Error: {e}")
        return None, None
    finally:
        if conn is not None:
            conn.close()

# -----------------------------------------------------------------------------
# 1. Page Title
# -----------------------------------------------------------------------------
st.title("Manage Item Catalog")

# -----------------------------------------------------------------------------
# 2. Add Material Form
# -----------------------------------------------------------------------------
st.header("Add New Item", divider="gray")

with st.form("add_material_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        item_name = st.text_input("Item Name *")
    with col2:
        category = st.text_input("Category")
        
    submitted = st.form_submit_button("Add Item")

    if submitted:
        # Validation
        if not item_name.strip():
            st.error("Item Name is a required field.")
        else:
            # Parameterized Insert
            insert_query = """
                INSERT INTO materials (item_name, category)
                VALUES (%s, %s)
            """
            success, _ = execute_query(insert_query, (item_name.strip(), category.strip()))
            
            if success:
                st.success(f"Item '{item_name}' added to the catalog successfully!")
                st.rerun()

# -----------------------------------------------------------------------------
# 3. Current Catalog Table
# -----------------------------------------------------------------------------
st.header("Current Catalog", divider="gray")

select_all_query = "SELECT id, item_name, category FROM materials ORDER BY id;"
data, columns = execute_query(select_all_query, fetch=True)

if data:
    df = pd.DataFrame(data, columns=columns)
    # Display only the relevant columns to the user
    display_df = df[["item_name", "category"]].rename(
        columns={"item_name": "Item Name", "category": "Category"}
    )
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("No items found in the catalog.")
    df = pd.DataFrame()

# -----------------------------------------------------------------------------
# 4. Update Material
# -----------------------------------------------------------------------------
if not df.empty:
    st.header("Modify Existing Item", divider="gray")
    
    # Create a dictionary for the selectbox mapping for clean UI
    # Example format: "ID: 1 | Brochures (Marketing)"
    item_dict = {f"ID: {row[0]} | {row[1]} ({row[2] or 'No Category'})": row for row in data}
    
    selected_option = st.selectbox(
        "Select an item to edit:", 
        options=["-- Select an Item --"] + list(item_dict.keys())
    )

    if selected_option != "-- Select an Item --":
        # Extract the selected item's current data
        m_id, m_name, m_category = item_dict[selected_option]
        
        with st.form("edit_material_form"):
            e_col1, e_col2 = st.columns(2)
            with e_col1:
                new_name = st.text_input("Item Name *", value=m_name)
            with e_col2:
                # Handle None values for category smoothly
                new_category = st.text_input("Category", value=m_category if m_category else "")
            
            update_submitted = st.form_submit_button("Update Item")
            
            if update_submitted:
                if not new_name.strip():
                    st.error("Item Name cannot be blank.")
                else:
                    update_query = """
                        UPDATE materials
                        SET item_name = %s, category = %s
                        WHERE id = %s
                    """
                    success, _ = execute_query(
                        update_query, 
                        (new_name.strip(), new_category.strip(), m_id)
                    )
                    if success:
                        st.success("Item updated successfully!")
                        st.rerun()
                        
