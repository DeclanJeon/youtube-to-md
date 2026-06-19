from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import settings
from app.models.schemas import HealthResponse

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="YouTube-to-Markdown",
    description="YouTube 영상의 음성 내용을 Markdown 파일로 변환하는 웹 애플리케이션",
    version="1.0.0",
)

# CORS
origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting (인메모리)
_rate_limit_store: dict[str, list[float]] = {}

START_TIME = time.time()


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    # 1분 윈도우 정리
    if client_ip in _rate_limit_store:
        _rate_limit_store[client_ip] = [
            t for t in _rate_limit_store[client_ip] if now - t < 60
        ]
    else:
        _rate_limit_store[client_ip] = []

    if len(_rate_limit_store[client_ip]) >= settings.rate_limit_per_minute:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
                },
            },
        )

    _rate_limit_store[client_ip].append(now)
    return await call_next(request)


# API 라우터
app.include_router(router)


# 헬스체크
@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        uptime=time.time() - START_TIME,
    )


# 정적 파일 서빙
app.mount("/", StaticFiles(directory="static", html=True), name="static")
