"""
설정 관리
프로젝트 루트의 `.env` 파일에서 설정을 통합 로드합니다.
"""

import os
from dotenv import load_dotenv

# 프로젝트 루트의 `.env` 파일 로드
# 경로: Neofish/.env (backend/app/config.py 기준 상대 경로)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # 루트에 `.env`가 없으면 시스템 환경 변수를 사용(운영 환경용)
    load_dotenv(override=True)


class Config:
    """애플리케이션 설정"""

    # 서버·세션
    SECRET_KEY = os.environ.get('SECRET_KEY')  # 반드시 .env에 설정하세요 (기본값 없음)
    if SECRET_KEY is None:
        import warnings
        warnings.warn(
            "SECRET_KEY가 설정되지 않았습니다. .env 파일에 SECRET_KEY를 설정해 주세요.",
            stacklevel=1
        )
        SECRET_KEY = os.urandom(32).hex()  # 재시작마다 달라지는 임시값 (세션 무효화됨)
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # JSON 설정 - ASCII 이스케이프 비활성화(문자가 `\\uXXXX` 대신 그대로 표시)
    JSON_AS_ASCII = False
    
    # LLM 설정(OpenAI 형식으로 통일)
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    # 대량·경량 호출(청크 추출, 에이전트 프로필, OASIS 런타임 기록 등)
    LLM_MODEL_NAME = os.environ.get(
        'LLM_MODEL_NAME',
        'gemini-3.1-flash-lite-preview',
    )
    # 보고서·리포트 에이전트 채팅, 온톨로지, 시뮬레이션 설정 생성 등 고급 추론
    LLM_REASONING_MODEL_NAME = os.environ.get(
        'LLM_REASONING_MODEL_NAME',
        'gemini-3.1-pro-preview',
    )
    # 텍스트 임베딩 모델 (Neo4j Vector Search 용)
    LLM_EMBEDDING_MODEL = os.environ.get(
        'LLM_EMBEDDING_MODEL',
        'gemini-embedding-2-preview',
    )
    
    # Google API Key (Gemini Embedding용, LLM_API_KEY와 동일할 수 있음)
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', os.environ.get('LLM_API_KEY'))
    
    # Neo4j 그래프 저장소
    # 단일 인스턴스: bolt://host:7687 권장. neo4j:// 는 클러스터 라우팅용이라
    # 로컬에서 "Unable to retrieve routing information" 이 나면 bolt:// 로 바꾸거나
    # neo4j_store에서 NEO4J_FORCE_BOLT=true(기본)로 bolt 로 자동 변환된다.
    NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', '')
    NEO4J_MEMORY_MAX_EPISODES = int(os.environ.get('NEO4J_MEMORY_MAX_EPISODES', '300'))
    NEO4J_MEMORY_MAX_ITEMS = int(os.environ.get('NEO4J_MEMORY_MAX_ITEMS', '1200'))
    NEO4J_MEMORY_RETENTION_DAYS = int(os.environ.get('NEO4J_MEMORY_RETENTION_DAYS', '30'))
    NEO4J_MEMORY_MIN_EFFECTIVE_SCORE = float(
        os.environ.get('NEO4J_MEMORY_MIN_EFFECTIVE_SCORE', '32')
    )
    # Neo4j 드라이버(연결 풀·타임아웃)
    NEO4J_MAX_CONNECTION_POOL_SIZE = int(os.environ.get('NEO4J_MAX_CONNECTION_POOL_SIZE', '50'))
    NEO4J_CONNECTION_ACQUISITION_TIMEOUT = float(
        os.environ.get('NEO4J_CONNECTION_ACQUISITION_TIMEOUT', '60')
    )
    # 그래프 검색 시 SimMemory 후보 상한(전량 로드 방지)
    NEO4J_SEARCH_MEMORY_MAX_SCAN = int(os.environ.get('NEO4J_SEARCH_MEMORY_MAX_SCAN', '400'))

    # 파일 업로드 설정
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}
    
    # 텍스트 처리 설정
    DEFAULT_CHUNK_SIZE = 500  # 기본 청크 크기
    DEFAULT_CHUNK_OVERLAP = 50  # 기본 청크 겹침 크기
    
    # OASIS 시뮬레이션 설정
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
    OASIS_PREPARE_PARALLEL_TASKS = os.environ.get(
        'OASIS_PREPARE_PARALLEL_TASKS', 'true'
    ).lower() == 'true'
    OASIS_PROFILE_VERBOSE_LOGGING = os.environ.get(
        'OASIS_PROFILE_VERBOSE_LOGGING', 'false'
    ).lower() == 'true'
    OASIS_PROFILE_REALTIME_SAVE_EVERY = int(
        os.environ.get('OASIS_PROFILE_REALTIME_SAVE_EVERY', '5')
    )
    OASIS_PROFILE_REALTIME_SAVE_MIN_INTERVAL_SECONDS = float(
        os.environ.get('OASIS_PROFILE_REALTIME_SAVE_MIN_INTERVAL_SECONDS', '1.5')
    )
    OASIS_CONFIG_BATCH_WORKERS = max(
        1, int(os.environ.get('OASIS_CONFIG_BATCH_WORKERS', '3'))
    )
    
    # OASIS 플랫폼별 사용 가능 액션
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]
    
    # Report Agent 설정
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))
    
    @classmethod
    def graph_storage_configured(cls) -> bool:
        return bool(cls.NEO4J_URI and cls.NEO4J_PASSWORD)

    @classmethod
    def validate(cls):
        """필수 설정 검증"""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY가 설정되지 않았습니다.")
        if not cls.NEO4J_URI:
            errors.append("NEO4J_URI가 설정되지 않았습니다.")
        if not cls.NEO4J_PASSWORD:
            errors.append("NEO4J_PASSWORD가 설정되지 않았습니다.")
        return errors
