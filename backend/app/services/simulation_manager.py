"""
OASIS 시뮬레이션 매니저.
Twitter/Reddit 양 플랫폼 병렬 시뮬레이션을 관리한다.
사전 제공 스크립트와 LLM 기반 설정 생성을 사용한다.
"""

import os
import json
import re
import shutil
import threading
import concurrent.futures
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..config import Config
from ..utils.logger import get_logger
from .graph_backend import get_entity_reader
from .entity_types import EntityNode, FilteredEntities
from .oasis_profile_generator import OasisProfileGenerator, OasisAgentProfile
from .simulation_config_generator import SimulationConfigGenerator, SimulationParameters

logger = get_logger('neofish.simulation')


class SimulationStatus(str, Enum):
    """시뮬레이션 상태."""
    CREATED = "created"
    PREPARING = "preparing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"      # 사용자가 수동 중지
    COMPLETED = "completed"  # 시뮬레이션 자연 종료
    FAILED = "failed"


class PlatformType(str, Enum):
    """플랫폼 타입."""
    TWITTER = "twitter"
    REDDIT = "reddit"


@dataclass
class SimulationState:
    """시뮬레이션 상태."""
    simulation_id: str
    project_id: str
    graph_id: str
    
    # 플랫폼 활성화 상태
    enable_twitter: bool = True
    enable_reddit: bool = True
    
    # 상태
    status: SimulationStatus = SimulationStatus.CREATED
    
    # 준비 단계 데이터
    entities_count: int = 0
    profiles_count: int = 0
    entity_types: List[str] = field(default_factory=list)
    
    # 설정 생성 정보
    config_generated: bool = False
    config_reasoning: str = ""
    
    # 실행 중 데이터
    current_round: int = 0
    twitter_status: str = "not_started"
    reddit_status: str = "not_started"
    
    # 타임스탬프
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # 오류 정보
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """전체 상태 dict(내부용)."""
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "enable_twitter": self.enable_twitter,
            "enable_reddit": self.enable_reddit,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "config_reasoning": self.config_reasoning,
            "current_round": self.current_round,
            "twitter_status": self.twitter_status,
            "reddit_status": self.reddit_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
        }
    
    def to_simple_dict(self) -> Dict[str, Any]:
        """요약 상태 dict(API 반환용)."""
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "config_generated": self.config_generated,
            "error": self.error,
        }


