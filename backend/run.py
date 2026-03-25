"""
Neofish Backend 실행 진입점
"""

import os
import sys

# Windows 콘솔 한글/중문 깨짐 방지: 모든 import 이전에 UTF-8 설정
if sys.platform == 'win32':
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import Config

app = create_app()


def main():
    """메인 함수"""
    errors = Config.validate()
    if errors:
        print("설정 오류:")
        for err in errors:
            print(f"  - {err}")
        print("\n.env 파일 설정을 확인해 주세요.")
        sys.exit(1)

    host = os.environ.get('FLASK_HOST', os.environ.get('FASTAPI_HOST', '0.0.0.0'))
    port = int(os.environ.get('FLASK_PORT', os.environ.get('FASTAPI_PORT', 5001)))
    debug = Config.DEBUG

    import uvicorn

    if debug:
        print(f"Uvicorn 개발 모드(리로드): http://{host}:{port}")
        uvicorn.run(
            "run:app",
            host=host,
            port=port,
            reload=True,
        )
    else:
        workers = max(1, int(os.environ.get("UVICORN_WORKERS", "1")))
        print(f"Uvicorn 서버: http://{host}:{port} (workers={workers})")
        if workers > 1:
            uvicorn.run(
                "run:app",
                host=host,
                port=port,
                workers=workers,
                log_level="info",
            )
        else:
            uvicorn.run(
                app,
                host=host,
                port=port,
                log_level="info",
            )


if __name__ == '__main__':
    main()
