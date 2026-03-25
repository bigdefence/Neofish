import json
import threading
from pathlib import Path

import app.services.simulation_manager as simulation_manager_module
import app.services.oasis_profile_generator as oasis_profile_generator_module
from app.config import Config
from app.services.entity_types import EntityNode, FilteredEntities
from app.services.oasis_profile_generator import OasisAgentProfile, OasisProfileGenerator
from app.services.simulation_manager import SimulationManager, SimulationStatus


def _entity(name: str, entity_type: str = "Company") -> EntityNode:
    return EntityNode(
        uuid=f"uuid_{name}",
        name=name,
        labels=["Entity", entity_type],
        summary=f"{name} summary",
        attributes={},
        related_edges=[],
        related_nodes=[],
    )


class _DummyReader:
    def __init__(self, filtered: FilteredEntities):
        self._filtered = filtered

    def filter_defined_entities(self, **kwargs) -> FilteredEntities:
        return self._filtered


class _DummyProfile:
    def __init__(self, name: str):
        self.name = name

    def to_reddit_format(self):
        return {"name": self.name}

    def to_twitter_format(self):
        return {"name": self.name}


def test_prepare_simulation_runs_profiles_and_config_in_parallel(tmp_path, monkeypatch):
    entity = _entity("NVIDIA")
    filtered = FilteredEntities(
        entities=[entity],
        entity_types={"Company"},
        total_count=1,
        filtered_count=1,
    )
    sync = {
        "profiles_started": threading.Event(),
        "config_started": threading.Event(),
    }

    class FakeProfileGenerator:
        def __init__(self, graph_id=None, **kwargs):
            self.graph_id = graph_id

        def generate_profiles_from_entities(self, entities, **kwargs):
            sync["profiles_started"].set()
            assert sync["config_started"].wait(0.5)
            return [_DummyProfile(item.name) for item in entities]

        def save_profiles(self, profiles, file_path, platform="reddit"):
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            if platform == "reddit":
                path.write_text(json.dumps([p.to_reddit_format() for p in profiles]), encoding="utf-8")
            else:
                path.write_text("name\n" + "\n".join(p.name for p in profiles), encoding="utf-8")

    class FakeSimulationParams:
        generation_reasoning = "parallel prepare test"

        def to_json(self):
            return json.dumps({"ok": True})

    class FakeConfigGenerator:
        def generate_config(self, **kwargs):
            sync["config_started"].set()
            assert sync["profiles_started"].wait(0.5)
            return FakeSimulationParams()

    SimulationManager._instance = None
    SimulationManager._simulations = {}
    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(Config, "OASIS_PREPARE_PARALLEL_TASKS", True)
    monkeypatch.setattr(simulation_manager_module, "get_entity_reader", lambda: _DummyReader(filtered))
    monkeypatch.setattr(simulation_manager_module, "OasisProfileGenerator", FakeProfileGenerator)
    monkeypatch.setattr(simulation_manager_module, "SimulationConfigGenerator", FakeConfigGenerator)

    manager = SimulationManager()
    state = manager.create_simulation(project_id="project-1", graph_id="graph-1")
    result = manager.prepare_simulation(
        simulation_id=state.simulation_id,
        simulation_requirement="predict demand",
        document_text="document",
        use_llm_for_profiles=False,
    )

    sim_dir = Path(tmp_path) / state.simulation_id

    assert result.status == SimulationStatus.READY
    assert result.profiles_count == 1
    assert result.config_generated is True
    assert result.config_reasoning == "parallel prepare test"
    assert sync["profiles_started"].is_set()
    assert sync["config_started"].is_set()
    assert (sim_dir / "simulation_config.json").exists()
    assert (sim_dir / "reddit_profiles.json").exists()
    assert (sim_dir / "twitter_profiles.csv").exists()


def test_generate_profiles_skips_verbose_profile_print_by_default(monkeypatch):
    class DummyOpenAI:
        def __init__(self, **kwargs):
            pass

    monkeypatch.setattr(Config, "OASIS_PROFILE_VERBOSE_LOGGING", False)
    monkeypatch.setattr(oasis_profile_generator_module, "OpenAI", DummyOpenAI)

    generator = OasisProfileGenerator(
        api_key="test-key",
        base_url="http://localhost",
        model_name="test-model",
    )
    entity = _entity("AMD")
    profile = OasisAgentProfile(
        user_id=0,
        user_name="amd_001",
        name="AMD",
        bio="bio",
        persona="persona",
    )
    printed = []

    monkeypatch.setattr(
        generator,
        "generate_profile_from_entity",
        lambda entity, user_id, use_llm=True: profile,
    )
    monkeypatch.setattr(
        generator,
        "_print_generated_profile",
        lambda *args, **kwargs: printed.append(True),
    )

    results = generator.generate_profiles_from_entities(
        entities=[entity],
        use_llm=False,
        parallel_count=1,
    )

    assert len(results) == 1
    assert printed == []
