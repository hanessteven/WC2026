"""
Reset a user's password by email.

Usage:
    python seed/reset_user_password.py user@example.com
"""
import os
import sys
import getpass
from pathlib import Path

import bcrypt
from dotenv import load_dotenv
from supabase import create_client

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()


def _client():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


def reset_password(email: str) -> None:
    """Reset a user's password. Prompts for confirmation."""
    email = email.strip().lower()
    client = _client()

    # Find the user
    result = (
        client.table("profiles")
        .select("id, display_name")
        .eq("email", email)
        .execute()
    )

    if not result.data:
        print(f"❌ No user found with email: {email}")
        sys.exit(1)

    user = result.data[0]
    print(f"\n📝 Resetting password for: {user['display_name']} ({email})")

    # Prompt for new password
    while True:
        pw = getpass.getpass("New password (8+ chars): ")
        if not pw:
            print("❌ Password cannot be empty.")
            continue
        if len(pw) < 8:
            print("❌ Password must be at least 8 characters.")
            continue

        pw_confirm = getpass.getpass("Confirm password: ")
        if pw != pw_confirm:
            print("❌ Passwords don't match.")
            continue

        break

    # Confirm
    confirm = input(f"\n⚠️  Reset password for {email}? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Cancelled.")
        sys.exit(0)

    # Hash and update
    pw_hash = bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    client.table("profiles").update({"password_hash": pw_hash}).eq("email", email).execute()

    print(f"✅ Password reset for {email}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python seed/reset_user_password.py <email>")
        sys.exit(1)

    reset_password(sys.argv[1])