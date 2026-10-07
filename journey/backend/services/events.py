"""
Domain-event bus for the journey layer.

`emit(db, type, cycle_id, patient_id, payload, actor_id)` appends a CycleEvent row and runs
every registered handler synchronously inside the caller's transaction scope. Each handler
is isolated: an exception is recorded in `event.handlers[name] = "error: ..."` and never
breaks the request. Handlers register with the @on(...) decorator (see handlers.py).

Event vocabulary (keep in sync with the spec, Section 3):
  cycle.created · plan.published · plan.updated · visit.booked · visit.checked_in · queue.called
  monitoring.recorded · results.released · trigger.set · procedure.scheduled · procedure.rescheduled
  lab.task.generated · lab.task.done · lab.task.failed
  witness.match · witness.mismatch · witness.manual
  observation.recorded · album.released
  consent.signed
  cryo.stored · cryo.renewal_due · cryo.renewed · cryo.thawed · cryo.discarded
  outcome.recorded · cycle.closed · report.generated
  invoice.issued · payment.received
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Callable, Optional

from sqlalchemy.orm import Session

from ..models.journey_models import CycleEvent

log = logging.getLogger("fcms.journey.events")

_HANDLERS: dict[str, list[tuple[str, Callable]]] = defaultdict(list)


def on(*event_types: str, name: Optional[str] = None):
    """Register a handler: fn(db, event: CycleEvent) -> str | None."""
    def deco(fn):
        for t in event_types:
            _HANDLERS[t].append((name or fn.__name__, fn))
        return fn
    return deco


def handlers_for(event_type: str):
    return list(_HANDLERS.get(event_type, [])) + list(_HANDLERS.get("*", []))


def emit(db: Session, type: str, *, cycle_id=None, patient_id=None, payload: dict | None = None,
         actor_id=None, run_handlers: bool = True) -> CycleEvent:
    ev = CycleEvent(cycle_id=str(cycle_id) if cycle_id else None,
                    patient_id=str(patient_id) if patient_id else None,
                    type=type, payload=payload or {}, actor_id=str(actor_id) if actor_id else None,
                    handlers={})
    db.add(ev)
    db.flush()
    if run_handlers:
        results = {}
        for name, fn in handlers_for(type):
            try:
                out = fn(db, ev)
                results[name] = out if isinstance(out, str) else "ok"
            except Exception as e:  # never let a side effect break the business transaction
                log.exception("handler %s failed for %s", name, type)
                results[name] = f"error: {type(e).__name__}: {e}"
        ev.handlers = results
        db.flush()
    return ev
