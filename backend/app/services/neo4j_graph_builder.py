"""
Neo4j 기반 그래프 구축(LLM 청크 추출).
"""

from __future__ import annotations

import threading
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..config import Config
from ..models.project import ProjectManager, ProjectStatus
from ..models.task import TaskManager, TaskStatus
from ..utils.logger import get_logger
from .graph_info import GraphInfo
from .neo4j_chunk_extractor import extract_entities_from_chunk
from .neo4j_store import (
    create_graph_meta,
    delete_graph_data,
    fetch_edges,
    fetch_nodes,
    upsert_entity,
    upsert_relationship,
    upsert_entities_batch,
    upsert_relationships_batch,
)
from .text_processor import TextProcessor

logger = get_logger("neofish.neo4j_graph_builder")


class Neo4jGraphBuilderService:
    """로컬 Neo4j에 그래프를 구축한다."""

    def __init__(self, task_manager: Optional[TaskManager] = None):
        self.task_manager = task_manager or TaskManager()

    def build_graph_async(
        self,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str = "Neofish Graph",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        batch_size: int = 3,
    ) -> str:
        task_id = self.task_manager.create_task(
            task_type="graph_build_neo4j",
            metadata={"graph_name": graph_name, "text_length": len(text)},
        )
        thread = threading.Thread(
            target=self._build_graph_worker,
            args=(task_id, text, ontology, graph_name, chunk_size, chunk_overlap, batch_size),
            daemon=True,
        )
        thread.start()
        return task_id

    def _build_graph_worker(
        self,
        task_id: str,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str,
        chunk_size: int,
        chunk_overlap: int,
        batch_size: int,
        project_id: Optional[str] = None,
    ):
        import json

        try:
            self.task_manager.update_task(
                task_id, status=TaskStatus.PROCESSING, progress=5, message="Neo4j 그래프 구축 시작..."
            )
            graph_id = f"neofish_{uuid.uuid4().hex[:16]}"
            create_graph_meta(graph_id, graph_name)
            self.task_manager.update_task(
                task_id, progress=10, message=f"그래프 ID 생성: {graph_id}"
            )

            if project_id:
                proj = ProjectManager.get_project(project_id)
                if proj:
                    proj.graph_id = graph_id
                    ProjectManager.save_project(proj)

            # 온톨로지 메타(참고용) — GraphMeta에 저장
            try:
                from .neo4j_store import session_scope

                with session_scope() as s:
                    s.run(
                        """
                        MATCH (g:GraphMeta {graph_id: $gid})
                        SET g.ontology_json = $oj
                        """,
                        gid=graph_id,
                        oj=json.dumps(ontology, ensure_ascii=False)[:500000],
                    )
            except Exception as e:
                logger.warning("온톨로지 JSON 저장 실패(무시): %s", e)

            chunks = TextProcessor.split_text(text, chunk_size, chunk_overlap)
            total = len(chunks)
            self.task_manager.update_task(
                task_id, progress=15, message=f"텍스트 {total}개 청크로 분할"
            )

            key_to_uuid: Dict[Tuple[str, str], str] = {}
            processed = 0
            for i, chunk in enumerate(chunks):
                nodes, rels = extract_entities_from_chunk(chunk, ontology, key_to_uuid)
                upsert_entities_batch(graph_id, nodes)
                upsert_relationships_batch(graph_id, rels)
                processed += 1
                prog = 15 + int(75 * processed / max(total, 1))
                self.task_manager.update_task(
                    task_id,
                    progress=min(prog, 95),
                    message=f"Neo4j 추출 {processed}/{total} 청크",
                )

            # --- 엔터티 병합 (Entity Resolution) ---
            self.task_manager.update_task(task_id, progress=95, message="엔터티 해상도(동의어 병합) 처리 중...")
            try:
                from .entity_resolution_service import EntityResolutionService
                resolution_service = EntityResolutionService()
                resolution_service.resolve_entities(graph_id)
            except Exception as e:
                logger.warning(f"Entity resolution failed: {e}")

            # --- 커뮤니티 요약 (Hierarchical GraphRAG) ---
            self.task_manager.update_task(task_id, progress=96, message="커뮤니티 식별 및 요약 생성 중...")
            try:
                from .community_summarizer import CommunitySummarizer
                summarizer = CommunitySummarizer()
                summarizer.build_and_summarize_communities(graph_id)
            except Exception as e:
                logger.warning(f"Community summarization failed: {e}")

            # --- 임베딩 갱신 (Vector Search 준비) ---
            self.task_manager.update_task(task_id, progress=97, message="벡터 검색용 노드 임베딩 생성 중...")
            try:
                from .neo4j_store import refresh_all_node_embeddings
                refresh_all_node_embeddings(graph_id)
            except Exception as e:
                logger.warning(f"Embedding refresh failed: {e}")

            self.task_manager.update_task(task_id, progress=98, message="마무리 중...")

            graph_info = self._get_graph_info(graph_id)
            if project_id:
                proj = ProjectManager.get_project(project_id)
                if proj:
                    proj.status = ProjectStatus.GRAPH_COMPLETED
                    proj.error = None
                    ProjectManager.save_project(proj)
            self.task_manager.complete_task(
                task_id,
                {
                    "project_id": project_id,
                    "graph_id": graph_id,
                    "node_count": graph_info.node_count,
                    "edge_count": graph_info.edge_count,
                    "chunk_count": total,
                    "graph_info": graph_info.to_dict(),
                },
            )
        except Exception as e:
            import traceback

            if project_id:
                proj = ProjectManager.get_project(project_id)
                if proj:
                    proj.status = ProjectStatus.FAILED
                    proj.error = str(e)
                    ProjectManager.save_project(proj)
            self.task_manager.fail_task(task_id, f"{e}\n{traceback.format_exc()}")

    def _get_graph_info(self, graph_id: str) -> GraphInfo:
        nodes = fetch_nodes(graph_id)
        edges = fetch_edges(graph_id)
        entity_types = set()
        for n in nodes:
            for lab in n.get("labels") or []:
                if lab not in ("Entity", "Node"):
                    entity_types.add(lab)
        return GraphInfo(
            graph_id=graph_id,
            node_count=len(nodes),
            edge_count=len(edges),
            entity_types=list(entity_types),
        )

    def get_graph_info(self, graph_id: str) -> Dict[str, Any]:
        """API용 그래프 요약(노드/엣지 수·엔터티 타입)."""
        return self._get_graph_info(graph_id).to_dict()

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        nodes = fetch_nodes(graph_id)
        edges = fetch_edges(graph_id)
        nodes_data = []
        for n in nodes:
            nodes_data.append(
                {
                    "uuid": n["uuid"],
                    "name": n["name"],
                    "labels": n["labels"],
                    "summary": n["summary"],
                    "attributes": n["attributes"],
                    "created_at": n.get("created_at"),
                }
            )
        edges_data = []
        for e in edges:
            edges_data.append(
                {
                    "uuid": e["uuid"],
                    "name": e["name"],
                    "fact": e["fact"],
                    "fact_type": e.get("fact_type") or e.get("name") or "",
                    "source_node_uuid": e["source_node_uuid"],
                    "target_node_uuid": e["target_node_uuid"],
                    "source_node_name": e.get("source_node_name") or "",
                    "target_node_name": e.get("target_node_name") or "",
                    "attributes": e.get("attributes") or {},
                    "created_at": e.get("created_at"),
                    "valid_at": e.get("valid_at"),
                    "invalid_at": e.get("invalid_at"),
                    "expired_at": e.get("expired_at"),
                    "episodes": e.get("episodes") or [],
                }
            )
        return {
            "graph_id": graph_id,
            "nodes": nodes_data,
            "edges": edges_data,
            "node_count": len(nodes_data),
            "edge_count": len(edges_data),
        }

    def delete_graph(self, graph_id: str):
        delete_graph_data(graph_id)
