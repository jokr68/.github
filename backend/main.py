"""Uvicorn entrypoint.

تشغيل:
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from app.api.main import app
