"""Group Stage Predictions — rank all 12 groups 1st–4th and pick 8 third-place advancers."""
from datetime import datetime, timezone

import streamlit as st

from src.auth import get_current_user
from src.predictions import (
    is_locked,
    load_group_predictions,
    load_teams_by_group,
    save_group_predictions,
)

user = get_current_user()

st.title("🏆 Group Stage Predictions")

locked = is_locked("group_stage")
if locked:
    st.warning("🔒 Group stage predictions are locked — shown read-only.")

# ── Load data ──────────────────────────────────────────────────────────────────
teams_by_group = load_teams_by_group()
existing = load_group_predictions(user["id"])
groups = sorted(teams_by_group.keys())  # A–L

# ── Group ranking cards (2-column grid) ───────────────────────────────────────
st.subheader("Rank each group 1st through 4th")
st.caption("Select a different team in each position. Duplicates will be flagged on save.")

current_rankings: dict[str, list[str]] = {}

col_l, col_r = st.columns(2)
for i, letter in enumerate(groups):
    teams = teams_by_group[letter]
    names = [t["name"] for t in teams]
    flag_map = {t["name"]: t.get("flag_emoji") or "" for t in teams}
    saved_ranking: list[str] = (existing.get(letter) or {}).get("predicted_ranking") or []

    with (col_l if i % 2 == 0 else col_r):
        with st.container(border=True):
            st.markdown(f"**Group {letter}**")
            picks: list[str] = []
            for pos, label in enumerate(["🥇 1st", "🥈 2nd", "🥉 3rd", "4th"]):
                if len(saved_ranking) > pos and saved_ranking[pos] in names:
                    default_idx = names.index(saved_ranking[pos])
                else:
                    default_idx = pos  # natural seed order if nothing saved
                pick = st.selectbox(
                    label,
                    options=names,
                    index=default_idx,
                    key=f"grp_{letter}_{pos}",
                    format_func=lambda n, fm=flag_map: f"{fm.get(n, '')} {n}".strip(),
                    disabled=locked,
                    label_visibility="visible",
                )
                picks.append(pick)
            current_rankings[letter] = picks

# ── Third-place advancers ─────────────────────────────────────────────────────
st.divider()
st.subheader("Which 8 third-place teams advance?")
st.caption(
    "Based on your rankings above. Check the 8 third-place finishers you predict will advance."
)

saved_advances = {
    letter: (existing.get(letter) or {}).get("third_place_advances", False)
    for letter in groups
}

tp_picks: dict[str, bool] = {}
tp_cols = st.columns(3)
for i, letter in enumerate(groups):
    # The current 3rd-place pick for this group (live from widget state)
    third_team = current_rankings[letter][2] if len(current_rankings.get(letter, [])) >= 3 else "?"
    flag = next(
        (t.get("flag_emoji", "") for t in teams_by_group[letter] if t["name"] == third_team),
        "",
    )
    label = f"{flag} {third_team} (Grp {letter})".strip()
    with tp_cols[i % 3]:
        tp_picks[letter] = st.checkbox(
            label,
            value=saved_advances.get(letter, False),
            key=f"tp_{letter}",
            disabled=locked,
        )

tp_count = sum(tp_picks.values())
if tp_count == 8:
    st.success(f"✅ {tp_count} / 8 selected")
else:
    st.caption(f"**{tp_count} / 8** selected — need exactly 8")

# ── Save ───────────────────────────────────────────────────────────────────────
if not locked:
    st.divider()
    if st.button("💾 Save Predictions", type="primary", use_container_width=True):
        errors: list[str] = []

        for letter in groups:
            if len(set(current_rankings[letter])) != 4:
                errors.append(f"Group {letter}: each team must appear exactly once.")

        if tp_count != 8:
            errors.append(f"Select exactly 8 third-place advancers ({tp_count} selected).")

        if errors:
            for msg in errors:
                st.error(msg)
        else:
            now = datetime.now(timezone.utc).isoformat()
            rows = [
                {
                    "user_id": user["id"],
                    "group_letter": letter,
                    "predicted_ranking": current_rankings[letter],
                    "third_place_advances": tp_picks[letter],
                    "updated_at": now,
                }
                for letter in groups
            ]
            try:
                save_group_predictions(user["id"], rows)
                st.success("✅ Predictions saved!")
                st.rerun()
            except Exception as e:
                st.error(f"Couldn't save: {e}")