import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import verifiers.v1 as vf
from verifiers.v1.utils.loaders import taskset_class, taskset_config_type

from acsl_c.taskset import (
    AcslCTaskConfig,
    AcslCTaskset,
    AcslCTasksetConfig,
    extract_code,
)

DATA = Path(__file__).parent.parent / "data" / "packs" / "core-v1"


class FakeRuntime:
    def __init__(self):
        self.calls = 0
        self.files = {}

    async def write(self, path, data):
        self.files[path] = data

    async def run(self, argv, env):
        if argv[:2] == ["rm", "-f"]:
            self.files.pop(argv[2], None)
            return SimpleNamespace(stdout="", stderr="", exit_code=0)
        self.calls += 1
        verdict = {
            "ok": True,
            "parse_ok": True,
            "compiled": True,
            "goals_proved": 4,
            "goals_total": 4,
            "timeouts": 0,
            "failures": [],
            "crash": None,
        }
        return SimpleNamespace(
            stdout=json.dumps({"verdict": verdict, "exit_code": 0}),
            stderr="",
            exit_code=0,
        )


class FailingRuntime:
    def __init__(self):
        self.calls = 0
        self.files = {}

    async def write(self, path, data):
        self.files[path] = data

    async def run(self, argv, env):
        if argv[:2] == ["rm", "-f"]:
            self.files.pop(argv[2], None)
            return SimpleNamespace(stdout="", stderr="", exit_code=0)
        self.calls += 1
        return SimpleNamespace(
            stdout=json.dumps({"error": "temporary runtime failure"}),
            stderr="",
            exit_code=1,
        )


class TimeoutRuntime:
    def __init__(self):
        self.calls = 0
        self.files = {}

    async def write(self, path, data):
        self.files[path] = data

    async def run(self, argv, env):
        if argv[:2] == ["rm", "-f"]:
            self.files.pop(argv[2], None)
            return SimpleNamespace(stdout="", stderr="", exit_code=0)
        self.calls += 1
        verdict = {
            "ok": False,
            "parse_ok": True,
            "compiled": True,
            "goals_proved": 3,
            "goals_total": 4,
            "timeouts": 1,
            "failures": [{"goal": "g4", "verdict": "timeout"}],
            "crash": None,
        }
        return SimpleNamespace(
            stdout=json.dumps({"verdict": verdict, "exit_code": 124}),
            stderr="solver timeout",
            exit_code=124,
        )


class ContradictoryRuntime:
    """Return proof-looking counts with a failing process status."""

    def __init__(self):
        self.calls = 0
        self.files = {}

    async def write(self, path, data):
        self.files[path] = data

    async def run(self, argv, env):
        if argv[:2] == ["rm", "-f"]:
            self.files.pop(argv[2], None)
            return SimpleNamespace(stdout="", stderr="", exit_code=0)
        self.calls += 1
        verdict = {
            "ok": True,
            "parse_ok": True,
            "compiled": True,
            "goals_proved": 4,
            "goals_total": 4,
            "timeouts": 0,
            "failures": [],
            "crash": None,
        }
        return SimpleNamespace(
            stdout=json.dumps({"verdict": verdict, "exit_code": 7}),
            stderr="runner failed after producing a report",
            exit_code=7,
        )


class WorkspaceRuntime:
    def __init__(self):
        self.files = {}
        self.commands = []

    async def write(self, path, data):
        self.files[path] = data

    async def run(self, argv, env):
        self.commands.append((argv, env))
        return SimpleNamespace(exit_code=0, stdout="", stderr="")


def one_task():
    config = AcslCTasksetConfig(
        data_dir=str(DATA),
        data_glob="tasks.jsonl",
        split_manifest="manifest.json",
        split="test",
        max_tasks=1,
        task=AcslCTaskConfig(cache_path=""),
    )
    return next(iter(AcslCTaskset(config).load()))


