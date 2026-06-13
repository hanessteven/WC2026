"""Admin Panel — locks, results, bracket progression, and user management."""
import streamlit as st

from src.auth import get_current_user, is_admin

if not is_admin(get_current_user()):
    st.error("Access denied.")
    st.stop()

from src.admin import (
    load_all_users,
    load_golden_boot_result_lock,
    load_group_result_locks,
    load_group_results,
    load_lock_state,
    load_player_goals,
    load_real_bracket,
    load_third_place_advancers_lock,
    reset_user_picks,
    save_bonus_correct_options,
    save_bracket_round,
    save_group_results,
    save_match_results,
    save_player_goals,
    save_third_place_advancers,
    set_golden_boot_result_lock,
    set_group_result_lock,
    set_lock,
    set_third_place_advancers_lock,
)
from src.predictions import load_bonus_questions, load_players_by_tier, load_teams_by_group

st.title("🔧 Admin Panel")

LOCK_LABELS: dict[str, str] = {
    "group_stage": "Group Stage",
    "champion": "Champion Pick",
    "golden_boot": "Golden Boot Draft",
    "bonus": "Bonus Questions",
    "R32": "Round of 32",
    "R16": "Round of 16",
    "QF": "Quarterfinals",
    "SF": "Semifinals",
    "F": "Final",
}

ROUND_SIZES: dict[str, int] = {"R32": 16, "R16": 8, "QF": 4, "SF": 2, "F": 1}
ROUNDS = list(ROUND_SIZES.keys())

