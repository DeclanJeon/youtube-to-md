import pytest
from app.services.transcript import extract_video_id, TranscriptError


class TestExtractVideoId:
    def test_standard_url(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_embed_url(self):
        assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_shorts_url(self):
        assert extract_video_id("https://youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_mobile_url(self):
        assert extract_video_id("https://m.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_url_with_params(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120") == "dQw4w9WgXcQ"

    def test_url_with_pp_param(self):
        assert extract_video_id("https://www.youtube.com/watch?v=z9WbRkiRQtc&pp=ugUEEgJlbg%3D%3D") == "z9WbRkiRQtc"

    def test_invalid_google_url(self):
        with pytest.raises(TranscriptError) as exc_info:
            extract_video_id("https://www.google.com")
        assert exc_info.value.code == "INVALID_URL"

    def test_short_video_id(self):
        with pytest.raises(TranscriptError) as exc_info:
            extract_video_id("https://www.youtube.com/watch?v=SHORT")
        assert exc_info.value.code == "INVALID_URL"

    def test_empty_string(self):
        with pytest.raises(TranscriptError) as exc_info:
            extract_video_id("")
        assert exc_info.value.code == "INVALID_URL"

    def test_no_protocol(self):
        assert extract_video_id("youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_http_protocol(self):
        assert extract_video_id("http://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
