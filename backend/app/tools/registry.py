"""backend/app/tools/registry.py

Tool Registry: إدارة وتسجيل 16 أداة ذكية.

التحليل أشار إلى أن الأدوات كانت Mock-only؛ هذا الإصدار يُبقي مسار
تشغيلي "mock" (افتراضي) لتجربة قابلة للتشغيل فورًا، ويضيف مسار "live"
بتكاملات فعلية قابلة للتفعيل عبر الإعدادات (SerpAPI/Replicate/LibreTranslate/LLM...).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

from pydantic import BaseModel

from app.core.config import settings


class ToolConfig(BaseModel):
    name: str
    category: str  # core | conditional | advanced
    cost_usd: float
    avg_latency_ms: int
    requires_confirmation: bool = False
    plan_required: str = "free"  # free | premium | enterprise
    implementation: Callable[..., Awaitable["ToolResult"]]

    class Config:  # pydantic v1
        arbitrary_types_allowed = True


class ToolResult(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: int = 0
    cost_incurred: float = 0.0


PLAN_RANK: Dict[str, int] = {"free": 0, "premium": 1, "enterprise": 2}


def plan_allows(user_plan: str, required_plan: str) -> bool:
    return PLAN_RANK.get(user_plan, 0) >= PLAN_RANK.get(required_plan, 0)


def _ms(start_s: float) -> int:
    return int((time.time() - start_s) * 1000)


class ToolManager:
    """يسجل ويدير 16 أداة ذكية."""

    def __init__(self):
        self.tools = self._register_all_tools()
        self.execution_history: List[Dict[str, Any]] = []

    def _register_all_tools(self) -> Dict[str, ToolConfig]:
        """تسجيل الـ16 أداة."""
        return {
            # === أدوات Core (دائماً متاحة) ===
            "web_search": ToolConfig(
                name="web_search",
                category="core",
                cost_usd=0.005,
                avg_latency_ms=1500,
                implementation=self._web_search,
            ),
            "image_generation": ToolConfig(
                name="image_generation",
                category="core",
                cost_usd=0.02,
                avg_latency_ms=3000,
                implementation=self._generate_image,
            ),
            "data_analysis": ToolConfig(
                name="data_analysis",
                category="core",
                cost_usd=0.001,
                avg_latency_ms=800,
                implementation=self._analyze_data,
            ),
            "translation": ToolConfig(
                name="translation",
                category="core",
                cost_usd=0.001,
                avg_latency_ms=500,
                implementation=self._translate,
            ),

            # === أدوات Conditional ===
            "code_execution": ToolConfig(
                name="code_execution",
                category="conditional",
                cost_usd=0.003,
                avg_latency_ms=2000,
                requires_confirmation=True,
                implementation=self._execute_code,
            ),
            "file_processing": ToolConfig(
                name="file_processing",
                category="conditional",
                cost_usd=0.002,
                avg_latency_ms=1200,
                implementation=self._process_file,
            ),
            "voice_processing": ToolConfig(
                name="voice_processing",
                category="conditional",
                cost_usd=0.01,
                avg_latency_ms=2500,
                implementation=self._process_voice,
            ),
            "automation": ToolConfig(
                name="automation",
                category="conditional",
                cost_usd=0.05,
                avg_latency_ms=5000,
                plan_required="premium",
                implementation=self._automate,
            ),

            # === أدوات Advanced ===
            "video_generation": ToolConfig(
                name="video_generation",
                category="advanced",
                cost_usd=0.15,
                avg_latency_ms=10000,
                plan_required="enterprise",
                implementation=self._generate_video,
            ),
            "advanced_analytics": ToolConfig(
                name="advanced_analytics",
                category="advanced",
                cost_usd=0.08,
                avg_latency_ms=3000,
                plan_required="premium",
                implementation=self._advanced_analytics,
            ),
            "api_integration": ToolConfig(
                name="api_integration",
                category="advanced",
                cost_usd=0.04,
                avg_latency_ms=2000,
                plan_required="premium",
                implementation=self._api_call,
            ),
            "database_query": ToolConfig(
                name="database_query",
                category="advanced",
                cost_usd=0.006,
                avg_latency_ms=1500,
                plan_required="premium",
                implementation=self._query_db,
            ),

            # === أدوات إضافية للتوسع ===
            "email_sending": ToolConfig(
                name="email_sending",
                category="conditional",
                cost_usd=0.003,
                avg_latency_ms=1000,
                implementation=self._send_email,
            ),
            "calendar_management": ToolConfig(
                name="calendar_management",
                category="conditional",
                cost_usd=0.004,
                avg_latency_ms=1200,
                implementation=self._manage_calendar,
            ),
            "social_media": ToolConfig(
                name="social_media",
                category="advanced",
                cost_usd=0.07,
                avg_latency_ms=2500,
                plan_required="premium",
                implementation=self._post_social,
            ),
            "ecommerce": ToolConfig(
                name="ecommerce",
                category="advanced",
                cost_usd=0.1,
                avg_latency_ms=4000,
                plan_required="enterprise",
                implementation=self._ecommerce_task,
            ),
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "category": t.category,
                "cost_usd": t.cost_usd,
                "avg_latency_ms": t.avg_latency_ms,
                "requires_confirmation": t.requires_confirmation,
                "plan_required": t.plan_required,
            }
            for t in self.tools.values()
        ]

    # ---------------- تنفيذات الأدوات ----------------

    async def _web_search(self, query: str, num_results: int = 5) -> ToolResult:
        start = time.time()
        if settings.TOOL_MODE == "live" and settings.SERPAPI_KEY:
            try:
                import httpx  # lazy

                params = {
                    "engine": "google",
                    "q": query,
                    "api_key": settings.SERPAPI_KEY,
                    "num": num_results,
                }
                async with httpx.AsyncClient(timeout=20) as client:
                    r = await client.get("https://serpapi.com/search.json", params=params)
                    r.raise_for_status()
                    payload = r.json()
                organic = payload.get("organic_results", [])[:num_results]
                results = [
                    {
                        "title": it.get("title"),
                        "link": it.get("link"),
                        "snippet": it.get("snippet"),
                        "position": it.get("position"),
                    }
                    for it in organic
                ]
                return ToolResult(
                    success=True,
                    data={"provider": "serpapi", "query": query, "results": results},
                    execution_time_ms=_ms(start),
                    cost_incurred=self.tools["web_search"].cost_usd,
                )
            except Exception as e:
                return ToolResult(
                    success=False,
                    error=f"web_search live failed: {e}",
                    execution_time_ms=_ms(start),
                    cost_incurred=self.tools["web_search"].cost_usd / 2,
                )

        await asyncio.sleep(0.05)
        return ToolResult(
            success=True,
            data={
                "provider": "mock",
                "query": query,
                "results": [
                    {"title": "نتيجة 1", "link": "https://example.com/1", "snippet": "..."},
                    {"title": "نتيجة 2", "link": "https://example.com/2", "snippet": "..."},
                ][:num_results],
            },
            execution_time_ms=_ms(start),
            cost_incurred=self.tools["web_search"].cost_usd,
        )

    async def _generate_image(self, prompt: str) -> ToolResult:
        start = time.time()
        if settings.TOOL_MODE == "live" and settings.REPLICATE_API_TOKEN and settings.REPLICATE_MODEL:
            try:
                import httpx

                headers = {
                    "Authorization": f"Token {settings.REPLICATE_API_TOKEN}",
                    "Content-Type": "application/json",
                }
                body = {
                    "version": settings.REPLICATE_MODEL,
                    "input": {"prompt": prompt},
                }
                async with httpx.AsyncClient(timeout=60) as client:
                    r = await client.post("https://api.replicate.com/v1/predictions", headers=headers, json=body)
                    r.raise_for_status()
                    prediction = r.json()

                # Replicate يحتاج polling عادة. نرجّع الـid لطبقة أعلى.
                return ToolResult(
                    success=True,
                    data={"provider": "replicate", "prediction": prediction},
                    execution_time_ms=_ms(start),
                    cost_incurred=self.tools["image_generation"].cost_usd,
                )
            except Exception as e:
                return ToolResult(
                    success=False,
                    error=f"image_generation live failed: {e}",
                    execution_time_ms=_ms(start),
                    cost_incurred=self.tools["image_generation"].cost_usd / 2,
                )

        await asyncio.sleep(0.05)
        return ToolResult(
            success=True,
            data={"provider": "mock", "image_url": "https://example.com/image.jpg", "prompt": prompt},
            execution_time_ms=_ms(start),
            cost_incurred=self.tools["image_generation"].cost_usd,
        )

    async def _analyze_data(self, data: Dict[str, Any]) -> ToolResult:
        start = time.time()
        try:
            if isinstance(data, dict):
                keys = list(data.keys())
                size = len(str(data))
                summary = {"keys": keys[:50], "approx_chars": size}
            else:
                summary = {"type": str(type(data))}
            await asyncio.sleep(0.01)
            return ToolResult(
                success=True,
                data={"provider": "local", "analysis": summary},
                execution_time_ms=_ms(start),
                cost_incurred=self.tools["data_analysis"].cost_usd,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"data_analysis failed: {e}",
                execution_time_ms=_ms(start),
                cost_incurred=self.tools["data_analysis"].cost_usd / 2,
            )

    async def _translate(self, text: str, target_lang: str = "en") -> ToolResult:
        start = time.time()
        if settings.TOOL_MODE == "live" and settings.LIBRETRANSLATE_URL:
            try:
                import httpx

                payload = {
                    "q": text,
                    "source": "auto",
                    "target": target_lang,
                    "format": "text",
                }
                if settings.LIBRETRANSLATE_API_KEY:
                    payload["api_key"] = settings.LIBRETRANSLATE_API_KEY

                async with httpx.AsyncClient(timeout=20) as client:
                    r = await client.post(f"{settings.LIBRETRANSLATE_URL.rstrip('/')}/translate", json=payload)
                    r.raise_for_status()
                    out = r.json()

                translated = out.get("translatedText") or out.get("translated_text")
                return ToolResult(
                    success=True,
                    data={"provider": "libretranslate", "translated_text": translated, "target": target_lang},
                    execution_time_ms=_ms(start),
                    cost_incurred=self.tools["translation"].cost_usd,
                )
            except Exception as e:
                return ToolResult(
                    success=False,
                    error=f"translation live failed: {e}",
                    execution_time_ms=_ms(start),
                    cost_incurred=self.tools["translation"].cost_usd / 2,
                )

        await asyncio.sleep(0.01)
        return ToolResult(
            success=True,
            data={"provider": "mock", "translated_text": f"[{target_lang}] {text}", "target": target_lang},
            execution_time_ms=_ms(start),
            cost_incurred=self.tools["translation"].cost_usd,
        )

    async def _execute_code(self, code: str) -> ToolResult:
        start = time.time()
        await asyncio.sleep(0.01)
        return ToolResult(
            success=False,
            error="code_execution disabled by default. Configure a sandbox runner to enable.",
            execution_time_ms=_ms(start),
            cost_incurred=self.tools["code_execution"].cost_usd / 2,
        )

    async def _process_file(self, file_data: bytes) -> ToolResult:
        start = time.time()
        await asyncio.sleep(0.01)
        return ToolResult(
            success=True,
            data={"provider": "local", "processed": True, "bytes": len(file_data)},
            execution_time_ms=_ms(start),
            cost_incurred=self.tools["file_processing"].cost_usd,
        )

    async def _process_voice(self, audio: bytes) -> ToolResult:
        start = time.time()
        await asyncio.sleep(0.01)
        return ToolResult(
            success=False,
            error="voice_processing requires STT provider. Configure integration to enable.",
            execution_time_ms=_ms(start),
            cost_incurred=self.tools["voice_processing"].cost_usd / 2,
        )

    async def _automate(self, workflow: Dict[str, Any]) -> ToolResult:
        start = time.time()
        await asyncio.sleep(0.02)
        steps = workflow.get("steps", []) if isinstance(workflow, dict) else []
        return ToolResult(
            success=True,
            data={"provider": "local", "completed_steps": len(steps), "workflow": workflow},
            execution_time_ms=_ms(start),
            cost_incurred=self.tools["automation"].cost_usd,
        )

    async def _generate_video(self, prompt: str) -> ToolResult:
        start = time.time()
        await asyncio.sleep(0.01)
        return ToolResult(
            success=False,
            error="video_generation requires an enterprise provider (e.g., Runway).",
            execution_time_ms=_ms(start),
            cost_incurred=self.tools["video_generation"].cost_usd / 2,
        )

    async def _advanced_analytics(self, query: str) -> ToolResult:
        start = time.time()
        await asyncio.sleep(0.02)
        return ToolResult(
            success=True,
            data={"provider": "mock", "insights": ["رؤية 1", "رؤية 2"], "query": query},
            execution_time_ms=_ms(start),
            cost_incurred=self.tools["advanced_analytics"].cost_usd,
        )

    async def _api_call(self, endpoint: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None) -> ToolResult:
        start = time.time()
        if settings.TOOL_MODE == "live":
            try:
                import httpx

                async with httpx.AsyncClient(timeout=30) as client:
                    r = await client.request(method.upper(), endpoint, json=payload)
                    return ToolResult(
                        success=True,
                        data={"status": r.status_code, "body": r.text[:2000]},
                        execution_time_ms=_ms(start),
                        cost_incurred=self.tools["api_integration"].cost_usd,
                    )
            except Exception as e:
                return ToolResult(
                    success=False,
                    error=f"api_integration failed: {e}",
                    execution_time_ms=_ms(start),
                    cost_incurred=self.tools["api_integration"].cost_usd / 2,
                )

        await asyncio.sleep(0.01)
        return ToolResult(
            success=True,
            data={"provider": "mock", "status": 200, "endpoint": endpoint, "method": method},
            execution_time_ms=_ms(start),
            cost_incurred=self.tools["api_integration"].cost_usd,
        )

    async def _query_db(self, sql: str) -> ToolResult:
        start = time.time()
        await asyncio.sleep(0.01)
        return ToolResult(
            success=True,
            data={"provider": "mock", "rows": [], "sql": sql},
            execution_time_ms=_ms(start),
            cost_incurred=self.tools["database_query"].cost_usd,
        )

    async def _send_email(self, to: str, subject: str, body: str = "") -> ToolResult:
        start = time.time()
        await asyncio.sleep(0.01)
        return ToolResult(
            success=True,
            data={"provider": "mock", "sent": True, "to": to, "subject": subject},
            execution_time_ms=_ms(start),
            cost_incurred=self.tools["email_sending"].cost_usd,
        )

    async def _manage_calendar(self, event: Dict[str, Any]) -> ToolResult:
        start = time.time()
        await asyncio.sleep(0.01)
        return ToolResult(
            success=True,
            data={"provider": "mock", "event_id": "cal_123", "event": event},
            execution_time_ms=_ms(start),
            cost_incurred=self.tools["calendar_management"].cost_usd,
        )

    async def _post_social(self, platform: str, content: str) -> ToolResult:
        start = time.time()
        await asyncio.sleep(0.01)
        return ToolResult(
            success=True,
            data={"provider": "mock", "posted": True, "platform": platform},
            execution_time_ms=_ms(start),
            cost_incurred=self.tools["social_media"].cost_usd,
        )

    async def _ecommerce_task(self, action: str, product: Dict[str, Any]) -> ToolResult:
        start = time.time()
        await asyncio.sleep(0.01)
        return ToolResult(
            success=True,
            data={"provider": "mock", "order_id": "ord_123", "action": action, "product": product},
            execution_time_ms=_ms(start),
            cost_incurred=self.tools["ecommerce"].cost_usd,
        )

    # ---------------- واجهة عامة ----------------

    async def execute_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        user_plan: str = "free",
        confirmed: bool = False,
    ) -> ToolResult:
        tool = self.tools.get(tool_name)
        if not tool:
            return ToolResult(success=False, error=f"الأداة {tool_name} غير موجودة")

        if not plan_allows(user_plan, tool.plan_required):
            return ToolResult(success=False, error="الخطة غير كافية لهذه الأداة")

        if tool.requires_confirmation and not confirmed:
            return ToolResult(success=False, error="هذه الأداة تتطلب تأكيد المستخدم قبل التنفيذ")

        start_time = time.time()
        try:
            result = await tool.implementation(**params)
            if result.execution_time_ms == 0:
                result.execution_time_ms = _ms(start_time)
            if result.cost_incurred == 0:
                result.cost_incurred = tool.cost_usd if result.success else tool.cost_usd / 2

            self.execution_history.append(
                {
                    "tool": tool_name,
                    "success": result.success,
                    "cost": result.cost_incurred,
                    "time": result.execution_time_ms,
                }
            )
            return result
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                execution_time_ms=_ms(start_time),
                cost_incurred=tool.cost_usd / 2,
            )
