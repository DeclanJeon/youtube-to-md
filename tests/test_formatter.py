import pytest
from app.services.formatter import MarkdownFormatter, sanitize_filename
from app.services.transcript import TranscriptSegment, VideoMetadata


@pytest.fixture
def formatter():
    return MarkdownFormatter()


@pytest.fixture
def metadata():
    return VideoMetadata(
        video_id="dQw4w9WgXcQ",
        title="테스트 영상 제목",
        channel="테스트 채널",
        duration="10:30",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        language="ko",
    )


class TestFormatWithTimestamps:
    def test_empty_segments(self, formatter, metadata):
        result = formatter.format([], metadata, include_timestamps=True, include_metadata=False)
        assert result == ""

    def test_single_segment(self, formatter, metadata):
        segments = [TranscriptSegment(text="안녕하세요", start=0.0, duration=2.0)]
        result = formatter.format(segments, metadata, include_timestamps=True, include_metadata=False)
        assert "## [00:00]" in result
        assert "안녕하세요" in result

    def test_two_segments_close(self, formatter, metadata):
        segments = [
            TranscriptSegment(text="첫 번째", start=0.0, duration=1.0),
            TranscriptSegment(text="두 번째", start=1.5, duration=1.0),
        ]
        result = formatter.format(segments, metadata, include_timestamps=True, include_metadata=False)
        # 0.5초 간격 = 같은 단락
        assert result.count("## [") == 1

    def test_two_segments_far(self, formatter, metadata):
        segments = [
            TranscriptSegment(text="첫 번째", start=0.0, duration=1.0),
            TranscriptSegment(text="두 번째", start=5.0, duration=1.0),
        ]
        result = formatter.format(segments, metadata, include_timestamps=True, include_metadata=False)
        # 4초 간격 = 다른 단락
        assert result.count("## [") == 2

    def test_hour_format(self, formatter, metadata):
        segments = [TranscriptSegment(text="긴 영상", start=3661.0, duration=2.0)]
        result = formatter.format(segments, metadata, include_timestamps=True, include_metadata=False)
        assert "[1:01:01]" in result


class TestFormatWithoutTimestamps:
    def test_no_timestamps(self, formatter, metadata):
        segments = [
            TranscriptSegment(text="첫 번째", start=0.0, duration=1.0),
            TranscriptSegment(text="두 번째", start=1.5, duration=1.0),
        ]
        result = formatter.format(segments, metadata, include_timestamps=False, include_metadata=False)
        assert "## [" not in result
        assert "첫 번째" in result


class TestMetadata:
    def test_metadata_included(self, formatter, metadata):
        segments = [TranscriptSegment(text="내용", start=0.0, duration=1.0)]
        result = formatter.format(segments, metadata, include_timestamps=False, include_metadata=True)
        assert "# 테스트 영상 제목" in result
        assert "**채널:** 테스트 채널" in result

    def test_metadata_excluded(self, formatter, metadata):
        segments = [TranscriptSegment(text="내용", start=0.0, duration=1.0)]
        result = formatter.format(segments, metadata, include_timestamps=False, include_metadata=False)
        assert "# 테스트 영상 제목" not in result


class TestCleanText:
    def test_html_tags_removed(self, formatter, metadata):
        segments = [TranscriptSegment(text="<b>굵은 글씨</b>", start=0.0, duration=1.0)]
        result = formatter.format(segments, metadata, include_timestamps=False, include_metadata=False)
        assert "<b>" not in result
        assert "</b>" not in result

    def test_html_entities_decoded(self, formatter, metadata):
        segments = [TranscriptSegment(text="hello &amp; world", start=0.0, duration=1.0)]
        result = formatter.format(segments, metadata, include_timestamps=False, include_metadata=False)
        assert "&amp;" not in result
        assert "hello & world" in result


class TestSanitizeFilename:
    def test_normal_title(self):
        result = sanitize_filename("파이썬 튜토리얼", "20260619")
        assert result == "파이썬_튜토리얼_20260619.md"

    def test_special_chars(self):
        result = sanitize_filename('Test: File "Name" <with> chars', "20260619")
        assert "<" not in result
        assert ">" not in result
        assert '"' not in result
        assert ":" not in result

    def test_long_title_truncated(self):
        result = sanitize_filename("A" * 100, "20260619")
        assert len(result) <= 50 + 9 + 3  # 50 chars + _YYYYMMDD + .md


class TestQualityCriteria:
    """PRD §10.2 기계적 검증 가능한 품질 기준 테스트."""

    def test_no_consecutive_blank_lines(self, formatter, metadata):
        """연속된 빈 줄이 3개 이상이면 안 된다."""
        segments = [
            TranscriptSegment(text="첫 번째", start=0.0, duration=1.0),
            TranscriptSegment(text="두 번째", start=5.0, duration=1.0),
            TranscriptSegment(text="세 번째", start=10.0, duration=1.0),
        ]
        result = formatter.format(segments, metadata, include_timestamps=True, include_metadata=True)
        assert "\n\n\n" not in result

    def test_no_html_tag_remnants(self, formatter, metadata):
        """HTML 태그가 출력에 잔존하면 안 된다."""
        segments = [
            TranscriptSegment(text="<b>굵은</b> <i>기울임</i> &amp; 텍스트", start=0.0, duration=1.0),
        ]
        result = formatter.format(segments, metadata, include_timestamps=False, include_metadata=False)
        assert "<" not in result
        assert ">" not in result
        assert "&amp;" not in result

    def test_timestamps_ascending(self, formatter, metadata):
        """타임스탬프가 오름차순 정렬이어야 한다."""
        segments = [
            TranscriptSegment(text="첫째", start=0.0, duration=1.0),
            TranscriptSegment(text="둘째", start=5.0, duration=1.0),
            TranscriptSegment(text="셋째", start=10.0, duration=1.0),
        ]
        result = formatter.format(segments, metadata, include_timestamps=True, include_metadata=False)
        import re
        timestamps = re.findall(r"\[(\d+:\d+(?::\d+)?)\]", result)
        # 타임스탬프가 존재하고 오름차순인지 확인
        assert len(timestamps) >= 2
        prev = timestamps[0]
        for ts in timestamps[1:]:
            assert ts >= prev, f"Timestamp {ts} is not after {prev}"
            prev = ts

    def test_h1_title_present_with_metadata(self, formatter, metadata):
        """메타데이터 포함 시 H1 제목이 존재해야 한다."""
        segments = [TranscriptSegment(text="내용", start=0.0, duration=1.0)]
        result = formatter.format(segments, metadata, include_timestamps=False, include_metadata=True)
        assert result.startswith("# 테스트 영상 제목")
