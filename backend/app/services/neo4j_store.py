"""
Neo4j graph store for Neofish.

The graph builder writes semantic entities/relationships, while simulation-time
memory updates write episodic logs plus consolidated long-term memories.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from neo4j import GraphDatabase

from ..config import Config

logger = logging.getLogger("neofish.neo4j_store")

_driver = None


def _normalize_neo4j_uri(uri: str) -> str:
    """
    `neo4j://` 스킴은 라우팅(클러스터)용이다. 단일 Neo4j 인스턴스에 연결하면
    라우팅 테이블을 가져오지 못해
    ``ServiceUnavailable: Unable to retrieve routing information`` 이 발생할 수 있다.

    로컬/단일 서버에서는 `bolt://` 직접 연결을 쓴다.
    Neo4j Aura 등은 보통 `neo4j+s://` 를 쓰므로 여기서는 건드리지 않는다.

    클러스터에 `neo4j://` 가 꼭 필요하면 환경 변수 ``NEO4J_FORCE_BOLT=false`` 로 비활성화한다.
    """
    u = (uri or "").strip()
    if not u.startswith("neo4j://"):
        return u
    force_bolt = os.environ.get("NEO4J_FORCE_BOLT", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    if not force_bolt:
        return u
    bolt_uri = "bolt://" + u[len("neo4j://") :]
    logger.info(
        "NEO4J_URI가 neo4j:// 입니다. 단일 인스턴스 연결을 위해 bolt:// 로 사용합니다: %s",
        bolt_uri,
    )
    return bolt_uri


def get_driver():
    global _driver
    if _driver is None:
        if not Config.NEO4J_URI:
            raise ValueError("NEO4J_URI가 설정되지 않았습니다.")
        effective_uri = _normalize_neo4j_uri(Config.NEO4J_URI)
        auth = (Config.NEO4J_USER, Config.NEO4J_PASSWORD)
        pool = max(1, int(getattr(Config, "NEO4J_MAX_CONNECTION_POOL_SIZE", 50)))
        acq = float(getattr(Config, "NEO4J_CONNECTION_ACQUISITION_TIMEOUT", 60.0))
        _driver = GraphDatabase.driver(
            effective_uri,
            auth=auth,
            max_connection_pool_size=pool,
            connection_acquisition_timeout=acq,
        )
    return _driver


def close_driver():
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


@contextmanager
def session_scope():
    drv = get_driver()
    with drv.session() as session:
        yield session


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _normalize_text(text: str, limit: int = 500) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _clamp_score(value: Any, default: float = 0.0) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = default
    return max(0.0, min(100.0, round(score, 2)))


def ensure_constraints():
    queries = [
        """
        CREATE CONSTRAINT graph_entity_uuid IF NOT EXISTS
        FOR (n:GraphEntity) REQUIRE n.uuid IS UNIQUE
        """,
        """
        CREATE CONSTRAINT sim_episode_uuid IF NOT EXISTS
        FOR (e:SimEpisode) REQUIRE e.uuid IS UNIQUE
        """,
        """
        CREATE CONSTRAINT sim_memory_key IF NOT EXISTS
        FOR (m:SimMemory) REQUIRE m.graph_scoped_key IS UNIQUE
        """,
        """
        CREATE INDEX sim_episode_graph_id IF NOT EXISTS
        FOR (e:SimEpisode) ON (e.graph_id)
        """,
        """
        CREATE INDEX sim_memory_graph_id IF NOT EXISTS
        FOR (m:SimMemory) ON (m.graph_id)
        """,
        """
        CREATE INDEX sim_memory_graph_platform IF NOT EXISTS
        FOR (m:SimMemory) ON (m.graph_id, m.platform)
        """,
        # Vector Index for Semantic Search (Dimension 768 for Gemini v4/v2)
        """
        CREATE VECTOR INDEX graph_entity_embedding IF NOT EXISTS
        FOR (n:GraphEntity) ON (n.embedding)
        OPTIONS {
          indexConfig: {
            `vector.dimensions`: 768,
            `vector.similarity_function`: 'cosine'
          }
        }
        """,
        # Full-Text Index for Hybrid Search
        """
        CREATE FULLTEXT INDEX graph_entity_fulltext IF NOT EXISTS
        FOR (n:GraphEntity) ON EACH [n.name, n.summary]
        """,
        """
        CREATE FULLTEXT INDEX graph_rel_fulltext IF NOT EXISTS
        FOR ()-[r:GRAPH_REL]-() ON EACH [r.name, r.fact]
        """,
    ]
    try:
        with session_scope() as s:
            for cypher in queries:
                s.run(cypher)
    except Exception as exc:
        logger.warning("Neo4j constraint/index creation skipped: %s", exc)


def create_graph_meta(graph_id: str, name: str) -> None:
    ensure_constraints()
    with session_scope() as s:
        s.run(
            """
            MERGE (g:GraphMeta {graph_id: $gid})
            SET g.name = $name
            """,
            gid=graph_id,
            name=name,
        )


def delete_graph_data(graph_id: str) -> None:
    with session_scope() as s:
        s.run(
            """
            MATCH (n)
            WHERE (n:GraphMeta OR n:GraphEntity OR n:SimEpisode OR n:SimMemory)
              AND n.graph_id = $gid
            DETACH DELETE n
            """,
            gid=graph_id,
        )


def upsert_entity(
    graph_id: str,
    uuid: str,
    name: str,
    labels: List[str],
    summary: str,
    attributes: Optional[Dict[str, Any]] = None,
) -> None:
    labels_json = json.dumps(labels or [], ensure_ascii=False)
    attr_json = json.dumps(attributes or {}, ensure_ascii=False)
    with session_scope() as s:
        s.run(
            """
            MERGE (n:GraphEntity {uuid: $uuid})
            SET n.graph_id = $gid,
                n.name = $name,
                n.labels_json = $labels_json,
                n.summary = coalesce($summary, ''),
                n.attributes_json = $attr_json
            """,
            uuid=uuid,
            gid=graph_id,
            name=name or "",
            labels_json=labels_json,
            summary=summary or "",
            attr_json=attr_json,
        )


def upsert_relationship(
    graph_id: str,
    rel_uuid: str,
    source_uuid: str,
    target_uuid: str,
    name: str,
    fact: str,
    fact_type: str,
) -> None:
    with session_scope() as s:
        s.run(
            """
            MATCH (a:GraphEntity {uuid: $su}), (b:GraphEntity {uuid: $tu})
            WHERE a.graph_id = $gid AND b.graph_id = $gid
            MERGE (a)-[r:GRAPH_REL {uuid: $ruuid}]->(b)
            SET r.graph_id = $gid,
                r.name = $name,
                r.fact = coalesce($fact, ''),
                r.fact_type = coalesce($ftype, '')
            """,
            su=source_uuid,
            tu=target_uuid,
            gid=graph_id,
            ruuid=rel_uuid,
            name=name or "",
            fact=fact or "",
            ftype=fact_type or name or "",
        )


def upsert_entities_batch(graph_id: str, nodes_list: List[Dict[str, Any]]) -> None:
    if not nodes_list:
        return
    batch = []
    for node in nodes_list:
        batch.append(
            {
                "uuid": node["uuid"],
                "name": node.get("name") or "",
                "labels_json": json.dumps(node.get("labels") or [], ensure_ascii=False),
                "summary": node.get("summary") or "",
                "attr_json": json.dumps(node.get("attributes") or {}, ensure_ascii=False),
            }
        )
    with session_scope() as s:
        s.run(
            """
            UNWIND $batch AS b
            MERGE (n:GraphEntity {uuid: b.uuid})
            SET n.graph_id = $gid,
                n.name = b.name,
                n.labels_json = b.labels_json,
                n.summary = coalesce(b.summary, ''),
                n.attributes_json = b.attr_json
            """,
            gid=graph_id,
            batch=batch,
        )


def upsert_relationships_batch(graph_id: str, rels_list: List[Dict[str, Any]]) -> None:
    if not rels_list:
        return
    batch = []
    for rel in rels_list:
        name = rel.get("name") or ""
        batch.append(
            {
                "su": rel["source_uuid"],
                "tu": rel["target_uuid"],
                "ruuid": rel["uuid"],
                "name": name,
                "fact": rel.get("fact") or "",
                "ftype": rel.get("fact_type") or name or "",
            }
        )
    with session_scope() as s:
        s.run(
            """
            UNWIND $batch AS b
            MATCH (a:GraphEntity {uuid: b.su}), (c:GraphEntity {uuid: b.tu})
            WHERE a.graph_id = $gid AND c.graph_id = $gid
            MERGE (a)-[r:GRAPH_REL {uuid: b.ruuid}]->(c)
            SET r.graph_id = $gid,
                r.name = b.name,
                r.fact = coalesce(b.fact, ''),
                r.fact_type = coalesce(b.ftype, '')
            """,
            gid=graph_id,
            batch=batch,
        )


def _row_to_graph_entity(row) -> Dict[str, Any]:
    try:
        labels = json.loads(row["labels_json"] or "[]")
    except json.JSONDecodeError:
        labels = []
    try:
        attributes = json.loads(row["attr_json"] or "{}")
    except json.JSONDecodeError:
        attributes = {}
    return {
        "uuid": row["uuid"] or "",
        "name": row["name"] or "",
        "labels": labels,
        "summary": row["summary"] or "",
        "attributes": attributes,
        "created_at": None,
    }


def fetch_nodes(graph_id: str) -> List[Dict[str, Any]]:
    with session_scope() as s:
        rows = s.run(
            """
            MATCH (n:GraphEntity)
            WHERE n.graph_id = $gid
            RETURN n.uuid AS uuid,
                   n.name AS name,
                   n.labels_json AS labels_json,
                   n.summary AS summary,
                   n.attributes_json AS attr_json
            """,
            gid=graph_id,
        )
        return [_row_to_graph_entity(row) for row in rows]


def _edge_row_to_dict(row) -> Dict[str, Any]:
    source_uuid, target_uuid = row["su"], row["tu"]
    return {
        "uuid": row["uuid"] or "",
        "name": row["name"] or "",
        "fact": row["fact"] or "",
        "fact_type": row["fact_type"] or row["name"] or "",
        "source_node_uuid": source_uuid,
        "target_node_uuid": target_uuid,
        "source_node_name": row.get("sn") or "",
        "target_node_name": row.get("tn") or "",
        "attributes": {},
        "created_at": None,
        "valid_at": None,
        "invalid_at": None,
        "expired_at": None,
        "episodes": [],
    }


def fetch_edges(graph_id: str) -> List[Dict[str, Any]]:
    """엣지를 한 번의 쿼리로 조회한다(노드 전량 스캔 없음)."""
    with session_scope() as s:
        rows = s.run(
            """
            MATCH (a:GraphEntity)-[r:GRAPH_REL]->(b:GraphEntity)
            WHERE r.graph_id = $gid AND a.graph_id = $gid AND b.graph_id = $gid
            RETURN r.uuid AS uuid,
                   r.name AS name,
                   r.fact AS fact,
                   r.fact_type AS fact_type,
                   a.uuid AS su,
                   b.uuid AS tu,
                   a.name AS sn,
                   b.name AS tn
            """,
            gid=graph_id,
        )
        return [_edge_row_to_dict(row) for row in rows]


def fetch_edges_for_node(graph_id: str, node_uuid: str) -> List[Dict[str, Any]]:
    """특정 노드에 연결된 엣지만 조회한다(전체 그래프 엣지 로드 없음)."""
    with session_scope() as s:
        rows = s.run(
            """
            MATCH (a:GraphEntity)-[r:GRAPH_REL]->(b:GraphEntity)
            WHERE r.graph_id = $gid AND a.graph_id = $gid AND b.graph_id = $gid
              AND (a.uuid = $nu OR b.uuid = $nu)
            RETURN r.uuid AS uuid,
                   r.name AS name,
                   r.fact AS fact,
                   r.fact_type AS fact_type,
                   a.uuid AS su,
                   b.uuid AS tu,
                   a.name AS sn,
                   b.name AS tn
            """,
            gid=graph_id,
            nu=node_uuid,
        )
        return [_edge_row_to_dict(row) for row in rows]


def fetch_nodes_by_uuids(graph_id: str, uuids: List[str]) -> List[Dict[str, Any]]:
    """지정 UUID 목록만 노드 조회한다."""
    if not uuids:
        return []
    # Neo4j IN 리스트는 최대 길이 제한(매우 큰 배치는 분할)
    out: List[Dict[str, Any]] = []
    chunk = 500
    with session_scope() as s:
        for i in range(0, len(uuids), chunk):
            part = uuids[i : i + chunk]
            rows = s.run(
                """
                MATCH (n:GraphEntity)
                WHERE n.graph_id = $gid AND n.uuid IN $uuids
                RETURN n.uuid AS uuid,
                       n.name AS name,
                       n.labels_json AS labels_json,
                       n.summary AS summary,
                       n.attributes_json AS attr_json
                """,
                gid=graph_id,
                uuids=part,
            )
            out.extend(_row_to_graph_entity(row) for row in rows)
    return out


def _memory_row_to_dict(row) -> Dict[str, Any]:
    return {
        "memory_key": row["memory_key"] or "",
        "platform": row["platform"] or "",
        "text": row["text"] or "",
        "summary": row["summary"] or "",
        "agent_name": row["agent_name"] or "",
        "action_type": row["action_type"] or "",
        "occurrence_count": int(row["occurrence_count"] or 0),
        "importance_score": float(row["importance_score"] or 0.0),
        "reinforcement_score": float(row["reinforcement_score"] or 0.0),
        "average_importance": float(row["average_importance"] or 0.0),
        "effective_score": float(row["effective_score"] or 0.0),
        "retention_state": row["retention_state"] or "",
        "first_seen_at": row["first_seen_at"] or "",
        "last_seen_at": row["last_seen_at"] or "",
        "first_round": int(row["first_round"] or 0),
        "last_round": int(row["last_round"] or 0),
    }


def fetch_memories(graph_id: str) -> List[Dict[str, Any]]:
    with session_scope() as s:
        rows = s.run(
            """
            MATCH (m:SimMemory)
            WHERE m.graph_id = $gid
            RETURN m.memory_key AS memory_key,
                   m.platform AS platform,
                   m.text AS text,
                   m.summary AS summary,
                   m.agent_name AS agent_name,
                   m.action_type AS action_type,
                   m.occurrence_count AS occurrence_count,
                   m.importance_score AS importance_score,
                   m.reinforcement_score AS reinforcement_score,
                   m.average_importance AS average_importance,
                   m.effective_score AS effective_score,
                   m.retention_state AS retention_state,
                   m.first_seen_at AS first_seen_at,
                   m.last_seen_at AS last_seen_at,
                   m.first_round AS first_round,
                   m.last_round AS last_round
            ORDER BY coalesce(m.effective_score, 0) DESC,
                     coalesce(m.last_seen_at, m.first_seen_at, '') DESC
            """,
            gid=graph_id,
        )
        return [_memory_row_to_dict(row) for row in rows]


def _fetch_memories_for_search(
    graph_id: str,
    query_lower: str,
    keywords: List[str],
) -> List[Dict[str, Any]]:
    """
    검색용 SimMemory 후보만 로드한다(전량 로드 대신 DB에서 토큰 매칭 + 상한).

    query_lower / keywords가 비어 있으면 빈 리스트(기존 search_simple은 이 경우 기억 점수 0).
    """
    tokens: List[str] = []
    for kw in keywords:
        k = (kw or "").strip().lower()
        if k and k not in tokens:
            tokens.append(k[:100])
    q = (query_lower or "").strip().lower()
    if q and q not in tokens:
        tokens.append(q[:200])
    tokens = tokens[:20]
    if not tokens:
        return []

    max_scan = max(50, min(int(getattr(Config, "NEO4J_SEARCH_MEMORY_MAX_SCAN", 400)), 2000))
    with session_scope() as s:
        rows = s.run(
            """
            MATCH (m:SimMemory)
            WHERE m.graph_id = $gid
              AND any(t IN $tokens WHERE
                  toLower(coalesce(m.text, '')) CONTAINS t
                  OR toLower(coalesce(m.summary, '')) CONTAINS t
                  OR toLower(coalesce(m.agent_name, '')) CONTAINS t
              )
            RETURN m.memory_key AS memory_key,
                   m.platform AS platform,
                   m.text AS text,
                   m.summary AS summary,
                   m.agent_name AS agent_name,
                   m.action_type AS action_type,
                   m.occurrence_count AS occurrence_count,
                   m.importance_score AS importance_score,
                   m.reinforcement_score AS reinforcement_score,
                   m.average_importance AS average_importance,
                   m.effective_score AS effective_score,
                   m.retention_state AS retention_state,
                   m.first_seen_at AS first_seen_at,
                   m.last_seen_at AS last_seen_at,
                   m.first_round AS first_round,
                   m.last_round AS last_round
            ORDER BY coalesce(m.effective_score, 0) DESC,
                     coalesce(m.last_seen_at, m.first_seen_at, '') DESC
            LIMIT $limit
            """,
            gid=graph_id,
            tokens=tokens,
            limit=max_scan,
        )
        return [_memory_row_to_dict(row) for row in rows]


def count_memories(graph_id: str) -> int:
    with session_scope() as s:
        row = s.run(
            """
            MATCH (m:SimMemory)
            WHERE m.graph_id = $gid
            RETURN count(m) AS count
            """,
            gid=graph_id,
        ).single()
    return int(row["count"] or 0) if row else 0


def fetch_node(graph_id: str, uuid: str) -> Optional[Dict[str, Any]]:
    """단일 GraphEntity 조회(전체 그래프 스캔 없음)."""
    with session_scope() as s:
        row = s.run(
            """
            MATCH (n:GraphEntity)
            WHERE n.graph_id = $gid AND n.uuid = $uuid
            RETURN n.uuid AS uuid,
                   n.name AS name,
                   n.labels_json AS labels_json,
                   n.summary AS summary,
                   n.attributes_json AS attr_json
            """,
            gid=graph_id,
            uuid=uuid,
        ).single()
    if not row:
        return None
    return _row_to_graph_entity(row)


def _prepare_memory_batch(
    graph_id: str,
    platform: str,
    memory_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    aggregated: Dict[str, Dict[str, Any]] = {}
    normalized_platform = (platform or "").strip().lower()

    for item in memory_items or []:
        text = _normalize_text(item.get("text") or item.get("summary") or "", limit=500)
        if not text:
            continue

        memory_key = str(
            item.get("memory_key")
            or hashlib.sha1(f"{normalized_platform}:{text.lower()}".encode("utf-8")).hexdigest()
        )
        graph_scoped_key = f"{graph_id}:{memory_key}"
        importance_score = _clamp_score(item.get("importance_score"), default=35.0)
        round_num = int(item.get("round_num") or 0)

        if graph_scoped_key not in aggregated:
            aggregated[graph_scoped_key] = {
                "graph_scoped_key": graph_scoped_key,
                "memory_key": memory_key,
                "platform": normalized_platform,
                "text": text,
                "summary": _normalize_text(item.get("summary") or text, limit=500),
                "agent_name": _normalize_text(item.get("agent_name") or "", limit=120),
                "action_type": _normalize_text(item.get("action_type") or "", limit=64).upper(),
                "signature": _normalize_text(item.get("signature") or "", limit=240),
                "round_num": round_num,
                "importance_score": importance_score,
                "initial_reinforcement": min(100.0, round(importance_score * 0.8 + 8.0, 2)),
                "reinforcement_delta": round(max(4.0, importance_score * 0.35), 2),
                "batch_occurrence_count": 1,
            }
            continue

        current = aggregated[graph_scoped_key]
        current["batch_occurrence_count"] += 1
        current["round_num"] = max(current["round_num"], round_num)
        current["reinforcement_delta"] = min(
            100.0,
            round(current["reinforcement_delta"] + max(2.0, importance_score * 0.15), 2),
        )
        if importance_score > current["importance_score"]:
            current["importance_score"] = importance_score
            current["initial_reinforcement"] = min(100.0, round(importance_score * 0.8 + 8.0, 2))
            current["text"] = text
            current["summary"] = _normalize_text(item.get("summary") or text, limit=500)

    return list(aggregated.values())


def _refresh_memory_scores(session, graph_id: str, platform: str) -> None:
    stale_cutoff = (
        datetime.now(timezone.utc) - timedelta(days=max(Config.NEO4J_MEMORY_RETENTION_DAYS, 1))
    ).isoformat(timespec="seconds").replace("+00:00", "Z")

    session.run(
        """
        MATCH (m:SimMemory)
        WHERE m.graph_id = $gid AND m.platform = $platform
        WITH m,
             coalesce(m.reinforcement_score, 0.0) AS reinforcement,
             coalesce(m.importance_score, 0.0) AS importance,
             toFloat(coalesce(m.occurrence_count, 1)) AS occurrences,
             CASE
                 WHEN coalesce(m.last_seen_at, '') < $stale_cutoff THEN 0.55
                 ELSE 1.0
             END AS freshness
        WITH m, ((reinforcement * freshness) + (importance * 0.35) + (occurrences * 2.5)) AS effective_score
        SET m.effective_score = round(effective_score * 100) / 100,
            m.retention_state = CASE
                WHEN effective_score >= 90 THEN 'long_term'
                WHEN effective_score >= 45 THEN 'working'
                ELSE 'stale'
            END
        """,
        gid=graph_id,
        platform=platform,
        stale_cutoff=stale_cutoff,
    )


def _prune_memory_nodes(session, graph_id: str, platform: str) -> None:
    stale_cutoff = (
        datetime.now(timezone.utc) - timedelta(days=max(Config.NEO4J_MEMORY_RETENTION_DAYS, 1))
    ).isoformat(timespec="seconds").replace("+00:00", "Z")

    session.run(
        """
        MATCH (e:SimEpisode)
        WHERE e.graph_id = $gid AND e.platform = $platform
        WITH e
        ORDER BY coalesce(e.importance_score, 0.0) DESC,
                 coalesce(e.round_num, 0) DESC,
                 coalesce(e.last_seen_at, e.created_at, '') DESC
        SKIP $keep
        DETACH DELETE e
        """,
        gid=graph_id,
        platform=platform,
        keep=max(Config.NEO4J_MEMORY_MAX_EPISODES, 1),
    )

    session.run(
        """
        MATCH (m:SimMemory)
        WHERE m.graph_id = $gid
          AND m.platform = $platform
          AND coalesce(m.last_seen_at, '') < $stale_cutoff
          AND coalesce(m.effective_score, 0.0) < $min_effective
        DETACH DELETE m
        """,
        gid=graph_id,
        platform=platform,
        stale_cutoff=stale_cutoff,
        min_effective=float(Config.NEO4J_MEMORY_MIN_EFFECTIVE_SCORE),
    )

    session.run(
        """
        MATCH (m:SimMemory)
        WHERE m.graph_id = $gid AND m.platform = $platform
        WITH m
        ORDER BY coalesce(m.effective_score, 0.0) DESC,
                 coalesce(m.last_seen_at, m.first_seen_at, '') DESC
        SKIP $keep
        DETACH DELETE m
        """,
        gid=graph_id,
        platform=platform,
        keep=max(Config.NEO4J_MEMORY_MAX_ITEMS, 1),
    )


def add_sim_memory_episode_batch(
    graph_id: str,
    text: str,
    platform: str,
    memory_items: List[Dict[str, Any]],
) -> None:
    ensure_constraints()

    episode_uuid = str(uuid4())
    normalized_platform = (platform or "").strip().lower()
    now = _utcnow_iso()
    prepared_memories = _prepare_memory_batch(graph_id, normalized_platform, memory_items)

    episode_importance = max(
        (memory["importance_score"] for memory in prepared_memories),
        default=20.0,
    )
    last_round = max((memory["round_num"] for memory in prepared_memories), default=0)
    memory_keys = [memory["graph_scoped_key"] for memory in prepared_memories]

    with session_scope() as s:
        s.run(
            """
            CREATE (e:SimEpisode {
                uuid: $eid,
                graph_id: $gid,
                text: $text,
                normalized_text: $normalized_text,
                platform: $platform,
                created_at: $now,
                last_seen_at: $now,
                round_num: $round_num,
                activity_count: $activity_count,
                importance_score: $importance_score,
                memory_keys_json: $memory_keys_json
            })
            """,
            eid=episode_uuid,
            gid=graph_id,
            text=text or "",
            normalized_text=_normalize_text(text or "", limit=1000),
            platform=normalized_platform,
            now=now,
            round_num=last_round,
            activity_count=max(len(memory_items or []), 1),
            importance_score=episode_importance,
            memory_keys_json=json.dumps(memory_keys, ensure_ascii=False),
        )

        if prepared_memories:
            s.run(
                """
                UNWIND $memories AS m
                MERGE (mem:SimMemory {graph_scoped_key: m.graph_scoped_key})
                ON CREATE SET
                    mem.graph_id = $gid,
                    mem.memory_key = m.memory_key,
                    mem.platform = m.platform,
                    mem.text = m.text,
                    mem.summary = m.summary,
                    mem.agent_name = m.agent_name,
                    mem.action_type = m.action_type,
                    mem.signature = m.signature,
                    mem.first_seen_at = $now,
                    mem.last_seen_at = $now,
                    mem.first_round = m.round_num,
                    mem.last_round = m.round_num,
                    mem.occurrence_count = m.batch_occurrence_count,
                    mem.total_importance = m.importance_score * toFloat(m.batch_occurrence_count),
                    mem.importance_score = m.importance_score,
                    mem.average_importance = m.importance_score,
                    mem.reinforcement_score = m.initial_reinforcement,
                    mem.best_text_score = m.importance_score
                ON MATCH SET
                    mem.graph_id = $gid,
                    mem.last_seen_at = $now,
                    mem.last_round = CASE
                        WHEN m.round_num > coalesce(mem.last_round, 0) THEN m.round_num
                        ELSE coalesce(mem.last_round, 0)
                    END,
                    mem.occurrence_count = coalesce(mem.occurrence_count, 0) + m.batch_occurrence_count,
                    mem.total_importance = coalesce(mem.total_importance, 0.0)
                        + (m.importance_score * toFloat(m.batch_occurrence_count)),
                    mem.importance_score = CASE
                        WHEN m.importance_score > coalesce(mem.importance_score, 0.0)
                        THEN m.importance_score
                        ELSE coalesce(mem.importance_score, 0.0)
                    END,
                    mem.reinforcement_score = CASE
                        WHEN coalesce(mem.reinforcement_score, 0.0) + m.reinforcement_delta > 100.0
                        THEN 100.0
                        ELSE coalesce(mem.reinforcement_score, 0.0) + m.reinforcement_delta
                    END,
                    mem.text = CASE
                        WHEN m.importance_score > coalesce(mem.best_text_score, 0.0)
                        THEN m.text
                        ELSE coalesce(mem.text, m.text)
                    END,
                    mem.summary = CASE
                        WHEN size(coalesce(m.summary, '')) > size(coalesce(mem.summary, ''))
                        THEN m.summary
                        ELSE coalesce(mem.summary, m.summary)
                    END,
                    mem.agent_name = CASE
                        WHEN coalesce(mem.agent_name, '') = '' THEN m.agent_name
                        ELSE mem.agent_name
                    END,
                    mem.action_type = CASE
                        WHEN coalesce(mem.action_type, '') = '' THEN m.action_type
                        ELSE mem.action_type
                    END,
                    mem.signature = CASE
                        WHEN coalesce(mem.signature, '') = '' THEN m.signature
                        ELSE mem.signature
                    END,
                    mem.best_text_score = CASE
                        WHEN m.importance_score > coalesce(mem.best_text_score, 0.0)
                        THEN m.importance_score
                        ELSE coalesce(mem.best_text_score, 0.0)
                    END
                WITH mem
                SET mem.average_importance = round(
                        (coalesce(mem.total_importance, 0.0)
                        / toFloat(coalesce(mem.occurrence_count, 1))) * 100
                    ) / 100
                """,
                gid=graph_id,
                now=now,
                memories=prepared_memories,
            )

            s.run(
                """
                MATCH (e:SimEpisode {uuid: $eid})
                UNWIND $memory_keys AS memory_key
                MATCH (mem:SimMemory {graph_scoped_key: memory_key})
                MERGE (mem)-[:HAS_EPISODE]->(e)
                """,
                eid=episode_uuid,
                memory_keys=memory_keys,
            )

        _refresh_memory_scores(s, graph_id, normalized_platform)
        _prune_memory_nodes(s, graph_id, normalized_platform)


def add_sim_episode(graph_id: str, text: str, platform: str) -> None:
    add_sim_memory_episode_batch(graph_id, text, platform, [])


def refresh_all_node_embeddings(graph_id: str) -> None:
    """
    해당 그래프의 모든 GraphEntity 노드에 대해 이름을 기반으로 임베딩을 생성/갱신한다.
    """
    from ..utils.llm_client import LLMClient
    llm = LLMClient()
    
    with session_scope() as s:
        res = s.run(
            """
            MATCH (n:GraphEntity {graph_id: $gid})
            WHERE n.embedding IS NULL OR n.name IS NOT NULL
            RETURN n.uuid as uuid, n.name as name, n.summary as summary
            """,
            gid=graph_id
        )
        nodes = [dict(record) for record in res]
    
    if not nodes:
        return
        
    # 배치로 임베딩 생성 (OpenAI 등은 리스트를 지원함)
    # 한 번에 너무 많으면 에러날 수 있으므로 100개씩 끊어서 처리
    batch_size = 100
    for i in range(0, len(nodes), batch_size):
        subset = nodes[i : i + batch_size]
        # 이름과 요약을 합쳐서 문맥 확보
        texts = [f"{n['name']}: {n['summary'] or ''}" for n in subset]
        try:
            vectors = llm.embed_batch(texts)
            
            with session_scope() as s:
                s.run(
                    """
                    UNWIND $batch AS item
                    MATCH (n:GraphEntity {uuid: item.uuid})
                    SET n.embedding = item.vec
                    """,
                    batch=[{"uuid": subset[j]["uuid"], "vec": vectors[j]} for j in range(len(subset))]
                )
        except Exception as e:
            logger.error("임베딩 갱신 중 오류: %s", e)


def search_hybrid(
    graph_id: str,
    query: str,
    limit: int = 20,
) -> Tuple[List[str], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Vector Search + Full-Text Search + Keyword Match를 결합한 하이브리드 검색.
    """
    from ..utils.llm_client import LLMClient
    llm = LLMClient()
    
    q_vec = []
    try:
        q_vec = llm.embed(query)
    except Exception as e:
        logger.warning("쿼리 임베딩 실패, 키워드 검색으로 전환: %s", e)

    facts: List[str] = []
    nodes_out: List[Dict[str, Any]] = []
    edges_out: List[Dict[str, Any]] = []
    
    with session_scope() as s:
        # 1. Vector Search (Semantic)
        vector_nodes = []
        if q_vec:
            res = s.run(
                """
                CALL db.index.vector.queryNodes('graph_entity_embedding', $limit, $vec)
                YIELD node, score
                WHERE node.graph_id = $gid
                RETURN node.uuid as uuid, node.name as name, node.summary as summary, score
                """,
                vec=q_vec, limit=limit, gid=graph_id
            )
            vector_nodes = [dict(r) for r in res]
        
        # 2. Full-Text Search (Lexical)
        res = s.run(
            """
            CALL db.index.fulltext.queryNodes('graph_entity_fulltext', $q)
            YIELD node, score
            WHERE node.graph_id = $gid
            RETURN node.uuid as uuid, node.name as name, node.summary as summary, score
            LIMIT $limit
            """,
            q=query, limit=limit, gid=graph_id
        )
        ft_nodes = [dict(r) for r in res]
        
        # 3. Combine & Deduplicate (Simple merge for now, can use RRF)
        seen_uuids = set()
        for n in vector_nodes + ft_nodes:
            if n["uuid"] not in seen_uuids:
                nodes_out.append({
                    "uuid": n["uuid"],
                    "name": n["name"],
                    "summary": n["summary"],
                    "labels": ["Entity"], # simplified
                    "attributes": {}
                })
                seen_uuids.add(n["uuid"])
        
        # 4. Fetch related edges for found nodes
        if seen_uuids:
            res = s.run(
                """
                MATCH (a:GraphEntity)-[r:GRAPH_REL]->(b:GraphEntity)
                WHERE a.uuid IN $uuids OR b.uuid IN $uuids
                RETURN r.uuid as uuid, r.name as name, r.fact as fact, 
                       a.uuid as source_node_uuid, b.uuid as target_node_uuid
                LIMIT $limit
                """,
                uuids=list(seen_uuids), limit=limit
            )
            for r in res:
                edge = dict(r)
                edges_out.append(edge)
                if edge["fact"]:
                    facts.append(edge["fact"])

        # 5. Memories search (Traditional)
        # (기존 search_simple의 메모리 검색 로직 활용 가능)
        keywords = [word for word in query.replace(",", " ").split() if len(word) > 1]
        memories = _fetch_memories_for_search(graph_id, query, keywords)
        for m in memories:
            if m.get("summary"):
                facts.append(f"[Memory] {m['summary']}")

    return facts, edges_out, nodes_out


