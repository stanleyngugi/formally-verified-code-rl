from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import random
import re
import secrets
from pathlib import Path
from typing import ClassVar

import verifiers.v1 as vf
from pydantic import Field
from verifiers.v1.configs.task import TaskConfig
from verifiers.v1.runtimes import Runtime
from verifiers.v1.state import State
from verifiers.v1.task import Task, TaskData, TaskResources, TaskTimeout
from verifiers.v1.taskset import Taskset
from verifiers.v1.trace import Trace
from verifiers.v1.utils.decorators import metric, reward

from acsl_c import framac
from acsl_c.cache import VerdictCache, verification_key
from acsl_c.integrity import IntegrityResult, check_fixed_task_integrity
from acsl_c.provenance import validate_record_provenance
from acsl_c.spectests import spec_strength_score

WEIGHT_GATE = 0.10
WEIGHT_VC_FRACTION = 0.50
WEIGHT_FULL_PROOF = 0.20
WEIGHT_SPEC_STRENGTH = 0.20
DEFAULT_TOOLCHAIN_ID = (
    "frama-c=33.0;why3=1.8.2;alt-ergo=2.6.3;z3=4.8.12;acsl-c-runner=3"
)
VERIFY_SCRIPT = (Path(__file__).with_name("verify_script.py")).read_text(
    encoding="utf-8"
)
VERIFY_SCRIPT_ID = hashlib.sha256(VERIFY_SCRIPT.encode("utf-8")).hexdigest()

SYSTEM_HINTS = (
    "You are an expert in formally verified C programming using ACSL. Complete only "
    "the target function body. Every annotation, declaration, include, signature, and "
    "all other code must remain unchanged. The result must discharge every Frama-C "
    "WP+RTE proof obligation. Output only the complete contents of solution.c."
)
SYSTEM_FULL = (
    "You are an expert in formally verified C programming. Write complete C code with "
    "strong ACSL contracts and all annotations required by Frama-C WP+RTE. Output only "
    "the complete contents of a .c file."
)
SYSTEM_AGENTIC = (
    "You are a coding agent working on formally verified C. The task is already in "
    "solution.c. Edit only the target function body; changing annotations, signatures, "
    "includes, or other code makes the reward zero. Run ./verify.sh after edits. Use its "
    "failed proof obligations as feedback and finish only when it reports every goal proved."
)

FENCE_RE = re.compile(r"```[a-zA-Z0-9_+-]*\s*\n([\s\S]*?)```")


def extract_code(text: str) -> str:
    match = FENCE_RE.search(text or "")
    return (match.group(1) if match else (text or "")).strip()


def stable_record_id(record: dict) -> str:
    explicit = record.get("stable_id")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    source = record.get("reference_solution") or record.get("skeleton_c") or ""
    digest = hashlib.sha256(source.replace("\r\n", "\n").encode("utf-8")).hexdigest()
    dataset_id = record.get("dataset_id")
    if isinstance(dataset_id, str) and dataset_id.strip():
        namespace = re.sub(r"[^a-z0-9.-]+", "-", dataset_id.strip().lower()).strip("-")
        if namespace:
            return f"acslc:{namespace}:sha256:{digest}"
    # Preserve existing CASP manifest IDs for explicitly supplied legacy data
    # directories. New public packs always declare dataset_id or stable_id.
    return f"casp-sha256:{digest}"


def _legacy_non_vacuous(record: dict) -> bool:
    """Interpret both corrected schema-v2 and the original inverted field."""
    value = record.get("non_vacuous")
    if int(record.get("data_schema_version", 1)) >= 2:
        return value is True
    # Schema v1 accidentally stored the result of `is_vacuous` under this name.
    return value is False


class AcslCData(TaskData):
    stable_id: str
    mode: str = "hints"
    skeleton_c: str | None = Field(default=None)
    reference_solution: str | None = Field(default=None)
    has_spectests: bool = False
    spectests: list[dict] | None = Field(default=None)
    vc_estimate: int = 0
    difficulty_bucket: str = "unknown"
    features: list[str] = Field(default_factory=list)
    provenance: str = "unknown"
    non_vacuous: bool = False
    dataset_id: str = "unknown"
    dataset_version: str = "unknown"
    source_kind: str = "unknown"
    source_repository_url: str = "unknown"
    source_revision: str = "unknown"
    source_path: str = "unknown"
    source_content_sha256: str = "unknown"
    license_spdx: str = "unknown"
    copyright_notice: str = "unknown"
    transformation_description: str = "unknown"
    semantic_family: str = "unknown"
    derivation_family: str = "unknown"
    review_status: str = "unknown"


