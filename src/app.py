import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from src.auth import get_current_user, is_admin, restore_session, show_login_ui
from src.components import render_sidebar

st.set_page_config(
    page_title="WC 2026 Predictor",
    page_icon="⚽",
    layout="centered",
)

# Rehydrate session from cookie before anything else.
restore_session()

user = get_current_user()
if not user:
    show_login_ui()
    st.stop()

# Build the page list; Admin only visible to admins.
pages = [
    st.Page("pages/1_🏠_Home.py", title="Home", icon="🏠"),
    st.Page("pages/2_🏆_Group_Stage.py", title="Group Stage", icon="🏆"),
    st.Page("pages/3_⭐_Champion_Pick.py", title="Champion Pick", icon="⭐"),
    st.Page("pages/4_⚽_Golden_Boot.py", title="Golden Boot Draft", icon="⚽"),
    st.Page("pages/5_❓_Bonus_Questions.py", title="Bonus Questions", icon="❓"),
]
if is_admin(user):
    pages.append(st.Page("pages/99_🔧_Admin.py", title="Admin Panel", icon="🔧"))

render_sidebar()
pg = st.navigation(pages)
pg.run()