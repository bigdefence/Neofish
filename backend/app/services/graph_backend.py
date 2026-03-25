"""Neo4j 그래프 빌더·엔터티 리더 팩토리."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .neo4j_graph_builder import Neo4jGraphBuilderService
    from .neo4j_entity_reader import Neo4jEntityReader


def get_graph_builder():
    from .neo4j_graph_builder import Neo4jGraphBuilderService

    return Neo4jGraphBuilderService()


def get_entity_reader():
    """엔터티 조회용 Neo4j 리더."""
    from .neo4j_entity_reader import Neo4jEntityReader

    return Neo4jEntityReader()