class AcslCTaskConfig(TaskConfig):
    framac_bin: str = "frama-c"
    provers: str = "alt-ergo,z3"
    wp_timeout: int = 20
    toolchain_id: str = DEFAULT_TOOLCHAIN_ID
    cache_path: str = "/tmp/acsl-c-cache/verdicts.sqlite3"
    agentic: bool = False
    workspace_file: str = "solution.c"
    missing_spectests_score: float = 0.0


class AcslCTask(Task[AcslCData, State, AcslCTaskConfig]):
    # Frama-C executes untrusted model-generated C and its preprocessor directives.
    # Production compilation must therefore reject a host subprocess runtime.
    NEEDS_CONTAINER = True
    _memory_cache: ClassVar[dict[str, framac.Verdict]] = {}

    def __init__(self, data: AcslCData, config: AcslCTaskConfig | None = None) -> None:
        super().__init__(data, config)
        self._verify_lock = asyncio.Lock()

    @property
    def key(self) -> str:
        return self.data.stable_id

    async def setup(self, trace: Trace, runtime: Runtime) -> None:
        if not self.config.agentic:
            return
        if not self.data.skeleton_c:
            raise ValueError("agentic mode requires skeleton_c")
        await runtime.write(
            self.config.workspace_file,
            self.data.skeleton_c.encode("utf-8"),
        )
        verify_command = (
            "#!/usr/bin/env bash\n"
            "set -u\n"
            f"{self.config.framac_bin} -wp -wp-rte -wp-prover "
            f"{self.config.provers} -wp-timeout {self.config.wp_timeout} "
            "-wp-cache none "
            f"{self.config.workspace_file}\n"
        )
        await runtime.write("verify.sh", verify_command.encode("utf-8"))
        result = await runtime.run(["chmod", "+x", "verify.sh"], {})
        if result.exit_code != 0:
            raise RuntimeError(f"could not prepare verify.sh: {result.stderr[-500:]}")

    async def _completion_source(self, trace: Trace, runtime: Runtime) -> str:
        if self.config.agentic:
            try:
                payload = await runtime.read(
                    self.config.workspace_file, max_bytes=2_000_000
                )
            # Runtime adapters can raise implementation-specific exceptions;
            # convert all of them into a non-scoring workspace-read result.
            except Exception as exc:  # noqa: BLE001
                return f"/* workspace read failed: {type(exc).__name__}: {exc} */"
            return payload.decode("utf-8", errors="replace").strip()
        return extract_code(trace.last_reply)

    def _integrity(self, source: str) -> IntegrityResult:
        if self.data.mode != "hints":
            return IntegrityResult(True, True, True)
        if not self.data.skeleton_c:
            return IntegrityResult(False, False, False, "missing fixed skeleton")
        return check_fixed_task_integrity(source, self.data.skeleton_c)

    async def _run_source(self, source: str, runtime: Runtime) -> framac.Verdict:
        key = verification_key(
            source,
            toolchain_id=self.config.toolchain_id,
            provers=self.config.provers,
            timeout=self.config.wp_timeout,
            # A changed runner must not reuse a verdict produced by the old
            # subprocess/parser policy, even if the human toolchain label was
            # not bumped at the same time.
            runner_id=VERIFY_SCRIPT_ID,
        )
        cached = self._memory_cache.get(key)
        if cached is not None:
            return cached

        cache = VerdictCache(self.config.cache_path) if self.config.cache_path else None
        if cache is not None:
            try:
                cached = await asyncio.to_thread(cache.get, key)
            except Exception:  # noqa: BLE001
                cached = None
            if cached is not None:
                self._memory_cache[key] = cached
                return cached

        encoded = base64.b64encode(source.encode("utf-8")).decode("ascii")
        env = {
            "FRAMAC_BIN": self.config.framac_bin,
            "ACSL_PROVERS": self.config.provers,
            "ACSL_TIMEOUT": str(self.config.wp_timeout),
        }
        try:
            # The verifier runner has no third-party dependencies. Execute it
            # with the image's pinned system Python instead of run_uv_script:
            # Verifiers' generic PEP-723 preparation upgrades uv at runtime,
            # which unnecessarily requires network/package-manager privileges
            # and fails correctly hardened, unprivileged judge images.
            runner_path = f"/tmp/acslc-verify-{secrets.token_hex(16)}.py"
            await runtime.write(runner_path, VERIFY_SCRIPT.encode("utf-8"))
            try:
                result = await runtime.run(["python3", runner_path, encoded], env)
            finally:
                await runtime.run(["rm", "-f", runner_path], {})
            verdict = framac.from_runner_output(
                result.stdout, exit_code=result.exit_code
            )
            if result.stderr and not verdict.stderr_tail:
                verdict.stderr_tail = result.stderr[-2000:]
        # A verifier/runtime failure must become an explicit failed verdict,
        # never escape the reward coroutine and crash the rollout.
        except Exception as exc:  # noqa: BLE001
            verdict = framac.Verdict(
                ok=False,
                crash=f"{type(exc).__name__}: {exc}",
            )
        # Do not fossilize transient infrastructure failures or solver timeouts.
        # Complete reports without timeouts are deterministic enough for reuse
        # under the fully keyed toolchain policy.
        cacheable = verdict.progress_eligible and verdict.timeouts == 0
        if cacheable:
            self._memory_cache[key] = verdict
        if cache is not None and cacheable:
            try:
                await asyncio.to_thread(cache.put, key, verdict)
            # Cache persistence is best-effort and must not affect scoring.
            except Exception:  # noqa: BLE001, S110
                pass
        return verdict

    async def _verify(
        self, trace: Trace, runtime: Runtime
    ) -> tuple[str, framac.Verdict]:
        source = await self._completion_source(trace, runtime)
        # Reject a changed problem statement before any model-controlled source
        # reaches Frama-C or its C preprocessor. This is both cheaper and safer.
        if not self._integrity(source).ok:
            verdict = framac.Verdict(ok=False)
        else:
            async with self._verify_lock:
                verdict = await self._run_source(source, runtime)
        info = getattr(trace, "info", None)
        if isinstance(info, dict):
            # Keep a compact, deduplicated state trace for credit-assignment
            # diagnostics. Reward hooks call _verify independently, so without
            # deduplication a single turn would appear four times merely because
            # the reward has four components. The source digest is intentionally
            # recorded even for integrity failures: a later audit can identify
            # the exact edit that caused a zero reward without storing the full
            # model output in the trace metadata.
            source_digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
            transition = {
                "source_sha256": source_digest,
                "goals_proved": verdict.goals_proved,
                "goals_total": verdict.goals_total,
                "timeouts": verdict.timeouts,
                "crash": verdict.crash,
                "parse_ok": verdict.parse_ok,
                "ok": verdict.ok,
            }
            history = info.setdefault("acsl_verdict_history", [])
            if not history or history[-1] != transition:
                history.append(transition)
            info["acsl_last_source_sha256"] = source_digest
            info["acsl_goals"] = f"{verdict.goals_proved}/{verdict.goals_total}"
            info["acsl_timeouts"] = verdict.timeouts
            info["acsl_crash"] = verdict.crash
            info["acsl_failures"] = verdict.failures
        return source, verdict

    async def _eligible_verdict(
        self, trace: Trace, runtime: Runtime
    ) -> tuple[str, framac.Verdict, IntegrityResult]:
        source, verdict = await self._verify(trace, runtime)
        integrity = self._integrity(source)
        info = getattr(trace, "info", None)
        if isinstance(info, dict):
            info["acsl_integrity"] = integrity.ok
            info["acsl_integrity_reason"] = integrity.reason
        return source, verdict, integrity

    @reward(weight=WEIGHT_GATE)
    async def acsl_gate(self, trace: Trace, runtime: Runtime) -> float:
        _, verdict, integrity = await self._eligible_verdict(trace, runtime)
        return float(integrity.ok and verdict.progress_eligible)

    @reward(weight=WEIGHT_VC_FRACTION)
    async def acsl_vc_fraction(self, trace: Trace, runtime: Runtime) -> float:
        _, verdict, integrity = await self._eligible_verdict(trace, runtime)
        return verdict.fraction if integrity.ok else 0.0

    @reward(weight=WEIGHT_FULL_PROOF)
    async def acsl_full_proof(self, trace: Trace, runtime: Runtime) -> float:
        _, verdict, integrity = await self._eligible_verdict(trace, runtime)
        return float(integrity.ok and verdict.ok)

    @reward(weight=WEIGHT_SPEC_STRENGTH)
    async def acsl_spec_strength(self, trace: Trace, runtime: Runtime) -> float:
        source, verdict, integrity = await self._eligible_verdict(trace, runtime)
        if not integrity.ok:
            return 0.0
        return spec_strength_score(
            source,
            mode=self.data.mode,
            skeleton_c=self.data.skeleton_c,
            has_spectests=self.data.has_spectests,
            spectests=self.data.spectests,
            verdict=verdict,
            missing_spectests_score=self.config.missing_spectests_score,
        )

    @metric()
    async def acsl_crashed(self, trace: Trace, runtime: Runtime) -> float:
        _, verdict = await self._verify(trace, runtime)
        return float(verdict.crash is not None)

    @metric()
    async def acsl_timeout_count(self, trace: Trace, runtime: Runtime) -> float:
        _, verdict = await self._verify(trace, runtime)
        return float(verdict.timeouts)

    async def validate(self, runtime: Runtime) -> bool:
        if not self.data.reference_solution:
            return False
        verdict = await self._run_source(self.data.reference_solution, runtime)
        return verdict.ok


