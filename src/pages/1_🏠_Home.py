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
st.title(f"Welcome, {display_name} ⚽")

# ── How to play ────────────────────────────────────────────────────────────────
st.header("How to Play")
st.write(
    "Make predictions across five categories before each phase locks. "
    "Points accumulate automatically as results come in — check the **Leaderboard** to see where you stand."
)

col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 Prediction Pages")
    st.markdown("""
**Group Stage** — rank all 4 teams in each group and predict which 3rd-place team advances. Locks before the group stage kicks off.

**Champion Pick** — pick the tournament winner and a dark horse team before the first match. This is your highest-value prediction — 13 pts if you nail it.

**Golden Boot Draft** — build a squad of players within a $100 budget. If any of your picks leads in goals at the end, you score.

**Bonus Questions** — five pre-tournament questions covering host nations, penalties, confederations, and more.

**Knockout Bracket** — pick match winners round by round as the real matchups are set. Opens for each round after the previous one finishes.
""")

with col2:
    st.subheader("🏆 Scoring")
    st.markdown("""
| Category | Points |
|---|---|
| Group qualifier (top 2) | 1 per team |
| Group exact position | +1 per team |
| 3rd-place advancer | 2 |
| Round of 32 winner | 1 |
| Round of 16 winner | 2 |
| Quarterfinal winner | 3 |
| Semifinal winner | 5 |
| Final winner | 8 |
| Upfront champion | 13 |
| Dark horse reaches QF | 3 |
| Golden Boot player | 7 |
| Bonus question | 2 each |
""")

# ── Key rules ─────────────────────────────────────────────────────────────────
st.subheader("Key Rules")
st.markdown("""
- **Locks are per-category.** Once a category locks you cannot edit those picks — save early.
- **Bracket is wave-based.** You don't fill in the full bracket upfront. Each round opens once the real matchups are known, so everyone picks from the same actual teams.
- **Champion Pick is separate** from the bracket Final pick and locks at tournament start — it's worth the most points so don't forget it.
- **Golden Boot ties** are shared — if multiple players finish level on goals, any drafted player among the joint leaders scores you the 7 pts.
- **Bonus ties** are handled the same way — if a question result is a tie, all tied answers are marked correct and everyone who picked any of them gets full points.
- **Scores update automatically** whenever the admin enters new results.
""")