import app.api.routes as routes_module


import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from app.main import app
from app.services.transcript import TranscriptSegment, VideoMetadata, TranscriptError


client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_cache():
    """각 테스트 전에 캐시를 초기화합니다."""
    routes_module.cache._cache.clear()


class TestHealthEndpoint:
    def test_health(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "uptime" in data


class TestTranscriptEndpoint:
    def test_invalid_url(self):
        resp = client.post("/api/transcript", json={"url": "https://www.google.com"})
        assert resp.status_code == 400
        data = resp.json()
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_URL"

    def test_invalid_url_short_id(self):
        resp = client.post("/api/transcript", json={"url": "https://www.youtube.com/watch?v=SHORT"})
        assert resp.status_code == 400

    def test_missing_url(self):
        resp = client.post("/api/transcript", json={})
        assert resp.status_code == 422

    @patch("app.services.transcript.YouTubeTranscriptApi")
    @patch("app.api.routes.fetch_metadata", new_callable=AsyncMock)
    @patch("app.api.routes.list_languages", new_callable=AsyncMock)
    def test_successful_extraction(self, mock_langs, mock_meta, mock_ytt):
        mock_meta.return_value = VideoMetadata(
            video_id="dQw4w9WgXcQ",
            title="Test Video",
            channel="Test Channel",
            duration="3:33",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            language="ko",
        )
        mock_langs.return_value = [
            {"code": "ko", "name": "Korean", "is_auto": False},
        ]

        # Mock youtube_transcript_api
        mock_instance = MagicMock()
        mock_snippet = MagicMock()
        mock_snippet.text = "안녕하세요"
        mock_snippet.start = 0.0
        mock_snippet.duration = 2.0
        mock_instance.fetch.return_value = [mock_snippet]
        mock_ytt.return_value = mock_instance

        resp = client.post(
            "/api/transcript",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["video_id"] == "dQw4w9WgXcQ"
        assert data["data"]["title"] == "Test Video"

    @patch("app.services.transcript.YouTubeTranscriptApi")
    @patch("app.api.routes.fetch_metadata", new_callable=AsyncMock)
    def test_transcript_unavailable(self, mock_meta, mock_ytt):
        from youtube_transcript_api._errors import TranscriptsDisabled

        mock_meta.return_value = VideoMetadata(
            video_id="dQw4w9WgXcQ",
            title="Test",
            channel="Test",
            duration="",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            language="ko",
        )

        mock_instance = MagicMock()
        mock_instance.fetch.side_effect = TranscriptsDisabled("dQw4w9WgXcQ")
        mock_ytt.return_value = mock_instance

        resp = client.post(
            "/api/transcript",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        )
        assert resp.status_code == 404
        data = resp.json()
        assert data["success"] is False
        assert data["error"]["code"] == "TRANSCRIPT_DISABLED"
