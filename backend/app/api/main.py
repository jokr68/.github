"""API Gateway (FastAPI) for Athir v5."""

from __future__ import annotations

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.agent.orchestrator import AgentOrchestrator
from app.api.deps import get_current_user
from app.api.schemas import AuthResponse, ChatRequest, ChatResponse, LoginRequest, RegisterRequest
from app.auth.security import create_token, hash_password, verify_password
from app.core.config import settings
from app.saas.database import Conversation, Message, User, get_db, init_db


app = FastAPI(title=settings.APP_NAME)

# CORS للربط مع الواجهة
if settings.CORS_ORIGINS.strip() == "*":
    origins = ["*"]
else:
    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/health")
def health():
    return {"ok": True, "app": settings.APP_NAME, "env": settings.ENV}


@app.get("/v1/tools")
def list_tools(user: User = Depends(get_current_user)):
    orch = AgentOrchestrator()
    return {"tools": orch.tools.list_tools(), "user_plan": user.plan_tier}


@app.post("/v1/auth/register", response_model=AuthResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")
    u = User(email=req.email, password_hash=hash_password(req.password), plan_tier="free")
    db.add(u)
    db.commit()
    db.refresh(u)
    token = create_token({"sub": str(u.id), "email": u.email, "plan": u.plan_tier}, settings.AUTH_SECRET, settings.AUTH_TOKEN_TTL_SECONDS)
    return AuthResponse(token=token, user_id=str(u.id), plan_tier=u.plan_tier)


@app.post("/v1/auth/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == req.email).first()
    if not u or not u.password_hash or not verify_password(req.password, u.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token({"sub": str(u.id), "email": u.email, "plan": u.plan_tier}, settings.AUTH_SECRET, settings.AUTH_TOKEN_TTL_SECONDS)
    return AuthResponse(token=token, user_id=str(u.id), plan_tier=u.plan_tier)


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # تأكد من وجود محادثة (أو أنشئ واحدة جديدة)
    conv = None
    if req.conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == req.conversation_id).first()

    if not conv:
        conv = Conversation(user_id=user.id, title=None)
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # خزّن رسالة المستخدم
    db.add(Message(conversation_id=conv.id, role="user", content=req.message, metadata=None))
    db.commit()

    orch = AgentOrchestrator()
    out = await orch.handle_message(
        user_id=str(user.id),
        conversation_id=str(conv.id),
        message=req.message,
        persona_id=req.persona_id,
        user_plan=user.plan_tier,
        db=db,
    )

    # خزّن رد المساعد
    db.add(Message(conversation_id=conv.id, role="assistant", content=out["reply"], metadata={"tool_outputs": out["tool_outputs"]}))
    db.commit()

    out["conversation_id"] = str(conv.id)
    return out
