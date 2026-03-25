"""그래프 요약 정보(노드·엣지 수, 엔터티 타입)."""

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class GraphInfo:
    """그래프 정보."""

    graph_id: str
    node_count: int
    edge_count: int
    entity_types: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "entity_types": self.entity_types,
        }
