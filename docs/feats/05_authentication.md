# 05 — Authentication (Email + Password + Whitelist)

**Status:** ✅ Done
**Depends on:** 01, 02

## Goal
Let friends sign in with email + password, restricted to a whitelist of allowed
emails. Derive admin status from the `ADMIN_EMAILS` config.

## Why not magic link
Magic link was the original plan but is unworkable on this stack:
- Supabase returns the session in the URL **fragment** (`#access_token=...`),
  which is browser-only and never reaches Streamlit's server-side script.
- The server-readable alternatives (6-digit OTP code, `?token_hash=` query param)
  require customizing the Supabase email template, which the free tier gates
  behind paid custom SMTP.

So auth is fully self-contained: no external provider, no email sending.

## Requirements
- **Self-registration (whitelist-gated):** a user enters their email; only emails
  in `allowed_emails` may register. They choose a password (bcrypt-hashed into
  `profiles.password_hash`) and a `display_name`.
- **Sign in:** returning users authenticate with email + password.
- **Session persistence:** the session is stored in a signed cookie
  (`itsdangerous`, 30-day expiry) so it survives a page refresh. Cookie ops are
  best-effort — if the cookie component fails, login still works for the session.
- **Admin flag:** `is_admin = user.email in ADMIN_EMAILS`. Gates the admin page.
- **Profiles are self-owned:** migration `005` detaches `profiles.id` from
  `auth.users`, self-generates UUIDs, adds `password_hash`, makes `email` unique,
  and retires the old Supabase-Auth signup trigger.

## Config
- `COOKIE_SECRET` — secret used to sign the session cookie (set in `.env` and in
  Streamlit Cloud secrets). Rotating it logs everyone out.

## Acceptance criteria
- A whitelisted email can register and is logged in immediately.
- A non-whitelisted email is cleanly rejected at registration.
- Registering an already-registered email is cleanly rejected.
- Sign in with correct credentials succeeds; wrong password is rejected.
- An admin email sees admin-only navigation; a normal user does not.
- A page refresh keeps the user signed in (cookie restore).
- Logout clears the session and the cookie.

## Notes / future
- Whitelist-email squatting (someone registering another friend's email first)
  is acceptable for a private friend group; the whitelist itself is gitignored.
- No password reset flow yet — admin can clear a `password_hash` to let a user
  re-register. Add a self-serve reset later if needed.