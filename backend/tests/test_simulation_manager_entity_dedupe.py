from app.services.simulation_manager import SimulationManager
from app.services.entity_types import EntityNode


def _entity(name: str, entity_type: str, summary: str = "", related_edges=None, attributes=None) -> EntityNode:
    return EntityNode(
        uuid=f"uuid_{name}",
        name=name,
        labels=["Entity", entity_type],
        summary=summary,
        attributes=attributes or {},
        related_edges=related_edges or [],
        related_nodes=[],
    )


def test_bilingual_company_aliases_are_merged_for_agent_generation():
    entities = [
        _entity("엔비디아", "Company", "AI GPU 기업"),
        _entity("NVIDIA", "Company", "GPU designer for AI infrastructure"),
    ]

    deduped = SimulationManager._dedupe_entities_for_agents(entities)

    assert len(deduped) == 1
    assert deduped[0].name == "엔비디아"
    assert "NVIDIA" in deduped[0].attributes.get("aliases", [])


def test_shared_context_alone_does_not_merge_distinct_companies():
    entities = [
        _entity(
            "삼성전자",
            "Company",
            "메모리와 파운드리 사업을 하는 기업",
            related_edges=[{"fact": "삼성전자는 엔비디아와 협력한다"}],
        ),
        _entity(
            "SK하이닉스",
            "Company",
            "HBM 메모리를 공급하는 기업",
            related_edges=[{"fact": "SK하이닉스는 엔비디아에 HBM을 공급한다"}],
        ),
    ]

    deduped = SimulationManager._dedupe_entities_for_agents(entities)

    assert len(deduped) == 2
    assert {entity.name for entity in deduped} == {"삼성전자", "SK하이닉스"}


def test_parenthetical_aliases_are_merged_even_without_static_alias_group():
    entities = [
        _entity("대한민국 정부", "GovernmentAgency", "대한민국 정부(South Korean Government)는 정책을 발표했다."),
        _entity("South Korean Government", "GovernmentAgency", "정부 기관"),
    ]

    deduped = SimulationManager._dedupe_entities_for_agents(entities)

    assert len(deduped) == 1
    assert deduped[0].name == "대한민국 정부"
    assert "South Korean Government" in deduped[0].attributes.get("aliases", [])
