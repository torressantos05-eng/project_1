import streamlit as st
import psycopg2
from psycopg2 import sql

st.set_page_config(page_title="Manage Inventory", layout="wide")
st.title("Manage Inventory")

# ── DB connection ──────────────────────────────────────────────────────────────
def get_conn():
    return psycopg2.connect(st.secrets["DB_URL"])

# ── 1. ADD MATERIAL FORM ───────────────────────────────────────────────────────
st.subheader("Add New Material")

with st.form("add_material_form", clear_on_submit=True):
    item_name = st.text_input("Item Name *")
    category = st.text_input("Category")
    quantity = st.number_input("Quantity in Stock", min_value=0, step=1, value=0)
    submitted = st.form_submit_button("Add Material")

if submitted:
    if not item_name.strip():
        st.error("Item Name cannot be blank.")
    else:
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO materials (item_name, category, quantity_in_stock) VALUES (%s, %s, %s)",
                (item_name.strip(), category.strip() or None, quantity),
            )
            conn.commit()
            cur.close()
            conn.close()
            st.success(f"✅ '{item_name.strip()}' added successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Database error: {e}")

st.divider()

# ── 2. CURRENT INVENTORY ───────────────────────────────────────────────────────
st.subheader("Current Inventory")

def fetch_all():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, item_name, category, quantity_in_stock FROM materials ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

try:
    rows = fetch_all()
    if rows:
        import pandas as pd
        df = pd.DataFrame(rows, columns=["ID", "Item Name", "Category", "Quantity in Stock"])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No materials found. Add one above.")
except Exception as e:
    st.error(f"Could not load inventory: {e}")
    rows = []

st.divider()

# ── 3. UPDATE MATERIAL ─────────────────────────────────────────────────────────
st.subheader("Update Material")

def fetch_item(item_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, item_name, category, quantity_in_stock FROM materials WHERE id = %s",
        (item_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

try:
    if not rows:
        st.info("No materials available to edit.")
    else:
        # Build selectbox options from current data
        options = {f"{r[1]} (ID: {r[0]})": r[0] for r in rows}
        selected_label = st.selectbox("Select a material to edit", list(options.keys()))
        selected_id = options[selected_label]

        # Fetch current values for pre-population
        current = fetch_item(selected_id)

        if current:
            with st.form("update_material_form"):
                st.markdown(f"**Editing:** {current[1]}")
                new_name = st.text_input("Item Name *", value=current[1])
                new_category = st.text_input("Category", value=current[2] or "")
                new_quantity = st.number_input(
                    "Quantity in Stock",
                    min_value=0,
                    step=1,
                    value=int(current[3]),
                )
                update_submitted = st.form_submit_button("Update Material")

            if update_submitted:
                if not new_name.strip():
                    st.error("Item Name cannot be blank.")
                else:
                    try:
                        conn = get_conn()
                        cur = conn.cursor()
                        cur.execute(
                            """
                            UPDATE materials
                            SET item_name = %s,
                                category = %s,
                                quantity_in_stock = %s
                            WHERE id = %s
                            """,
                            (
                                new_name.strip(),
                                new_category.strip() or None,
                                new_quantity,
                                selected_id,
                            ),
                        )
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success(f"✅ Material updated successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Database error: {e}")

except Exception as e:
    st.error(f"Could not load update section: {e}")