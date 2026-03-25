FROM python:3.11

# Node.js(>=18)와 필수 도구 설치
RUN apt-get update \
  && apt-get install -y --no-install-recommends nodejs npm \
  && rm -rf /var/lib/apt/lists/*

# uv 공식 이미지에서 uv 바이너리 복사
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

# 캐시 활용을 위해 의존성 파일 먼저 복사
COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package-lock.json ./frontend/
COPY backend/pyproject.toml backend/uv.lock ./backend/

# 의존성 설치 (Node + Python)
RUN npm ci \
  && npm ci --prefix frontend \
  && cd backend && uv sync --frozen

# 프로젝트 소스 복사
COPY . .

EXPOSE 3000 5001

# 프런트엔드/백엔드를 동시에 실행 (개발 모드)
CMD ["npm", "run", "dev"]
