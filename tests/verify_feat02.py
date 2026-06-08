"""
AC verification for feature 02 -- run directly: python tests/verify_feat02.py
Checks: all tables exist, lock_state seeded, RLS blocks anon writes, RLS blocks unauthenticated reads.
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

URL = os.environ["SUPABASE_URL"]
ANON = os.environ["SUPABASE_KEY"]
SERVICE = os.environ["SUPABASE_SERVICE_KEY"]

anon = create_client(URL, ANON)
admin = create_client(URL, SERVICE)

PASS = "[PASS]"
FAIL = "[FAIL]"

results = []

# -- AC 1: All tables exist ---------------------------------------------------
EXPECTED_TABLES = [
    "profiles", "allowed_emails",
    "seed_groups", "seed_teams", "seed_players", "bonus_question_defs",
    "lock_state", "real_bracket",
    "results_group_stage", "results_player_goals",
    "predictions_group_stage", "predictions_champion", "predictions_bracket",
    "predictions_golden_boot", "predictions_bonus",
    "scores",
]

print("\n-- AC 1: Tables exist --------------------------------------------------")
for table in EXPECTED_TABLES:
    try:
        admin.table(table).select("*").limit(1).execute()
        print(f"  {PASS}  {table}")
        results.append(True)
    except Exception as e:
        print(f"  {FAIL}  {table}  ({e})")
        results.append(False)

# -- AC 2: lock_state pre-seeded with all 9 categories -----------------------
print("\n-- AC 2: lock_state pre-seeded -----------------------------------------")
EXPECTED_LOCKS = {"group_stage", "champion", "golden_boot", "bonus", "R32", "R16", "QF", "SF", "F"}
try:
    rows = admin.table("lock_state").select("category").execute().data
    found = {r["category"] for r in rows}
    missing = EXPECTED_LOCKS - found
    if not missing:
        print(f"  {PASS}  All 9 lock categories present")
        results.append(True)
    else:
        print(f"  {FAIL}  Missing categories: {missing}")
        results.append(False)
except Exception as e:
    print(f"  {FAIL}  Could not query lock_state: {e}")
    results.append(False)

# -- AC 3: Anon key cannot write to lock_state (RLS blocks it) ---------------
print("\n-- AC 3: Anon key blocked from writing lock_state ----------------------")
try:
    resp = anon.table("lock_state").update({"is_locked": True}).eq("category", "group_stage").execute()
    if resp.data:
        print(f"  {FAIL}  Anon key was able to write lock_state -- RLS not working!")
        results.append(False)
    else:
        print(f"  {PASS}  Anon key write silently blocked (0 rows affected)")
        results.append(True)
except Exception as e:
    print(f"  {PASS}  Anon key blocked: {str(e)[:100]}")
    results.append(True)

# -- AC 4: Unauthenticated anon key gets no prediction rows ------------------
print("\n-- AC 4: Unauthenticated anon key gets no prediction rows --------------")
try:
    rows = anon.table("predictions_group_stage").select("*").execute().data
    if rows:
        print(f"  {FAIL}  Unauthenticated read returned {len(rows)} rows -- RLS not working!")
        results.append(False)
    else:
        print(f"  {PASS}  Unauthenticated read returned 0 rows (RLS enforced)")
        results.append(True)
except Exception as e:
    print(f"  {PASS}  Unauthenticated read blocked: {str(e)[:100]}")
    results.append(True)

# -- Summary ------------------------------------------------------------------
print("\n-----------------------------------------------------------------------")
passed = sum(results)
total = len(results)
overall = PASS if passed == total else FAIL
print(f"  {overall}  {passed}/{total} checks passed\n")