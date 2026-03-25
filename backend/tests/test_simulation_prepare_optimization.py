import json
import threading

from app.services import oasis_profile_generator as profile_module
from app.services import simulation_manager as simulation_manager_module
from app.services.entity_types import EntityNode, FilteredEntities
from app.services.oasis_profile_generator import OasisAgentProfile, OasisProfileGenerator
from app.services.simulation_manager import SimulationManager, SimulationState, SimulationStatus


def _entity(index: int, entity_type: str = "Person") -> EntityNode:
    return EntityNode(
        uuid=f"entity-{index}",
        name=f"Entity {index}",
        labels=["Entity", entity_type],
        summary=f"Summary {index}",
        attributes={},
        related_edges=[],
        related_nodes=[],
    )


def _profile(index: int, entity: EntityNode) -> OasisAgentProfile:
    return OasisAgentProfile(
        user_id=index,
        user_name=f"user_{index}",
        name=entity.name,
        bio=f"bio {index}",
        persona=f"persona {index}",
        source_entity_uuid=entity.uuid,
        source_entity_type=entity.get_entity_type(),
    )


def test_profile_generation_throttles_realtime_writes(tmp_path, monkeypatch):
    generator = OasisProfileGenerator(
        api_key="test-key",
        base_url="http://localhost",
        model_name="test-model",
    )
    generator.verbose_profile_logging = False
    generator.realtime_save_every = 2
    generator.realtime_save_min_interval_seconds = 0.0

    dump_calls = []
    original_dump = profile_module.json.dump

    def counting_dump(*args, **kwargs):
        dump_calls.append(1)
        return original_dump(*args, **kwargs)

    def fake_generate_profile(self, entity, user_id, use_llm=True):
        return _profile(user_id, entity)

    monkeypatch.setattr(profile_module.json, "dump", counting_dump)
    monkeypatch.setattr(
        OasisProfileGenerator,
        "generate_profile_from_entity",
        fake_generate_profile,
    )

    profiles = generator.generate_profiles_from_entities(
        entities=[_entity(index) for index in range(5)],
        use_llm=False,
        parallel_count=1,
        realtime_output_path=str(tmp_path / "profiles.json"),
        output_platform="reddit",
    )

    assert len(profiles) == 5
    assert len(dump_calls) == 3

    saved_profiles = json.loads((tmp_path / "profiles.json").read_text(encoding="utf-8"))
    assert len(saved_profiles) == 5


def test_prepare_simulation_runs_profile_and_config_generation_in_parallel(tmp_path, monkeypatch):
    profile_started = threading.Event()
    config_started = threading.Event()
    allow_finish = threading.Event()
    result_box = {}

    class DummyReader:
        def filter_defined_entities(self, graph_id, defined_entity_types=None, enrich_with_edges=True):
            entities = [_entity(0), _entity(1)]
            return FilteredEntities(
                entities=entities,
                entity_types={"Person"},
                total_count=len(entities),
                filtered_count=len(entities),
            )

    class DummyProfileGenerator:
        def __init__(self, graph_id=None):
            self.graph_id = graph_id

        def generate_profiles_from_entities(self, entities, **kwargs):
            profile_started.set()
            assert config_started.wait(timeout=1.0)
            assert allow_finish.wait(timeout=2.0)
            progress_callback = kwargs.get("progress_callback")
            if progress_callback:
                progress_callback(len(entities), len(entities), "profiles ready")
            return [_profile(index, entity) for index, entity in enumerate(entities)]

        def save_profiles(self, profiles, file_path, platform="reddit"):
            if platform == "reddit":
                data = [profile.to_reddit_format() for profile in profiles]
                with open(file_path, "w", encoding="utf-8") as file:
                    json.dump(data, file, ensure_ascii=False, indent=2)
                return

            with open(file_path, "w", encoding="utf-8", newline="") as file:
                file.write("user_id,username\n")
                for profile in profiles:
                    file.write(f"{profile.user_id},{profile.user_name}\n")

    class DummySimParams:
        generation_reasoning = "parallel-config"

        def to_json(self):
            return json.dumps({"status": "ok"})

    class DummyConfigGenerator:
        def generate_config(self, **kwargs):
            config_started.set()
            assert profile_started.wait(timeout=1.0)
            assert allow_finish.wait(timeout=2.0)
            progress_callback = kwargs.get("progress_callback")
            if progress_callback:
                progress_callback(1, 1, "config ready")
            return DummySimParams()

    manager = SimulationManager()
    state = SimulationState(
        simulation_id="sim_parallel",
        project_id="proj_parallel",
        graph_id="graph_parallel",
        enable_twitter=False,
        enable_reddit=True,
    )
    simulation_dir = tmp_path / state.simulation_id
    simulation_dir.mkdir()

    monkeypatch.setattr(simulation_manager_module, "get_entity_reader", lambda: DummyReader())
    monkeypatch.setattr(simulation_manager_module, "OasisProfileGenerator", DummyProfileGenerator)
    monkeypatch.setattr(simulation_manager_module, "SimulationConfigGenerator", DummyConfigGenerator)
    monkeypatch.setattr(simulation_manager_module.Config, "OASIS_PREPARE_PARALLEL_TASKS", True)
    monkeypatch.setattr(manager, "_load_simulation_state", lambda simulation_id: state)
    monkeypatch.setattr(manager, "_save_simulation_state", lambda current_state: None)
    monkeypatch.setattr(manager, "_get_simulation_dir", lambda simulation_id: str(simulation_dir))

    def run_prepare():
        result_box["state"] = manager.prepare_simulation(
            simulation_id=state.simulation_id,
            simulation_requirement="run a fast scenario",
            document_text="document",
            use_llm_for_profiles=False,
            parallel_profile_count=2,
        )

    worker = threading.Thread(target=run_prepare)
    worker.start()

    assert profile_started.wait(timeout=1.0)
    assert config_started.wait(timeout=1.0)

    allow_finish.set()
    worker.join(timeout=3.0)

    assert not worker.is_alive()
    assert result_box["state"].status == SimulationStatus.READY
    assert (simulation_dir / "reddit_profiles.json").exists()
    assert (simulation_dir / "simulation_config.json").exists()
