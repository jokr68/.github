"""FastAPI dependencies (DB + Auth)."""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.auth.security import verify_token
from app.core.config import settings
from app.saas.database import User, get_db


def ensure_demo_user(db: Session) -> User:
    """يضمن وجود مستخدم تجريبي عندما تكون المصادقة معطلة."""
    demo = db.query(User).filter(User.email == "demo@athir.local").first()
    if demo:
        return demo
    demo = User(email="demo@athir.local", password_hash=None, plan_tier="free")
    db.add(demo)
    db.commit()
    db.refresh(demo)
    return demo


def get_current_user(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
) -> User:
    if not settings.AUTH_ENABLED:
        return ensure_demo_user(db)

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    payload = verify_token(token, settings.AUTH_SECRET)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(User).filter(User.id == sub).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
