"""app.core.config

ملف الإعدادات المركزي للنظام.

التحليل أشار أن `context_manager.py` يعتمد على `settings` لكن ملف الإعدادات
غير موجود، لذلك هذا الملف هو المصدر الموحّد لكل متغيرات البيئة الحساسة
وغير الحساسة (روابط قواعد البيانات، Redis، مفاتيح API، وضع التشغيل...).
"""

from __future__ import annotations

from typing import Optional


# Pydantic v2 يستخدم pydantic-settings، بينما v1 يوفّر BaseSettings داخل pydantic.
try:  # pragma: no cover
    from pydantic_settings import BaseSettings
except Exception:  # pragma: no cover
    from pydantic import BaseSettings  # type: ignore


class Settings(BaseSettings):
    # --- عام ---
    APP_NAME: str = "athir_v5"
    ENV: str = "dev"  # dev | staging | prod

    # --- قواعد البيانات ---
    DATABASE_URL: str = "sqlite:///./athir_v5.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # --- وضع تشغيل الأدوات ---
    # mock: يرجّع بيانات وهمية لكن متسقة لاختبارات الـMVP
    # live: يفعّل التكاملات الخارجية (يتطلب مفاتيح)
    TOOL_MODE: str = "mock"  # mock | live

    # --- مفاتيح تكامل الأدوات ---
    SERPAPI_KEY: Optional[str] = None
    REPLICATE_API_TOKEN: Optional[str] = None
    # Replicate يتطلب version/model identifier (غالبًا hash لنسخة النموذج)
    REPLICATE_MODEL: Optional[str] = None
    LIBRETRANSLATE_URL: Optional[str] = None
    LIBRETRANSLATE_API_KEY: Optional[str] = None

    # --- LLM ---
    LLM_PROVIDER: str = "none"  # none | openai
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4.1-mini"

    # --- Auth ---
    AUTH_ENABLED: bool = False
    AUTH_SECRET: str = "change-me"  # غيّره في prod
    AUTH_TOKEN_TTL_SECONDS: int = 60 * 60 * 24  # 24h

    # --- تشغيل API ---
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # CORS
    CORS_ORIGINS: str = "*"  # comma-separated or *

    class Config:  # pydantic v1
        env_file = ".env"
        case_sensitive = True


settings = Settings()
