<div align="center">

# 🎬 YouTube → Markdown

**YouTube 영상의 음성을 아름다운 Markdown으로 변환합니다**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

<br />

YouTube URL을 입력하면 영상의 자막을 깔끔한 Markdown 파일로 변환해주는 웹 애플리케이션입니다.

[기능](#-주요-기능) · [설치](#-빠른-시작) · [사용법](#-사용법) · [API](#-api) · [배포](#-배포)

</div>

---

## ✨ 주요 기능

| 기능 | 설명 |
|:-----|:-----|
| 🔗 **URL 입력** | YouTube URL 붙여넣기만 하면 변환 시작 |
| 🌍 **다국어 지원** | 한국어, 영어, 일본어, 중국어 등 자막 자동 감지 |
| ⏱️ **타임스탬프** | `[MM:SS]` 형식의 구간별 타임스탬프 포함 |
| 📝 **스마트 포맷팅** | 3초 이상 침묵 구간 기반 단락 자동 분리 |
| 📥 **파일 다운로드** | Markdown 파일 즉시 다운로드 |
| 📋 **클립보드 복사** | 한 번의 클릭으로 내용 복사 |
| ⚡ **캐싱** | 동일 영상 반복 요청 시 즉시 응답 |
| 🛡️ **서킷 브레이커** | YouTube API 장애 시 자동 복구 |
| 🎯 **진행률 표시** | 4단계 프로그레스 바로 처리 과정 시각화 |

---

## 🚀 빠른 시작

### 사전 요구사항

- Python 3.11+
- FFmpeg (yt-dlp fallback용)

### 설치

```bash
# 저장소 클론
git clone https://github.com/DeclanJeon/youtube-to-md.git
cd youtube-to-md

# 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 의존성 설치
pip install -r requirements.txt

# (선택) YouTube Data API 키 설정
cp .env.example .env
# .env 파일에서 YOUTUBE_API_KEY 설정
```

### 실행

```bash
uvicorn app.main:app --reload
# → http://localhost:8000
```

---

## 📖 사용법

1. 브라우저에서 `http://localhost:8000` 접속
2. YouTube URL 입력
3. (선택) 옵션에서 타임스탬프/메타데이터/언어 설정
4. **Markdown으로 변환** 클릭
5. 다운로드 또는 클립보드 복사

<div align="center">
<img src="https://via.placeholder.com/720x400/202124/8ab4f8?text=YouTube→MD+Screenshot" alt="Screenshot" width="720" />
</div>

---

## 📡 API

### 트랜스크립트 추출

```http
POST /api/transcript
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "language": "ko",           // null = 자동 감지
  "include_timestamps": true,
  "include_metadata": true
}
```

**응답:**
```json
{
  "success": true,
  "data": {
    "video_id": "dQw4w9WgXcQ",
    "title": "Rick Astley - Never Gonna Give You Up",
    "channel": "Rick Astley",
    "language": "en",
    "markdown": "# Rick Astley - Never Gonna Give You Up\n...",
    "segment_count": 394,
    "word_count": 25810,
    "download_filename": "Rick_Astley_-_Never_Gonna_Give_You_Up_20260619.md"
  }
}
```

### 자막 언어 목록

```http
GET /api/languages/{video_id}
```

### 헬스체크

```http
GET /api/health
```

---

## 🏗️ 아키텍처

```
youtube-to-md/
├── app/
│   ├── main.py              ← FastAPI 앱 + 미들웨어
│   ├── config.py             ← Pydantic Settings
│   ├── api/routes.py         ← API 엔드포인트
│   ├── models/schemas.py     ← Pydantic 모델
│   └── services/
│       ├── transcript.py     ← 자막 추출 (2단계 fallback)
│       ├── formatter.py      ← Markdown 포맷터
│       ├── cache.py          ← 캐시 추상 인터페이스
│       └── circuit_breaker.py ← 서킷 브레이커
├── static/                   ← 프론트엔드 (Vanilla JS)
├── tests/                    ← 45개 테스트
├── Dockerfile
└── docker-compose.yml
```

### 자막 추출 전략

```
URL → 캐시 확인 → (API 키?) → YouTube Data API v3
                              → youtube-transcript-api
                              → yt-dlp fallback
                              → 에러
```

---

## 🧪 테스트

```bash
# 전체 테스트 실행
pytest tests/ -v

# 특정 테스트만
pytest tests/test_url_validation.py -v
pytest tests/test_formatter.py -v
```

```
45 passed in 0.82s
```

---

## 🐳 배포

### Docker

```bash
docker compose up --build
# → http://localhost:8000
```

### 환경 변수

| 변수 | 설명 | 기본값 |
|:-----|:-----|:-------|
| `YOUTUBE_API_KEY` | YouTube Data API v3 키 (선택) | - |
| `APP_PORT` | 서버 포트 | `8000` |
| `RATE_LIMIT_PER_MINUTE` | 분당 요청 제한 | `10` |
| `CACHE_TTL_SECONDS` | 캐시 TTL | `3600` |

---

## 🛠️ 기술 스택

| 계층 | 기술 |
|:-----|:-----|
| **Backend** | Python 3.11+, FastAPI, Uvicorn |
| **Frontend** | HTML, CSS, Vanilla JavaScript |
| **자막 추출** | youtube-transcript-api, yt-dlp |
| **메타데이터** | YouTube oEmbed API |
| **캐시** | cachetools (TTLCache) |
| **설정** | Pydantic Settings |
| **배포** | Docker, docker-compose |

---

## 📄 License

MIT License - [LICENSE](LICENSE) 파일 참조

---

<div align="center">

**⭐ 이 프로젝트가 유용하다면 Star를 눌러주세요!**

Made with ❤️ by [DeclanJeon](https://github.com/DeclanJeon)

</div>