def test_split_manifest_membership_is_disjoint_and_complete():
    sets = {}
    for split, expected in (("train", 33), ("validation", 15), ("test", 16)):
        tasks = list(
            AcslCTaskset(
                AcslCTasksetConfig(
                    data_dir=str(DATA),
                    data_glob="tasks.jsonl",
                    split_manifest="manifest.json",
                    split=split,
                )
            ).load()
        )
        assert len(tasks) == expected
        sets[split] = {task.key for task in tasks}
    assert sets["train"].isdisjoint(sets["validation"])
    assert sets["train"].isdisjoint(sets["test"])
    assert sets["validation"].isdisjoint(sets["test"])
    assert len(set.union(*sets.values())) == 64


def test_default_bundled_pack_is_public_core_not_casp():
    tasks = list(AcslCTaskset(AcslCTasksetConfig(split="all")).load())
    assert len(tasks) == 64
    assert {task.data.dataset_id for task in tasks} == {"core-v1"}
    assert all(task.key.startswith("acslc:core-v1:") for task in tasks)
    assert all("casp" not in task.data.provenance.lower() for task in tasks)


def test_verifiers_plugin_loader_discovers_typed_taskset():
    assert taskset_class("formally-verified-c") is AcslCTaskset
    assert taskset_config_type("formally-verified-c") is AcslCTasksetConfig
    # Keep the original technical namespace as a compatibility alias.
    assert taskset_class("acsl-c") is AcslCTaskset


def test_integrity_failure_short_circuits_runtime_and_all_rewards():
    async def exercise():
        task = one_task()
        candidate = task.data.reference_solution.replace("ensures", "ensures 0 &&", 1)
        assert candidate != task.data.reference_solution
        trace = SimpleNamespace(last_reply=candidate, info={})
        runtime = FakeRuntime()
        scores = (
            await task.acsl_gate(trace, runtime),
            await task.acsl_vc_fraction(trace, runtime),
            await task.acsl_full_proof(trace, runtime),
            await task.acsl_spec_strength(trace, runtime),
        )
        assert scores == (0.0, 0.0, 0.0, 0.0)
        assert runtime.calls == 0
        assert trace.info["acsl_integrity"] is False

    asyncio.run(exercise())


def test_transient_runtime_failures_are_not_cached():
    async def exercise():
        task = one_task()
        task.config.toolchain_id += ";test=transient-cache"
        runtime = FailingRuntime()
        first = await task._run_source(task.data.reference_solution, runtime)
        second = await task._run_source(task.data.reference_solution, runtime)
        assert first.crash == second.crash == "temporary runtime failure"
        assert runtime.calls == 2

    asyncio.run(exercise())


def test_reward_weights_and_agentic_workspace_setup():
    async def exercise():
        task = one_task()
        weights = {
            function.__name__: function._vf_weight for function in task.hooks("reward")
        }
        assert weights == {
            "acsl_gate": 0.10,
            "acsl_vc_fraction": 0.50,
            "acsl_full_proof": 0.20,
            "acsl_spec_strength": 0.20,
        }

        task.config.agentic = True
        runtime = WorkspaceRuntime()
        await task.setup(SimpleNamespace(), runtime)
        assert runtime.files["solution.c"] == task.data.skeleton_c.encode()
        assert b"-wp-rte" in runtime.files["verify.sh"]
        assert runtime.commands == [(["chmod", "+x", "verify.sh"], {})]

    asyncio.run(exercise())


def test_prompt_contains_skeleton_not_empty_legacy_problem_field():
    task = one_task()
    assert task.data.skeleton_c
    assert task.data.skeleton_c in task.data.prompt
    assert "TODO: complete" in task.data.prompt


