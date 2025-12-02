import streamlit as st
from memory import MemoryDB

st.set_page_config(page_title="DB Test", page_icon="🗄️")
st.title("🗄️ DB Connectivity Test")

db = MemoryDB()
st.write("Connected:", db.is_connected())

if db.is_connected():
    st.write("Trying a simple query...")
    try:
        rows = db.load_memory("Perry", limit=1)
        st.success(f"Query OK. Rows: {len(rows)}")
    except Exception as e:
        st.error(f"Query failed: {e}")
else:
    st.error("DB not connected")

st.write("Done.")
