# ai-generated: 100% - drafted with ChatGPT from API.md and CHECKS.md and reviewed by the student

import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field


UTC = timezone.utc
WARSAW = ZoneInfo("Europe/Warsaw")

DB_PATH = os.getenv("SVCDESK_DB", "/data/svcdesk.db")

C1 = "wallclock"
C2 = "immutable"
C3 = "matrix"


app = FastAPI(title="svcdesk")


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation",
                "message": "request validation failed",
            }
        },
    )


class ReporterInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=100)
    email: str | None = None
    vip: bool = False


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    reporter: ReporterInput
    impact: int = Field(ge=1, le=3, strict=True)
    urgency: int = Field(ge=1, le=3, strict=True)
    related_to: str | None = None


PRIORITY_MATRIX = {
    (1, 1): "P1",
    (1, 2): "P2",
    (1, 3): "P3",
    (2, 1): "P2",
    (2, 2): "P3",
    (2, 3): "P4",
    (3, 1): "P3",
    (3, 2): "P4",
    (3, 3): "P4",
}


SLA_TARGETS = {
    "P1": {
        "ack": timedelta(minutes=15),
        "resolve": timedelta(hours=4),
    },
    "P2": {
        "ack": timedelta(hours=1),
        "resolve": timedelta(hours=8),
    },
    "P3": {
        "ack": timedelta(hours=4),
        "resolve": timedelta(hours=24),
    },
    "P4": {
        "ack": timedelta(hours=8),
        "resolve": timedelta(hours=72),
    },
}


def init_db() -> None:
    parent = Path(DB_PATH).parent
    parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL
            )
            """
        )
        connection.commit()


def save_ticket(ticket: dict[str, Any]) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            INSERT INTO tickets (id, data)
            VALUES (?, ?)
            ON CONFLICT(id) DO UPDATE SET data = excluded.data
            """,
            (ticket["id"], json.dumps(ticket)),
        )
        connection.commit()


def load_ticket(ticket_id: str) -> dict[str, Any]:
    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            "SELECT data FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()

    if row is None:
        raise ApiError(404, "not_found", "ticket not found")

    return json.loads(row[0])


