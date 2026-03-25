"""
Report API라우트
시뮬레이션보고서 생성, , API
"""

import os
import traceback
import threading
import wave
from fastapi import Request
from fastapi.responses import JSONResponse, FileResponse

from . import report_router
from ..config import Config
from ..services.report_agent import ReportAgent, ReportManager, ReportStatus
from ..services.simulation_manager import SimulationManager
from ..models.project import ProjectManager
from ..models.task import TaskManager, TaskStatus
from ..utils.logger import get_logger

logger = get_logger('neofish.api.report')


def _qp_int(params, key: str, default: int) -> int:
    v = params.get(key)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _is_valid_podcast_file(path: str) -> bool:
    if not os.path.exists(path):
        return False

    try:
        if os.path.getsize(path) <= 44:
            return False

        with wave.open(path, 'rb') as audio_file:
            return audio_file.getnframes() > 0 and audio_file.getnchannels() > 0
    except (OSError, wave.Error):
        return False


# ============== 보고서 생성API ==============

@report_router.post('/generate')
async def generate_report(request: Request):
    """
    생성시뮬레이션분석보고서(작업)
    
    , API반환task_id, 
     GET /api/report/generate/status 진행률 조회
    
    요청(JSON):
        {
            "simulation_id": "sim_xxxx",    // 필수, 시뮬레이션 ID
            "force_regenerate": false        // 선택, 생성
        }
    
    반환:
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "task_id": "task_xxxx",
                "status": "generating",
                "message": "보고서 생성작업 시작"
            }
        }
    """
    try:
        data = (await request.json()) or {}
        
        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return JSONResponse(status_code=400, content={
                "success": False,
                "error": "simulation_id를 입력해 주세요."
            })
        
        force_regenerate = data.get('force_regenerate', False)
        
        # 시뮬레이션정보
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        
        if not state:
            return JSONResponse(status_code=404, content={
                "success": False,
                "error": f"시뮬레이션이 존재하지 않습니다: {simulation_id}"
            })
        
        # 보고서
        if not force_regenerate:
            existing_report = ReportManager.get_report_by_simulation(simulation_id)
            if existing_report and existing_report.status == ReportStatus.COMPLETED:
                return {
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "report_id": existing_report.report_id,
                        "status": "completed",
                        "message": "보고서",
                        "already_generated": True
                    }
                }
        
        # 프로젝트정보
        project = ProjectManager.get_project(state.project_id)
        if not project:
            return JSONResponse(status_code=404, content={
                "success": False,
                "error": f"프로젝트가 존재하지 않습니다: {state.project_id}"
            })
        
        graph_id = state.graph_id or project.graph_id
        if not graph_id:
            return JSONResponse(status_code=400, content={
                "success": False,
                "error": "누락그래프 ID, 그래프"
            })
        
        simulation_requirement = project.simulation_requirement
        if not simulation_requirement:
            return JSONResponse(status_code=400, content={
                "success": False,
                "error": "누락시뮬레이션"
            })
        
        # 생성 report_id, 반환
        import uuid
        report_id = f"report_{uuid.uuid4().hex[:12]}"
        
        # 작업
        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="report_generate",
            metadata={
                "simulation_id": simulation_id,
                "graph_id": graph_id,
                "report_id": report_id
            }
        )
        
        # 작업
        def run_generate():
            try:
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.PROCESSING,
                    progress=0,
                    message="Report Agent..."
                )
                
                # Report Agent
                agent = ReportAgent(
                    graph_id=graph_id,
                    simulation_id=simulation_id,
                    simulation_requirement=simulation_requirement
                )
                
                # 진행률
                def progress_callback(stage, progress, message):
                    task_manager.update_task(
                        task_id,
                        progress=progress,
                        message=f"[{stage}] {message}"
                    )
                
                # 생성보고서(생성 report_id)
                report = agent.generate_report(
                    progress_callback=progress_callback,
                    report_id=report_id
                )
                
                # 저장보고서
                ReportManager.save_report(report)
                
                if report.status == ReportStatus.COMPLETED:
                    task_manager.complete_task(
                        task_id,
                        result={
                            "report_id": report.report_id,
                            "simulation_id": simulation_id,
                            "status": "completed"
                        }
                    )
                else:
                    task_manager.fail_task(task_id, report.error or "보고서 생성 실패")
                
            except Exception as e:
                logger.error(f"보고서 생성 실패: {str(e)}")
                task_manager.fail_task(task_id, str(e))
        
        # 시작
        thread = threading.Thread(target=run_generate, daemon=True)
        thread.start()
        
        return {
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "report_id": report_id,
                "task_id": task_id,
                "status": "generating",
                "message": "보고서 생성작업 시작,  /api/report/generate/status 진행률 조회",
                "already_generated": False
            }
        }
        
    except Exception as e:
        logger.error(f"시작보고서 생성작업실패: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })


@report_router.post('/generate/status')
async def get_generate_status(request: Request):
    """
    조회보고서 생성작업진행률
    
    요청(JSON):
        {
            "task_id": "task_xxxx",         // 선택, generate반환task_id
            "simulation_id": "sim_xxxx"     // 선택, 시뮬레이션 ID
        }
    
    반환:
        {
            "success": true,
            "data": {
                "task_id": "task_xxxx",
                "status": "processing|completed|failed",
                "progress": 45,
                "message": "..."
            }
        }
    """
    try:
        data = (await request.json()) or {}
        
        task_id = data.get('task_id')
        simulation_id = data.get('simulation_id')
        
        # simulation_id, 완료보고서
        if simulation_id:
            existing_report = ReportManager.get_report_by_simulation(simulation_id)
            if existing_report and existing_report.status == ReportStatus.COMPLETED:
                return {
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "report_id": existing_report.report_id,
                        "status": "completed",
                        "progress": 100,
                        "message": "보고서 생성",
                        "already_completed": True
                    }
                }
        
        if not task_id:
            return JSONResponse(status_code=400, content={
                "success": False,
                "error": "task_id  simulation_id를 입력해 주세요."
            })
        
        task_manager = TaskManager()
        task = task_manager.get_task(task_id)
        
        if not task:
            return JSONResponse(status_code=404, content={
                "success": False,
                "error": f"작업이 존재하지 않습니다: {task_id}"
            })
        
        return {
            "success": True,
            "data": task.to_dict()
        }
        
    except Exception as e:
        logger.error(f"조회작업상태실패: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e)
        })


