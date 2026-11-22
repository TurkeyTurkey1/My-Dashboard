from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "app" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _parse_imap_accounts() -> list[dict[str, str | int]]:
    raw = os.getenv("GMAIL_IMAP_ACCOUNTS", "").strip()
    accounts: list[dict[str, str | int]] = []
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                for i, item in enumerate(parsed):
                    if not isinstance(item, dict):
                        continue
                    user = str(item.get("user") or item.get("email") or "").strip()
                    pwd = str(item.get("app_password") or item.get("password") or "").replace(" ", "").strip()
                    if not (user and pwd):
                        continue
                    accounts.append({
                        "label": str(item.get("label") or user),
                        "user": user,
                        "app_password": pwd,
                        "host": str(item.get("host") or "imap.gmail.com").strip(),
                        "port": int(item.get("port") or 993),
                    })
        except Exception:
            accounts = []
    if accounts:
        return accounts

    def add(user_env: str, pass_env: str, label_fallback: str) -> None:
        user = os.getenv(user_env, "").strip()
        pwd = os.getenv(pass_env, "").replace(" ", "").strip()
        if user and pwd:
            accounts.append({
                "label": os.getenv(user_env + "_LABEL", label_fallback).strip() or label_fallback,
                "user": user,
                "app_password": pwd,
                "host": os.getenv("GMAIL_IMAP_HOST", "imap.gmail.com").strip(),
                "port": int(os.getenv("GMAIL_IMAP_PORT", "993")),
            })

    add("GMAIL_IMAP_USER", "GMAIL_IMAP_APP_PASSWORD", "Gmail")
    add("GMAIL_IMAP_USER_2", "GMAIL_IMAP_APP_PASSWORD_2", "Gmail 2")
    add("GMAIL_IMAP_USER_3", "GMAIL_IMAP_APP_PASSWORD_3", "Gmail 3")
    return accounts


class Settings:
    def __init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        load_dotenv(ROOT / ".env", override=True)
        self.demo_mode = _flag("DEMO_MODE", "true")
        self.cache_seconds = int(os.getenv("CACHE_SECONDS", "30"))

        self.gmail_imap_accounts = _parse_imap_accounts()

        self.seqta_mode = os.getenv("SEQTA_MODE", "import").strip().lower()  # import | playwright | off
        self.seqta_import_path = ROOT / os.getenv("SEQTA_IMPORT_FILE", "app/data/seqta.json").strip()

        self.seqta_base_url = os.getenv("SEQTA_BASE_URL", "").strip()
        self.seqta_username = os.getenv("SEQTA_USERNAME", "").strip()
        self.seqta_password = os.getenv("SEQTA_PASSWORD", "").strip()
        self.seqta_timetable_url = os.getenv("SEQTA_TIMETABLE_URL", "").strip()
        self.seqta_assessments_url = os.getenv("SEQTA_ASSESSMENTS_URL", "").strip()
        self.seqta_results_url = os.getenv("SEQTA_RESULTS_URL", "").strip()
        self.seqta_user_selector = os.getenv("SEQTA_USER_SELECTOR", 'input[name="username"], input[type="email"], #username').strip()
        self.seqta_pass_selector = os.getenv("SEQTA_PASS_SELECTOR", 'input[type="password"], #password').strip()
        self.seqta_login_selector = os.getenv("SEQTA_LOGIN_SELECTOR", 'button[type="submit"], input[type="submit"]').strip()
        self.seqta_row_selector = os.getenv("SEQTA_ROW_SELECTOR", "tr").strip()
        self.seqta_wait_ms = int(os.getenv("SEQTA_WAIT_MS", "2000"))
        self.seqta_headless = _flag("SEQTA_HEADLESS", "true")

        self.dashboard_password = os.getenv("DASHBOARD_PASSWORD", "").strip()
        self.session_secret = os.getenv("SESSION_SECRET", "change-me-in-production").strip()


settings = Settings()
