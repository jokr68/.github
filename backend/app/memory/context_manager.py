"""backend/app/memory/context_manager.py

Contextual Memory: 4 طبقات ذاكرة متكاملة
1) Short-term: Redis (آخر 10 رسائل)
2) Long-term: ChromaDB (Vector search)
3) Persona Memory: Redis (تفضيلات)
4) Conversation Summary: SQL (PostgreSQL/SQLite) عبر SQLAlchemy

التحليل أشار إلى أن طبقة Summary كانت Mock فقط؛ هنا نضيف دعم حقيقي
مع تصميم يسمح بالعمل حتى لو Redis/Chroma غير متاحين (fallback in-memory).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.config import settings


# ---- Optional imports (graceful fallback) ----

try:  # pragma: no cover
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore

try:  # pragma: no cover
    import chromadb  # type: ignore
    from chromadb.config import Settings as ChromaSettings  # type: ignore
except Exception:  # pragma: no cover
    chromadb = None  # type: ignore
    ChromaSettings = None  # type: ignore


@dataclass
class _InMemoryList:
    items: List[str]

    def lpush(self, key: str, value: str):
        self.items.insert(0, value)

    def ltrim(self, key: str, start: int, end: int):
        self.items[:] = self.items[start : end + 1]

    def lrange(self, key: str, start: int, end: int) -> List[str]:
        return self.items[start : end + 1]

    def expire(self, key: str, seconds: int):
        return None


class ContextualMemory:
    """يبني سياق الوكيل من 4 طبقات."""

    def __init__(self):
        # --- Layer 1: Short-term (Redis) ---
        if redis is not None:
            try:
                self.short_term = redis.Redis.from_url(settings.REDIS_URL, db=0, decode_responses=True)
            except Exception:
                self.short_term = _InMemoryList(items=[])
        else:
            self.short_term = _InMemoryList(items=[])

        # --- Layer 2: Vector store (ChromaDB) ---
        self._chroma_enabled = False
        self.long_term = None
        self.conversations_collection = None
        if chromadb is not None and ChromaSettings is not None:
            try:
                self.long_term = chromadb.Client(
                    ChromaSettings(
                        chroma_db_impl="duckdb+parquet",
                        persist_directory=settings.CHROMA_PERSIST_DIR,
                    )
                )
                self.conversations_collection = self.long_term.get_or_create_collection("conversations")
                self._chroma_enabled = True
            except Exception:
                self._chroma_enabled = False

        # --- Layer 3: Persona prefs (Redis) ---
        if redis is not None:
            try:
                self.persona_memory = redis.Redis.from_url(settings.REDIS_URL, db=1, decode_responses=True)
            except Exception:
                self.persona_memory = {}
        else:
            self.persona_memory = {}

        # --- Layer 4: Summary store (SQLAlchemy) ---
        # تُدار عبر app.saas.database و SessionLocal.

    # ---------------- Layer 1 ----------------

    def add_short_term(self, user_id: str, message: Dict[str, Any]):
        key = f"st:{user_id}"
        message_str = json.dumps(message, ensure_ascii=False)
        self.short_term.lpush(key, message_str)
        self.short_term.ltrim(key, 0, 9)
        try:
            self.short_term.expire(key, 3600)
        except Exception:
            pass

    def get_short_term(self, user_id: str, last_n: int = 5) -> List[Dict[str, Any]]:
        key = f"st:{user_id}"
        raw = self.short_term.lrange(key, 0, max(0, last_n - 1))
        out: List[Dict[str, Any]] = []
        for msg in raw:
            try:
                out.append(json.loads(msg))
            except Exception:
                continue
        return out

    # ---------------- Layer 2 ----------------

    def add_to_vector_store(self, user_id: str, conversation_id: str, text: str):
        if not self._chroma_enabled or not self.conversations_collection:
            return
        doc_id = f"{user_id}:{conversation_id}:{int(datetime.now().timestamp())}"
        self.conversations_collection.add(
            documents=[text],
            ids=[doc_id],
            metadatas=[{"user_id": user_id, "conversation_id": conversation_id}],
        )

    def vector_search(self, query: str, user_id: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not self._chroma_enabled or not self.conversations_collection:
            return []

        results = self.conversations_collection.query(
            query_texts=[query],
            n_results=top_k,
            where={"user_id": user_id},
        )
        docs = (results or {}).get("documents") or []
        metas = (results or {}).get("metadatas") or []
        if not docs:
            return []

        return [
            {"text": doc, "metadata": meta}
            for doc, meta in zip(docs[0], metas[0])
        ]

    # ---------------- Layer 3 ----------------

    def set_persona_preference(self, user_id: str, persona_id: str, preferences: Dict[str, Any]):
        key = f"prefs:{user_id}:{persona_id}"
        payload = json.dumps(preferences, ensure_ascii=False)
        if hasattr(self.persona_memory, "setex"):
            self.persona_memory.setex(key, 86400, payload)
        else:
            self.persona_memory[key] = payload

    def get_persona_preference(self, user_id: str, persona_id: str) -> Optional[Dict[str, Any]]:
        key = f"prefs:{user_id}:{persona_id}"
        if hasattr(self.persona_memory, "get"):
            data = self.persona_memory.get(key)
        else:
            data = self.persona_memory.get(key)
        if not data:
            return None
        try:
            return json.loads(data)
        except Exception:
            return None

    # ---------------- Layer 4 ----------------

    def save_conversation_summary(
        self,
        db,
        conversation_id: str,
        summary_text: str,
        tokens_estimate: Optional[int] = None,
    ):
        """يحفظ/يُحدّث ملخص المحادثة."""

        from app.saas.database import ConversationSummary  # local import

        latest = (
            db.query(ConversationSummary)
            .filter(ConversationSummary.conversation_id == conversation_id)
            .order_by(ConversationSummary.created_at.desc())
            .first()
        )
        if latest:
            latest.summary = summary_text
            latest.tokens_estimate = tokens_estimate
            latest.updated_at = datetime.utcnow()
        else:
            latest = ConversationSummary(
                conversation_id=conversation_id,
                summary=summary_text,
                tokens_estimate=tokens_estimate,
            )
            db.add(latest)
        db.commit()
        return latest

    def get_conversation_summary(self, db, conversation_id: str) -> Optional[str]:
        from app.saas.database import ConversationSummary  # local import

        latest = (
            db.query(ConversationSummary)
            .filter(ConversationSummary.conversation_id == conversation_id)
            .order_by(ConversationSummary.created_at.desc())
            .first()
        )
        return latest.summary if latest else None

    # ---------------- Context Builder ----------------

    def build_full_context(self, user_id: str, query: str, conversation_id: str, db=None) -> Dict[str, Any]:
        recent_messages = self.get_short_term(user_id, 5)
        relevant_history = self.vector_search(query, user_id, 3)
        persona_prefs = self.get_persona_preference(user_id, "aether")

        summary = None
        if db is not None:
            try:
                summary = self.get_conversation_summary(db, conversation_id)
            except Exception:
                summary = None

        summary = summary or f"المحادثة رقم {conversation_id} - {len(recent_messages)} رسائل"

        return {
            "recent_messages": recent_messages,
            "relevant_history": relevant_history,
            "persona_preferences": persona_prefs,
            "conversation_summary": summary,
            "context_tokens_estimate": len(str(recent_messages).split()) + len(query.split()),
        }