def search_simple(
    graph_id: str,
    query: str,
    limit: int = 20,
    scope: str = "edges",
) -> Tuple[List[str], List[Dict[str, Any]], List[Dict[str, Any]]]:
    q = (query or "").lower()
    keywords = [word for word in q.replace(",", " ").split() if len(word) > 1]

    def score_text(text: str) -> int:
        if not text:
            return 0
        lowered = text.lower()
        if q and q in lowered:
            return 100
        return sum(10 for keyword in keywords if keyword in lowered)

    facts: List[str] = []
    edges_out: List[Dict[str, Any]] = []
    nodes_out: List[Dict[str, Any]] = []

    nodes = fetch_nodes(graph_id)
    edges = fetch_edges(graph_id)
    memories = (
        _fetch_memories_for_search(graph_id, q, keywords)
        if (q.strip() or keywords)
        else []
    )

    if scope in ("edges", "both"):
        scored_edges = []
        for edge in edges:
            score = score_text(edge.get("fact", "")) + score_text(edge.get("name", ""))
            if score > 0:
                scored_edges.append((score, edge))
        scored_edges.sort(key=lambda item: item[0], reverse=True)
        for _, edge in scored_edges[:limit]:
            if edge.get("fact"):
                facts.append(edge["fact"])
            edges_out.append(
                {
                    "uuid": edge["uuid"],
                    "name": edge.get("name", ""),
                    "fact": edge.get("fact", ""),
                    "source_node_uuid": edge.get("source_node_uuid", ""),
                    "target_node_uuid": edge.get("target_node_uuid", ""),
                }
            )

        memory_limit = max(3, min(limit, limit // 2 + 1))
        scored_memories = []
        for memory in memories:
            score = score_text(memory.get("text", "")) + score_text(memory.get("summary", ""))
            if score <= 0:
                continue
            score += int(min(memory.get("importance_score", 0.0) / 10.0, 10))
            score += min(memory.get("occurrence_count", 0), 10)
            if memory.get("retention_state") == "long_term":
                score += 6
            scored_memories.append((score, memory))
        scored_memories.sort(key=lambda item: item[0], reverse=True)
        for _, memory in scored_memories[:memory_limit]:
            if memory.get("text"):
                facts.append(memory["text"])
            if memory.get("summary") and memory["summary"] != memory["text"]:
                facts.append(memory["summary"])

    if scope in ("nodes", "both"):
        scored_nodes = []
        for node in nodes:
            score = score_text(node.get("name", "")) + score_text(node.get("summary", ""))
            if score > 0:
                scored_nodes.append((score, node))
        scored_nodes.sort(key=lambda item: item[0], reverse=True)
        for _, node in scored_nodes[:limit]:
            nodes_out.append(
                {
                    "uuid": node["uuid"],
                    "name": node.get("name", ""),
                    "labels": node.get("labels", []),
                    "summary": node.get("summary", ""),
                }
            )
            if node.get("summary"):
                facts.append(f"[{node.get('name')}]: {node.get('summary')}")

    facts = list(dict.fromkeys(facts))
    return facts, edges_out, nodes_out


def store_community_summaries(graph_id: str, summaries: List[Dict[str, Any]]) -> None:
    """커뮤니티 요약 정보를 저장한다."""
    with session_scope() as s:
        # 기존 요약 삭제
        s.run(
            "MATCH (c:CommunitySummary) WHERE c.graph_id = $gid DETACH DELETE c",
            gid=graph_id
        )
        
        for comm in summaries:
            s.run(
                """
                CREATE (c:CommunitySummary {
                    uuid: $comm_id,
                    graph_id: $gid,
                    summary: $summary
                })
                WITH c
                UNWIND $node_uuids AS node_uuid
                MATCH (n:GraphEntity {uuid: node_uuid, graph_id: $gid})
                CREATE (c)-[:SUMMARIZES]->(n)
                """,
                gid=graph_id,
                comm_id=comm["community_id"],
                summary=comm["summary"],
                node_uuids=comm["node_uuids"]
            )

def fetch_community_summaries(graph_id: str) -> List[Dict[str, Any]]:
    """거시적 질의응답을 위한 커뮤니티 요약 조회"""
    with session_scope() as s:
        rows = s.run(
            """
            MATCH (c:CommunitySummary)
            WHERE c.graph_id = $gid
            RETURN c.uuid AS uuid, c.summary AS summary
            """,
            gid=graph_id
        )
        return [{"uuid": r["uuid"], "summary": r["summary"]} for r in rows]

def merge_nodes(graph_id: str, target_name: str, alias_names: List[str], entity_type: str) -> None:
    """
    동일한 엔터티로 판별된 여러 노드(aliases)를 하나의 타겟 노드(target)로 병합합니다.
    """
    if not alias_names:
        return
        
    with session_scope() as s:
        # APOC가 없어도 동작하도록 순수 Cypher로 구현 (제한적이지만 효과적)
        s.run(
            """
            MATCH (target:GraphEntity {graph_id: $gid, name: $target_name})
            WHERE $type IN labels(target) OR $type = 'Entity'
            WITH target LIMIT 1
            
            UNWIND $alias_names AS alias_name
            MATCH (alias:GraphEntity {graph_id: $gid, name: alias_name})
            WHERE alias <> target
            
            // Inbound edges 이전
            WITH target, alias
            MATCH (source)-[r_in:GRAPH_REL]->(alias)
            MERGE (source)-[new_r_in:GRAPH_REL {name: r_in.name}]->(target)
            ON CREATE SET new_r_in = r_in
            
            // Outbound edges 이전
            WITH target, alias
            MATCH (alias)-[r_out:GRAPH_REL]->(target_node)
            MERGE (target)-[new_r_out:GRAPH_REL {name: r_out.name}]->(target_node)
            ON CREATE SET new_r_out = r_out
            
            // 속성 병합 (단순화: target에 없는 summary 채우기 등)
            WITH target, alias
            SET target.summary = CASE WHEN target.summary = '' THEN alias.summary ELSE target.summary END
            
            // Alias 삭제
            DETACH DELETE alias
            """,
            gid=graph_id,
            target_name=target_name,
            alias_names=alias_names,
            type=entity_type
        )

def fetch_unreflected_episodes(graph_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Reflection(회고) 처리가 되지 않은 최근 에피소드들을 가져옵니다."""
    with session_scope() as s:
        rows = s.run(
            """
            MATCH (e:SimEpisode {graph_id: $gid})
            WHERE e.reflected IS NULL OR e.reflected = false
            RETURN e.uuid AS uuid, e.text AS text
            ORDER BY e.created_at DESC
            LIMIT $limit
            """,
            gid=graph_id,
            limit=limit
        )
        return [{"uuid": r["uuid"], "text": r["text"]} for r in rows]

def mark_episodes_reflected(graph_id: str, episode_uuids: List[str]) -> None:
    """에피소드들을 회고 처리 완료로 표시합니다."""
    if not episode_uuids:
        return
    with session_scope() as s:
        s.run(
            """
            UNWIND $uuids AS eid
            MATCH (e:SimEpisode {graph_id: $gid, uuid: eid})
            SET e.reflected = true
            """,
            gid=graph_id,
            uuids=episode_uuids
        )

def store_semantic_memories(graph_id: str, insights: List[str], episode_uuids: List[str]) -> None:
    """추출된 의미 기억(Semantic Memory)을 저장하고 원본 에피소드와 연결합니다."""
    if not insights:
        return
        
    now = _utcnow_iso()
    with session_scope() as s:
        for insight in insights:
            s.run(
                """
                CREATE (m:SemanticMemory {
                    uuid: randomUUID(),
                    graph_id: $gid,
                    text: $text,
                    created_at: $now,
                    importance_score: 50.0
                })
                WITH m
                UNWIND $episode_uuids AS eid
                MATCH (e:SimEpisode {graph_id: $gid, uuid: eid})
                CREATE (m)-[:ABSTRACTED_FROM]->(e)
                SET e.reflected = true
                """,
                gid=graph_id,
                text=insight,
                now=now,
                episode_uuids=episode_uuids
            )


