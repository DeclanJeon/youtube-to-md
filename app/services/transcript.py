from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from app.services.circuit_breaker import CircuitBreaker, CircuitState

logger = logging.getLogger(__name__)

YOUTUBE_URL_PATTERN = re.compile(
    r"(?:https?://)?"
    r"(?:(?:www\.)?youtube\.com/watch\?v="
    r"|(?:www\.)?youtube\.com/embed/"
    r"|(?:www\.)?youtube\.com/shorts/"
    r"|(?:m\.)?youtube\.com/watch\?v="
    r"|youtu\.be/)"
    r"([a-zA-Z0-9_-]{11})"
    r"(?:[?&].*)?"
    r"$"
)


@dataclass
class TranscriptSegment:
    text: str
    start: float
    duration: float


@dataclass
class VideoMetadata:
    video_id: str
    title: str
    channel: str
    duration: str
    url: str
    language: str


class TranscriptError(Exception):
    def __init__(self, code: str, message: str, detail: str | None = None) -> None:
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(message)


def extract_video_id(url: str) -> str:
    """YouTube URL에서 video_id를 추출합니다."""
    match = YOUTUBE_URL_PATTERN.match(url.strip())
    if not match:
        raise TranscriptError(
            code="INVALID_URL",
            message="올바른 YouTube URL을 입력해주세요.",
            detail=f"입력된 URL: {url}",
        )
    return match.group(1)


_cb_ytt = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
_cb_ytdlp = CircuitBreaker(failure_threshold=5, recovery_timeout=60)


async def extract_transcript_primary(
    video_id: str, language: str = "ko"
) -> list[TranscriptSegment]:
    """youtube-transcript-api로 트랜스크립트를 추출합니다 (1차)."""
    if _cb_ytt.is_open():
        raise TranscriptError(
            code="SERVICE_UNAVAILABLE",
            message="YouTube 연결이 일시적으로 불안정합니다.",
            detail="youtube-transcript-api 서킷 브레이커 열림",
        )

    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id, languages=[language])
        _cb_ytt.record_success()
        return [
            TranscriptSegment(
                text=snippet.text,
                start=snippet.start,
                duration=snippet.duration,
            )
            for snippet in transcript
        ]
    except TranscriptsDisabled as e:
        _cb_ytt.record_failure()
        raise TranscriptError(
            code="TRANSCRIPT_DISABLED",
            message="이 영상은 자막이 비활성화되어 있습니다.",
        ) from e
    except (NoTranscriptFound, VideoUnavailable) as e:
        _cb_ytt.record_failure()
        raise TranscriptError(
            code="TRANSCRIPT_UNAVAILABLE",
            message="선택한 언어의 자막을 찾을 수 없습니다.",
            detail=str(e),
        ) from e
    except Exception as e:
        _cb_ytt.record_failure()
        raise TranscriptError(
            code="UPSTREAM_ERROR",
            message="YouTube 서버에서 오류가 발생했습니다.",
            detail=str(e),
        ) from e


