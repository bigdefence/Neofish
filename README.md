# NeoFish

시드 문서와 자연어 요구만으로 **예측 리포트·하이브리드 그래프·소셜 시뮬레이션(OASIS)**을 묶은 풀스택 앱입니다. **Graph RAG(Vector + Full-Text + Keyword)**로 검색·질의를 넓히고, 에이전트 시뮬·ReportAgent·팟캐스트까지 한 흐름으로 제공합니다.

---

## 목차

- [기능 요약](#기능-요약)
- [스택](#스택)
- [환경 변수](#환경-변수)
- [REST API](#rest-api)
- [빠른 시작](#빠른-시작)
- [보안·운영](#보안운영)
- [관련 오픈소스](#관련-오픈소스)

---

## 기능 요약

| 영역 | 내용 |
|------|------|
| **RAG** | Vector(Gemini) + Full-Text + Keyword 하이브리드 검색 |
| **그래프** | LLM 추출 → Neo4j, 벡터 기반 엔터티 해상도 |
| **시뮬** | Twitter / Reddit / 병렬 OASIS, subprocess + 파일 IPC(인터뷰 등) |
| **리포트** | ReportAgent + InsightForge 도구, 채팅·팟캐스트 |
| **UI** | Vue 3 + D3 관계 네트워크 |

---

## 스택

- **백엔드**: FastAPI, Uvicorn  
- **그래프**: Neo4j 5.x (Vector / Full-Text)  
- **LLM**: OpenAI SDK 호환 + `google-genai`(임베딩)  
- **프런트**: Vue 3, Vite, D3  

모델·청크·업로드 한도 등 세부 기본값은 **`backend/app/config.py`**를 참고하세요.

---

## 환경 변수

`backend/app/config.py`가 **프로젝트 루트 `.env`**를 우선 로드합니다. 키 이름은 **`.env.example`**과 동일합니다.

| 변수 | 용도 |
|------|------|
| `LLM_API_KEY`, `LLM_BASE_URL` | LLM(필수, OpenAI 호환 엔드포인트) |
| `GOOGLE_API_KEY` | Gemini 임베딩(없으면 `LLM_API_KEY`와 공유 가능) |
| `LLM_MODEL_NAME`, `LLM_REASONING_MODEL_NAME`, `LLM_EMBEDDING_MODEL` | 모델 ID(제공자 문서와 맞출 것) |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | Neo4j Bolt(필수) |
| `SECRET_KEY` | 세션용(운영 시 반드시 설정) |
| `ALLOWED_ORIGINS` | CORS(미설정 시 `*`) |
| `LLM_BOOST_*` | 선택, 병렬 시뮬 등(`.env.example` 참고) |
| `OASIS_*`, `REPORT_AGENT_*` | 시뮬·보고서 튜닝(선택) |

---

## REST API

접두사: **`/api/graph`**, **`/api/simulation`**, **`/api/report`**. 라우트·파라미터는 **`backend/app/api/*.py`**가 정본입니다. 헬스: **`GET /health`**.

---

## 빠른 시작

### 요구 사항

Node.js 18+, Python 3.11/3.12, **uv** 권장.

### 1. 환경 변수

```bash
cp .env.example .env
# API 키·Neo4j 비밀번호 입력
```

`LLM_BASE_URL`과 모델명은 **같은 제공자(게이트웨이)**에 맞춥니다.

### 2. 설치

```bash
npm run setup:all
```

또는 `npm run setup` 후 `npm run setup:backend`.

### 3. Neo4j(로컬)

```bash
docker compose up -d neo4j
```

브라우저 `http://localhost:7474` — `NEO4J_PASSWORD`는 `docker-compose.yml`의 `NEO4J_AUTH`와 맞춥니다(예: `neo4j/neofish_local`).

### 4. 개발 서버

```bash
npm run dev
```

| 서비스 | URL |
|--------|-----|
| 프런트 | http://localhost:3000 |
| API | http://localhost:5001 |

개별 실행: `npm run backend`, `npm run frontend`.

### Docker

```bash
cp .env.example .env
docker compose up -d
```

포트: **3000** / **5001**. `docker-compose.yml` 주석에 이미지 미러 안내가 있을 수 있습니다.

---

## 보안·운영

- 공개 배포 시 CORS·역프록시로 **`ALLOWED_ORIGINS`**를 구체적으로 두는 것을 권장합니다.  
- API 키는 **저장소에 커밋하지 말고** `.env` 또는 배포 환경 변수로만 주입하세요.

---

## 관련 오픈소스

- **[OASIS (CAMEL-AI)](https://github.com/camel-ai/oasis)** — 시뮬레이션 런타임  
- **[Neo4j](https://neo4j.com/)** — 그래프 저장소(Bolt)
