import logging
from typing import List, Dict, Any

from . import neo4j_store
from ..utils.llm_client import LLMClient

logger = logging.getLogger("neofish.entity_resolution")

class EntityResolutionService:
    def __init__(self, llm: LLMClient = None):
        self.llm = llm or LLMClient()

    def resolve_entities(self, graph_id: str):
        """
        벡터 유사도를 기반으로 후보를 선정하고 LLM으로 최종 확인하여 엔터티를 병합한다.
        """
        logger.info(f"Starting Vector-based Entity Resolution for graph {graph_id}...")
        
        # 1. 임베딩이 없는 경우를 위해 먼저 갱신 호출 (실제로는 builder에서 호출되지만 안전장치)
        from .neo4j_store import refresh_all_node_embeddings
        refresh_all_node_embeddings(graph_id)

        with neo4j_store.session_scope() as s:
            # 2. 모든 노드와 그 임베딩 가져오기
            res = s.run(
                """
                MATCH (n:GraphEntity {graph_id: $gid})
                WHERE n.embedding IS NOT NULL
                RETURN n.uuid as uuid, n.name as name, n.embedding as embedding, n.labels_json as labels
                """,
                gid=graph_id
            )
            all_nodes = [dict(record) for record in res]
        
        if len(all_nodes) < 2:
            return

        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity

        embeddings = np.array([n["embedding"] for n in all_nodes])
        # 코사인 유사도 행렬 계산
        similarity_matrix = cosine_similarity(embeddings)
        
        threshold = 0.92 # 매우 유사한 것들만 후보로 선정
        candidate_groups = []
        visited = set()

        for i in range(len(all_nodes)):
            if i in visited:
                continue
            
            group = [all_nodes[i]]
            visited.add(i)
            
            for j in range(i + 1, len(all_nodes)):
                if j not in visited and similarity_matrix[i][j] > threshold:
                    # 라벨이 다르면(예: Person vs Organization) 병합하지 않음
                    # (labels_json은 "[...]" 형태)
                    if all_nodes[i]["labels"] == all_nodes[j]["labels"]:
                        group.append(all_nodes[j])
                        visited.add(j)
            
            if len(group) > 1:
                candidate_groups.append(group)

        total_merged = 0
        for group in candidate_groups:
            names = [n["name"] for n in group]
            # LLM에게 최종 확인 요청
            duplicates = self._find_duplicates_with_llm(names)
            
            if duplicates:
                for dup_list in duplicates:
                    if len(dup_list) > 1:
                        target_name = dup_list[0]
                        alias_names = dup_list[1:]
                        # 실제 병합 수행
                        try:
                            neo4j_store.merge_nodes(graph_id, target_name, alias_names, "Entity")
                            total_merged += len(alias_names)
                        except Exception as e:
                            logger.error(f"Merge failed for {target_name}: {e}")

        logger.info(f"Entity Resolution complete. Merged {total_merged} nodes via vector-hybrid approach.")

    def _find_duplicates_with_llm(self, names: List[str]) -> List[List[str]]:
        system = "You are an entity resolution assistant. Group identical entities together."
        user = f"""
Given the following list of entity names, identify which ones refer to the exact same real-world concept or entity.
Return ONLY valid JSON with a list of lists. Each inner list should contain names that are synonyms.
Ignore casing or minor punctuation differences if they clearly mean the same thing. Do not group related but distinct entities.

Names: {names}

Format:
[
  ["AI", "Artificial Intelligence", "A.I."],
  ["OpenAI", "Open AI"]
]
"""
        try:
            result = self.llm.chat_json([
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ], temperature=0.1)
            
            if isinstance(result, list):
                return result
            return []
        except Exception as e:
            logger.warning(f"Entity resolution LLM call failed: {e}")
            return []