async def extract_transcript_fallback(
    video_id: str, language: str = "ko"
) -> list[TranscriptSegment]:
    """yt-dlp로 트랜스크립트를 추출합니다 (2차 Fallback)."""
    if _cb_ytdlp.is_open():
        raise TranscriptError(
            code="SERVICE_UNAVAILABLE",
            message="YouTube 연결이 일시적으로 불안정합니다.",
            detail="yt-dlp 서킷 브레이커 열림",
        )

    import asyncio

    def _extract() -> list[TranscriptSegment]:
        import json
        import tempfile
        import os

        import yt_dlp

        url = f"https://www.youtube.com/watch?v={video_id}"
        tmp_dir = tempfile.mkdtemp()

        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [language, "en"],
            "subtitlesformat": "json3",
            "quiet": True,
            "no_warnings": True,
            "outtmpl": os.path.join(tmp_dir, "%(id)s"),
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                subtitles = info.get("subtitles") or {}
                auto_subs = info.get("automatic_captions") or {}

                subs = subtitles.get(language) or auto_subs.get(language)
                if not subs:
                    raise TranscriptError(
                        code="TRANSCRIPT_UNAVAILABLE",
                        message="선택한 언어의 자막을 찾을 수 없습니다.",
                        detail=f"언어 '{language}' 자막 없음",
                    )

                # json3 형식의 자막 데이터 파싱
                # yt-dlp는 자막을 리스트로 반환 (각 항목은 dict)
                segments = []
                for entry in subs:
                    if isinstance(entry, dict):
                        segments.append(
                            TranscriptSegment(
                                text=entry.get("text", ""),
                                start=entry.get("start", 0.0),
                                duration=entry.get("duration", 0.0),
                            )
                        )
                _cb_ytdlp.record_success()
                return segments
        except TranscriptError:
            _cb_ytdlp.record_failure()
            raise
        except Exception as e:
            _cb_ytdlp.record_failure()
            raise TranscriptError(
                code="UPSTREAM_ERROR",
                message="YouTube 서버에서 오류가 발생했습니다.",
                detail=str(e),
            ) from e
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

    return await asyncio.to_thread(_extract)


async def fetch_metadata(video_id: str) -> VideoMetadata:
    """YouTube oEmbed API로 영상 메타데이터를 조회합니다."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(oembed_url)
            if resp.status_code != 200:
                raise TranscriptError(
                    code="VIDEO_UNAVAILABLE",
                    message="영상을 찾을 수 없습니다. 비공개이거나 삭제된 영상일 수 있습니다.",
                )
            data = resp.json()

        return VideoMetadata(
            video_id=video_id,
            title=data.get("title", "Unknown"),
            channel=data.get("author_name", "Unknown"),
            duration="N/A",  # oEmbed는 길이 미제공
            url=url,
            language="",
        )
    except httpx.HTTPError as e:
        raise TranscriptError(
            code="VIDEO_UNAVAILABLE",
            message="영상을 찾을 수 없습니다.",
            detail=str(e),
        ) from e


async def list_languages(video_id: str) -> list[dict]:
    """영상에서 사용 가능한 자막 언어 목록을 반환합니다."""
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        return [
            {
                "code": t.language_code,
                "name": t.language,
                "is_auto": t.is_generated,
            }
            for t in transcript_list
        ]
    except Exception as e:
        raise TranscriptError(
            code="VIDEO_UNAVAILABLE",
            message="영상의 자막 정보를 가져올 수 없습니다.",
            detail=str(e),
        ) from e


async def detect_language(video_id: str) -> str:
    """영상의 자막 언어를 자동 감지합니다."""
    try:
        langs = await list_languages(video_id)
        if not langs:
            return "en"
        # 수동 자막 우선, 없으면 자동 자막
        manual = [l for l in langs if not l["is_auto"]]
        if manual:
            return manual[0]["code"]
        auto = [l for l in langs if l["is_auto"]]
        if auto:
            return auto[0]["code"]
        return "en"
    except Exception:
        return "en"


async def extract_transcript(
    video_id: str, language: str | None = None
) -> list[TranscriptSegment]:
    """2단계 fallback 전략으로 트랜스크립트를 추출합니다.

    language가 None이면 자동 감지 후 추출을 시도합니다.
    """
    if not language:
        language = await detect_language(video_id)
        logger.info(f"자동 감지된 언어: {language}")

    # 1차: 지정 언어로 시도
    try:
        return await extract_transcript_primary(video_id, language)
    except TranscriptError as e:
        if e.code not in ("TRANSCRIPT_UNAVAILABLE", "SERVICE_UNAVAILABLE", "UPSTREAM_ERROR"):
            raise
        logger.warning(f"1차 추출 실패 ({e.code}), fallback 시도")

    # 2차: 자동 감지된 다른 언어로 시도 (지정 언어와 다를 경우)
    if language != "en":
        try:
            return await extract_transcript_primary(video_id, "en")
        except TranscriptError:
            pass

    # 3차: yt-dlp fallback
    return await extract_transcript_fallback(video_id, language)
