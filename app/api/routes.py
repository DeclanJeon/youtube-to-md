from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.models.schemas import (
    ErrorResponse,
    ErrorDetail,
    LanguagesResponse,
    LanguageInfo,
    TranscriptRequest,
    TranscriptResponse,
    TranscriptData,
)
from app.services.cache import MemoryCacheBackend
from app.services.formatter import MarkdownFormatter, sanitize_filename
from app.services.transcript import (
    TranscriptError,
    extract_transcript,
    extract_video_id,
    fetch_metadata,
    list_languages,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# 캐시 및 포맷터 인스턴스
cache = MemoryCacheBackend(max_size=1000, ttl=3600)
formatter = MarkdownFormatter()


def _cache_key(video_id: str, language: str, timestamps: bool, metadata: bool) -> str:
    return f"{video_id}:{language}:{timestamps}:{metadata}"


@router.post("/transcript", response_model=TranscriptResponse)
async def get_transcript(request: TranscriptRequest) -> TranscriptResponse | JSONResponse:
    start_time = time.monotonic()
    try:
        video_id = extract_video_id(request.url)
        language = request.language or "auto"

        # 캐시 확인
        key = _cache_key(video_id, language, request.include_timestamps, request.include_metadata)
        cached = await cache.get(key)
        if cached:
            logger.info(f"Cache hit: {video_id}")
            return TranscriptResponse(**cached)

        # 메타데이터 조회
        metadata = await fetch_metadata(video_id)

        # 트랜스크립트 추출
        segments = await extract_transcript(video_id, None if language == "auto" else language)

        # Markdown 포맷팅
        markdown = formatter.format(
            segments=segments,
            metadata=metadata,
            include_timestamps=request.include_timestamps,
            include_metadata=request.include_metadata,
        )

        # 사용 가능한 언어 조회
        try:
            langs = await list_languages(video_id)
            available = [l["code"] for l in langs]
        except Exception:
            available = [language]

        elapsed = time.monotonic() - start_time
        word_count = len(markdown)

        result = {
            "success": True,
            "data": {
                "video_id": video_id,
                "title": metadata.title,
                "channel": metadata.channel,
                "duration": metadata.duration,
                "language": language or "auto",
                "available_languages": available,
                "markdown": markdown,
                "download_filename": sanitize_filename(metadata.title),
                "segment_count": len(segments),
                "word_count": word_count,
            },
        }

        await cache.set(key, result)
        logger.info(f"Transcript extracted: {video_id}, {len(segments)} segments, {elapsed:.2f}s")

        return TranscriptResponse(**result)

    except TranscriptError as e:
        logger.warning(f"TranscriptError: {e.code} - {e.message}")
        return JSONResponse(
            status_code=_error_status_code(e.code),
            content=ErrorResponse(
                error=ErrorDetail(code=e.code, message=e.message, detail=e.detail)
            ).model_dump(),
        )
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message="서버 오류가 발생했습니다.",
                    detail=str(e),
                )
            ).model_dump(),
        )


@router.get("/languages/{video_id}", response_model=LanguagesResponse)
async def get_languages(video_id: str) -> LanguagesResponse | JSONResponse:
    try:
        langs = await list_languages(video_id)
        return LanguagesResponse(
            video_id=video_id,
            languages=[LanguageInfo(**l) for l in langs],
        )
    except TranscriptError as e:
        return JSONResponse(
            status_code=_error_status_code(e.code),
            content=ErrorResponse(
                error=ErrorDetail(code=e.code, message=e.message, detail=e.detail)
            ).model_dump(),
        )


def _error_status_code(code: str) -> int:
    mapping = {
        "INVALID_URL": 400,
        "VIDEO_UNAVAILABLE": 404,
        "TRANSCRIPT_DISABLED": 404,
        "TRANSCRIPT_UNAVAILABLE": 404,
        "RATE_LIMITED": 429,
        "UPSTREAM_ERROR": 502,
        "SERVICE_UNAVAILABLE": 503,
        "INTERNAL_ERROR": 500,
    }
    return mapping.get(code, 500)
