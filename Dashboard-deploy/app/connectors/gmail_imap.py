from __future__ import annotations

import email
import imaplib
from datetime import datetime
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime

from app.config import settings
from app.connectors.demo import demo_data
from app.models import ConnectorResult, ConnectorState, Item


def _decode(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _msg_datetime(msg: email.message.Message) -> datetime | None:
    raw = msg.get("Date")
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        if dt is None:
            return None
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    except Exception:
        return None


def _snippet(msg: email.message.Message, limit: int = 140) -> str:
    text = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "")
            if ctype == "text/plain" and "attachment" not in disp:
                try:
                    payload = part.get_payload(decode=True) or b""
                    charset = part.get_content_charset() or "utf-8"
                    text = payload.decode(charset, errors="replace")
                    break
                except Exception:
                    continue
    else:
        try:
            payload = msg.get_payload(decode=True) or b""
            charset = msg.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
        except Exception:
            text = ""
    text = " ".join(text.split())
    return (text[: limit - 1] + "…") if len(text) > limit else text


def _fetch_account(account: dict) -> tuple[list[Item], str | None]:
    host = str(account.get("host") or "imap.gmail.com")
    port = int(account.get("port") or 993)
    user = str(account.get("user") or "")
    pwd = str(account.get("app_password") or "")
    label = str(account.get("label") or user)
    items: list[Item] = []

    mail = imaplib.IMAP4_SSL(host, port)
    try:
        mail.login(user, pwd)
        typ, _ = mail.select("INBOX")
        if typ != "OK":
            raise RuntimeError("Could not open INBOX")
        # Prefer unread; fall back to recent messages if none.
        typ, data = mail.search(None, "UNSEEN")
        ids = (data[0] or b"").split() if typ == "OK" else []
        mode = "unread"
        if not ids:
            typ, data = mail.search(None, "ALL")
            ids = (data[0] or b"").split() if typ == "OK" else []
            mode = "recent"
        ids = ids[-15:]  # newest-ish slice
        ids = list(reversed(ids))
        for msg_id in ids:
            typ, msg_data = mail.fetch(msg_id, "(RFC822)")
            if typ != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            subject = _decode(msg.get("Subject")) or "(no subject)"
            from_name, from_addr = parseaddr(msg.get("From") or "")
            sender = _decode(from_name) or from_addr or "Unknown sender"
            items.append(Item(
                id=f"imap-{label}-{msg_id.decode(errors='ignore')}",
                source=label,
                title=subject,
                subtitle=sender,
                timestamp=_msg_datetime(msg),
                meta={"snippet": _snippet(msg), "from": from_addr, "mode": mode},
            ))
    finally:
        try:
            mail.logout()
        except Exception:
            pass
    return items, label


class GmailImapConnector:
    name = "Gmail (IMAP)"

    async def fetch(self) -> ConnectorResult:
        accounts = settings.gmail_imap_accounts
        if not accounts:
            detail = "Set GMAIL_IMAP_USER and GMAIL_IMAP_APP_PASSWORD in .env (App Password, no Google Cloud needed)"
            if settings.demo_mode:
                return ConnectorResult(
                    state=ConnectorState(name=self.name, status="demo", detail=detail),
                    data={"emails": demo_data()["emails"]},
                )
            return ConnectorResult(state=ConnectorState(name=self.name, status="not_configured", detail=detail), data={})

        all_items: list[Item] = []
        errors: list[str] = []
        ok_labels: list[str] = []
        for acc in accounts:
            label = str(acc.get("label") or acc.get("user") or "Gmail")
            try:
                items, used_label = _fetch_account(acc)
                all_items.extend(items)
                ok_labels.append(f"{used_label}: {len(items)}")
            except Exception as exc:
                errors.append(f"{label}: {str(exc)[:140]}")

        if ok_labels and not errors:
            return ConnectorResult(
                state=ConnectorState(name=self.name, status="ok", detail="; ".join(ok_labels)),
                data={"emails": all_items},
            )
        if ok_labels and errors:
            return ConnectorResult(
                state=ConnectorState(name=self.name, status="error", detail="; ".join(ok_labels + errors)),
                data={"emails": all_items},
            )
        # all failed
        detail = "; ".join(errors) or "Could not connect"
        if settings.demo_mode:
            return ConnectorResult(
                state=ConnectorState(name=self.name, status="error", detail=detail + " (showing demo)"),
                data={"emails": demo_data()["emails"]},
            )
        return ConnectorResult(state=ConnectorState(name=self.name, status="error", detail=detail), data={})
