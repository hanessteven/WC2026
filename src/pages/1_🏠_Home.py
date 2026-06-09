import streamlit as st

profile = st.session_state.get("profile") or {}
user = st.session_state.get("user") or {}
display_name = profile.get("display_name") or user.get("email", "")

st.title("🏠 Home")
st.write(f"Hey **{display_name}**, you're signed in!")
st.info("Prediction pages coming soon.")