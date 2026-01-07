"""backend/app/agent/orchestrator.py

منطق الوكيل (Orchestrator) — "العقل" المركزي.

التحليل أوضح غياب هذا المكوّن كأكبر نقص: ملف يقرر متى يستخدم أي أداة،
وكيف يدمج الذاكرة، وكيف ينتج الإجابة النهائية.

هذا Orchestrator يعمل بطريقتين:
1) Rule-based (افتراضي): قابل للتشغيل فوراً بدون مفاتيح.
2) LLM-based (اختياري): إذا تم ضبط LLM_PROVIDER وفت...
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.memory.context_manager import ContextualMemory
from app.persona.manager import PersonaManager, PersonaProfile
from app.tools.registry import ToolManager, ToolResult


@dataclass
class ToolCall:
    name: str
    params: Dict[str, Any]
    confirmed: bool = False


class AgentOrchestrator:
    """عقل الوكيل: يبني السياق، يخطط، ينفّذ الأدوات، ويُركّب الإجابة."""

    def __init__(self, tool_manager: Optional[ToolManager] = None, memory: Optional[ContextualMemory] = None):
        self.tools = tool_manager or ToolManager()
        self.memory = memory or ContextualMemory()
        self.personas = PersonaManager()

    # ---------------- Planning ----------------

    def _rule_based_plan(self, user_message: str) -> List[ToolCall]:
        """Planner بسيط (قابل للتوسعة) يحدد الأدوات من كلمات مفتاحية."""
        msg = user_message.strip().lower()
        plan: List[ToolCall] = []

        # بحث
        if any(k in msg for k in ["ابحث", "بحث", "search", "google", "ويب"]):
            plan.append(ToolCall(name="web_search", params={"query": user_message, "num_results": 5}))

        # ترجمة
        if any(k in msg for k in ["ترجم", "translate"]):
            plan.append(ToolCall(name="translation", params={"text": user_message, "target_lang": "en"}))

        # تحليل بيانات
        if any(k in msg for k in ["حلل", "تحليل", "analyze"]):
            plan.append(ToolCall(name="data_analysis", params={"data": {"text": user_message}}))

        return plan

    async def _execute_plan(self, plan: List[ToolCall], user_plan: str) -> List[Tuple[ToolCall, ToolResult]]:
        outputs: List[Tuple[ToolCall, ToolResult]] = []
        for call in plan:
            res = await self.tools.execute_tool(
                tool_name=call.name,
                params=call.params,
                user_plan=user_plan,
                confirmed=call.confirmed,
            )
            outputs.append((call, res))
        return outputs

    # ---------------- Response composition ----------------

    def _compose_response_without_llm(
        self,
        persona: PersonaProfile,
        user_message: str,
        context: Dict[str, Any],
        tool_outputs: List[Tuple[ToolCall, ToolResult]],
    ) -> str:
        """تركيب إجابة افتراضية (بدون LLM) — مفيدة للتشغيل الفوري."""
        lines: List[str] = []
        lines.append(f"[{persona.name}] فهمت ✅")
        lines.append(user_message)

        if tool_outputs:
            lines.append("\n---\nنتائج الأدوات:")
            for call, out in tool_outputs:
                if out.success:
                    lines.append(f"- {call.name}: {out.data}")
                else:
                    lines.append(f"- {call.name}: خطأ: {out.error}")

        recent = context.get("recent_messages") or []
        if recent:
            lines.append("\n---\n(ملحوظة: تم أخذ آخر رسائل من الذاكرة قصيرة المدى)")

        return "\n".join(lines)

    async def _compose_response_with_llm(
        self,
        persona: PersonaProfile,
        user_message: str,
        context: Dict[str, Any],
        tool_outputs: List[Tuple[ToolCall, ToolResult]],
    ) -> str:
        """تركيب إجابة عبر LLM (اختياري)."""
        if settings.LLM_PROVIDER != "openai" or not settings.OPENAI_API_KEY:
            return self._compose_response_without_llm(persona, user_message, context, tool_outputs)

        system_prompt = persona.system_prompt
        memory_snippets = []
        for item in context.get("relevant_history", [])[:3]:
            memory_snippets.append(item.get("text", ""))
        tool_block = []
        for call, out in tool_outputs:
            tool_block.append({"tool": call.name, "success": out.success, "data": out.data, "error": out.error})

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "system",
                "content": "Relevant memory:\n" + "\n---\n".join(memory_snippets)
                if memory_snippets
                else "Relevant memory: (none)",
            },
            {"role": "system", "content": "Tool outputs:\n" + str(tool_block)},
            {"role": "user", "content": user_message},
        ]

        import httpx  # lazy

        url = f"{settings.OPENAI_BASE_URL.rstrip('/')}/chat/completions"
        payload = {
            "model": settings.OPENAI_MODEL,
            "messages": messages,
            "temperature": 0.4,
        }
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}

        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        return data["choices"][0]["message"]["content"]

    # ---------------- Public API ----------------

    async def handle_message(
        self,
        user_id: str,
        conversation_id: str,
        message: str,
        persona_id: str = "aether",
        user_plan: str = "free",
        db=None,
    ) -> Dict[str, Any]:
        """مدخل واحد: رسالة المستخدم -> رد الوكيل + تتبع الأدوات."""

        persona = self.personas.load_persona(user_id=user_id, persona_id=persona_id, memory=self.memory, db=db)

        self.memory.add_short_term(user_id, {"role": "user", "content": message})

        context = self.memory.build_full_context(user_id=user_id, query=message, conversation_id=conversation_id, db=db)

        plan = self._rule_based_plan(message)

        # تطبيق سياسة الأدوات الخاصة بالشخصية
        try:
            blocked = set((persona.tool_policy or {}).get("blocked_tools", []) or [])
            if blocked:
                plan = [c for c in plan if c.name not in blocked]
        except Exception:
            pass

        tool_outputs = await self._execute_plan(plan, user_plan=user_plan)

        try:
            self.memory.add_to_vector_store(user_id=user_id, conversation_id=conversation_id, text=message)
        except Exception:
            pass

        reply = await self._compose_response_with_llm(persona, message, context, tool_outputs)

        self.memory.add_short_term(user_id, {"role": "assistant", "content": reply})

        # تحديث ملخص المحادثة (Layer 4) إن توفرت DB
        if db is not None:
            try:
                recent = context.get("recent_messages", [])[-5:]
                brief = " | ".join([m.get("role", "").split()[0] + ":" + (m.get("content", "")[:80]) for m in recent])
                summary_text = f"{brief}\nآخر رد: {reply[:200]}"
                self.memory.save_conversation_summary(db, str(conversation_id), summary_text, tokens_estimate=context.get("context_tokens_estimate"))
            except Exception:
                pass

        return {
            "reply": reply,
            "persona": {"id": persona.persona_id, "name": persona.name},
            "plan": [{"tool": c.name, "params": c.params} for c in plan],
            "tool_outputs": [
                {
                    "tool": c.name,
                    "success": r.success,
                    "data": r.data,
                    "error": r.error,
                    "ms": r.execution_time_ms,
                    "cost": r.cost_incurred,
                }
                for c, r in tool_outputs
            ],
            "context_meta": {
                "tokens_estimate": context.get("context_tokens_estimate"),
            },
        }
