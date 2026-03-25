"""
API 라우트 모듈
"""

from fastapi import APIRouter

graph_router = APIRouter()
simulation_router = APIRouter()
report_router = APIRouter()

from . import graph  # noqa: E402, F401
from . import simulation  # noqa: E402, F401
from . import report  # noqa: E402, F401
