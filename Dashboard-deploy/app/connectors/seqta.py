from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings
from app.connectors.demo import demo_data
from app.models import ConnectorResult, ConnectorState, Item


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    try:
        # ISO / with Z
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None


def _item(raw: Any, bucket: str) -> Item | None:
    if isinstance(raw, str):
        raw = {"title": raw}
    if not isinstance(raw, dict):
        return None
    title = raw.get("title") or raw.get("name") or raw.get("subject") or raw.get("assessment") or raw.get("class")
    if not title:
        return None
    subtitle = (
        raw.get("subtitle") or raw.get("teacher") or raw.get("room") or raw.get("location")
        or raw.get("course") or raw.get("code") or raw.get("notes")
    )
    ts = _parse_dt(raw.get("start") or raw.get("time") or raw.get("timestamp") or raw.get("date"))
    due = _parse_dt(raw.get("due") or raw.get("dueDate") or raw.get("end") or raw.get("deadline"))
    meta = dict(raw)
    for k in ("title", "name", "subject", "assessment", "class", "subtitle", "teacher", "room", "location", "course", "code", "notes", "start", "time", "timestamp", "date", "due", "dueDate", "end", "deadline", "url", "id"):
        meta.pop(k, None)
    # keep some useful keys in meta as-is
    for k in ("day", "period", "status", "color", "colour"):
        if k in raw and raw.get(k) is not None:
            meta[k] = raw.get(k)
    return Item(
        id=str(raw.get("id")) if raw.get("id") is not None else None,
        source="SEQTA",
        title=str(title),
        subtitle=str(subtitle) if subtitle not in (None, "") else None,
        url=str(raw.get("url")) if raw.get("url") else None,
        timestamp=ts,
        due=due,
        meta=meta,
    )


def normalize(payload: Any) -> dict[str, list[Item]]:
    out: dict[str, list[Item]] = {"timetable": [], "assignments": []}
    if isinstance(payload, list):
        # ambiguous list: treat as assignments
        for raw in payload:
            it = _item(raw, "assignments")
            if it:
                out["assignments"].append(it)
        return out
    if not isinstance(payload, dict):
        return out

    mapping = {
        "timetable": "timetable", "classes": "timetable", "schedule": "timetable", "periods": "timetable", "today": "timetable",
        "assignments": "assignments", "assessments": "assignments", "upcoming": "assignments", "homework": "assignments", "duework": "assignments", "tasks": "assignments",
    }
    for key, bucket in mapping.items():
        rows = payload.get(key)
        if not isinstance(rows, list):
            continue
        for raw in rows:
            it = _item(raw, bucket)
            if it:
                out[bucket].append(it)

    # some exports nest under data
    if not any(out.values()) and isinstance(payload.get("data"), (dict, list)):
        return normalize(payload["data"])

    return out


def _load_import(path: Path) -> dict[str, list[Item]]:
    if not path.exists():
        return {"timetable": [], "assignments": []}
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {"timetable": [], "assignments": []}
    return normalize(json.loads(raw))


async def _perform_login(page) -> None:
    # Generic SEQTA/login form first
    try:
        if "login.microsoftonline" not in page.url and "microsoftonline" not in page.url:
            if await page.locator(settings.seqta_user_selector).count():
                await page.fill(settings.seqta_user_selector, settings.seqta_username)
            if await page.locator(settings.seqta_pass_selector).count():
                await page.fill(settings.seqta_pass_selector, settings.seqta_password)
            if await page.locator(settings.seqta_login_selector).count():
                await page.click(settings.seqta_login_selector)
                await page.wait_for_load_state("networkidle", timeout=30000)
                await page.wait_for_timeout(1500)
    except Exception:
        pass

    # Microsoft SSO flow (common for school SEQTA)
    for _ in range(6):
        url = page.url.lower()
        if "login.microsoftonline" not in url and "login.live.com" not in url:
            break
        try:
            # Email/username step
            email_loc = page.locator('input[name="loginfmt"], input[type="email"]')
            if await email_loc.count() and await email_loc.first.is_visible():
                current = ""
                try:
                    current = await email_loc.first.input_value()
                except Exception:
                    pass
                if not current:
                    await email_loc.first.fill(settings.seqta_username)
                next_btn = page.locator('#idSIButton9, input[type="submit"]')
                if await next_btn.count():
                    await next_btn.first.click()
                    await page.wait_for_timeout(1500)

            # Password step
            pass_loc = page.locator('input[name="passwd"], input[type="password"]')
            if await pass_loc.count() and await pass_loc.first.is_visible():
                current = ""
                try:
                    current = await pass_loc.first.input_value()
                except Exception:
                    pass
                if not current:
                    await pass_loc.first.fill(settings.seqta_password)
                sign_btn = page.locator('#idSIButton9, input[type="submit"]')
                if await sign_btn.count():
                    await sign_btn.first.click()
                    await page.wait_for_load_state("networkidle", timeout=30000)
                    await page.wait_for_timeout(1500)

            # "Stay signed in?" prompt
            stay = page.locator('#idSIButton9')
            kmsi_text = page.locator('text=Stay signed in')
            if await kmsi_text.count() and await stay.count():
                await stay.first.click()
                await page.wait_for_load_state("networkidle", timeout=30000)
                await page.wait_for_timeout(1500)

            await page.wait_for_timeout(1000)
        except Exception:
            await page.wait_for_timeout(1000)

    try:
        await page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass


