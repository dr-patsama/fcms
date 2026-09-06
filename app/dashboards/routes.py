"""
Dashboard API: JSON snapshot + Server-Sent Events stream that pushes a new
snapshot only when the underlying data changed (hash diff, polled every 3 s).
EventSource can't send headers, so the stream accepts ?token=<jwt>.
"""
import asyncio
import hashlib
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from module1.backend.core.database import get_db, SessionLocal
from module1.backend.core.auth import get_current_user, SYSTEM_ROLES, canonical_role
from module1.backend.core.security import decode_access_token
from module1.backend.models.user_models import User
from .queries import SNAPSHOTS

router = APIRouter(prefix="/api/v1/dashboard", tags=["Live Dashboards"])

BOARD_ROLES = {
    "opd":    {"admin", "it_admin", "physician", "nurse", "receptionist", "sonographer", "embryologist", "lab_supervisor", "lab_technician"},
    "embryo": {"admin", "it_admin", "physician", "nurse", "embryologist", "lab_supervisor", "lab_technician"},
}
POLL_SECONDS = 3
HEARTBEAT_SECONDS = 20


def _check_board(board: str, role: str):
    if board not in SNAPSHOTS:
        raise HTTPException(404, "Unknown board")
    role = canonical_role(role)
    if role not in BOARD_ROLES[board] and SYSTEM_ROLES.get(role, {}).get("level", 0) < 95:
        raise HTTPException(403, "Insufficient permissions for this board")


def _user_from_token(token: str, db: Session) -> User:
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(401, "Invalid token")
    u = db.query(User).filter(User.id == payload.get("sub"), User.is_active == True).first()
    if not u:
        raise HTTPException(401, "User not found")
    return u


def _snapshot(board: str) -> dict:
    db = SessionLocal()
    try:
        return SNAPSHOTS[board](db)
    finally:
        db.close()


def _digest(snap: dict) -> str:
    body = {k: v for k, v in snap.items() if k != "generated_at"}
    return hashlib.sha1(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


@router.get("/{board}")
def get_snapshot(board: str, user: User = Depends(get_current_user)):
    _check_board(board, user.role)
    return _snapshot(board)


@router.get("/{board}/stream")
async def stream(board: str, token: Optional[str] = Query(None), db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(401, "token required")
    user = _user_from_token(token, db)
    _check_board(board, user.role)

    async def gen():
        last = None
        idle = 0
        yield "retry: 3000\n\n"
        while True:
            try:
                snap = await asyncio.to_thread(_snapshot, board)
                d = _digest(snap)
                if d != last:
                    last = d
                    idle = 0
                    yield f"event: snapshot\ndata: {json.dumps(snap, default=str, ensure_ascii=False)}\n\n"
                else:
                    idle += POLL_SECONDS
                    if idle >= HEARTBEAT_SECONDS:
                        idle = 0
                        yield f"event: heartbeat\ndata: {snap['generated_at']}\n\n"
            except Exception as e:  # keep the stream alive, surface the error to the board
                yield f"event: error\ndata: {json.dumps(str(e))}\n\n"
            await asyncio.sleep(POLL_SECONDS)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