# ============== 보고서API ==============

@report_router.get('/list')
async def list_reports(request: Request):
    """
    보고서

    Query파라미터:
        simulation_id: 시뮬레이션 ID(선택)
        limit: 반환(50)
    """
    try:
        simulation_id = request.query_params.get('simulation_id')
        limit = _qp_int(request.query_params, 'limit', 50)

        reports = ReportManager.list_reports(
            simulation_id=simulation_id,
            limit=limit
        )

        return {
            "success": True,
            "data": [r.to_dict() for r in reports],
            "count": len(reports)
        }

    except Exception as e:
        logger.error(f"보고서실패: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })


@report_router.get('/by-simulation/{simulation_id}')
async def get_report_by_simulation(request: Request, simulation_id: str):
    """
    시뮬레이션 ID보고서
    """
    try:
        report = ReportManager.get_report_by_simulation(simulation_id)

        if not report:
            return JSONResponse(status_code=404, content={
                "success": False,
                "error": f"시뮬레이션보고서: {simulation_id}",
                "has_report": False
            })

        return {
            "success": True,
            "data": report.to_dict(),
            "has_report": True
        }

    except Exception as e:
        logger.error(f"보고서실패: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })


@report_router.get('/{report_id}')
async def get_report(request: Request, report_id: str):
    """보고서 단건 조회"""
    try:
        report = ReportManager.get_report(report_id)

        if not report:
            return JSONResponse(status_code=404, content={
                "success": False,
                "error": f"보고서가 존재하지 않습니다: {report_id}"
            })

        return {
            "success": True,
            "data": report.to_dict()
        }

    except Exception as e:
        logger.error(f"보고서실패: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })


@report_router.get('/{report_id}/download')
async def download_report(request: Request, report_id: str):
    """
    다운로드보고서(Markdown)
    
    반환Markdown파일
    """
    try:
        report = ReportManager.get_report(report_id)
        
        if not report:
            return JSONResponse(status_code=404, content={
                "success": False,
                "error": f"보고서가 존재하지 않습니다: {report_id}"
            })
        
        md_path = ReportManager._get_report_markdown_path(report_id)
        
        if not os.path.exists(md_path):
            # MD파일이 존재하지 않습니다, 생성파일
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(report.markdown_content)
                temp_path = f.name
            
            return FileResponse(
                temp_path,
                filename=f"{report_id}.md",
                media_type="text/markdown",
            )

        return FileResponse(
            md_path,
            filename=f"{report_id}.md",
            media_type="text/markdown",
        )
        
    except Exception as e:
        logger.error(f"다운로드보고서실패: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })


@report_router.delete('/{report_id}')
async def delete_report(request: Request, report_id: str):
    """삭제보고서"""
    try:
        success = ReportManager.delete_report(report_id)
        
        if not success:
            return JSONResponse(status_code=404, content={
                "success": False,
                "error": f"보고서가 존재하지 않습니다: {report_id}"
            })
        
        return {
            "success": True,
            "message": f"보고서삭제: {report_id}"
        }
        
    except Exception as e:
        logger.error(f"삭제보고서실패: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })


# ============== Report AgentAPI ==============

@report_router.post('/chat')
async def chat_with_report_agent(request: Request):
    """
    Report Agent
    
    Report Agent호출도구질문
    
    요청(JSON):
        {
            "simulation_id": "sim_xxxx",        // 필수, 시뮬레이션 ID
            "message": "",    // 필수, 
            "chat_history": [                   // 선택, 과거
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ]
        }
    
    반환:
        {
            "success": true,
            "data": {
                "response": "Agent...",
                "tool_calls": [도구 호출목록],
                "sources": [정보출처]
            }
        }
    """
    try:
        data = (await request.json()) or {}
        
        simulation_id = data.get('simulation_id')
        message = data.get('message')
        chat_history = data.get('chat_history', [])
        
        if not simulation_id:
            return JSONResponse(status_code=400, content={
                "success": False,
                "error": "simulation_id를 입력해 주세요."
            })
        
        if not message:
            return JSONResponse(status_code=400, content={
                "success": False,
                "error": "message를 입력해 주세요."
            })
        
        # 시뮬레이션프로젝트정보
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        
        if not state:
            return JSONResponse(status_code=404, content={
                "success": False,
                "error": f"시뮬레이션이 존재하지 않습니다: {simulation_id}"
            })
        
        project = ProjectManager.get_project(state.project_id)
        if not project:
            return JSONResponse(status_code=404, content={
                "success": False,
                "error": f"프로젝트가 존재하지 않습니다: {state.project_id}"
            })
        
        graph_id = state.graph_id or project.graph_id
        if not graph_id:
            return JSONResponse(status_code=400, content={
                "success": False,
                "error": "누락그래프 ID"
            })
        
        simulation_requirement = project.simulation_requirement or ""
        
        # Agent
        agent = ReportAgent(
            graph_id=graph_id,
            simulation_id=simulation_id,
            simulation_requirement=simulation_requirement
        )
        
        result = agent.chat(message=message, chat_history=chat_history)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"실패: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })


# ============== 보고서진행률섹션API ==============

@report_router.get('/{report_id}/progress')
async def get_report_progress(request: Request, report_id: str):
    """
    보고서 생성진행률()
    
    반환:
        {
            "success": true,
            "data": {
                "status": "generating",
                "progress": 45,
                "message": "진행 중생성섹션: 핵심",
                "current_section": "핵심",
                "completed_sections": ["요약", "시뮬레이션"],
                "updated_at": "2025-12-09T..."
            }
        }
    """
    try:
        progress = ReportManager.get_progress(report_id)
        
        if not progress:
            return JSONResponse(status_code=404, content={
                "success": False,
                "error": f"보고서가 존재하지 않습니다진행률정보: {report_id}"
            })
        
        return {
            "success": True,
            "data": progress
        }
        
    except Exception as e:
        logger.error(f"보고서진행률실패: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })


@report_router.get('/{report_id}/sections')
async def get_report_sections(request: Request, report_id: str):
    """
    생성섹션목록(섹션)
    
    API생성섹션, 보고서완료
    
    반환:
        {
            "success": true,
            "data": {
                "report_id": "report_xxxx",
                "sections": [
                    {
                        "filename": "section_01.md",
                        "section_index": 1,
                        "content": "## 요약\\n\\n..."
                    },
                    ...
                ],
                "total_sections": 3,
                "is_complete": false
            }
        }
    """
    try:
        sections = ReportManager.get_generated_sections(report_id)
        
        # 보고서상태
        report = ReportManager.get_report(report_id)
        is_complete = report is not None and report.status == ReportStatus.COMPLETED
        
        return {
            "success": True,
            "data": {
                "report_id": report_id,
                "sections": sections,
                "total_sections": len(sections),
                "is_complete": is_complete
            }
        }
        
    except Exception as e:
        logger.error(f"섹션목록실패: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })


@report_router.get('/{report_id}/section/{section_index:int}')
async def get_single_section(request: Request, report_id: str, section_index: int):
    """
    섹션
    
    반환:
        {
            "success": true,
            "data": {
                "filename": "section_01.md",
                "content": "## 요약\\n\\n..."
            }
        }
    """
    try:
        section_path = ReportManager._get_section_path(report_id, section_index)
        
        if not os.path.exists(section_path):
            return JSONResponse(status_code=404, content={
                "success": False,
                "error": f"섹션존재하지 않습니다: section_{section_index:02d}.md"
            })
        
        with open(section_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "success": True,
            "data": {
                "filename": f"section_{section_index:02d}.md",
                "section_index": section_index,
                "content": content
            }
        }
        
    except Exception as e:
        logger.error(f"섹션실패: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })


# ============== 보고서상태API ==============

@report_router.get('/check/{simulation_id}')
async def check_report_status(request: Request, simulation_id: str):
    """
    시뮬레이션보고서, 보고서상태
    
    Interview
    
    반환:
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "has_report": true,
                "report_status": "completed",
                "report_id": "report_xxxx",
                "interview_unlocked": true
            }
        }
    """
    try:
        report = ReportManager.get_report_by_simulation(simulation_id)
        
        has_report = report is not None
        report_status = report.status.value if report else None
        report_id = report.report_id if report else None
        
        # 보고서완료interview
        interview_unlocked = has_report and report.status == ReportStatus.COMPLETED
        
        return {
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "has_report": has_report,
                "report_status": report_status,
                "report_id": report_id,
                "interview_unlocked": interview_unlocked
            }
        }
        
    except Exception as e:
        logger.error(f"보고서상태실패: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })


# ============== Agent 로그API ==============

@report_router.get('/{report_id}/agent-log')
async def get_agent_log(request: Request, report_id: str):
    """
     Report Agent 상세로그
    
    보고서 생성진행 중, :
    - 보고서시작, 시작/완료
    - 섹션시작, 도구 호출, LLM, 완료
    - 보고서완료실패
    
    Query파라미터:
        from_line: 시작읽기(선택, 0, )
    
    반환:
        {
            "success": true,
            "data": {
                "logs": [
                    {
                        "timestamp": "2025-12-13T...",
                        "elapsed_seconds": 12.5,
                        "report_id": "report_xxxx",
                        "action": "tool_call",
                        "stage": "generating",
                        "section_title": "요약",
                        "section_index": 1,
                        "details": {
                            "tool_name": "insight_forge",
                            "parameters": {...},
                            ...
                        }
                    },
                    ...
                ],
                "total_lines": 25,
                "from_line": 0,
                "has_more": false
            }
        }
    """
    try:
        from_line = _qp_int(request.query_params, 'from_line', 0)
        
        log_data = ReportManager.get_agent_log(report_id, from_line=from_line)
        
        return {
            "success": True,
            "data": log_data
        }
        
    except Exception as e:
        logger.error(f"Agent로그실패: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })


@report_router.get('/{report_id}/agent-log/stream')
async def stream_agent_log(request: Request, report_id: str):
    """
     Agent 로그()
    
    반환:
        {
            "success": true,
            "data": {
                "logs": [...],
                "count": 25
            }
        }
    """
    try:
        logs = ReportManager.get_agent_log_stream(report_id)
        
        return {
            "success": True,
            "data": {
                "logs": logs,
                "count": len(logs)
            }
        }
        
    except Exception as e:
        logger.error(f"Agent로그실패: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })


# ============== 콘솔로그API ==============

@report_router.get('/{report_id}/console-log')
async def get_console_log(request: Request, report_id: str):
    """
     Report Agent 콘솔로그
    
    보고서 생성진행 중(INFO, WARNING), 
     agent-log API반환 JSON 로그, 
    콘솔로그.
    
    Query파라미터:
        from_line: 시작읽기(선택, 0, )
    
    반환:
        {
            "success": true,
            "data": {
                "logs": [
                    "[19:46:14] INFO: 검색완료:  15건사실",
                    "[19:46:14] INFO: 그래프검색: graph_id=xxx, query=...",
                    ...
                ],
                "total_lines": 100,
                "from_line": 0,
                "has_more": false
            }
        }
    """
    try:
        from_line = _qp_int(request.query_params, 'from_line', 0)
        
        log_data = ReportManager.get_console_log(report_id, from_line=from_line)
        
        return {
            "success": True,
            "data": log_data
        }
        
    except Exception as e:
        logger.error(f"콘솔로그실패: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })


@report_router.get('/{report_id}/console-log/stream')
async def stream_console_log(request: Request, report_id: str):
    """
    콘솔로그()
    
    반환:
        {
            "success": true,
            "data": {
                "logs": [...],
                "count": 100
            }
        }
    """
    try:
        logs = ReportManager.get_console_log_stream(report_id)
        
        return {
            "success": True,
            "data": {
                "logs": logs,
                "count": len(logs)
            }
        }
        
    except Exception as e:
        logger.error(f"콘솔로그실패: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })


# ============== 도구 호출API(디버그)==============

@report_router.post('/tools/search')
async def search_graph_tool(request: Request):
    """
    그래프검색도구API(디버그)
    
    요청(JSON):
        {
            "graph_id": "neofish_xxxx",
            "query": "검색조회",
            "limit": 10
        }
    """
    try:
        data = (await request.json()) or {}
        
        graph_id = data.get('graph_id')
        query = data.get('query')
        limit = data.get('limit', 10)
        
        if not graph_id or not query:
            return JSONResponse(status_code=400, content={
                "success": False,
                "error": "graph_id  query를 입력해 주세요."
            })
        
        from ..services.graph_tools import GraphToolsService
        
        tools = GraphToolsService()
        result = tools.search_graph(
            graph_id=graph_id,
            query=query,
            limit=limit
        )
        
        return {
            "success": True,
            "data": result.to_dict()
        }
        
    except Exception as e:
        logger.error(f"그래프검색실패: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })


@report_router.post('/tools/statistics')
async def get_graph_statistics_tool(request: Request):
    """
    그래프도구API(디버그)
    
    요청(JSON):
        {
            "graph_id": "neofish_xxxx"
        }
    """
    try:
        data = (await request.json()) or {}
        
        graph_id = data.get('graph_id')
        
        if not graph_id:
            return JSONResponse(status_code=400, content={
                "success": False,
                "error": "graph_id를 입력해 주세요."
            })
        
        from ..services.graph_tools import GraphToolsService
        
        tools = GraphToolsService()
        result = tools.get_graph_statistics(graph_id)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"그래프실패: {str(e)}")
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })


# ============== 팟캐스트 API ==============

@report_router.post('/{report_id}/podcast/generate')
async def generate_podcast(request: Request, report_id: str):
    """보고서 내용을 바탕으로 팟캐스트 사운드 생성(비동기)"""
    try:
        from ..services.podcast_generator import PodcastGenerator
        
        report = ReportManager.get_report(report_id)
        if not report or report.status != ReportStatus.COMPLETED:
            return JSONResponse(status_code=404, content={"success": False, "error": "완료된 보고서가 없습니다."})
            
        podcast_dir = os.path.join(Config.UPLOAD_FOLDER, 'podcasts')
        output_path = os.path.join(podcast_dir, f"{report_id}.wav")
        
        if _is_valid_podcast_file(output_path):
            return {
                "success": True, 
                "data": {"status": "completed", "already_exists": True}
            }
            
        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="podcast_generate",
            metadata={"report_id": report_id}
        )
        
        def run_generate():
            try:
                task_manager.update_task(task_id, status=TaskStatus.PROCESSING, progress=0, message="팟캐스트 준비 중...")
                
                def progress_callback(progress, message):
                    task_manager.update_task(task_id, progress=progress, message=message)
                
                generator = PodcastGenerator()
                generator.create_podcast(report.markdown_content, output_path, progress_callback)
                
                task_manager.complete_task(task_id, result={"output_path": output_path, "status": "completed"})
            except Exception as e:
                task_manager.fail_task(task_id, str(e))
                logger.error(f"팟캐스트 생성 중 에러 발생: {e}")
                
        thread = threading.Thread(target=run_generate, daemon=True)
        thread.start()
        
        return {
            "success": True,
            "data": {
                "report_id": report_id,
                "task_id": task_id,
                "status": "generating"
            }
        }
    except Exception as e:
        logger.error(f"팟캐스트 생성 시작 실패: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e), "traceback": traceback.format_exc()})

@report_router.get('/podcast/status/{task_id}')
async def get_podcast_task_status(request: Request, task_id: str):
    """팟캐스트 생성 진행 상태 조회"""
    try:
        task_manager = TaskManager()
        task = task_manager.get_task(task_id)
        if not task:
            return JSONResponse(status_code=404, content={"success": False, "error": "Task not found"})
        return {"success": True, "data": task.to_dict()}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@report_router.get('/{report_id}/podcast')
async def get_podcast_info(request: Request, report_id: str):
    """팟캐스트 존재 여부 확인"""
    try:
        podcast_dir = os.path.join(Config.UPLOAD_FOLDER, 'podcasts')
        output_path = os.path.join(podcast_dir, f"{report_id}.wav")
        
        exists = _is_valid_podcast_file(output_path)
        return {
            "success": True,
            "data": {
                "report_id": report_id,
                "has_podcast": exists,
                "audio_url": f"/api/report/{report_id}/podcast/download" if exists else None
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@report_router.get('/{report_id}/podcast/download')
async def download_podcast(request: Request, report_id: str):
    """팟캐스트 파일 다운로드 또는 스트리밍"""
    try:
        podcast_dir = os.path.join(Config.UPLOAD_FOLDER, 'podcasts')
        output_path = os.path.join(podcast_dir, f"{report_id}.wav")
        
        if not _is_valid_podcast_file(output_path):
            return JSONResponse(status_code=404, content={"success": False, "error": "팟캐스트 파일이 존재하지 않습니다."})
            
        return FileResponse(output_path, media_type="audio/wav")
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})
