from pydantic import BaseModel, Field


class TranscriptRequest(BaseModel):
    url: str = Field(..., description="YouTube 영상 URL")
    language: str | None = Field(None, description="자막 언어 코드 (예: ko, en)")
    include_timestamps: bool = Field(True, description="타임스탬프 포함 여부")
    include_metadata: bool = Field(True, description="영상 메타데이터 포함 여부")


class TranscriptData(BaseModel):
    video_id: str
    title: str
    channel: str
    duration: str
    language: str
    available_languages: list[str]
    markdown: str
    download_filename: str
    segment_count: int
    word_count: int


class TranscriptResponse(BaseModel):
    success: bool = True
    data: TranscriptData


class ErrorDetail(BaseModel):
    code: str
    message: str
    detail: str | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class LanguageInfo(BaseModel):
    code: str
    name: str
    is_auto: bool


class LanguagesResponse(BaseModel):
    video_id: str
    languages: list[LanguageInfo]


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    uptime: float
