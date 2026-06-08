# 05 — Authentication (Magic Link + Whitelist)

**Status:** ✅ Done
**Depends on:** 01, 02

## Goal
Let friends sign in passwordlessly via Supabase magic link, restricted to a whitelist of allowed emails. Derive admin status from the `ADMIN_EMAILS` config.

## Requirements
- **Magic link sign-in:** user enters email → Supabase sends a magic link → clicking it authenticates the session.
- **Whitelist enforcement:** only emails present in `allowed_emails` may sign in. Non-whitelisted emails get a friendly "you're not on the guest list" message and no link is sent (or the session is rejected).
- **Session persistence:** keep the user logged in across Streamlit reruns (`st.session_state`), with a logout action.
- **Admin flag:** `is_admin = user.email in ADMIN_EMAILS`. Used to gate the admin page (feature 10).
- **Profile bootstrap:** on first login, create a `profiles` row; prompt for `display_name` if unset.

## Acceptance criteria
- A whitelisted email receives a link and logs in successfully.
- A non-whitelisted email is cleanly rejected.
- An admin email sees admin-only navigation; a normal user does not.
- Logout clears the session.

## TODO
- Work out the Streamlit + Supabase magic-link redirect/token-capture flow (Streamlit has no native callback route — confirm token handling approach).
- Decide session timeout behavior.