class AcslCTasksetConfig(vf.TasksetConfig):
    # Public installs default to a named, provenance-checked pack. Research
    # corpora such as CASP must be supplied through an explicit data_dir and are
    # never discovered or bundled implicitly.
    data_dir: str = ""
    data_pack: str = "core-v1"
    data_glob: str = "*.jsonl"
    split_manifest: str = "manifest.json"
    split: str = "train"
    max_tasks: int | None = None
    seed: int = 20260909
    shuffle: bool = False
    curriculum: str = "none"
    require_non_vacuous: bool = True
    allow_full_mode: bool = False
    task: AcslCTaskConfig = AcslCTaskConfig()


class AcslCTaskset(Taskset[AcslCTask, AcslCTasksetConfig]):
    def load(self):
        records = self._load_jsonl_records()
        records = self._select_split(records)
        if self.config.require_non_vacuous:
            records = [record for record in records if _legacy_non_vacuous(record)]
        if not self.config.allow_full_mode:
            records = [
                record for record in records if record.get("mode", "hints") == "hints"
            ]
        if self.config.curriculum == "easy-to-hard":
            records.sort(
                key=lambda record: (
                    int(record.get("vc_estimate", 0)),
                    stable_record_id(record),
                )
            )
        elif self.config.curriculum != "none":
            raise ValueError("curriculum must be 'none' or 'easy-to-hard'")
        if self.config.shuffle:
            random.Random(self.config.seed).shuffle(records)
        if self.config.max_tasks is not None:
            records = records[: self.config.max_tasks]

        for index, record in enumerate(records):
            mode = record.get("mode", "hints")
            if self.config.task.agentic:
                prompt = (
                    "Open solution.c, replace its TODO with a verified implementation, and use "
                    "./verify.sh until all proof obligations are discharged."
                )
                system_prompt = SYSTEM_AGENTIC
            elif mode == "full":
                prompt = (
                    "Write C with strong ACSL annotations satisfying this specification:\n\n"
                    + record.get("problem", "")
                )
                system_prompt = SYSTEM_FULL
            else:
                prompt = (
                    "Complete only the target body in this file so every annotation verifies. "
                    "Do not change anything outside that body:\n\n```c\n"
                    + record.get("skeleton_c", "")
                    + "\n```"
                )
                system_prompt = SYSTEM_HINTS
            record_id = stable_record_id(record)
            yield AcslCTask(
                AcslCData(
                    idx=index,
                    stable_id=record_id,
                    name=f"acsl-{record_id[-12:]}",
                    prompt=prompt,
                    system_prompt=system_prompt,
                    mode=mode,
                    skeleton_c=record.get("skeleton_c"),
                    reference_solution=record.get("reference_solution"),
                    has_spectests=bool(record.get("spectests")),
                    spectests=record.get("spectests"),
                    vc_estimate=int(record.get("vc_estimate", 0)),
                    difficulty_bucket=record.get("difficulty_bucket", "unknown"),
                    features=list(record.get("features", [])),
                    provenance=record.get("provenance", "unknown"),
                    non_vacuous=_legacy_non_vacuous(record),
                    dataset_id=record.get("dataset_id", "unknown"),
                    dataset_version=record.get("dataset_version", "unknown"),
                    source_kind=record.get("source_kind", "unknown"),
                    source_repository_url=record.get(
                        "source_repository_url", "unknown"
                    ),
                    source_revision=record.get("source_revision", "unknown"),
                    source_path=record.get("source_path", "unknown"),
                    source_content_sha256=record.get(
                        "source_content_sha256", "unknown"
                    ),
                    license_spdx=record.get("license_spdx", "unknown"),
                    copyright_notice=record.get("copyright_notice", "unknown"),
                    transformation_description=record.get(
                        "transformation_description", "unknown"
                    ),
                    semantic_family=record.get("semantic_family", "unknown"),
                    derivation_family=record.get("derivation_family", "unknown"),
                    review_status=record.get("review_status", "unknown"),
                    resources=TaskResources(cpu=2, memory=4),
                    timeout=TaskTimeout(
                        scoring=float(self.config.task.wp_timeout * 12 + 90)
                    ),
                    network_allow=[],
                ),
                self.config.task,
            )

    def _load_jsonl_records(self) -> list[dict]:
        root = self._data_root()
        records: list[dict] = []
        seen: set[str] = set()
        for path in sorted(root.glob(self.config.data_glob)):
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                record.setdefault("provenance", path.name)
                record["_source_file"] = path.name
                if not self.config.data_dir:
                    issues = validate_record_provenance(record)
                    if issues:
                        rendered = "; ".join(
                            f"{issue.field}: {issue.message}" for issue in issues[:5]
                        )
                        raise ValueError(
                            f"invalid bundled public record in {path}: {rendered}"
                        )
                record_id = stable_record_id(record)
                if record_id in seen:
                    continue
                seen.add(record_id)
                records.append(record)
        return records

    def _select_split(self, records: list[dict]) -> list[dict]:
        split = "validation" if self.config.split == "eval" else self.config.split
        if split == "all":
            return records
        manifest_path = self._data_root() / self.config.split_manifest
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            try:
                selected = set(manifest["splits"][split])
            except KeyError as exc:
                raise ValueError(f"unknown split {split!r} in {manifest_path}") from exc
            return [
                record for record in records if stable_record_id(record) in selected
            ]
        # Compatibility for old data directories. New research runs require a manifest.
        marker = "casp_eval.jsonl" if split == "validation" else "casp_train.jsonl"
        return [record for record in records if record.get("_source_file") == marker]

    def _data_root(self) -> Path:
        if self.config.data_dir:
            return Path(self.config.data_dir)
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]*", self.config.data_pack):
            raise ValueError(
                "data_pack must contain only lowercase letters, digits, dots, and hyphens"
            )
        bundled = Path(__file__).with_name("data") / "packs" / self.config.data_pack
        if bundled.is_dir():
            return bundled
        editable = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "packs"
            / self.config.data_pack
        )
        if editable.is_dir():
            return editable
        raise FileNotFoundError(
            f"ACSL-C data pack {self.config.data_pack!r} is not bundled; "
            "select an installed pack or set taskset.data_dir explicitly for research data"
        )


def load_taskset(config: AcslCTasksetConfig) -> AcslCTaskset:
    """Construct the reusable v1 taskset from its framework-resolved config."""
    return AcslCTaskset(config)


def load_environment(config: vf.EnvConfig) -> vf.Env:
    """Construct the standard single-agent v1 environment.

    Prime/Verifiers supplies a fully resolved config here. Keeping the argument
    mandatory prevents a local fallback from silently discarding hub, evaluation,
    or training overrides.
    """
    return vf.SingleAgentEnv(config)


__all__ = [
    "AcslCData",
    "AcslCTask",
    "AcslCTaskConfig",
    "AcslCTaskset",
    "AcslCTasksetConfig",
    "extract_code",
    "load_environment",
    "load_taskset",
    "stable_record_id",
]
