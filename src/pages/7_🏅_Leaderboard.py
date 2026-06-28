import streamlit as st
import pandas as pd
from collections import Counter, defaultdict

from src.predictions import (
    load_all_bonus_answers,
    load_all_champion_picks,
    load_all_golden_boot_picks,
    load_bonus_answers,
    load_bonus_questions,
    load_bracket_matchups,
    load_bracket_picks,
    load_champion_pick,
    load_golden_boot_picks,
    load_group_predictions,
    load_leaderboard,
    load_players_by_tier,
)

st.title("🏅 Leaderboard")

user = st.session_state.get("user")
profile = st.session_state.get("profile") or {}
current_user_id: str | None = profile.get("id") or (user or {}).get("id")

rows = load_leaderboard()

if not rows:
    st.info("No players registered yet.")
    st.stop()

# ── Standings table ────────────────────────────────────────────────────────────

display_data = []
for row in rows:
    name = ("★ " if row["user_id"] == current_user_id else "") + (row["display_name"] or "—")
    entry: dict = {
        "Rank": row["rank"],
        "Name": name,
        "Total": row["total_pts"],
        "Group": row["group_stage_pts"],
        "Bracket": row["bracket_pts"],
        "Champion": row["champion_pts"],
        "Boot": row["golden_boot_pts"],
        "Bonus": row["bonus_pts"],
    }
    if user:
        entry["Email"] = row["email"]
    display_data.append(entry)

df = pd.DataFrame(display_data)
st.dataframe(df, hide_index=True, use_container_width=True)

st.caption("Scores are calculated dynamically based on entered results and update automatically as the tournament progresses.")

if not user:
    st.caption("Sign in from the Home page to see email addresses, track your own rank, and view everyone's predictions.")
    st.stop()

# ── Social section (login-gated) ───────────────────────────────────────────────

st.divider()
st.subheader("Predictions at a Glance")

name_map: dict[str, str] = {r["user_id"]: r["display_name"] or "—" for r in rows}

# ── Summary expanders ─────────────────────────────────────────────────────────

col_a, col_b, col_c = st.columns(3)

with col_a:
    with st.expander("🏆 Champion Picks"):
        all_champ = load_all_champion_picks()
        if not all_champ:
            st.caption("No picks yet.")
        else:
            # Group champion picks by team
            by_team: dict[str, list[str]] = defaultdict(list)
            for p in all_champ:
                by_team[p["champion"]].append(name_map.get(p["user_id"], "?"))
            for team, pickers in sorted(by_team.items(), key=lambda x: -len(x[1])):
                st.markdown(f"**{team}** ({len(pickers)})")
                st.caption(", ".join(sorted(pickers)))

            # Dark horse picks
            dh_picks = [p for p in all_champ if p.get("dark_horse")]
            if dh_picks:
                st.markdown("---")
                st.markdown("**Dark horses**")
                by_dh: dict[str, list[str]] = defaultdict(list)
                for p in dh_picks:
                    by_dh[p["dark_horse"]].append(name_map.get(p["user_id"], "?"))
                for team, pickers in sorted(by_dh.items(), key=lambda x: -len(x[1])):
                    st.caption(f"{team} ({len(pickers)}): {', '.join(sorted(pickers))}")

with col_b:
    with st.expander("🎯 Bonus Votes"):
        questions = load_bonus_questions()
        all_answers = load_all_bonus_answers()
        if not all_answers:
            st.caption("No answers yet.")
        else:
            by_q: dict[int, list[str]] = defaultdict(list)
            for a in all_answers:
                by_q[a["question_id"]].append(a["chosen_option"])
            for q in questions:
                votes = by_q.get(q["id"], [])
                if not votes:
                    continue
                st.markdown(f"**Q{q['id']}:** {q['question_text']}")
                counts = Counter(votes)
                total = len(votes)
                for option, n in counts.most_common():
                    pct = n / total
                    st.progress(pct, text=f"{option} — {n}")
                st.markdown("")

with col_c:
    with st.expander("⚽ Golden Boot"):
        all_gb = load_all_golden_boot_picks()
        if not all_gb:
            st.caption("No picks yet.")
        else:
            player_counts: Counter = Counter(p["player_name"] for p in all_gb)
            gb_data = [{"Player": name, "Picks": count}
                       for name, count in player_counts.most_common(10)]
            st.dataframe(pd.DataFrame(gb_data), hide_index=True, use_container_width=True)

