"""Shared helpers for the journey layer."""
from __future__ import annotations

import base64
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..core.config import jsettings

TZ = ZoneInfo(jsettings.CLINIC_TIMEZONE)


def now() -> datetime:
    return datetime.now(TZ)


def today() -> date:
    return now().date()


def to_json(v):
    """Make ORM/DB values JSON-safe (dates ISO, Decimal→float, UUID→str, enum→value)."""
    if isinstance(v, datetime):
        return (v.astimezone(TZ) if v.tzinfo else v).isoformat()
    if isinstance(v, (date, time)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, uuid.UUID):
        return str(v)
    if hasattr(v, "value") and not isinstance(v, (str, bytes)):
        return v.value
    if isinstance(v, dict):
        return {k: to_json(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [to_json(x) for x in v]
    return v


def row(obj, *, exclude=("_sa_instance_state",)) -> dict:
    """ORM object → plain dict of its columns."""
    if obj is None:
        return None
    return {c.name: to_json(getattr(obj, c.name)) for c in obj.__table__.columns}


def rows(objs) -> list[dict]:
    return [row(o) for o in objs]


def new_label_code() -> str:
    raw = base64.b32encode(uuid.uuid4().bytes).decode().rstrip("=")
    return "LBL-" + raw[:10]


def next_number(db: Session, model, column, prefix: str, width: int = 4) -> str:
    """Sequential numbering like CYC-2026-0007 (same pattern as Module 2)."""
    year = today().year
    last = db.query(model).filter(column.like(f"{prefix}-{year}-%")).order_by(desc(column)).first()
    seq = 1
    if last:
        try:
            seq = int(getattr(last, column.key).split("-")[-1]) + 1
        except ValueError:
            seq = 1
    return f"{prefix}-{year}-{seq:0{width}d}"


def patient_name(p, lang: str = "en") -> str:
    if p is None:
        return ""
    if lang == "th" and (p.first_name_th or p.last_name_th):
        return f"{p.first_name_th or ''} {p.last_name_th or ''}".strip()
    return f"{p.first_name_en or ''} {p.last_name_en or ''}".strip()


def age_years(dob: date | None, on: date | None = None) -> int | None:
    if not dob:
        return None
    on = on or today()
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


def buddhist_year(d: date) -> int:
    return d.year + 543


def th_date(d: date | None) -> str:
    """dd/mm/พ.ศ. for labels and documents."""
    if not d:
        return ""
    return f"{d.day:02d}/{d.month:02d}/{buddhist_year(d)}"


def parse_date(s) -> date | None:
    if s is None or s == "":
        return None
    if isinstance(s, date):
        return s
    return date.fromisoformat(str(s)[:10])


def parse_time(s) -> time | None:
    if s is None or s == "":
        return None
    if isinstance(s, time):
        return s
    parts = str(s).split(":")
    return time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)


def combine(d: date, t: time | None) -> datetime:
    return datetime.combine(d, t or time(8, 0), TZ)


def add_days(d: date, n: int) -> date:
    return d + timedelta(days=n)
