"""Pydantic schemas for API."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: str
    plan_tier: str


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    persona_id: str = "aether"


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    persona: Dict[str, Any]
    plan: list
    tool_outputs: list
    context_meta: Dict[str, Any]