def load_tickets() -> list[dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(
            "SELECT data FROM tickets"
        ).fetchall()

    return [json.loads(row[0]) for row in rows]


def parse_instant(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise ApiError(422, "validation", "invalid RFC 3339 timestamp")

    if parsed.tzinfo is None:
        raise ApiError(422, "validation", "timestamp must include an offset")

    return parsed.astimezone(UTC)


def format_instant(value: datetime) -> str:
    value = value.astimezone(UTC).replace(microsecond=0)
    return value.isoformat().replace("+00:00", "Z")


def request_now(request: Request) -> datetime:
    enabled = os.getenv("SVCDESK_TEST_CLOCK", "").lower() in {"1", "true"}

    if enabled:
        header = request.headers.get("X-Test-Clock")
        if header is not None:
            return parse_instant(header)

    return datetime.now(UTC)


def next_business_open(value: datetime) -> datetime:
    local = value.astimezone(WARSAW)

    if local.weekday() < 5:
        opening = datetime.combine(
            local.date(),
            time(8, 0),
            tzinfo=WARSAW,
        )
        closing = datetime.combine(
            local.date(),
            time(16, 0),
            tzinfo=WARSAW,
        )

        if local < opening:
            return opening

        if local < closing:
            return local

    next_date = local.date() + timedelta(days=1)

    while next_date.weekday() >= 5:
        next_date += timedelta(days=1)

    return datetime.combine(
        next_date,
        time(8, 0),
        tzinfo=WARSAW,
    )


def is_business_time(value: datetime) -> bool:
    local = value.astimezone(WARSAW)

    if local.weekday() >= 5:
        return False

    opening = datetime.combine(
        local.date(),
        time(8, 0),
        tzinfo=WARSAW,
    )
    closing = datetime.combine(
        local.date(),
        time(16, 0),
        tzinfo=WARSAW,
    )

    return opening <= local < closing


def add_business_time(start: datetime, duration: timedelta) -> datetime:
    current = next_business_open(start)
    remaining = duration.total_seconds()

    while True:
        closing = datetime.combine(
            current.date(),
            time(16, 0),
            tzinfo=WARSAW,
        )

        available = (closing - current).total_seconds()

        if remaining <= available:
            result = current + timedelta(seconds=remaining)
            return result.astimezone(UTC)

        remaining -= available

        next_date = current.date() + timedelta(days=1)
        while next_date.weekday() >= 5:
            next_date += timedelta(days=1)

        current = datetime.combine(
            next_date,
            time(8, 0),
            tzinfo=WARSAW,
        )


def calculate_priority(impact: int, urgency: int, vip: bool) -> str:
    priority = PRIORITY_MATRIX[(impact, urgency)]

    # C3 = matrix: VIP is stored but never changes priority.
    return priority


def calculate_due_times(
    created_at: datetime,
    priority: str,
) -> tuple[datetime, datetime]:
    targets = SLA_TARGETS[priority]

    if priority == "P1" and C1 == "wallclock":
        ack_due = created_at + targets["ack"]
        resolve_due = created_at + targets["resolve"]
    else:
        ack_due = add_business_time(created_at, targets["ack"])
        resolve_due = add_business_time(created_at, targets["resolve"])

    return ack_due.astimezone(UTC), resolve_due.astimezone(UTC)


def parse_ticket_instant(ticket: dict[str, Any], field: str) -> datetime | None:
    value = ticket.get(field)

    if value is None:
        return None

    return parse_instant(value)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "svcdesk",
    }


@app.post("/tickets", status_code=201)
def create_ticket(payload: TicketCreate, request: Request):
    now = request_now(request)

    priority = calculate_priority(
        payload.impact,
        payload.urgency,
        payload.reporter.vip,
    )

    ack_due, resolve_due = calculate_due_times(
        now,
        priority,
    )

    ticket = {
        "id": str(uuid.uuid4()),
        "title": payload.title,
        "description": payload.description,
        "reporter": {
            "name": payload.reporter.name,
            "email": payload.reporter.email,
            "vip": payload.reporter.vip,
        },
        "impact": payload.impact,
        "urgency": payload.urgency,
        "priority": priority,
        "state": "new",
        "created_at": format_instant(now),
        "acknowledged_at": None,
        "resolved_at": None,
        "closed_at": None,
        "related_to": payload.related_to,
        "sla": {
            "ack_due_at": format_instant(ack_due),
            "resolve_due_at": format_instant(resolve_due),
        },
    }

    save_ticket(ticket)
    return ticket


@app.get("/tickets")
def list_tickets(
    state: str | None = None,
    priority: str | None = None,
):
    tickets = load_tickets()

    if state is not None:
        tickets = [
            ticket
            for ticket in tickets
            if ticket["state"] == state
        ]

    if priority is not None:
        tickets = [
            ticket
            for ticket in tickets
            if ticket["priority"] == priority
        ]

    return tickets


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    return load_ticket(ticket_id)


@app.post("/tickets/{ticket_id}/ack")
def acknowledge_ticket(ticket_id: str, request: Request):
    ticket = load_ticket(ticket_id)
    now = request_now(request)

    if ticket["state"] != "new":
        raise ApiError(
            409,
            "invalid_transition",
            "only a new ticket can be acknowledged",
        )

    ticket["state"] = "acknowledged"
    ticket["acknowledged_at"] = format_instant(now)

    save_ticket(ticket)
    return ticket


@app.post("/tickets/{ticket_id}/start")
def start_ticket(ticket_id: str, request: Request):
    ticket = load_ticket(ticket_id)
    request_now(request)

    if ticket["state"] != "acknowledged":
        raise ApiError(
            409,
            "invalid_transition",
            "only an acknowledged ticket can be started",
        )

    ticket["state"] = "in_progress"

    save_ticket(ticket)
    return ticket


@app.post("/tickets/{ticket_id}/resolve")
def resolve_ticket(ticket_id: str, request: Request):
    ticket = load_ticket(ticket_id)
    now = request_now(request)

    if ticket["state"] != "in_progress":
        raise ApiError(
            409,
            "invalid_transition",
            "only a ticket in progress can be resolved",
        )

    ticket["state"] = "resolved"
    ticket["resolved_at"] = format_instant(now)
    ticket["closed_at"] = None

    save_ticket(ticket)
    return ticket


@app.post("/tickets/{ticket_id}/close")
def close_ticket(ticket_id: str, request: Request):
    ticket = load_ticket(ticket_id)
    now = request_now(request)

    if ticket["state"] != "resolved":
        raise ApiError(
            409,
            "invalid_transition",
            "only a resolved ticket can be closed",
        )

    ticket["state"] = "closed"
    ticket["closed_at"] = format_instant(now)

    save_ticket(ticket)
    return ticket


@app.post("/tickets/{ticket_id}/reopen")
def reopen_ticket(ticket_id: str, request: Request):
    ticket = load_ticket(ticket_id)
    now = request_now(request)

    if ticket["state"] == "closed":
        raise ApiError(
            409,
            "ticket_closed",
            "closed tickets are immutable",
        )

    if ticket["state"] != "resolved":
        raise ApiError(
            409,
            "invalid_transition",
            "only a resolved ticket can be reopened",
        )

    resolved_at = parse_ticket_instant(ticket, "resolved_at")

    if resolved_at is None:
        raise ApiError(
            409,
            "invalid_transition",
            "ticket has no resolution timestamp",
        )

    if now > resolved_at + timedelta(days=7):
        raise ApiError(
            409,
            "reopen_window_expired",
            "the reopen window has expired",
        )

    ticket["state"] = "in_progress"
    ticket["resolved_at"] = None
    ticket["closed_at"] = None

    save_ticket(ticket)
    return ticket


@app.get("/tickets/{ticket_id}/sla")
def ticket_sla(ticket_id: str, request: Request):
    ticket = load_ticket(ticket_id)
    now = request_now(request)

    ack_due = parse_instant(ticket["sla"]["ack_due_at"])
    resolve_due = parse_instant(ticket["sla"]["resolve_due_at"])

    acknowledged_at = parse_ticket_instant(
        ticket,
        "acknowledged_at",
    )
    resolved_at = parse_ticket_instant(
        ticket,
        "resolved_at",
    )

    if acknowledged_at is None:
        ack_breached = now > ack_due
    else:
        ack_breached = acknowledged_at > ack_due

    if resolved_at is None:
        resolve_breached = now > resolve_due
    else:
        resolve_breached = resolved_at > resolve_due

    resolution_uses_business_clock = not (
        ticket["priority"] == "P1" and C1 == "wallclock"
    )

    paused = (
        ticket["state"] not in {"resolved", "closed"}
        and resolution_uses_business_clock
        and not is_business_time(now)
    )

    return {
        "priority": ticket["priority"],
        "ack_due_at": ticket["sla"]["ack_due_at"],
        "resolve_due_at": ticket["sla"]["resolve_due_at"],
        "ack_breached": ack_breached,
        "resolve_breached": resolve_breached,
        "paused": paused,
    }