# ── Per-user picks dialog ─────────────────────────────────────────────────────

st.divider()
st.subheader("👀 Spy on someone's picks")

options = [r for r in rows if r["user_id"] != current_user_id]
if not options:
    st.caption("You're the only one here so far.")
else:
    choice_labels = {r["user_id"]: f"{r['rank']}. {r['display_name'] or '—'}" for r in options}
    selected_id = st.selectbox(
        "Choose a player",
        options=[r["user_id"] for r in options],
        format_func=lambda uid: choice_labels[uid],
        label_visibility="collapsed",
    )

    if st.button("View their picks", type="secondary"):
        st.session_state["_spy_target"] = selected_id

    @st.dialog("Picks", width="large")
    def _show_picks(uid: str, display_name: str) -> None:
        st.markdown(f"### {display_name}'s picks")

        champ = load_champion_pick(uid)
        if champ:
            st.markdown("**🏆 Champion & Dark Horse**")
            c1, c2 = st.columns(2)
            c1.metric("Champion", champ["champion"])
            c2.metric("Dark Horse", champ.get("dark_horse") or "—")
        else:
            st.caption("No champion pick yet.")

        st.divider()
        st.markdown("**🌍 Group Stage**")
        group_preds = load_group_predictions(uid)
        if not group_preds:
            st.caption("No group picks yet.")
        else:
            sorted_groups = sorted(group_preds.items())
            cols = st.columns(4)
            for i, (letter, pred) in enumerate(sorted_groups):
                ranking: list[str] = pred.get("predicted_ranking") or []
                third_advances: bool = pred.get("third_place_advances", False)
                lines = [f"**{letter}**"]
                for pos, team in enumerate(ranking, 1):
                    advances = pos <= 2 or (pos == 3 and third_advances)
                    lines.append(f"{pos}. {team} \\*" if advances else f"{pos}. {team}")
                cols[i % 4].markdown("  \n".join(lines))

        st.divider()
        st.markdown("**⚽ Golden Boot Draft**")
        gb_ids = load_golden_boot_picks(uid)
        if gb_ids:
            all_players = {
                p["id"]: p["name"]
                for tier_players in load_players_by_tier().values()
                for p in tier_players
            }
            st.write(", ".join(all_players.get(pid, str(pid)) for pid in sorted(gb_ids)))
        else:
            st.caption("No golden boot picks yet.")

        st.divider()
        st.markdown("**🎯 Bonus Answers**")
        questions = load_bonus_questions()
        answers = load_bonus_answers(uid)
        if answers:
            for q in questions:
                ans = answers.get(q["id"])
                if ans:
                    st.caption(f"Q{q['id']}: {q['question_text']}")
                    st.markdown(f"→ **{ans}**")
        else:
            st.caption("No bonus answers yet.")

        st.divider()
        st.markdown("**🏟️ Knockout Bracket**")
        matchups_by_round = load_bracket_matchups()
        bracket_picks = load_bracket_picks(uid)
        if not matchups_by_round or not bracket_picks:
            st.caption("No bracket picks yet.")
        else:
            ROUND_LABELS = {"R32": "Round of 32", "R16": "Round of 16", "QF": "Quarterfinals", "SF": "Semifinals", "F": "Final"}
            for round_code in ["R32", "R16", "QF", "SF", "F"]:
                matchups = matchups_by_round.get(round_code, [])
                if not matchups:
                    continue
                round_picks = [m for m in matchups if bracket_picks.get(m["id"])]
                if not round_picks:
                    continue
                st.caption(f"**{ROUND_LABELS[round_code]}**")
                for m in round_picks:
                    pick = bracket_picks[m["id"]]
                    st.markdown(f"Match {m['slot']}: {m['team_a']} vs {m['team_b']} → **{pick}**")

    if st.session_state.get("_spy_target"):
        spy_id = st.session_state.pop("_spy_target")
        _show_picks(spy_id, choice_labels.get(spy_id, "?").split(". ", 1)[-1])