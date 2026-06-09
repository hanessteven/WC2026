import streamlit as st

user = st.session_state.get("user")
profile = st.session_state.get("profile") or {}

if not user:
    st.title("WC 2026 Predictor")
    st.write("Sign in to make your predictions.")
    from src.auth import show_login_ui
    show_login_ui()
    st.stop()

display_name = profile.get("display_name") or user.get("email", "")
st.title("🏠 Home")
st.write(f"Hey **{display_name}**, you're signed in!")
st.info("Use the sidebar to navigate to your prediction pages.")