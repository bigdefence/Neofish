"""
Neofish Backend - FastAPI 애플리케이션 팩토리
"""

import os
import warnings
from contextlib import asynccontextmanager

# `multiprocessing resource_tracker` 경고 억제(transformers 등 서드파티 라이브러리에서 발생)
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from .config import Config
from .utils.logger import setup_logger, get_logger


def _start_task_cleanup_scheduler(logger):
    """완료/실패 작업을 1시간마다 정리하는 백그라운드 스레드를 시작합니다."""
    import threading
    import time as _time

    def _cleanup_loop():
        while True:
            _time.sleep(3600)  # 1시간 대기
            try:
                from .models.task import TaskManager
                TaskManager().cleanup_old_tasks(max_age_hours=24)
                logger.debug("TaskManager: 오래된 작업 정리 실행 완료")
            except Exception as e:
                logger.warning(f"TaskManager 정리 중 오류: {e}")

    t = threading.Thread(target=_cleanup_loop, daemon=True, name="task-cleanup")
    t.start()


def create_app(config_class=Config):
    """FastAPI 애플리케이션 팩토리 함수"""
    logger = setup_logger('neofish')

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        from .services.simulation_runner import SimulationRunner
        SimulationRunner.register_cleanup()
        logger.info("시뮬레이션 프로세스 정리 함수 등록 완료")
        _start_task_cleanup_scheduler(logger)
        logger.info("Neofish Backend 시작 완료")
        yield

    app = FastAPI(
        title="Neofish Backend",
        lifespan=lifespan,
    )

    logger.info("=" * 50)
    logger.info("Neofish Backend 앱 생성 중...")
    logger.info("=" * 50)

    # 응답 압축(큰 JSON에 유리)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # CORS
    allowed_origins = os.environ.get('ALLOWED_ORIGINS', '*').split(',')
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_request(request: Request, call_next):
        req_logger = get_logger('neofish.request')
        req_logger.debug(f"요청: {request.method} {request.url.path}")
        response = await call_next(request)
        req_logger.debug(f"응답: {response.status_code}")
        return response

    from .api import graph_router, simulation_router, report_router
    app.include_router(graph_router, prefix='/api/graph', tags=['graph'])
    app.include_router(simulation_router, prefix='/api/simulation', tags=['simulation'])
    app.include_router(report_router, prefix='/api/report', tags=['report'])

    @app.get('/health')
    def health():
        return {'status': 'ok', 'service': 'Neofish Backend'}

    return app
