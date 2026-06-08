# Admin panel — implemented in feature 10.
import streamlit as st
from src.auth import require_auth, is_admin
from src.components import render_sidebar

user = require_auth()
render_sidebar()

if not is_admin(user):
    st.error("Access denied.")
    st.stop()

st.title("🔧 Admin Panel")
st.info("Admin tools coming soon (feature 10).")