Athir v5 Backend

تشغيل سريع:
1) cd backend
2) pip install -r requirements.txt
3) cp .env.example .env
4) uvicorn main:app --reload --host 0.0.0.0 --port 8000

مسارات:
- GET /health
- GET /v1/tools
- POST /v1/auth/register
- POST /v1/auth/login
- POST /v1/chat
