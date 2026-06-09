"""Golden Boot Salary-Cap Draft — pick players within a $100 budget."""
import streamlit as st

from src.auth import get_current_user
from src.models import GOLDEN_BOOT_BUDGET, GOLDEN_BOOT_WINNER_PTS
from src.predictions import (
    is_locked,
    load_golden_boot_picks,
    load_players_by_tier,
    load_teams_by_group,
    save_golden_boot_picks,
)

TIER_LABELS = {
    1: "Tier 1 — Tournament favourites",
    2: "Tier 2 — Strong contenders",
    3: "Tier 3 — Mid-range value",
    4: "Tier 4 — Sleeper picks",
}

user = get_current_user()

st.title("⚽ Golden Boot Draft")
st.caption(
    f"Draft players within a **${GOLDEN_BOOT_BUDGET} budget**. "
    f"You earn **{GOLDEN_BOOT_WINNER_PTS} pts** if any player you drafted wins the Golden Boot "
    f"(top scorer of the tournament). Seeded list only — no write-ins."
)

locked = is_locked("golden_boot")
if locked:
    st.warning("🔒 Golden Boot draft is locked — shown read-only.")

# ── Load data ──────────────────────────────────────────────────────────────────
players_by_tier = load_players_by_tier()
saved_picks: set[int] = load_golden_boot_picks(user["id"])

# Build flag map from teams (best-effort — missing teams show no flag)
teams_by_group = load_teams_by_group()
flag_map = {t["name"]: t.get("flag_emoji") or "" for g in teams_by_group.values() for t in g}

# ── Render player tiers ────────────────────────────────────────────────────────
checked: dict[int, bool] = {}   # player_id -> currently checked

for tier in sorted(players_by_tier.keys()):
    players = players_by_tier[tier]
    st.subheader(TIER_LABELS.get(tier, f"Tier {tier}"))

    for player in players:
        pid = player["id"]
        flag = flag_map.get(player["team_name"] or "", "")
        label = f"{flag} **{player['name']}** — {player['team_name'] or '?'}  `${player['cost']}`".strip()

        checked[pid] = st.checkbox(
            label,
            value=pid in saved_picks,
            key=f"gb_{pid}",
            disabled=locked,
        )

# ── Live budget meter ──────────────────────────────────────────────────────────
all_players_flat = [p for players in players_by_tier.values() for p in players]
cost_map = {p["id"]: p["cost"] for p in all_players_flat}

spent = sum(cost_map[pid] for pid, ticked in checked.items() if ticked)
remaining = GOLDEN_BOOT_BUDGET - spent
over_budget = spent > GOLDEN_BOOT_BUDGET

st.divider()
col_spent, col_left = st.columns(2)
with col_spent:
    st.metric("Budget used", f"${spent} / ${GOLDEN_BOOT_BUDGET}")
with col_left:
    st.metric("Remaining", f"${remaining}" if remaining >= 0 else f"-${abs(remaining)}")

if over_budget:
    st.error(f"Over budget by ${abs(remaining)}. Remove players before saving.")
elif spent == 0:
    st.caption("No players drafted yet.")
else:
    st.progress(spent / GOLDEN_BOOT_BUDGET, text=f"${spent} of ${GOLDEN_BOOT_BUDGET} spent")

# ── Save ───────────────────────────────────────────────────────────────────────
if not locked:
    st.divider()
    if st.button("💾 Save Draft", type="primary", use_container_width=True):
        if over_budget:
            st.error(f"Cannot save — over budget by ${abs(remaining)}. Remove players first.")
        else:
            selected_ids = [pid for pid, ticked in checked.items() if ticked]
            try:
                save_golden_boot_picks(user["id"], selected_ids)
                st.success(
                    f"✅ Draft saved — {len(selected_ids)} player(s), ${spent} spent."
                )
                st.rerun()
            except Exception as e:
                st.error(f"Couldn't save: {e}")