async def _scrape_playwright() -> dict[str, list[Item]]:
    try:
        from playwright.async_api import async_playwright
    except Exception as exc:
        raise RuntimeError(
            "Playwright is not installed. Run: pip install -r requirements-seqta.txt && python -m playwright install chromium"
        ) from exc

    if not (settings.seqta_base_url and settings.seqta_username and settings.seqta_password):
        raise RuntimeError("Set SEQTA_BASE_URL, SEQTA_USERNAME and SEQTA_PASSWORD in .env")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=settings.seqta_headless)
        context = await browser.new_context()
        page = await context.new_page()
        try:
            await page.goto(settings.seqta_base_url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(1500)
            await _perform_login(page)
            await page.wait_for_timeout(settings.seqta_wait_ms)

            out: dict[str, list[Item]] = {"timetable": [], "assignments": []}
            targets = [
                ("timetable", settings.seqta_timetable_url),
                ("assignments", settings.seqta_assessments_url),
            ]
            # if no specific page URLs given, scrape current page as timetable best-effort
            if not any(url for _, url in targets):
                targets = [("timetable", page.url)]

            for bucket, url in targets:
                if url:
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                        await page.wait_for_timeout(settings.seqta_wait_ms)
                    except Exception:
                        continue
                rows = page.locator(settings.seqta_row_selector)
                count = await rows.count()
                for i in range(min(count, 200)):
                    try:
                        txt = (await rows.nth(i).inner_text()).strip()
                    except Exception:
                        continue
                    if not txt:
                        continue
                    parts = [ln.strip() for ln in txt.splitlines() if ln.strip()]
                    if not parts:
                        continue
                    title = parts[0][:160]
                    sub = " · ".join(parts[1:4])[:200] if len(parts) > 1 else None
                    out[bucket].append(Item(source="SEQTA", title=title, subtitle=sub, meta={"scraped": True}))
            return out
        finally:
            await context.close()
            await browser.close()


class SeqtaConnector:
    name = "SEQTA"

    async def fetch(self) -> ConnectorResult:
        mode = settings.seqta_mode
        if mode == "off":
            return ConnectorResult(state=ConnectorState(name=self.name, status="disabled", detail="SEQTA disabled in .env"), data={})

        try:
            if mode == "playwright":
                data = await _scrape_playwright()
                detail = "Playwright scrape"
            else:
                data = await asyncio.to_thread(_load_import, settings.seqta_import_path)
                if not any(data.values()):
                    detail = f"No imported data yet ({settings.seqta_import_path.name}). Use Import in the dashboard."
                    if settings.demo_mode:
                        demo = demo_data()
                        return ConnectorResult(
                            state=ConnectorState(name=self.name, status="demo", detail=detail),
                            data={"timetable": demo["timetable"], "assignments": demo["assignments"]},
                        )
                    return ConnectorResult(state=ConnectorState(name=self.name, status="not_configured", detail=detail), data={})
                detail = f"Imported ({sum(len(v) for v in data.values())} items)"

            if not any(data.values()):
                raise RuntimeError("No timetable/assignments found. Check SEQTA URLs/selectors or import JSON.")
            return ConnectorResult(state=ConnectorState(name=self.name, status="ok", detail=detail), data=data)
        except Exception as exc:
            msg = str(exc)[:220]
            if settings.demo_mode:
                demo = demo_data()
                return ConnectorResult(
                    state=ConnectorState(name=self.name, status="error", detail=msg + " (showing demo)"),
                    data={"timetable": demo["timetable"], "assignments": demo["assignments"]},
                )
            return ConnectorResult(state=ConnectorState(name=self.name, status="error", detail=msg), data={})
