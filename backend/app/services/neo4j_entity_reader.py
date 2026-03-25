"""
Neo4j 그래프에서 엔터티를 읽어 필터링한다.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from ..utils.logger import get_logger
from .entity_types import EntityNode, FilteredEntities
from .neo4j_store import (
    fetch_edges,
    fetch_edges_for_node,
    fetch_node,
    fetch_nodes,
    fetch_nodes_by_uuids,
)

logger = get_logger("neofish.neo4j_entity_reader")


class Neo4jEntityReader:
    """Neo4j 백엔드 엔터티 리더."""

    def get_all_nodes(self, graph_id: str) -> List[Dict[str, Any]]:
        logger.info("Neo4j 그래프 %s 노드 조회...", graph_id)
        return fetch_nodes(graph_id)

    def get_all_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        logger.info("Neo4j 그래프 %s 엣지 조회...", graph_id)
        return fetch_edges(graph_id)

    def get_node_edges(self, node_uuid: str, graph_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not graph_id:
            return []
        return fetch_edges_for_node(graph_id, node_uuid)

    def filter_defined_entities(
        self,
        graph_id: str,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True,
    ) -> FilteredEntities:
        all_nodes = self.get_all_nodes(graph_id)
        total_count = len(all_nodes)
        all_edges = self.get_all_edges(graph_id) if enrich_with_edges else []
        node_map = {n["uuid"]: n for n in all_nodes}

        edges_by_source = {}
        edges_by_target = {}
        if enrich_with_edges:
            for edge in all_edges:
                su = edge["source_node_uuid"]
                tu = edge["target_node_uuid"]
                edges_by_source.setdefault(su, []).append(edge)
                edges_by_target.setdefault(tu, []).append(edge)

        filtered_entities: List[EntityNode] = []
        entity_types_found: Set[str] = set()

        for node in all_nodes:
            labels = node.get("labels", [])
            custom_labels = [l for l in labels if l not in ["Entity", "Node"]]
            if not custom_labels:
                continue
            if defined_entity_types:
                matching = [l for l in custom_labels if l in defined_entity_types]
                if not matching:
                    continue
                entity_type = matching[0]
            else:
                entity_type = custom_labels[0]
            entity_types_found.add(entity_type)

            entity = EntityNode(
                uuid=node["uuid"],
                name=node["name"],
                labels=labels,
                summary=node.get("summary", ""),
                attributes=node.get("attributes") or {},
            )

            if enrich_with_edges:
                related_edges = []
                related_node_uuids = set()
                
                for edge in edges_by_source.get(node["uuid"], []):
                    related_edges.append(
                        {
                            "direction": "outgoing",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "target_node_uuid": edge["target_node_uuid"],
                        }
                    )
                    related_node_uuids.add(edge["target_node_uuid"])
                    
                for edge in edges_by_target.get(node["uuid"], []):
                    related_edges.append(
                        {
                            "direction": "incoming",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "source_node_uuid": edge["source_node_uuid"],
                        }
                    )
                    related_node_uuids.add(edge["source_node_uuid"])
                    
                entity.related_edges = related_edges
                related_nodes = []
                for ru in related_node_uuids:
                    if ru in node_map:
                        rn = node_map[ru]
                        related_nodes.append(
                            {
                                "uuid": rn["uuid"],
                                "name": rn["name"],
                                "labels": rn["labels"],
                                "summary": rn.get("summary", ""),
                            }
                        )
                entity.related_nodes = related_nodes

            filtered_entities.append(entity)

        logger.info(
            "Neo4j 필터링: 전체 %s, 선택 %s, 타입 %s",
            total_count,
            len(filtered_entities),
            entity_types_found,
        )
        return FilteredEntities(
            entities=filtered_entities,
            entity_types=entity_types_found,
            total_count=total_count,
            filtered_count=len(filtered_entities),
        )

    def get_entity_with_context(self, graph_id: str, entity_uuid: str) -> Optional[EntityNode]:
        node = fetch_node(graph_id, entity_uuid)
        if not node:
            return None
        edges = fetch_edges_for_node(graph_id, entity_uuid)
        related_edges = []
        related_node_uuids = set()
        for edge in edges:
            if edge["source_node_uuid"] == entity_uuid:
                related_edges.append(
                    {
                        "direction": "outgoing",
                        "edge_name": edge["name"],
                        "fact": edge["fact"],
                        "target_node_uuid": edge["target_node_uuid"],
                    }
                )
                related_node_uuids.add(edge["target_node_uuid"])
            else:
                related_edges.append(
                    {
                        "direction": "incoming",
                        "edge_name": edge["name"],
                        "fact": edge["fact"],
                        "source_node_uuid": edge["source_node_uuid"],
                    }
                )
                related_node_uuids.add(edge["source_node_uuid"])
        related_list = fetch_nodes_by_uuids(graph_id, list(related_node_uuids))
        node_map = {n["uuid"]: n for n in related_list}
        related_nodes = []
        for ru in related_node_uuids:
            if ru in node_map:
                rn = node_map[ru]
                related_nodes.append(
                    {
                        "uuid": rn["uuid"],
                        "name": rn["name"],
                        "labels": rn["labels"],
                        "summary": rn.get("summary", ""),
                    }
                )
        return EntityNode(
            uuid=node["uuid"],
            name=node["name"],
            labels=node["labels"],
            summary=node.get("summary", ""),
            attributes=node.get("attributes") or {},
            related_edges=related_edges,
            related_nodes=related_nodes,
        )

    def get_entities_by_type(
        self,
        graph_id: str,
        entity_type: str,
        enrich_with_edges: bool = True,
    ) -> List[EntityNode]:
        r = self.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=[entity_type],
            enrich_with_edges=enrich_with_edges,
        )
        return r.entities
