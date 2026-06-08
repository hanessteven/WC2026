# Deployment & Release

## Pre-Deployment Checklist
TODO: Verification steps before pushing to production
- All tests passing
- Code review complete
- .env variables configured in Streamlit Cloud secrets
- Database migrations completed (if any)

## Streamlit Community Cloud Setup
TODO: Step-by-step guide:
- Connect GitHub repository
- Configure environment variables/secrets
- Deploy branch (typically main)
- Verify app loads and authentication works

## GitHub Integration
TODO: Document the automatic redeploy on push to main

## Secrets Management
TODO: How to securely store Supabase API keys and other sensitive data in Streamlit Cloud secrets manager

## Nightly Results Update Process
TODO: Document how you (the admin) will:
- Access the app or a backend script to add tournament results
- Trigger score recalculation for all users
- Verify results were recorded correctly

## Rollback Procedure
TODO: Steps to revert to a previous version if something breaks in production

## Monitoring & Logging
TODO: How to check app health, error logs, and performance metrics in Streamlit Cloud

## Database Backups
TODO: Strategy for backing up Supabase data (Supabase built-in backup features, export procedures)