tab_locks, tab_groups, tab_bracket, tab_results, tab_pb, tab_users = st.tabs([
    "🔒 Locks",
    "📊 Group Results",
    "🏟️ Bracket",
    "⚽ Match Results",
    "🌟 Players & Bonus",
    "👥 Users",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — LOCKS
# ─────────────────────────────────────────────────────────────────────────────
with tab_locks:
    st.subheader("Lock controls")
    st.caption(
        "Locking a category makes it read-only for all users. "
        "Changes take effect immediately."
    )

    locks = load_lock_state()

    pre_tournament = ["group_stage", "champion", "golden_boot", "bonus"]
    knockout = ["R32", "R16", "QF", "SF", "F"]

    def _lock_row(category: str) -> None:
        label = LOCK_LABELS.get(category, category)
        locked = locks.get(category, False)
        col_label, col_status, col_btn = st.columns([3, 2, 2])
        with col_label:
            st.write(label)
        with col_status:
            st.write("🔒 Locked" if locked else "🔓 Open")
        with col_btn:
            btn_label = "Unlock" if locked else "Lock"
            if st.button(btn_label, key=f"lock_{category}"):
                try:
                    set_lock(category, not locked)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")

    st.markdown("**Pre-tournament**")
    for cat in pre_tournament:
        _lock_row(cat)

    st.divider()
    st.markdown("**Knockout rounds**")
    for cat in knockout:
        _lock_row(cat)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — GROUP RESULTS
# ─────────────────────────────────────────────────────────────────────────────
with tab_groups:
    st.subheader("Group stage results")
    st.caption("Enter the final standings for all 12 groups and which 8 third-place teams advanced.")

    # ── Results Finalization ────────────────────────────────────────────
    st.markdown("### 🔒 Results Finalization")
    st.caption("Lock each group's results to prevent accidental edits. Locked groups are read-only.")

    group_locks = load_group_result_locks()
    groups_ordered = sorted(group_locks.keys())

    col_grps = st.columns(4)
    for i, letter in enumerate(groups_ordered):
        locked = group_locks.get(letter, False)
        with col_grps[i % 4]:
            col_label, col_btn = st.columns([3, 1])
            with col_label:
                st.write(f"Group {letter}")
            with col_btn:
                if locked:
                    st.write("🔒")
                    if st.button("Unlock", key=f"unlock_group_{letter}", use_container_width=True):
                        set_group_result_lock(letter, False)
                        st.rerun()
                else:
                    st.write("🔓")
                    if st.button("Lock", key=f"lock_group_{letter}", use_container_width=True):
                        set_group_result_lock(letter, True)
                        st.rerun()

    st.divider()
    gb_locked = load_golden_boot_result_lock()
    col_gb_label, col_gb_status, col_gb_btn = st.columns([2, 1, 1])
    with col_gb_label:
        st.write("Golden Boot Results")
    with col_gb_status:
        st.write("🔒" if gb_locked else "🔓")
    with col_gb_btn:
        if gb_locked:
            if st.button("Unlock GB", key="unlock_gb", use_container_width=True):
                set_golden_boot_result_lock(False)
                st.rerun()
        else:
            if st.button("Lock GB", key="lock_gb", use_container_width=True):
                set_golden_boot_result_lock(True)
                st.rerun()

    st.divider()

    teams_by_group = load_teams_by_group()
    saved_results = load_group_results()
    groups = sorted(teams_by_group.keys())

    final_rankings: dict[str, list[str]] = {}
    col_l, col_r = st.columns(2)

    for i, letter in enumerate(groups):
        teams = teams_by_group[letter]
        names = [t["name"] for t in teams]
        flag_map = {t["name"]: t.get("flag_emoji") or "" for t in teams}
        saved_ranking: list[str] = (saved_results.get(letter) or {}).get("final_ranking") or []
        group_is_locked = group_locks.get(letter, False)

        with (col_l if i % 2 == 0 else col_r):
            with st.container(border=True):
                header = f"**Group {letter}**" + (" 🔒" if group_is_locked else "")
                st.markdown(header)
                if group_is_locked:
                    st.caption("Results locked. Unlock above to edit.")
                picks: list[str] = []
                for pos, label in enumerate(["🥇 1st", "🥈 2nd", "🥉 3rd", "4th"]):
                    if len(saved_ranking) > pos and saved_ranking[pos] in names:
                        default_idx = names.index(saved_ranking[pos])
                    else:
                        default_idx = pos
                    pick = st.selectbox(
                        label,
                        options=names,
                        index=default_idx,
                        key=f"res_grp_{letter}_{pos}",
                        format_func=lambda n, fm=flag_map: f"{fm.get(n, '')} {n}".strip(),
                        disabled=group_is_locked,
                    )
                    picks.append(pick)
                final_rankings[letter] = picks

    st.divider()
    if st.button("💾 Save Group Results", type="primary", use_container_width=True):
        errors: list[str] = []
        for letter in groups:
            if len(set(final_rankings[letter])) != 4:
                errors.append(f"Group {letter}: all four positions must be different teams.")
        if errors:
            for msg in errors:
                st.error(msg)
        else:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            rows = [
                {
                    "group_letter": letter,
                    "final_ranking": final_rankings[letter],
                    "updated_at": now,
                }
                for letter in groups
            ]
            try:
                save_group_results(rows)
                st.success("✅ Group results saved.")
                st.rerun()
            except Exception as e:
                st.error(f"Couldn't save: {e}")

    st.divider()
    st.markdown("### ⭐ Third-Place Advancers")
    st.caption("Select which 8 third-place teams advance to the knockout round.")

    tp_locked = load_third_place_advancers_lock()
    col_tp_status, col_tp_btn = st.columns([4, 1])
    with col_tp_status:
        st.write("🔒 Locked" if tp_locked else "🔓 Unlocked")
    with col_tp_btn:
        if tp_locked:
            if st.button("Unlock TP", key="unlock_tp", use_container_width=True):
                set_third_place_advancers_lock(False)
                st.rerun()
        else:
            if st.button("Lock TP", key="lock_tp", use_container_width=True):
                set_third_place_advancers_lock(True)
                st.rerun()

    if tp_locked:
        st.info("3rd place selection locked. Unlock above to edit.")

    saved_advances = {
        letter: (saved_results.get(letter) or {}).get("third_place_advances", False)
        for letter in groups
    }

    tp_results: dict[str, bool] = {}
    tp_cols = st.columns(3)
    all_flags = {t["name"]: t.get("flag_emoji") or "" for g in teams_by_group.values() for t in g}

    for i, letter in enumerate(groups):
        third_team = final_rankings[letter][2] if len(final_rankings.get(letter, [])) >= 3 else "?"
        flag = all_flags.get(third_team, "")
        label = f"{flag} {third_team} (Grp {letter})".strip()
        with tp_cols[i % 3]:
            tp_results[letter] = st.checkbox(
                label,
                value=saved_advances.get(letter, False),
                key=f"res_tp_{letter}",
                disabled=tp_locked,
            )

    tp_count = sum(tp_results.values())
    if tp_count == 8:
        st.success(f"✅ {tp_count} / 8 selected")
    else:
        st.caption(f"**{tp_count} / 8** selected — need exactly 8")

    if st.button("💾 Save Advancers", type="primary", use_container_width=True, disabled=tp_locked):
        if tp_count != 8:
            st.error(f"Select exactly 8 third-place advancers ({tp_count} selected).")
        else:
            try:
                save_third_place_advancers(tp_results)
                st.success("✅ Third-place advancers saved.")
                st.rerun()
            except Exception as e:
                st.error(f"Couldn't save: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — BRACKET (enter matchups)
# ─────────────────────────────────────────────────────────────────────────────
with tab_bracket:
    st.subheader("Enter knockout matchups")
    st.caption(
        "After each stage completes, enter the real matchups for the next round. "
        "These populate the bracket users pick from."
    )

    all_teams_flat = sorted(t["name"] for grp in teams_by_group.values() for t in grp)
    existing_bracket = load_real_bracket()
    bracket_by_round: dict[str, list[dict]] = {}
    for m in existing_bracket:
        bracket_by_round.setdefault(m["round"], []).append(m)

    selected_round = st.radio(
        "Round",
        options=ROUNDS,
        format_func=lambda r: LOCK_LABELS[r],
        horizontal=True,
        key="bracket_round_select",
    )

    n_slots = ROUND_SIZES[selected_round]
    saved_matchups = {m["slot"]: m for m in bracket_by_round.get(selected_round, [])}

    st.markdown(f"**{LOCK_LABELS[selected_round]} — {n_slots} matches**")
    st.caption("Select Team A and Team B for each match slot. Slot order matters for bracket seeding.")

    new_matchups: list[dict] = []
    for slot in range(1, n_slots + 1):
        saved = saved_matchups.get(slot, {})
        saved_a = saved.get("team_a")
        saved_b = saved.get("team_b")

        a_idx = all_teams_flat.index(saved_a) if saved_a in all_teams_flat else 0
        b_idx = all_teams_flat.index(saved_b) if saved_b in all_teams_flat else min(1, len(all_teams_flat) - 1)

        col_slot, col_a, col_vs, col_b = st.columns([1, 5, 1, 5])
        with col_slot:
            st.write(f"**{slot}**")
        with col_a:
            team_a = st.selectbox(
                "Team A",
                options=all_teams_flat,
                index=a_idx,
                key=f"bracket_{selected_round}_{slot}_a",
                label_visibility="collapsed",
            )
        with col_vs:
            st.markdown("<div style='text-align:center;padding-top:8px'>vs</div>", unsafe_allow_html=True)
        with col_b:
            team_b = st.selectbox(
                "Team B",
                options=all_teams_flat,
                index=b_idx,
                key=f"bracket_{selected_round}_{slot}_b",
                label_visibility="collapsed",
            )
        new_matchups.append({"slot": slot, "team_a": team_a, "team_b": team_b})

    st.divider()
    if st.button(f"💾 Save {LOCK_LABELS[selected_round]} Matchups", type="primary", use_container_width=True):
        errors = [
            f"Slot {m['slot']}: Team A and Team B must be different."
            for m in new_matchups if m["team_a"] == m["team_b"]
        ]
        if errors:
            for msg in errors:
                st.error(msg)
        else:
            try:
                save_bracket_round(selected_round, new_matchups)
                st.success(f"✅ {LOCK_LABELS[selected_round]} matchups saved ({n_slots} matches).")
                st.rerun()
            except Exception as e:
                st.error(f"Couldn't save: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — MATCH RESULTS
# ─────────────────────────────────────────────────────────────────────────────
with tab_results:
    st.subheader("Enter match results")
    st.caption("Record the winner and whether the match was decided by penalties.")

    bracket_data = load_real_bracket()
    results_by_round: dict[str, list[dict]] = {}
    for m in bracket_data:
        results_by_round.setdefault(m["round"], []).append(m)

    rounds_with_matchups = [r for r in ROUNDS if r in results_by_round]
    if not rounds_with_matchups:
        st.info("No matchups entered yet — add them in the **Bracket** tab first.")
    else:
        selected_results_round = st.radio(
            "Round",
            options=rounds_with_matchups,
            format_func=lambda r: LOCK_LABELS[r],
            horizontal=True,
            key="results_round_select",
        )

        matchups = sorted(results_by_round[selected_results_round], key=lambda m: m["slot"])
        st.markdown(f"**{LOCK_LABELS[selected_results_round]}**")

        updates: list[dict] = []
        for m in matchups:
            winner_options = [m["team_a"], m["team_b"]]
            saved_winner = m.get("winner")
            winner_idx = winner_options.index(saved_winner) if saved_winner in winner_options else 0

            with st.container(border=True):
                col_match, col_winner, col_pen = st.columns([3, 3, 2])
                with col_match:
                    st.write(f"**Match {m['slot']}:** {m['team_a']} vs {m['team_b']}")
                with col_winner:
                    winner = st.selectbox(
                        "Winner",
                        options=winner_options,
                        index=winner_idx,
                        key=f"res_winner_{m['id']}",
                        label_visibility="visible",
                    )
                with col_pen:
                    is_pen = st.checkbox(
                        "Penalties",
                        value=bool(m.get("is_penalty")),
                        key=f"res_pen_{m['id']}",
                    )
            updates.append({"id": m["id"], "winner": winner, "is_penalty": is_pen})

        st.divider()
        if st.button(f"💾 Save {LOCK_LABELS[selected_results_round]} Results", type="primary", use_container_width=True):
            try:
                save_match_results(updates)
                st.success(f"✅ {LOCK_LABELS[selected_results_round]} results saved.")
                st.rerun()
            except Exception as e:
                st.error(f"Couldn't save: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — PLAYERS & BONUS
# ─────────────────────────────────────────────────────────────────────────────
with tab_pb:

    # ── Golden Boot goals ──────────────────────────────────────────────────────
    st.subheader("Golden Boot goals")
    st.caption("Record goals scored per player. Used to determine the Golden Boot winner.")

    gb_result_locked = load_golden_boot_result_lock()
    if gb_result_locked:
        st.info("🔒 Golden Boot results are locked. Unlock in the Group Results tab to edit.")

    players_by_tier = load_players_by_tier()
    saved_goals = load_player_goals()

    TIER_LABELS = {
        1: "Tier 1 — Tournament favourites",
        2: "Tier 2 — Strong contenders",
        3: "Tier 3 — Mid-range",
        4: "Tier 4 — Sleepers",
    }

    goal_inputs: dict[int, int] = {}
    for tier in sorted(players_by_tier.keys()):
        with st.expander(TIER_LABELS.get(tier, f"Tier {tier}"), expanded=(tier <= 2)):
            for player in players_by_tier[tier]:
                pid = player["id"]
                col_name, col_input = st.columns([4, 1])
                with col_name:
                    st.write(f"{player['name']} — {player['team_name'] or '?'}")
                with col_input:
                    goal_inputs[pid] = st.number_input(
                        "Goals",
                        min_value=0,
                        value=saved_goals.get(pid, 0),
                        step=1,
                        key=f"goals_{pid}",
                        label_visibility="collapsed",
                        disabled=gb_result_locked,
                    )

    if st.button("💾 Save Goals", type="primary", use_container_width=True, key="save_goals", disabled=gb_result_locked):
        try:
            save_player_goals(goal_inputs)
            st.success("✅ Goals saved.")
            st.rerun()
        except Exception as e:
            st.error(f"Couldn't save: {e}")

    st.divider()

    # ── Bonus correct answers ──────────────────────────────────────────────────
    st.subheader("Bonus question answers")
    st.caption(
        "Select the correct option(s) for each question. "
        "Select multiple if the outcome was a tie — all users who picked any correct option receive full points."
    )

    questions = load_bonus_questions()
    for q in questions:
        with st.container(border=True):
            st.markdown(f"**{q['question_text']}**")
            saved_correct = q.get("correct_options") or []
            chosen = st.multiselect(
                "Correct answer(s)",
                options=q["valid_options"],
                default=[o for o in saved_correct if o in q["valid_options"]],
                key=f"bonus_correct_{q['id']}",
            )
            col_save, col_clear = st.columns([2, 1])
            with col_save:
                if st.button("Save", key=f"save_bonus_{q['id']}"):
                    try:
                        save_bonus_correct_options(q["id"], chosen or None)
                        st.success("Saved.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Couldn't save: {e}")
            with col_clear:
                if st.button("Clear", key=f"clear_bonus_{q['id']}"):
                    try:
                        save_bonus_correct_options(q["id"], None)
                        st.success("Cleared.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Couldn't clear: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — USERS
# ─────────────────────────────────────────────────────────────────────────────
with tab_users:
    st.subheader("Reset user picks")
    st.caption(
        "Wipes all prediction data for a user (group stage, champion, bracket, "
        "golden boot, bonus). Does **not** delete the account or profile."
    )

    users = load_all_users()
    if not users:
        st.info("No registered users yet.")
    else:
        user_options = {
            u["id"]: f"{u.get('display_name') or '(no name)'} — {u['email']}"
            for u in users
        }
        selected_uid = st.selectbox(
            "Select user",
            options=list(user_options.keys()),
            format_func=lambda uid: user_options[uid],
            key="reset_user_select",
        )

        selected_user = next((u for u in users if u["id"] == selected_uid), None)
        if selected_user:
            display = selected_user.get("display_name") or selected_user["email"]

            if st.button("🗑️ Reset picks for this user", key="reset_btn_first"):
                st.session_state["reset_confirm_uid"] = selected_uid

            if st.session_state.get("reset_confirm_uid") == selected_uid:
                st.warning(
                    f"⚠️ This will permanently delete **all picks** for **{display}**. "
                    f"This cannot be undone."
                )
                col_yes, col_cancel = st.columns(2)
                with col_yes:
                    if st.button("Yes, reset all picks", type="primary", key="reset_confirm_yes"):
                        try:
                            reset_user_picks(selected_uid)
                            st.session_state.pop("reset_confirm_uid", None)
                            st.success(f"✅ All picks for {display} have been deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Couldn't reset: {e}")
                with col_cancel:
                    if st.button("Cancel", key="reset_confirm_cancel"):
                        st.session_state.pop("reset_confirm_uid", None)
                        st.rerun()