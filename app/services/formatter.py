from __future__ import annotations

import html
import re
from datetime import datetime

from app.services.transcript import TranscriptSegment, VideoMetadata


class MarkdownFormatter:
    """트랜스크립트를 Markdown으로 변환합니다."""

    def format(
        self,
        segments: list[TranscriptSegment],
        metadata: VideoMetadata,
        include_timestamps: bool = True,
        include_metadata: bool = True,
        paragraph_gap: float = 3.0,
    ) -> str:
        parts: list[str] = []

        if include_metadata:
            parts.append(self._format_metadata(metadata))

        if include_timestamps:
            parts.append(self._format_with_timestamps(segments, paragraph_gap))
        else:
            parts.append(self._format_without_timestamps(segments, paragraph_gap))

        return "\n".join(parts)

    def _format_metadata(self, metadata: VideoMetadata) -> str:
        lines = [
            f"# {metadata.title}",
            "",
            f"> **채널:** {metadata.channel}  ",
        ]
        if metadata.duration and metadata.duration != "N/A":
            lines.append(f"> **길이:** {metadata.duration}  ")
        lines.extend([
            f"> **URL:** [{metadata.url}]({metadata.url})  ",
            f"> **추출일:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
            "",
            "---",
            "",
        ])
        return "\n".join(lines)

    def _format_with_timestamps(
        self, segments: list[TranscriptSegment], paragraph_gap: float
    ) -> str:
        if not segments:
            return ""

        paragraphs: list[list[TranscriptSegment]] = []
        current_para: list[TranscriptSegment] = [segments[0]]

        for i in range(1, len(segments)):
            gap = segments[i].start - (segments[i - 1].start + segments[i - 1].duration)
            if gap >= paragraph_gap:
                paragraphs.append(current_para)
                current_para = [segments[i]]
            else:
                current_para.append(segments[i])
        paragraphs.append(current_para)

        lines: list[str] = []
        for para in paragraphs:
            if not para:
                continue
            start_time = self._format_time(para[0].start)
            text = self._clean_text(" ".join(s.text for s in para))
            if text.strip():
                lines.append(f"## [{start_time}]")
                lines.append("")
                lines.append(text)
                lines.append("")

        return "\n".join(lines)

    def _format_without_timestamps(
        self, segments: list[TranscriptSegment], paragraph_gap: float
    ) -> str:
        if not segments:
            return ""

        paragraphs: list[list[TranscriptSegment]] = []
        current_para: list[TranscriptSegment] = [segments[0]]

        for i in range(1, len(segments)):
            gap = segments[i].start - (segments[i - 1].start + segments[i - 1].duration)
            if gap >= paragraph_gap:
                paragraphs.append(current_para)
                current_para = [segments[i]]
            else:
                current_para.append(segments[i])
        paragraphs.append(current_para)

        lines: list[str] = []
        for para in paragraphs:
            text = self._clean_text(" ".join(s.text for s in para))
            if text.strip():
                lines.append(text)
                lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_time(seconds: float) -> str:
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    @staticmethod
    def _clean_text(text: str) -> str:
        # HTML 태그 제거
        text = re.sub(r"<[^>]+>", "", text)
        # HTML 엔티티 디코딩
        text = html.unescape(text)
        # 연속된 공백 정리
        text = re.sub(r" {2,}", " ", text)
        # 연속된 빈 줄 정리 (최대 1개)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def sanitize_filename(title: str, date: str | None = None) -> str:
    """파일명에서 특수문자를 제거하고 안전한 파일명을 생성합니다."""
    if date is None:
        date = datetime.now().strftime("%Y%m%d")
    # 특수문자 제거, 공백을 언더스코어로
    sanitized = re.sub(r'[<>:"/\\|?*]', "", title)
    sanitized = re.sub(r"\s+", "_", sanitized)
    sanitized = sanitized[:50]
    return f"{sanitized}_{date}.md"
