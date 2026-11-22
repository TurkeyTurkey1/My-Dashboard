# My Dashboard

Local dashboard for **Gmail**, **SEQTA timetable**, and **upcoming assignments**.

## Easiest way to run (Windows)

1. Double-click **`Start Dashboard.bat`** in this folder.
2. It will install/check dependencies, start the dashboard, and open http://127.0.0.1:8000.
3. In the dashboard, click **Import / Setup** to connect Gmail or import SEQTA data.

> You need Python 3.10+ installed. If you don’t have it: https://www.python.org/downloads/

To stop the dashboard, close the `Start Dashboard.bat` window.

## Connect Gmail (easiest: App Password, no Google Cloud/OAuth)

This avoids Google Cloud OAuth setup.

1. Open the dashboard and click **Import / Setup**.
2. In your Google account, enable **2‑Step Verification** and create an **App Password**: https://myaccount.google.com/apppasswords
3. Enter your Gmail address and the 16-character App Password, then click **Save Gmail settings**.
4. The Inbox panel should refresh with your emails.

**Notes:**
- Personal Gmail usually works with App Passwords. Some school/work Google accounts block App Passwords or IMAP; those accounts may not connect this way.
- You can add multiple accounts (up to 3) in the setup form if they allow IMAP/App Passwords.
- App Passwords can be revoked anytime from your Google account security page.

## Add SEQTA

### Option 1: Manual import (easiest/reliable)
1. Click **Import / Setup**.
2. Paste JSON with `timetable` and `assignments` and click **Import SEQTA JSON**.
3. Data is saved locally to `app/data/seqta.json`.

Example:

```json
{
  "timetable": [
    {"day":"Monday","start":"08:50","end":"09:40","subject":"Mathematics","room":"B12","teacher":"Mr Nguyen","period":"P1"}
  ],
  "assignments": [
    {"title":"Essay draft","subject":"English","due":"2026-11-25T23:59","notes":"800 words","status":"pending"}
  ]
}
```

### Option 2: Playwright automation (advanced/school-specific)
SEQTA has no public API, so automation is experimental and may need tweaking for your school.

1. Install: `python -m pip install -r requirements-seqta.txt`
2. Install browser: `python -m playwright install chromium`
3. Edit `.env`: set `SEQTA_MODE=playwright`, `SEQTA_BASE_URL`, `SEQTA_USERNAME`, `SEQTA_PASSWORD`, and (recommended) `SEQTA_TIMETABLE_URL` / `SEQTA_ASSESSMENTS_URL`.
4. Adjust `SEQTA_*_SELECTOR` values if needed. Set `SEQTA_HEADLESS=false` to debug.
5. Restart the dashboard.

## Manual terminal run (optional)

```powershell
cd "Dashboard"
python -m pip install -r requirements.txt
python run.py
```

## Privacy

- **Local mode:** runs on `127.0.0.1` by default.
- **Hosted mode:** set a strong `DASHBOARD_PASSWORD` before deploying. Anyone with the URL and password can view the connected data.
- `.env` contains credentials/settings and `app/data/` contains imported SEQTA data — both are gitignored. **Never commit `.env` or `app/data/*`.**

## Deploy as a private website (GitHub + Render)

GitHub stores the code, but it cannot run this Python/Playwright app by itself. The simplest path is a **private GitHub repo** deployed to **Render**.

### 1. Prep the repo locally

Git is not installed in this environment, so do these steps on your PC (install [Git for Windows](https://git-scm.com/download/win) first if needed):

1. Make sure `Dashboard/.env` is **not** committed (it is already in `.gitignore`).
2. Create a **Private** repository on GitHub (e.g. `my-dashboard`).
3. In PowerShell, from the `Dashboard` folder:

   ```powershell
   cd "C:\Users\wupit01\Documents\Default Project\Dashboard"
   git init
   git add .
   git commit -m "Initial dashboard"
   git branch -M main
   git remote add origin https://github.com/<your-username>/my-dashboard.git
   git push -u origin main
   ```

4. Before pushing, confirm secrets are not staged: `git status` should not show `.env` or `app/data/*`.

### 2. Deploy on Render

1. Create a [Render](https://render.com/) account and choose **New + > Web Service**.
2. Connect GitHub and select your **private** repo.
3. Render can detect the included `Dockerfile` (or use `render.yaml` as a Blueprint).
4. Set environment variables in Render (do **not** put these in the repo):

   | Variable | Value |
   |---|---|
   | `DASHBOARD_PASSWORD` | Strong password you will use to sign in (required) |
   | `SESSION_SECRET` | Long random string |
   | `DEMO_MODE` | `false` |
   | `CACHE_SECONDS` | `300` (or higher to reduce scraping) |
   | `SEQTA_HEADLESS` | `true` |
   | `RELOAD` | `false` |
   | `HOST` | `0.0.0.0` |
   | `GMAIL_IMAP_USER` | Your Gmail address |
   | `GMAIL_IMAP_APP_PASSWORD` | 16-char Gmail App Password |
   | `GMAIL_IMAP_HOST` | `imap.gmail.com` |
   | `GMAIL_IMAP_PORT` | `993` |
   | `SEQTA_MODE` | `playwright` |
   | `SEQTA_BASE_URL` | `https://coneqt.tatachilla.sa.edu.au/` |
   | `SEQTA_USERNAME` | Your SEQTA/Microsoft login email |
   | `SEQTA_PASSWORD` | Your SEQTA password |
   | `SEQTA_TIMETABLE_URL` | `https://coneqt.tatachilla.sa.edu.au/#?page=/timetable` |
   | `SEQTA_ASSESSMENTS_URL` | `https://coneqt.tatachilla.sa.edu.au/#?page=/assessments` |

5. Deploy. The first Docker build can take several minutes because it installs Playwright/Chromium.
6. Open the Render URL and sign in with `DASHBOARD_PASSWORD`.

### Notes / caveats

- **Single-user only.** This password gate protects access, but it is not a full multi-user auth system.
- **Secrets:** keep them in Render environment variables, not in GitHub. Keep the repo private.
- **SEQTA on hosted servers:** Playwright/Microsoft SSO can be slower or fragile on cloud IPs; keep `SEQTA_HEADLESS=true`. If it fails, you can fall back to `SEQTA_MODE=import` and upload JSON manually.
- **Speed:** increase `CACHE_SECONDS` (e.g. `600`) and avoid frequent refreshes; SEQTA scraping is the slowest part.
- **School Gmail:** `@tatachilla.sa.edu.au` is likely Microsoft 365 and may not work with Gmail IMAP/App Passwords; it may require Microsoft Graph/OAuth and school admin consent.
