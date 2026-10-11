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
