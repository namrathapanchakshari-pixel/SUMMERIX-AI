# SUMMERIX AI
SUMMARIX AI account pages update

Files in this package:
- app.py: updated Flask backend with /profile, /history, /settings and per-user upload-history records. Logout clears the session.
- profile.html, history.html, settings.html: put these in your project's templates/ folder.
- WORKSPACE_ACCOUNT_NAV_SNIPPET.html: add this small link block inside the existing workspace.html header so users can reach the pages.

Safe replacement steps:
1. Stop Flask with Ctrl+C.
2. Back up your current app.py (for example, copy it to app_backup.py).
3. Replace app.py with this package's app.py.
4. Copy profile.html, history.html and settings.html into D:\SUMMERIX AI\templates\. Do not replace workspace.html.
5. Add the navigation snippet inside the existing workspace.html header.
6. Start the app using python app.py and test Profile, Document history, Settings, and Log out.

Existing users and database rows are not deleted. Do not share your .env file.
SUMMARIX AI — Saved TXT Results Feature

1. Extract this ZIP.
2. Copy install_saved_results.py into D:\SUMMERIX AI (same folder as app.py).
3. Open PowerShell in D:\SUMMERIX AI. Activate your venv if needed.
4. Run: python install_saved_results.py
5. Restart: python app.py
6. Generate a NEW summary and test Download TXT.

The installer backs up app.py before changing it, adds persistent TXT saving and protected view/download routes, and merges saved results into the history data sent to history.html. It creates templates/saved_result.html. Your existing history template may need a small link change to make result rows clickable; this package does not replace your design. Old results generated before installation are not backfilled.

If the installer says it cannot safely find a code section, stop and send me that exact message.
SUMMARIX AI admin upgrade bundle. Contains four admin templates, a route patch, and installation notes. It intentionally excludes .env, database, uploads, saved results, and credentials.