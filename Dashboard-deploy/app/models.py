from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ConnectorStatus = Literal["ok", "demo", "not_configured", "error", "disabled"]


class ConnectorState(BaseModel):
    name: str
    status: ConnectorStatus
    detail: str = ""


class Item(BaseModel):
    id: str | None = None
    source: str
    title: str
    subtitle: str | None = None
    url: str | None = None
    timestamp: datetime | None = None
    due: datetime | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class ConnectorResult(BaseModel):
    state: ConnectorState
    data: dict[str, list[Item]] = Field(default_factory=dict)


class DashboardData(BaseModel):
    generated_at: datetime
    connectors: list[ConnectorState]
    emails: list[Item]
    timetable: list[Item]
    assignments: list[Item]
    warnings: list[str] = Field(default_factory=list)
