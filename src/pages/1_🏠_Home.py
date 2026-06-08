import streamlit as st
from src.auth import require_auth
from src.components import render_sidebar

user = require_auth()
render_sidebar()

profile = st.session_state.get("profile", {})
display_name = profile.get("display_name", user["email"])

st.title("🏠 Home")
st.write(f"Hey **{display_name}**, you're signed in!")
st.info("Prediction pages coming soon.")