def _simulation_state_from_run_state_only(simulation_id: str, sim_dir: str) -> Optional[SimulationState]:
    """
    state.json 이 없고 run_state.json 만 있는 디렉터리(스크립트 직접 실행·구버전 등)도
    이력 목록에 포함되도록 최소 SimulationState 를 구성한다.
    """
    run_path = os.path.join(sim_dir, "run_state.json")
    if not os.path.exists(run_path):
        return None
    try:
        with open(run_path, "r", encoding="utf-8") as f:
            rs = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(rs, dict):
        return None

    file_sim_id = rs.get("simulation_id")
    if file_sim_id and file_sim_id != simulation_id:
        logger.warning(
            "run_state.json 의 simulation_id 가 폴더명과 다름: dir=%s file=%s",
            simulation_id,
            file_sim_id,
        )

    project_id = ""
    graph_id = ""
    cfg_path = os.path.join(sim_dir, "simulation_config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as cf:
                cfg = json.load(cf)
            if isinstance(cfg, dict):
                project_id = str(cfg.get("project_id") or "")
                graph_id = str(cfg.get("graph_id") or "")
        except (OSError, json.JSONDecodeError):
            pass

    runner_status = (rs.get("runner_status") or "idle").lower()
    if runner_status == "completed":
        status = SimulationStatus.COMPLETED
    elif runner_status == "failed":
        status = SimulationStatus.FAILED
    elif runner_status in ("running", "starting", "stopping"):
        status = SimulationStatus.RUNNING
    elif runner_status == "stopped":
        tr = int(rs.get("total_rounds") or 0)
        cr = int(rs.get("current_round") or 0)
        if (
            tr > 0
            and cr >= tr
            and rs.get("twitter_completed")
            and rs.get("reddit_completed")
        ):
            status = SimulationStatus.COMPLETED
        else:
            status = SimulationStatus.STOPPED
    else:
        status = SimulationStatus.READY

    created = rs.get("started_at") or rs.get("updated_at") or datetime.now().isoformat()
    updated = rs.get("updated_at") or rs.get("completed_at") or created

    tw_done = bool(rs.get("twitter_completed"))
    rd_done = bool(rs.get("reddit_completed"))
    if runner_status == "running":
        twitter_status = "completed" if tw_done else "running"
        reddit_status = "completed" if rd_done else "running"
    else:
        twitter_status = "completed" if tw_done else "not_started"
        reddit_status = "completed" if rd_done else "not_started"

    return SimulationState(
        simulation_id=simulation_id,
        project_id=project_id,
        graph_id=graph_id,
        enable_twitter=True,
        enable_reddit=True,
        status=status,
        current_round=int(rs.get("current_round") or 0),
        twitter_status=twitter_status,
        reddit_status=reddit_status,
        created_at=created,
        updated_at=updated,
        error=rs.get("error"),
    )


class SimulationManager:
    """
    시뮬레이션 매니저 (싱글턴).

    핵심 기능:
    1. Neo4j 그래프에서 엔터티를 조회/필터링
    2. OASIS Agent Profile 생성
    3. LLM 기반 시뮬레이션 설정값 생성
    4. 사전 제공 스크립트 실행에 필요한 파일 준비
    """

    _instance = None
    _lock = threading.Lock()
    _simulations: Dict[str, 'SimulationState'] = {}

    # 시뮬레이션 데이터 저장 디렉터리
    SIMULATION_DATA_DIR = os.path.join(
        os.path.dirname(__file__),
        '../../uploads/simulations'
    )
    ENTITY_ALIAS_GROUPS = (
        ("nvidia", "엔비디아"),
        ("amd", "에이엠디"),
        ("meta", "메타"),
        ("google", "구글"),
        ("amazon", "아마존"),
        ("microsoft", "마이크로소프트"),
        ("samsung electronics", "삼성전자"),
        ("sk hynix", "sk하이닉스"),
        ("south korean government", "대한민국 정부", "한국 정부"),
        ("united states government", "us government", "미국 정부"),
    )

    def __new__(cls):
        """싱글턴 패턴 — API 호출 간 인메모리 캐시를 유지합니다."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    os.makedirs(cls.SIMULATION_DATA_DIR, exist_ok=True)
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        # 싱글턴이므로 __new__에서 초기화가 완료됨 — 여기서는 아무것도 하지 않습니다.
        pass

    @classmethod
    def _normalize_entity_alias(cls, value: Any) -> str:
        text = str(value or "").strip().lower()
        if not text:
            return ""
        text = re.sub(r"[\"'`]", "", text)
        text = re.sub(r"[^0-9a-z가-힣&+/.\-\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        tokens = text.split()
        removable_suffixes = {
            "inc", "corp", "corporation", "co", "company", "ltd", "limited", "llc"
        }
        while tokens and tokens[-1].rstrip(".") in removable_suffixes:
            tokens.pop()
        return " ".join(tokens).strip()

    @classmethod
    def _alias_lookup(cls) -> Dict[str, str]:
        lookup: Dict[str, str] = {}
        for group in cls.ENTITY_ALIAS_GROUPS:
            normalized = [cls._normalize_entity_alias(item) for item in group]
            normalized = [item for item in normalized if item]
            if not normalized:
                continue
            canonical = normalized[0]
            for item in normalized:
                lookup[item] = canonical
        return lookup

    @classmethod
    def _extract_alias_candidates_from_text(cls, text: Any) -> List[str]:
        source = str(text or "").strip()
        if not source:
            return []

        candidates: List[str] = []
        for left, right in re.findall(r"([A-Za-z0-9가-힣&+./\-\s]{2,60})\(([^()]{2,60})\)", source):
            left = left.strip(" ,.;:|/-")
            right = right.strip(" ,.;:|/-")
            if left:
                candidates.append(left)
            if right:
                candidates.append(right)
        return candidates

    @classmethod
    def _extract_linked_aliases(cls, entity_name: str, text: Any) -> List[str]:
        source = str(text or "").strip()
        target = cls._normalize_entity_alias(entity_name)
        if not source or not target:
            return []

        lookup = cls._alias_lookup()
        target_keys = {target, lookup.get(target, target)}
        aliases: List[str] = []

        for left, right in re.findall(r"([A-Za-z0-9가-힣&+./\-\s]{2,60})\(([^()]{2,60})\)", source):
            left_clean = left.strip(" ,.;:|/-")
            right_clean = right.strip(" ,.;:|/-")
            left_norm = cls._normalize_entity_alias(left_clean)
            right_norm = cls._normalize_entity_alias(right_clean)
            left_keys = {left_norm, lookup.get(left_norm, left_norm)}
            right_keys = {right_norm, lookup.get(right_norm, right_norm)}

            if target_keys & left_keys and right_clean:
                aliases.append(right_clean)
            elif target_keys & right_keys and left_clean:
                aliases.append(left_clean)

        return aliases

    @classmethod
    def _entity_alias_signatures(cls, entity: EntityNode) -> set[str]:
        lookup = cls._alias_lookup()
        raw_aliases = {entity.name}

        if entity.summary:
            raw_aliases.update(cls._extract_linked_aliases(entity.name, entity.summary))

        for edge in entity.related_edges or []:
            raw_aliases.update(cls._extract_linked_aliases(entity.name, edge.get("fact", "")))

        alias_like_keys = {"alias", "aliases", "aka", "english_name", "korean_name", "alternate_names"}
        for key, value in (entity.attributes or {}).items():
            if str(key or "").strip().lower() not in alias_like_keys:
                continue
            if isinstance(value, list):
                for item in value:
                    raw_aliases.update(cls._extract_alias_candidates_from_text(item))
                    raw_aliases.add(str(item or ""))
            else:
                raw_aliases.update(cls._extract_alias_candidates_from_text(value))
                raw_aliases.add(str(value or ""))

        signatures: set[str] = set()
        for alias in raw_aliases:
            normalized = cls._normalize_entity_alias(alias)
            if not normalized:
                continue
            signatures.add(normalized)
            canonical = lookup.get(normalized)
            if canonical:
                signatures.add(canonical)

        return signatures

    @staticmethod
    def _entity_type_matches(left: EntityNode, right: EntityNode) -> bool:
        left_type = left.get_entity_type() or "Entity"
        right_type = right.get_entity_type() or "Entity"
        return left_type == right_type or "Entity" in {left_type, right_type}

    @staticmethod
    def _contains_hangul(text: str) -> bool:
        return bool(re.search(r"[가-힣]", text or ""))

    @classmethod
    def _choose_canonical_entity_name(cls, names: List[str]) -> str:
        unique_names = []
        seen = set()
        for name in names:
            clean = str(name or "").strip()
            if clean and clean not in seen:
                seen.add(clean)
                unique_names.append(clean)

        if not unique_names:
            return ""

        hangul_names = [name for name in unique_names if cls._contains_hangul(name)]
        if hangul_names:
            return min(hangul_names, key=lambda item: (len(item), item))
        return min(unique_names, key=lambda item: (len(item), item.lower()))

    @staticmethod
    def _merge_related_edges(primary: EntityNode, secondary: EntityNode) -> List[Dict[str, Any]]:
        merged: List[Dict[str, Any]] = []
        seen = set()
        for edge in list(primary.related_edges or []) + list(secondary.related_edges or []):
            key = (
                edge.get("direction", ""),
                edge.get("edge_name", ""),
                edge.get("fact", ""),
                edge.get("source_node_uuid", ""),
                edge.get("target_node_uuid", ""),
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(edge)
        return merged

    @staticmethod
    def _merge_related_nodes(primary: EntityNode, secondary: EntityNode) -> List[Dict[str, Any]]:
        merged: List[Dict[str, Any]] = []
        seen = set()
        for node in list(primary.related_nodes or []) + list(secondary.related_nodes or []):
            key = (node.get("uuid", ""), node.get("name", ""))
            if key in seen:
                continue
            seen.add(key)
            merged.append(node)
        return merged

    @classmethod
    def _merge_duplicate_entities(cls, entities: List[EntityNode]) -> EntityNode:
        primary = entities[0]
        aliases = []
        for entity in entities:
            aliases.append(entity.name)
            aliases.extend((entity.attributes or {}).get("aliases", []))

        merged_attributes: Dict[str, Any] = {}
        for entity in entities:
            for key, value in (entity.attributes or {}).items():
                if key == "aliases":
                    continue
                if value not in (None, "", [], {}):
                    merged_attributes.setdefault(key, value)

        canonical_name = cls._choose_canonical_entity_name(aliases) or primary.name
        alias_values = []
        for alias in aliases:
            clean = str(alias or "").strip()
            if clean and clean != canonical_name and clean not in alias_values:
                alias_values.append(clean)
        if alias_values:
            merged_attributes["aliases"] = alias_values

        merged_labels = []
        for entity in entities:
            for label in entity.labels:
                if label not in merged_labels:
                    merged_labels.append(label)

        summaries = [str(entity.summary or "").strip() for entity in entities if str(entity.summary or "").strip()]
        merged_summary = max(summaries, key=len) if summaries else ""

        return EntityNode(
            uuid=primary.uuid,
            name=canonical_name,
            labels=merged_labels or primary.labels,
            summary=merged_summary,
            attributes=merged_attributes,
            related_edges=cls._merge_related_edges(primary, entities[-1]) if len(entities) == 2 else [],
            related_nodes=cls._merge_related_nodes(primary, entities[-1]) if len(entities) == 2 else [],
        )

    @classmethod
    def _merge_duplicate_entities_group(cls, entities: List[EntityNode]) -> EntityNode:
        merged = entities[0]
        for entity in entities[1:]:
            merged = cls._merge_duplicate_entities([merged, entity])
        return merged

    @classmethod
    def _dedupe_entities_for_agents(cls, entities: List[EntityNode]) -> List[EntityNode]:
        if len(entities) < 2:
            return entities

        signatures = [cls._entity_alias_signatures(entity) for entity in entities]
        consumed = set()
        deduped: List[EntityNode] = []

        for idx, entity in enumerate(entities):
            if idx in consumed:
                continue

            group = [entity]
            group_indices = [idx]
            consumed.add(idx)
            changed = True
            while changed:
                changed = False
                for other_idx, other in enumerate(entities):
                    if other_idx in consumed:
                        continue
                    if not any(cls._entity_type_matches(candidate, other) for candidate in group):
                        continue
                    current_signatures = set().union(*(signatures[i] for i in group_indices))
                    if current_signatures & signatures[other_idx]:
                        group.append(other)
                        group_indices.append(other_idx)
                        consumed.add(other_idx)
                        changed = True

            if len(group) == 1:
                deduped.append(entity)
                continue

            merged = cls._merge_duplicate_entities_group(group)
            deduped.append(merged)
            logger.info(
                "중복 엔터티 병합: %s -> %s",
                ", ".join(item.name for item in group),
                merged.name,
            )

        return deduped
    
    def _get_simulation_dir(self, simulation_id: str) -> str:
        """시뮬레이션 데이터 디렉터리를 반환한다."""
        sim_dir = os.path.join(self.SIMULATION_DATA_DIR, simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        return sim_dir
    
    def _save_simulation_state(self, state: SimulationState):
        """시뮬레이션 상태를 파일에 저장한다."""
        sim_dir = self._get_simulation_dir(state.simulation_id)
        state_file = os.path.join(sim_dir, "state.json")
        
        state.updated_at = datetime.now().isoformat()
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
        
        self._simulations[state.simulation_id] = state
    
    def _load_simulation_state(self, simulation_id: str) -> Optional[SimulationState]:
        """파일에서 시뮬레이션 상태를 불러온다."""
        if simulation_id in self._simulations:
            return self._simulations[simulation_id]
        
        sim_dir = self._get_simulation_dir(simulation_id)
        state_file = os.path.join(sim_dir, "state.json")
        
        if os.path.exists(state_file):
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            state = SimulationState(
                simulation_id=simulation_id,
                project_id=data.get("project_id", ""),
                graph_id=data.get("graph_id", ""),
                enable_twitter=data.get("enable_twitter", True),
                enable_reddit=data.get("enable_reddit", True),
                status=SimulationStatus(data.get("status", "created")),
                entities_count=data.get("entities_count", 0),
                profiles_count=data.get("profiles_count", 0),
                entity_types=data.get("entity_types", []),
                config_generated=data.get("config_generated", False),
                config_reasoning=data.get("config_reasoning", ""),
                current_round=data.get("current_round", 0),
                twitter_status=data.get("twitter_status", "not_started"),
                reddit_status=data.get("reddit_status", "not_started"),
                created_at=data.get("created_at", datetime.now().isoformat()),
                updated_at=data.get("updated_at", datetime.now().isoformat()),
                error=data.get("error"),
            )
            
            self._simulations[simulation_id] = state
            return state

        # state.json 없이 run_state.json 만 있는 경우(이력 API에서도 보이도록)
        fallback = _simulation_state_from_run_state_only(simulation_id, sim_dir)
        if fallback:
            self._simulations[simulation_id] = fallback
            return fallback
        return None
    
    def create_simulation(
        self,
        project_id: str,
        graph_id: str,
        enable_twitter: bool = True,
        enable_reddit: bool = True,
    ) -> SimulationState:
        """
        새 시뮬레이션을 생성한다.

        Args:
            project_id: 프로젝트 ID
            graph_id: Neo4j graph_id
            enable_twitter: Twitter 시뮬레이션 사용 여부
            enable_reddit: Reddit 시뮬레이션 사용 여부

        Returns:
            SimulationState
        """
        import uuid
        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"
        
        state = SimulationState(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            enable_twitter=enable_twitter,
            enable_reddit=enable_reddit,
            status=SimulationStatus.CREATED,
        )
        
        self._save_simulation_state(state)
        logger.info(f"시뮬레이션 생성: {simulation_id}, project={project_id}, graph={graph_id}")
        
        return state
    
    def prepare_simulation(
        self,
        simulation_id: str,
        simulation_requirement: str,
        document_text: str,
        defined_entity_types: Optional[List[str]] = None,
        use_llm_for_profiles: bool = True,
        progress_callback: Optional[callable] = None,
        parallel_profile_count: int = 3,
        max_agents: Optional[int] = None
    ) -> SimulationState:
        """
        시뮬레이션 환경을 자동으로 준비한다.

        단계:
        1. Neo4j 그래프에서 엔터티 조회/필터링
        2. 엔터티별 OASIS Agent Profile 생성(옵션: LLM 강화, 병렬 지원)
        3. LLM으로 시뮬레이션 설정값 생성(시간/활성도/발화 빈도 등)
        4. 설정 파일 및 Profile 파일 저장

        Args:
            simulation_id: 시뮬레이션 ID
            simulation_requirement: 시뮬레이션 요구사항(LLM 설정 생성용)
            document_text: 원문 문서(LLM 배경 이해용)
            defined_entity_types: 사전 정의 엔터티 타입(선택)
            use_llm_for_profiles: 상세 프로필 생성 시 LLM 사용 여부
            progress_callback: 진행 콜백 (stage, progress, message)
            parallel_profile_count: 프로필 병렬 생성 개수(기본 3)
            max_agents: 최대 생성 에이전트 수 (선택)

        Returns:
            SimulationState
        """
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"시뮬레이션이 존재하지 않습니다: {simulation_id}")
        
        try:
            state.status = SimulationStatus.PREPARING
            self._save_simulation_state(state)
            
            sim_dir = self._get_simulation_dir(simulation_id)
            
            # ========== 1단계: 엔터티 조회/필터링 ==========
            if progress_callback:
                progress_callback("reading", 0, "지식 그래프에 연결 중...")
            
            reader = get_entity_reader()
            
            if progress_callback:
                progress_callback("reading", 30, "노드 데이터를 읽는 중...")
            
            filtered = reader.filter_defined_entities(
                graph_id=state.graph_id,
                defined_entity_types=defined_entity_types,
                enrich_with_edges=True
            )

            deduped_entities = self._dedupe_entities_for_agents(filtered.entities)
            if len(deduped_entities) != len(filtered.entities):
                logger.info(
                    "에이전트 생성용 엔터티 중복 제거: %s -> %s",
                    len(filtered.entities),
                    len(deduped_entities),
                )
                filtered.entities = deduped_entities
                filtered.filtered_count = len(deduped_entities)
                filtered.entity_types = {e.get_entity_type() or "Unknown" for e in deduped_entities}
             
            if max_agents is not None and max_agents > 0 and len(filtered.entities) > max_agents:
                logger.info(f"설정된 최대 에이전트 수 한계({max_agents})에 도달하여 엔터티 목록을 자릅니다. 기존 엔터티 수: {len(filtered.entities)}")
                filtered.entities = filtered.entities[:max_agents]
                filtered.filtered_count = len(filtered.entities)
                # 남아있는 엔터티 타입을 기반으로 타입 목록 다시 계산
                filtered.entity_types = {e.get_entity_type() or "Unknown" for e in filtered.entities}
            
            state.entities_count = filtered.filtered_count
            state.entity_types = list(filtered.entity_types)
            
            if progress_callback:
                progress_callback(
                    "reading", 100, 
                    f"완료, 총 {filtered.filtered_count}개 엔터티",
                    current=filtered.filtered_count,
                    total=filtered.filtered_count
                )
            
            if filtered.filtered_count == 0:
                state.status = SimulationStatus.FAILED
                state.error = "조건에 맞는 엔터티를 찾지 못했습니다. 그래프 구축 상태를 확인해 주세요."
                self._save_simulation_state(state)
                return state
            
            # ========== 2단계: Agent Profile 생성 ==========
            total_entities = len(filtered.entities)
            
            if progress_callback:
                progress_callback(
                    "generating_profiles", 0, 
                    "생성을 시작합니다...",
                    current=0,
                    total=total_entities
                )
            
            # graph_id를 전달해 그래프 검색 컨텍스트를 활성화
            generator = OasisProfileGenerator(graph_id=state.graph_id)
            
            def profile_progress(current, total, msg):
                if progress_callback:
                    progress_callback(
                        "generating_profiles", 
                        int(current / total * 100), 
                        msg,
                        current=current,
                        total=total,
                        item_name=msg
                    )

            config_generator = SimulationConfigGenerator()

            def config_progress(current_step, total_steps, msg):
                if progress_callback:
                    progress_callback(
                        "generating_config",
                        int(current_step / max(total_steps, 1) * 90),
                        msg,
                        current=current_step,
                        total=total_steps
                    )

            def run_profile_generation():
                realtime_output_path = None
                realtime_platform = "reddit"
                if state.enable_reddit:
                    realtime_output_path = os.path.join(sim_dir, "reddit_profiles.json")
                    realtime_platform = "reddit"
                elif state.enable_twitter:
                    realtime_output_path = os.path.join(sim_dir, "twitter_profiles.csv")
                    realtime_platform = "twitter"

                profiles = generator.generate_profiles_from_entities(
                    entities=filtered.entities,
                    use_llm=use_llm_for_profiles,
                    progress_callback=profile_progress,
                    graph_id=state.graph_id,
                    parallel_count=parallel_profile_count,
                    realtime_output_path=realtime_output_path,
                    output_platform=realtime_platform
                )

                if progress_callback:
                    progress_callback(
                        "generating_profiles", 95,
                        "Profile ?뚯씪 ???以?..",
                        current=total_entities,
                        total=total_entities
                    )

                if state.enable_reddit:
                    generator.save_profiles(
                        profiles=profiles,
                        file_path=os.path.join(sim_dir, "reddit_profiles.json"),
                        platform="reddit"
                    )

                if state.enable_twitter:
                    generator.save_profiles(
                        profiles=profiles,
                        file_path=os.path.join(sim_dir, "twitter_profiles.csv"),
                        platform="twitter"
                    )

                if progress_callback:
                    progress_callback(
                        "generating_profiles", 100,
                        f"?꾨즺, 珥?{len(profiles)}媛?Profile",
                        current=len(profiles),
                        total=len(profiles)
                    )

                return profiles

            def run_config_generation():
                if progress_callback:
                    progress_callback(
                        "generating_config", 0,
                        "?쒕??덉씠???붽뎄?ы빆 遺꾩꽍 以?..",
                        current=0,
                        total=1
                    )

                sim_params = config_generator.generate_config(
                    simulation_id=simulation_id,
                    project_id=state.project_id,
                    graph_id=state.graph_id,
                    simulation_requirement=simulation_requirement,
                    document_text=document_text,
                    entities=filtered.entities,
                    enable_twitter=state.enable_twitter,
                    enable_reddit=state.enable_reddit,
                    progress_callback=config_progress,
                )

                if progress_callback:
                    progress_callback(
                        "generating_config", 95,
                        "?ㅼ젙 ?뚯씪 ???以?..",
                        current=1,
                        total=1
                    )

                config_path = os.path.join(sim_dir, "simulation_config.json")
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write(sim_params.to_json())

                if progress_callback:
                    progress_callback(
                        "generating_config", 100,
                        "?ㅼ젙 ?앹꽦 ?꾨즺",
                        current=1,
                        total=1
                    )

                return sim_params
            
            # 실시간 저장 경로 설정(기본 우선순위: Reddit JSON)
            if Config.OASIS_PREPARE_PARALLEL_TASKS:
                logger.info(
                    "prepare tasks running in parallel: simulation_id=%s, profiles=%s, config=1",
                    simulation_id,
                    parallel_profile_count,
                )
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    profiles_future = executor.submit(run_profile_generation)
                    config_future = executor.submit(run_config_generation)
                    profiles = profiles_future.result()
                    sim_params = config_future.result()
            else:
                profiles = run_profile_generation()
                sim_params = run_config_generation()

            state.profiles_count = len(profiles)
            state.config_generated = True
            state.config_reasoning = sim_params.generation_reasoning
            state.status = SimulationStatus.READY
            self._save_simulation_state(state)

            logger.info(f"?쒕??덉씠??以鍮??꾨즺: {simulation_id}, "
                       f"entities={state.entities_count}, profiles={state.profiles_count}")

            return state

            realtime_output_path = None
            realtime_platform = "reddit"
            if state.enable_reddit:
                realtime_output_path = os.path.join(sim_dir, "reddit_profiles.json")
                realtime_platform = "reddit"
            elif state.enable_twitter:
                realtime_output_path = os.path.join(sim_dir, "twitter_profiles.csv")
                realtime_platform = "twitter"
            
            profiles = generator.generate_profiles_from_entities(
                entities=filtered.entities,
                use_llm=use_llm_for_profiles,
                progress_callback=profile_progress,
                graph_id=state.graph_id,
                parallel_count=parallel_profile_count,  # 병렬 생성 수
                realtime_output_path=realtime_output_path,  # 실시간 저장 경로
                output_platform=realtime_platform  # 출력 형식
            )
            
            state.profiles_count = len(profiles)
            
            # Profile 파일 저장(Twitter=CSV, Reddit=JSON)
            # Reddit은 생성 중에도 저장되지만 완전성을 위해 한 번 더 저장
            if progress_callback:
                progress_callback(
                    "generating_profiles", 95, 
                    "Profile 파일 저장 중...",
                    current=total_entities,
                    total=total_entities
                )
            
            if state.enable_reddit:
                generator.save_profiles(
                    profiles=profiles,
                    file_path=os.path.join(sim_dir, "reddit_profiles.json"),
                    platform="reddit"
                )
            
            if state.enable_twitter:
                # Twitter는 CSV 형식 필수(OASIS 요구사항)
                generator.save_profiles(
                    profiles=profiles,
                    file_path=os.path.join(sim_dir, "twitter_profiles.csv"),
                    platform="twitter"
                )
            
            if progress_callback:
                progress_callback(
                    "generating_profiles", 100, 
                    f"완료, 총 {len(profiles)}개 Profile",
                    current=len(profiles),
                    total=len(profiles)
                )
            
            # ========== 3단계: LLM 기반 설정 생성 ==========
            if progress_callback:
                progress_callback(
                    "generating_config", 0, 
                    "시뮬레이션 요구사항 분석 중...",
                    current=0,
                    total=3
                )
            
            config_generator = SimulationConfigGenerator()
            
            if progress_callback:
                progress_callback(
                    "generating_config", 30, 
                    "LLM으로 설정 생성 중...",
                    current=1,
                    total=3
                )
            
            sim_params = config_generator.generate_config(
                simulation_id=simulation_id,
                project_id=state.project_id,
                graph_id=state.graph_id,
                simulation_requirement=simulation_requirement,
                document_text=document_text,
                entities=filtered.entities,
                enable_twitter=state.enable_twitter,
                enable_reddit=state.enable_reddit
            )
            
            if progress_callback:
                progress_callback(
                    "generating_config", 70, 
                    "설정 파일 저장 중...",
                    current=2,
                    total=3
                )
            
            # 설정 파일 저장
            config_path = os.path.join(sim_dir, "simulation_config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(sim_params.to_json())
            
            state.config_generated = True
            state.config_reasoning = sim_params.generation_reasoning
            
            if progress_callback:
                progress_callback(
                    "generating_config", 100, 
                    "설정 생성 완료",
                    current=3,
                    total=3
                )
            
            # 실행 스크립트는 backend/scripts/를 그대로 사용(시뮬레이션 디렉터리로 복사하지 않음)
            # simulation_runner가 scripts 디렉터리에서 직접 실행
            
            # 상태 갱신
            state.status = SimulationStatus.READY
            self._save_simulation_state(state)
            
            logger.info(f"시뮬레이션 준비 완료: {simulation_id}, "
                       f"entities={state.entities_count}, profiles={state.profiles_count}")
            
            return state
            
        except Exception as e:
            logger.error(f"시뮬레이션 준비 실패: {simulation_id}, error={str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            state.status = SimulationStatus.FAILED
            state.error = str(e)
            self._save_simulation_state(state)
            raise
    
    def get_simulation(self, simulation_id: str) -> Optional[SimulationState]:
        """시뮬레이션 상태를 조회한다."""
        return self._load_simulation_state(simulation_id)
    
    def list_simulations(self, project_id: Optional[str] = None) -> List[SimulationState]:
        """시뮬레이션 목록을 조회한다."""
        simulations = []
        
        if os.path.exists(self.SIMULATION_DATA_DIR):
            for sim_id in os.listdir(self.SIMULATION_DATA_DIR):
                # 숨김 파일(.DS_Store 등)과 비디렉터리는 건너뜀
                sim_path = os.path.join(self.SIMULATION_DATA_DIR, sim_id)
                if sim_id.startswith('.') or not os.path.isdir(sim_path):
                    continue
                
                state = self._load_simulation_state(sim_id)
                if state:
                    if project_id is None or state.project_id == project_id:
                        simulations.append(state)
        
        # 최신순(이력 API·UI에서 일관되게 보이도록)
        simulations.sort(key=lambda s: s.updated_at or s.created_at or "", reverse=True)
        return simulations
    
    def get_profiles(self, simulation_id: str, platform: str = "reddit") -> List[Dict[str, Any]]:
        """시뮬레이션 Agent Profile을 조회한다."""
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"시뮬레이션이 존재하지 않습니다: {simulation_id}")
        
        sim_dir = self._get_simulation_dir(simulation_id)
        profile_path = os.path.join(sim_dir, f"{platform}_profiles.json")
        
        if not os.path.exists(profile_path):
            return []
        
        with open(profile_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        """시뮬레이션 설정을 조회한다."""
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        
        if not os.path.exists(config_path):
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_run_instructions(self, simulation_id: str) -> Dict[str, str]:
        """실행 안내를 반환한다."""
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts'))
        
        return {
            "simulation_dir": sim_dir,
            "scripts_dir": scripts_dir,
            "config_file": config_path,
            "commands": {
                "twitter": f"python {scripts_dir}/run_twitter_simulation.py --config {config_path}",
                "reddit": f"python {scripts_dir}/run_reddit_simulation.py --config {config_path}",
                "parallel": f"python {scripts_dir}/run_parallel_simulation.py --config {config_path}",
            },
            "instructions": (
                f"1. conda 환경 활성화: conda activate Neofish\n"
                f"2. 시뮬레이션 실행 (스크립트 위치: {scripts_dir})\n"
                f"   - Twitter 단독 실행: python {scripts_dir}/run_twitter_simulation.py --config {config_path}\n"
                f"   - Reddit 단독 실행: python {scripts_dir}/run_reddit_simulation.py --config {config_path}\n"
                f"   - 양 플랫폼 병렬 실행: python {scripts_dir}/run_parallel_simulation.py --config {config_path}"
            )
        }
