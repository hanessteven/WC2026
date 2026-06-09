"""Wave-Based Knockout Bracket — pick winners round by round from real matchups."""
import streamlit as st

from src.auth import get_current_user
from src.locks import load_lock_state
from src.predictions import (
    load_bracket_matchups,
    load_bracket_picks,
    load_teams_by_group,
    save_bracket_picks,
)

ROUNDS = ["R32", "R16", "QF", "SF", "F"]
ROUND_LABELS = {
    "R32": "Round of 32",
    "R16": "Round of 16",
    "QF": "Quarterfinals",
    "SF": "Semifinals",
    "F": "Final",
}
ROUND_POINTS = {"R32": 1, "R16": 2, "QF": 3, "SF": 5, "F": 8}
NO_PICK = "— select winner —"

user = get_current_user()

st.title("🏟️ Knockout Bracket")
st.caption(
    "Pick the winner of each match once the admin posts the real matchups. "
    "Points per correct pick: R32 **1** · R16 **2** · QF **3** · SF **5** · Final **8**"
)

# Load everything once — avoids repeated DB calls inside the tab loop
matchups_by_round = load_bracket_matchups()
existing_picks = load_bracket_picks(user["id"])
lock_state = load_lock_state()

teams_by_group = load_teams_by_group()
flag_map = {
    t["name"]: t.get("flag_emoji") or ""
    for grp in teams_by_group.values()
    for t in grp
}


def fmt_team(name: str) -> str:
    return f"{flag_map.get(name, '')} {name}".strip()


tabs = st.tabs([ROUND_LABELS[r] for r in ROUNDS])

for tab, round_code in zip(tabs, ROUNDS):
    with tab:
        matchups: list[dict] = matchups_by_round.get(round_code, [])
        locked: bool = lock_state.get(round_code, False)
        pts: int = ROUND_POINTS[round_code]
        n: int = len(matchups)
        # R32 (16) and R16 (8) get a 2-column grid; smaller rounds stay single column
        use_two_cols: bool = n >= 8

        # ── Round not yet populated ───────────────────────────────────────────
        if not matchups:
            st.info(
                f"⏳ {ROUND_LABELS[round_code]} matchups haven't been posted yet — "
                "check back after the previous round concludes."
            )
            continue

        # ── Status banner ─────────────────────────────────────────────────────
        if locked:
            st.warning(f"🔒 {ROUND_LABELS[round_code]} picks are locked.")
        else:
            pts_label = f"{pts} pt{'s' if pts > 1 else ''}"
            st.caption(
                f"**{n} matches · {pts_label} per correct pick** — "
                "select a winner for every match, then save."
            )

        # ── OPEN ROUND ────────────────────────────────────────────────────────
        if not locked:
            new_picks: dict[int, str | None] = {}

            if use_two_cols:
                half = (n + 1) // 2
                col_l, col_r = st.columns(2)
                for i, m in enumerate(matchups):
                    saved = existing_picks.get(m["id"])
                    options = [NO_PICK, m["team_a"], m["team_b"]]
                    idx = options.index(saved) if saved in options else 0
                    with (col_l if i < half else col_r):
                        with st.container(border=True):
                            st.caption(f"Match {m['slot']}")
                            choice = st.radio(
                                label="winner",
                                options=options,
                                index=idx,
                                format_func=lambda x: x if x == NO_PICK else fmt_team(x),
                                key=f"bracket_{round_code}_{m['id']}",
                                label_visibility="collapsed",
                                horizontal=True,
                            )
                    new_picks[m["id"]] = choice if choice != NO_PICK else None
            else:
                for m in matchups:
                    saved = existing_picks.get(m["id"])
                    options = [NO_PICK, m["team_a"], m["team_b"]]
                    idx = options.index(saved) if saved in options else 0
                    with st.container(border=True):
                        st.caption(f"Match {m['slot']}")
                        choice = st.radio(
                            label="winner",
                            options=options,
                            index=idx,
                            format_func=lambda x: x if x == NO_PICK else fmt_team(x),
                            key=f"bracket_{round_code}_{m['id']}",
                            label_visibility="collapsed",
                            horizontal=True,
                        )
                    new_picks[m["id"]] = choice if choice != NO_PICK else None

            st.divider()
            unpicked = [m["slot"] for m in matchups if new_picks.get(m["id"]) is None]
            if unpicked:
                st.caption(
                    f"Pick all matches before saving. "
                    f"Missing: {', '.join(f'Match {s}' for s in unpicked)}"
                )
            if st.button(
                f"💾 Save {ROUND_LABELS[round_code]} Picks",
                type="primary",
                use_container_width=True,
                key=f"save_{round_code}",
                disabled=bool(unpicked),
            ):
                try:
                    save_bracket_picks(
                        user["id"],
                        {mid: w for mid, w in new_picks.items() if w is not None},
                    )
                    st.success(f"✅ {ROUND_LABELS[round_code]} picks saved.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Couldn't save: {e}")

        # ── LOCKED ROUND (read-only) ───────────────────────────────────────────
        else:
            def _locked_card(m: dict) -> None:
                pick = existing_picks.get(m["id"])
                result_known = bool(m.get("winner"))
                with st.container(border=True):
                    st.caption(
                        f"Match {m['slot']}: "
                        f"{fmt_team(m['team_a'])} vs {fmt_team(m['team_b'])}"
                    )
                    if not pick:
                        st.markdown("_No pick recorded_")
                    elif result_known:
                        pts_label = f"{pts} pt{'s' if pts > 1 else ''}"
                        if pick == m["winner"]:
                            st.markdown(f"Your pick: **{fmt_team(pick)}** ✅ (+{pts_label})")
                        else:
                            st.markdown(
                                f"Your pick: **{fmt_team(pick)}** ❌  "
                                f"Winner: **{fmt_team(m['winner'])}**"
                            )
                    else:
                        st.markdown(f"Your pick: **{fmt_team(pick)}** ⏳ awaiting result")

            if use_two_cols:
                half = (n + 1) // 2
                col_l, col_r = st.columns(2)
                for i, m in enumerate(matchups):
                    with (col_l if i < half else col_r):
                        _locked_card(m)
            else:
                for m in matchups:
                    _locked_card(m)