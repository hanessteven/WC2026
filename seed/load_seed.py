"""
Seed loader — populates all static reference tables in Supabase.
Idempotent: safe to run multiple times (uses upsert with on-conflict ignore).

Usage:
    python seed/load_seed.py
"""
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from supabase import create_client

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import SeedTeam, SeedPlayer, BonusQuestionDef

load_dotenv()

SEED_DIR = Path(__file__).parent


def _client():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


def _load_yaml(filename: str) -> dict:
    with open(SEED_DIR / filename, encoding="utf-8") as f:
        return yaml.safe_load(f)


def seed_groups_and_teams(client) -> None:
    data = _load_yaml("groups_and_teams.yaml")
    groups = list(data["groups"].keys())

    # seed_groups
    group_rows = [{"letter": letter} for letter in groups]
    client.table("seed_groups").upsert(group_rows, on_conflict="letter").execute()
    print(f"  seed_groups: {len(group_rows)} rows upserted")

    # seed_teams — validate each against SeedTeam model (sans id, which DB assigns)
    team_rows = []
    for letter, teams in data["groups"].items():
        for t in teams:
            # Validate shape before insert
            SeedTeam(id=0, name=t["name"], group_letter=letter,
                     flag_emoji=t.get("flag_emoji"))
            team_rows.append({
                "name": t["name"],
                "group_letter": letter,
                "flag_emoji": t.get("flag_emoji"),
            })

    client.table("seed_teams").upsert(team_rows, on_conflict="name").execute()
    print(f"  seed_teams:  {len(team_rows)} rows upserted")


def seed_players(client) -> None:
    data = _load_yaml("players.yaml")
    rows = []
    for p in data["players"]:
        SeedPlayer(id=0, name=p["name"], team_name=p.get("team_name"),
                   tier=p["tier"], cost=p["cost"])
        rows.append({
            "name": p["name"],
            "team_name": p.get("team_name"),
            "tier": p["tier"],
            "cost": p["cost"],
        })

    # Upsert on name (no natural unique key beyond that in the seed)
    client.table("seed_players").upsert(rows, on_conflict="name").execute()
    print(f"  seed_players: {len(rows)} rows upserted")


def seed_bonus_questions(client) -> None:
    data = _load_yaml("bonus_questions.yaml")
    rows = []
    for q in data["questions"]:
        BonusQuestionDef(
            id=0,
            question_text=q["question_text"],
            valid_options=q["valid_options"],
            point_value=q["point_value"],
        )
        rows.append({
            "question_text": q["question_text"],
            "valid_options": q["valid_options"],
            "correct_options": None,
            "point_value": q["point_value"],
        })

    # Upsert on question_text so re-runs don't duplicate questions
    client.table("bonus_question_defs").upsert(
        rows, on_conflict="question_text"
    ).execute()
    print(f"  bonus_question_defs: {len(rows)} rows upserted")


def seed_allowed_emails(client) -> None:
    data = _load_yaml("allowed_emails.yaml")
    rows = [{"email": e.strip().lower()} for e in data["emails"] if e]
    client.table("allowed_emails").upsert(rows, on_conflict="email").execute()
    print(f"  allowed_emails: {len(rows)} rows upserted")


def main() -> None:
    print("Loading seed data...")
    client = _client()

    seed_groups_and_teams(client)
    seed_players(client)
    seed_bonus_questions(client)
    seed_allowed_emails(client)

    print("\nDone. All seed tables populated.")


if __name__ == "__main__":
    main()