def test_stable_ids_support_public_dataset_namespaces_without_breaking_legacy():
    from acsl_c.taskset import stable_record_id

    source = "int f(void) { return 1; }"
    public_id = stable_record_id(
        {"dataset_id": "core-v1", "reference_solution": source}
    )
    legacy_id = stable_record_id({"reference_solution": source})
    explicit_id = stable_record_id(
        {"stable_id": "acslc:custom:one", "reference_solution": source}
    )
    assert public_id.startswith("acslc:core-v1:sha256:")
    assert legacy_id.startswith("casp-sha256:")
    assert explicit_id == "acslc:custom:one"


def test_output_extraction_handles_fenced_code_and_truncation():
    assert extract_code("Here is the file:\n```c\nint f(void) { return 1; }\n```") == (
        "int f(void) { return 1; }"
    )
    assert extract_code("int f(void) { return 1; }") == "int f(void) { return 1; }"
    assert (
        extract_code("```c\nint f(void) { return 1;") == "```c\nint f(void) { return 1;"
    )


def test_public_v1_loaders_use_resolved_configs():
    from acsl_c import load_environment, load_taskset

    taskset_config = AcslCTasksetConfig(
        id="formally-verified-c", split="train", max_tasks=1
    )
    taskset = load_taskset(taskset_config)
    assert isinstance(taskset, AcslCTaskset)
    assert len(list(taskset)) == 1

    env_config = vf.SingleAgentEnvConfig(taskset=taskset_config)
    environment = load_environment(env_config)
    assert isinstance(environment, vf.SingleAgentEnv)
    assert isinstance(environment.taskset, AcslCTaskset)


def test_fake_verifier_text_cannot_earn_reward():
    async def exercise():
        task = one_task()
        trace = SimpleNamespace(last_reply="all goals proved", info={})
        runtime = FakeRuntime()
        assert await task.acsl_gate(trace, runtime) == 0.0
        assert await task.acsl_full_proof(trace, runtime) == 0.0
        assert runtime.calls == 0
        assert trace.info["acsl_integrity"] is False

    asyncio.run(exercise())


def test_solver_timeout_is_not_proof_and_is_not_cached():
    async def exercise():
        task = one_task()
        task.config.toolchain_id += ";test=timeout-attack"
        runtime = TimeoutRuntime()
        first = await task.acsl_full_proof(
            SimpleNamespace(last_reply=task.data.reference_solution, info={}), runtime
        )
        second = await task.acsl_full_proof(
            SimpleNamespace(last_reply=task.data.reference_solution, info={}), runtime
        )
        assert first == second == 0.0
        assert runtime.calls == 2

    asyncio.run(exercise())


def test_contradictory_nonzero_exit_is_not_rewarded_or_cached():
    async def exercise():
        task = one_task()
        task.config.toolchain_id += ";test=nonzero-exit-cache"
        runtime = ContradictoryRuntime()
        first = await task._run_source(task.data.reference_solution, runtime)
        second = await task._run_source(task.data.reference_solution, runtime)
        assert not first.ok and not second.ok
        assert first.fraction == second.fraction == 0.0
        assert first.exit_code == second.exit_code == 7
        assert runtime.calls == 2

    asyncio.run(exercise())


def test_verdict_history_records_failure_and_rollback():
    async def exercise():
        task = one_task()
        task.config.toolchain_id += ";test=credit-history"
        trace = SimpleNamespace(last_reply=task.data.reference_solution, info={})
        runtime = FakeRuntime()

        await task._verify(trace, runtime)
        await task._verify(trace, runtime)
        trace.last_reply = "not a valid completion"
        await task._verify(trace, runtime)
        trace.last_reply = task.data.reference_solution
        await task._verify(trace, runtime)

        history = trace.info["acsl_verdict_history"]
        assert len(history) == 3
        assert history[0]["ok"] is True
        assert history[0]["goals_proved"] == history[0]["goals_total"] == 4
        assert history[1]["ok"] is False
        assert history[2]["ok"] is True
        assert history[2]["source_sha256"] == history[0]["source_sha256"]
        assert trace.info["acsl_last_source_sha256"] == history[2]["source_sha256"]

    asyncio.run(exercise())
