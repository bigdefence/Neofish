"""
텍스트 청크에서 LLM으로 엔터티/관계를 추출해 Neo4j 적재용 구조로 만든다.
(LLM 기반 엔터티·관계 추출)
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..utils.llm_client import LLMClient

logger = logging.getLogger("neofish.neo4j_chunk_extractor")


def _entity_key(name: str, entity_type: str) -> Tuple[str, str]:
    return ((name or "").strip().lower(), (entity_type or "Entity").strip())


def extract_entities_from_chunk(
    chunk_text: str,
    ontology: Dict[str, Any],
    key_to_uuid: Dict[Tuple[str, str], str],
    llm: Optional[LLMClient] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    단일 청크에서 노드/관계 후보를 추출한다.

    Returns:
        (nodes_for_upsert, rels_for_upsert) 각 노드는 uuid,name,labels,summary,attributes
        관계는 source_uuid,target_uuid,name,fact,fact_type,uuid
    """
    llm = llm or LLMClient()
    entity_types = [e.get("name", "") for e in ontology.get("entity_types", [])][:20]
    edge_types = [e.get("name", "") for e in ontology.get("edge_types", [])][:20]

    system = (
        "You extract a knowledge graph fragment as strict JSON only. "
        "Use entity types and relationship names from the ontology when possible."
    )
    user = f"""Ontology entity types (prefer these): {entity_types}
Ontology relationship types (prefer these): {edge_types}

Text chunk:
---
{chunk_text[:12000]}
---

Return JSON with this shape:
{{
  "nodes": [
    {{"name": "Display Name", "entity_type": "OneOfOntologyTypes", "summary": "short phrase"}}
  ],
  "relationships": [
    {{"source_name": "A", "source_type": "TypeOfA", "target_name": "B", "target_type": "TypeOfB",
      "predicate": "RELATIONSHIP_TYPE", "fact": "natural language fact"}}
  ]
}}
Rules:
- Only include nodes/edges grounded in the text.
- If unsure of type, use "Entity".
- Keep nodes concise (max ~24 nodes per chunk).
"""

    try:
        data = llm.chat_json(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=4096,
        )
    except Exception as e:
        logger.warning("청크 LLM 추출 실패: %s", e)
        return [], []

    if not isinstance(data, dict):
        return [], []

    raw_nodes = data.get("nodes") or []
    raw_rels = data.get("relationships") or []

    nodes_out: List[Dict[str, Any]] = []
    for n in raw_nodes:
        if not isinstance(n, dict):
            continue
        name = str(n.get("name", "")).strip()
        if not name:
            continue
        et = str(n.get("entity_type", "Entity") or "Entity").strip()
        key = _entity_key(name, et)
        if key not in key_to_uuid:
            key_to_uuid[key] = str(uuid.uuid4())
        uid = key_to_uuid[key]
        if any(x["uuid"] == uid for x in nodes_out):
            continue
        labels = ["Entity", et] if et else ["Entity"]
        nodes_out.append(
            {
                "uuid": uid,
                "name": name,
                "labels": labels,
                "summary": str(n.get("summary", "") or "")[:2000],
                "attributes": {},
            }
        )

    def _ensure_node(key: Tuple[str, str], display_name: str, et: str) -> str:
        if key not in key_to_uuid:
            key_to_uuid[key] = str(uuid.uuid4())
        uid = key_to_uuid[key]
        if not any(n["uuid"] == uid for n in nodes_out):
            et_clean = (et or "Entity").strip() or "Entity"
            nodes_out.append(
                {
                    "uuid": uid,
                    "name": display_name.strip(),
                    "labels": ["Entity", et_clean],
                    "summary": "",
                    "attributes": {},
                }
            )
        return uid

    rels_out: List[Dict[str, Any]] = []
    for r in raw_rels:
        if not isinstance(r, dict):
            continue
        sn = str(r.get("source_name", "")).strip()
        tn = str(r.get("target_name", "")).strip()
        if not sn or not tn:
            continue
        st = str(r.get("source_type", "Entity") or "Entity").strip()
        tt = str(r.get("target_type", "Entity") or "Entity").strip()
        sk = _entity_key(sn, st)
        tk = _entity_key(tn, tt)
        su = _ensure_node(sk, sn, st)
        tu = _ensure_node(tk, tn, tt)
        pred = str(r.get("predicate", "RELATED_TO") or "RELATED_TO")
        fact = str(r.get("fact", "") or "")
        rels_out.append(
            {
                "uuid": str(uuid.uuid4()),
                "source_uuid": su,
                "target_uuid": tu,
                "name": pred,
                "fact": fact,
                "fact_type": pred,
            }
        )

    return nodes_out, rels_out
