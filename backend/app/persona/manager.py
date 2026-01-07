"""backend/app/persona/manager.py

Persona Logic.

التحليل أشار أن نماذج الشخصيات موجودة في قاعدة البيانات لكن لا يوجد
منطق تحميلها وتطبيق تفضيلاتها على سلوك الوكيل.

هذا الملف يعرّف:
- PersonaProfile: تمثيل جاهز للاستخدام داخل Orchestrator.
- PersonaManager: تحميل شخصية افتراضية، أو مخصصة من DB، ودمج تفضيلات
  Redis (Persona Memory) إن وجدت.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class PersonaProfile:
    persona_id: str
    name: str
    system_prompt: str
    tool_policy: Dict[str, Any]


DEFAULT_PERSONA_ID = "aether"


DEFAULT_SYSTEM_PROMPT = """أنت أثير (Athir) — وكيل عام.

مهمتك: مساعدة المستخدم بشكل عملي وذكي، وتفويض المهام للأدوات عند الحاجة.
قواعد:
1) إذا طُلب بحث: استخدم web_search ثم لخّص النتائج.
2) إذا طُلب ترجمة: استخدم translation.
3) إذا لم تكن هناك حاجة لأداة: أجب مباشرة.
4) احترم خطة المستخدم: free/premium/enterprise.
5) لا تنفذ أي فعل خطير بدون تأكيد.
"""


class PersonaManager:
    """تحميل الشخصية ودمج تفضيلاتها."""

    def load_persona(self, user_id: str, persona_id: str, memory=None, db=None) -> PersonaProfile:
        # 1) شخصية افتراضية
        persona = PersonaProfile(
            persona_id=persona_id or DEFAULT_PERSONA_ID,
            name="أثير",
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            tool_policy={"allow_all": True, "blocked_tools": []},
        )

        # 2) محاولة تحميل من DB إن توفرت (اختياري)
        if db is not None:
            try:
                from app.saas.database import Persona  # local import

                row = (
                    db.query(Persona)
                    .filter(Persona.user_id == user_id)
                    .filter(Persona.name == persona_id)
                    .first()
                )
                if row:
                    persona.name = row.name
                    if row.description:
                        persona.system_prompt = row.description
            except Exception:
                pass

        # 3) دمج تفضيلات Redis (Persona Memory)
        if memory is not None:
            try:
                prefs = memory.get_persona_preference(user_id, persona.persona_id)
            except Exception:
                prefs = None
            if prefs:
                persona = self._apply_preferences(persona, prefs)

        return persona

    def _apply_preferences(self, persona: PersonaProfile, prefs: Dict[str, Any]) -> PersonaProfile:
        # مثال: تغيير النبرة أو منع أدوات
        tone = prefs.get("tone")
        if tone:
            persona.system_prompt = persona.system_prompt + f"\n\nنبرة الرد: {tone}"

        blocked = prefs.get("blocked_tools")
        if blocked and isinstance(blocked, list):
            persona.tool_policy["blocked_tools"] = blocked
            persona.tool_policy["allow_all"] = False

        return persona
