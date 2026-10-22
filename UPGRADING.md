# Updating an existing installation

The account update changes password storage and session configuration. Apply it to a development copy first.

1. Stop the app and back up the SQLite database to a private location. Backups of the old database contain plaintext passwords and must not be committed or shared.
2. Install the updated requirements in a Python 3.12 virtual environment.
3. Set a unique `SECRET_KEY`. `PREPRN_DATABASE_PATH` must point to the existing database if it is outside this repository.
4. Run `flask --app app migrate-passwords` before reopening the app. This hashes legacy passwords in a transaction and preserves account IDs and their data. Running it again makes no further changes to already migrated accounts.
5. Verify sign-in with a development account. New accounts are hashed immediately; legacy rows are not accepted by login until migrated.
6. Enable `SESSION_COOKIE_SECURE=true` behind HTTPS and restart the app. Changing the signing secret invalidates existing sessions, so users must sign in again.

POST forms and JSON mutation requests now require CSRF tokens. The included templates send those tokens. External clients must obtain a token/session before submitting mutations.

Credential values are no longer printed at startup. Review existing deployment logs and rotate affected API keys if they were recorded. The older repository is retained as a historical snapshot; deploy this maintained version instead.

The current Gemini integration uses the legacy `google-generativeai` SDK and its original model setting. The provider's SDK/model migration is still pending; verify model availability before relying on live generated descriptions. Tests use fallbacks or mocks and do not certify provider availability.
