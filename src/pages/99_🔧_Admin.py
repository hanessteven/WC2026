# Admin panel — full implementation in feature 10.
import streamlit as st
from src.auth import get_current_user, is_admin

# Defense-in-depth: app.py already gates nav, but verify here too.
if not is_admin(get_current_user()):
    st.error("Access denied.")
    st.stop()

st.title("🔧 Admin Panel")
st.info("Admin tools coming soon (feature 10).")