import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.data import router
from app.routers.conversations import router as conversations_router
from app.routers.chat import router as chat_router
from app.routers.actions import router as actions_router

load_dotenv()
app = FastAPI(title='전국 보통휘발유 가격 분석 AI 비서', version='0.1.0')
app.add_middleware(CORSMiddleware,
                  allow_origins=[s.strip() for s in os.getenv('ALLOWED_ORIGINS', '').split(',') if s.strip()],
                  allow_methods=['GET', 'POST', 'PUT', 'DELETE'],
                  allow_headers=['Content-Type', 'X-Admin-Token', 'X-Session-Token'])
app.include_router(router)
app.include_router(conversations_router)
app.include_router(chat_router)
app.include_router(actions_router)


@app.get('/health')
def health():
    return {'status': 'ok', 'note': '프로세스 상태이며 Firestore 연결 검증은 아닙니다.'}
