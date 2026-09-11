# Worklog

## Session 2026-09-09 — research refresh and hardening

### Repository audit and research

- Re-read repository code, docs, configs, datasets, quarantine reports,
  baselines, and the historical training log.
- Researched current Prime-RL/Verifiers docs and source, Frama-C/WP/E-ACSL,
  SpecRL, CASP, Re:Form, DAPO/Dr.GRPO, and recent verifier-gaming/formal-RL work.
- Selected Prime-RL v0.9.0 and its exact vendored Verifiers commit as one frozen
  compatibility target.

### Implementation

- Added immutable-contract/context checking. An annotation mutation now zeros
  every reward component.
- Added a cross-process SQLite/WAL verdict cache keyed by completion and full
  toolchain/scoring policy.
- Reworked verification into a self-contained runtime script with structured
  JSON failures and one Frama-C invocation.
- Corrected schema-v1 `non_vacuous` inversion and schema-v2 ingestion semantics.
- Fixed body extraction that previously mistook braces inside comments/ACSL for
  C function bodies; two malformed historical tasks are now excluded.
- Added deterministic stable-ID splits: 222 train, 47 validation, 48 test, 21
  excluded, 2 duplicate groups.
- Implemented current typed Task/Taskset rewards, Docker-required production
  execution, and Bash-harness agentic setup.
- Replaced stale Prime config shape with current v0.9.0 training and standalone
  agentic-validation configs.
- Pinned Dockerfile dependencies and removed obsolete one-off debug/introspection
  scripts, including a script that printed an API-key prefix.

### Validation evidence

- Clean Python 3.12 install against Verifiers commit
  `b2e4e8157783b2c0dffc7821044c87f29f1c3ccf` succeeded after enabling Hatch
  direct-reference metadata.
- 18/18 unit/integration-level tests passed.
- Shell syntax, Ruff formatting/lint, the exact Prime-RL config schemas, and
  Verifiers plugin discovery all passed. A repository `.gitattributes` now keeps
  Linux-executed sources at LF line endings when edited on Windows.
- Task loading returned exactly 222/47/48/317 for train/validation/test/all.
- Real local Frama-C 33.0 scoring: reference solution 4/4 goals and reward
  components `(1,1,1,1)`; a guaranteed ACSL mutation produced integrity failure
  and `(0,0,0,0)`.

### External blockers / next execution

- This workstation has no Docker CLI, so the image still needs a real build,
  label/version check, full reference replay, and digest capture elsewhere.
- The supported Prime-RL topology and GPU dry-run/training have not run yet.
- Executed negative spectests and claim-bearing multi-seed RL remain open.

## Session 2026-08-24

### Done
- Created repo + full documentation suite (README, RESEARCH, DECISIONS, PLAN).
- Implemented acsl-c Phase-1 skeleton: taskset, staged rewards, WP JSON parser,
  sandbox verify script, pinned Dockerfile, sample tasks, train TOML.
- Discovered verifiers **0.3.0 already installed** on the Windows host; its v1
  runtime imports `fcntl` → **Unix-only**. Decision: all env execution targets
  WSL/Linux; Windows host used only for docs/editing/pure-python tests.
- Made parser tests import `framac.py` by file path so they run without the
  verifiers dependency.
- **Parser unit tests: 6/6 PASS** (all-pass report, partial+timeout, smoke
  exclusion, malformed→stdout fallback, crash-not-exception, empty report).
- Wrote `scripts/roundtrip_test.py` (Milestone-0 judge round-trip) and
  `scripts/ingest_casp.py` (Milestone-1 ingestion per ADR-008: re-verify all
  pairs locally, quarantine flips, emit train/eval jsonl + ingest_report.json).

### Blockers hit & resolutions
- WSL `sudo` requires a password; background/synced apt installs hung invisibly.
  Resolution: user runs one install command manually; passwordless sudo enabled
  via /etc/sudoers.d/stanley so future steps don't stall.
- Ubuntu 24.04 (noble) repos dropped `frama-c` and `alt-ergo`. Resolution:
  apt for why3/z3/libgmp/opam, then opam userland build of frama-c + alt-ergo
  (scripts/wsl_setup_opam.sh). Expected ~30-45 min compile.
- verifiers.v1 is Unix-only (`fcntl`) → package `__init__` now degrades
  gracefully on Windows (parser-only exports); full stack targets WSL/Linux.
- Reward-chain simulation on Windows: WP report JSON -> Verdict -> staged score
  verified end-to-end without the toolchain.

### Next (in order)
1. After toolchain lands in WSL: run round-trip on examples/sample_tasks.jsonl;
   fix any ACSL that doesn't actually verify (expected: maybe abs_diff/sum_array
   need contract tweaks — that's what the test is for).
2. Record Frama-C version from apt vs CASP's 30.x; add `-wp-report-json`
   availability check to roundtrip script output.
3. Run ingest_casp.py --limit 25 as a smoke test, then full 506.
4. Smoke-test taskset loading against real jsonl under WSL python + uv.

## Session 2026-08-24 (later) — Milestone 0 COMPLETE

### Toolchain built
- User installed prereqs via apt (opam 2.1.5, why3 1.6.0, z3 4.8.12, gmp-dev);
  opam then built frama-c 33.0 (Arsenic), why3 1.8.2, alt-ergo 2.6.3 (~15 min,
  -j4 for 7GB RAM). graphviz added after opam depext refusal.
- Pin recorded in ADR-006. cvc5 dropped (absent; frama-c aborts on unknown
  prover names — now a documented operational constraint).

### Round-trip validation (scripts/roundtrip_test.py)
- Task 0 abs_diff: **7/7 goals proved incl. all RTE guards** — first complete
  end-to-end proof through the reward path. Notably the judge REJECTED my first
  spec (near-full-range ints genuinely overflow) and forced a correct contract:
  exactly the behavior we want to train into models.
- Task 1 sum_array: 11/14; \sum+lambda goals time out at 20s — known-hard,
  ideal dense-reward material.
- Task 2 swap skeleton: expected-incomplete, behaves as designed.
- Result: PASS, Milestone 0 closed.

### Fixes made along the way
- cvc5 removed from default prover lists everywhere.
- roundtrip_test.py + tests use importlib path-loading (no verifiers dep).
- Sample tasks rewritten with correct contracts (bounded ranges, loop variant,
  sum-bound invariant).

### Next (Milestone 1)
1. `pip install datasets` in WSL; run ingest_casp.py --limit 25 smoke, then 506.
2. Re-verification stats -> ingest_report.json; expect flips vs CASP's frama-c 30.
3. Wire spectests generator v0; wire taskset loading under WSL uv env.

## Session 2026-08-24 (evening) — Milestone 1 core COMPLETE

### CASP ingestion (scripts/ingest_casp.py)
- Full corpus: **399/464 pairs re-verified under our pinned toolchain (86%)**;
  65 quarantined flips logged in data/ingest_report.json per ADR-008.
- Split: casp_train.jsonl (351) / casp_eval.jsonl (48).
- vc_estimate from CASP's own `goals` column: range 4–120, median 14 → natural
  difficulty curriculum signal.
- Dataset schema discovered: columns `file_content`, `goals`; 464 rows.

### verifiers v1 ground truth (installed 0.3.0, introspected)
Docs/blog drift found and resolved by reading installed source:
- `Taskset.load()` is the abstract method (not `load_tasks(split=)`); split
  handled via config field.
- Rewards/@metric live on the **Task** class (blog shape), args injected by
  name from {task, trace, runtime}; runtime injected only if declared without
  default. Rewards may return dict[str,float] (named rewards).
- TaskData is frozen pydantic: idx/name/description/prompt/system_prompt/...
  custom fields subclass cleanly.
- `Runtime.run_uv_script(script, args=None, env=None) -> ProgramResult`
  confirmed on base class; content-addressed script caching built in.
- Trace exposes .assistant_messages/.last_reply/.num_turns.

### taskset.py rewritten to real API
- AcslCData/AcslCTask/AcslCTaskset match installed signatures exactly.
- Class-level verdict cache (shared across task instances, keyed by completion
  content hash).
- spec_strength signature extended (verdict-aware; sound gate until spectest
  executor lands).

### Smoke results
- Taskset load: 5 tasks from real CASP train file OK.
- Offline scoring path: all four rewards = 1.0, weighted total exactly 1.000.

### Remaining for Milestone 1 closure
- Historical next step at that time: `uv run eval acsl-c-v1` with the then-current
  docker/subprocess runtime
  (needs uv in WSL image or docker build of Dockerfile).
- Spectest generator v0 (negative tests) to activate r4.
- Eval-split taskset variant config.

## Session 2026-08-24 (night) — LIVE runtime path proven

### Live scoring through real frama-c: WORKING
- scripts/live_runtime_smoke.py: verifiers SubprocessRuntime -> run_uv_script ->
  uv PEP-723 script -> frama-c 33.0 -> WP JSON -> parser -> staged rewards.
- Correct completion scores 1.000; broken control 0.100. LIVE SMOKE OK.
- uv 0.12.5 installed in WSL (~/.local/bin).

### Bugs found & fixed
1. verify_script.py passed the input file AFTER `-then`, so WP ran with no input
   ("no input file" warning) and silently produced 0 goals. Removed `-then
   -no-unicode`; file is now a direct positional arg.
2. gate reward tightened: parse_ok alone allowed 0-goal reports to score; now
   requires goals_total > 0.
3. SubprocessRuntime.start() fails if workdir exists -> unique runtime names in
   smokes.

### Anti-Goodhart layer v0: vacuity probe (ADR-004 r4 groundwork)
- Real motivating example found in our own data: CASP task `int max(a,b){
  return INT_MAX; }` verifies against spec `\result >= a && \result >= b` —
  a genuinely vacuous contract in the seed corpus.
- ingest_casp.py --vacuity-check: stubs every function body (keeping all ACSL
  contracts), re-verifies; if stub still fully verifies, the pair is vacuous ->
  quarantined with status "vacuous-spec". Demo on 40 pairs caught 3.
- Tasks get non_vacuous field (True/False/unknown).

### In flight → DONE
- Full 464-pair re-ingestion WITH vacuity check complete (~90 min detached run).
- **Headline: 61/399 (15.3%) of CASP's "verified" pairs are VACUOUS** — their
  contracts fully verify against stubbed function bodies, i.e., they constrain
  nothing. All quarantined.
- Final canonical dataset: 338 tasks (290 train / 48 eval), every one verified
  under our pinned toolchain AND non-vacuous; 126 total quarantined entries
  (65 re-verification flips + 61 vacuous specs) in data/quarantine/ +
  ingest_report.json.
- vc_estimate spread on final set: 4–120, median 15.
- Milestone 1 data work CLOSED.

## Session 2026-08-24 (late night) — first model baselines via Cerebras

### Setup
- Cerebras API (OpenAI-compatible) wired through urllib with custom User-Agent
  (their Cloudflare blocks default python UA, error 1010). Key stored at
  ~/.cerebras_api_key outside the repo.
- Models: gpt-oss-120b (reasoning; separate `reasoning` field in response),
  gemma-4-31b.

### Baselines run (docs/BASELINES.md)
- Easy slice n=12: both ~83–92% full-proof — non-discriminating.
- Hard slice n=8: gpt-oss 87.5% full / 93.4% frac; gemma 62.5% full / 95.9% frac
- Two important findings:
  1. gpt-oss truncation artifact: reasoning tokens ate a 2048 budget producing
     "0/0 goals" outputs; fixed with 8192 budget -> +25pp full-proof. Our gate
     metric flags truncation instantly.
  2. gemma's near-misses (42/43, 100/106 goals) demonstrate the dense
     vc_fraction reward giving exactly the partial-credit signal GRPO needs.
- Spend: ~60k tokens total (<$1 of $4 credit).

### Next
1. GRPO prep for GPU box: prime-rl config against our taskset; small model
   (Qwen2.5-Coder-3B/7B) per ANCORA recipe (~200 GPU-hrs on 2xA100).
2. Spectest generator v0 to activate r4 before training (prevents spec hacking
   during RL).
3. Optional: full-mode task synthesis (NL -> annotated C) as second env variant.

## Session 2026-09-09 — managed Colab model feasibility

### Runtime
- Reconnected managed Colab to one Tesla T4 (15,360 MiB VRAM; compute
  capability 7.5), Python 3.13.15, Torch 2.11.0+cu128, CUDA 12.8.
- Installed Unsloth 2026.9.3, TRL 0.24.0, bitsandbytes 0.50.2, and
  Transformers 5.5.0.
- Re-uploaded the sanitized repository archive after the prior runtime was
  reclaimed; notebook cells and outputs persisted, `/content` files did not.

### Fresh-process QLoRA probes
- `unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit`, resolved revision
  `4858886f896bd05db823557fc5cbc4ac28342af7`, sequence length 2,048:
  load 5.39 GiB, generation peak 5.33 GiB, optimizer peak 7.61 GiB,
  finite loss 0.0181, 40,370,176 trainable parameters — **passed**.
- `unsloth/Qwen2.5-Coder-14B-Instruct-bnb-4bit`, resolved revision
  `ecfc63c083900ce4f19daad695e711f38ab98fcf`, sequence length 1,024:
  load 9.58 GiB, generation peak 9.48 GiB, optimizer peak 12.16 GiB,
  finite loss 0.0357, 68,812,800 trainable parameters — **passed**.
- These are model/generation/one-step feasibility measurements only. They do
  not prove Prime-RL compatibility, multi-sample GRPO capacity, or a training
  improvement. Default claim-bearing model remains 7B; 14B is a tightly
  budgeted ablation.

### Operational conclusion
- Managed Colab is suitable for probes, baseline generation, and small QLoRA
  tests. It lacks Docker and Frama-C in the observed runtime and cannot replace
  the production verifier sandbox.
- SSH/remote-control workarounds are not part of the managed-runtime plan;
  use a user-controlled local runtime or real GPU VM for Docker, Frama-C, and
  Prime-RL.

## Session 2026-09-09 — executed spectest guard

- Added `scripts/execute_spectests.py`, an offline Frama-C WP+RTE executor that
  records `executed`, `rejected`, the complete parsed verdict, and an executor
  identity. A spectest earns a rejection flag only after clean parsing,
  compilation, nonzero goals, no timeout, and a non-full proof.
- Tightened `spec_strength_score`: bare `rejected` fields, missing execution
  evidence, crashes, parse failures, and timeouts now score zero.
- Added three unit tests for the strict schema; WSL suite is now **21 passed**.
- A fixture run confirmed the executor distinguishes a proved reference from a
  negative case that timed out; the latter is retained as infrastructure/
  inconclusive evidence, never rewarded.
- Full-mode specification synthesis remains disabled until spectest records are
  generated from independently audited negative behaviors on the production
  Frama-C image.

## Session 2026-09-09 — deterministic validation baseline captured

- Generated 8 deterministic completions on the connected Tesla T4 using
  `unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit`, sequence length 2,048, and a
  512-token completion cap.
- Corrected the input selection after discovering that validation IDs are in
  `casp_eval.jsonl` (the 222-record `casp_train.jsonl` has no validation-ID
  overlap). The run captured 8 unique validation IDs, 1,001 completion tokens,
  and a 5,697-byte JSONL artifact in the Colab session.
- The exact model revision, IDs, timings, and command are recorded in
  `docs/COLAB_BASELINE_2026-09-09.json`. This is generation evidence only;
  Frama-C/Docker replay and reward scoring remain outstanding.
- Hardened `colab_generate_baseline.py` to validate paths/splits and fail
  before model loading when no records match, instead of silently emitting an
  empty file.

### Follow-up — complete validation capture

- Reconnected the same managed T4 runtime and completed the full 47-task
  validation generation with deterministic decoding and the same pinned model
  revision. The artifact contains 47 unique IDs, 7,010 completion tokens, and
  36,458 bytes in Colab session storage.
- Added the full-run command, counts, revision, and preservation status to
  `docs/COLAB_BASELINE_2026-09-09.json`; the raw JSONL still needs to be
  downloaded or copied to durable storage before verifier replay.
- Colab remains intentionally generation-only: no Docker, Frama-C, or
  claim-bearing Prime-RL result is inferred from this capture.

## Session 2026-09-10 — Prime CLI gate, preflight, and storage boundary

- Materialized the exact Prime-RL v0.9.0 core environment on Python 3.12.3
  with `uv sync --package prime-rl --no-default-groups`; uv installed 156
  packages including `prime-rl==0.9.0`, `verifiers==0.3.1`, and the pinned
  local config/renderers packages. The earlier all-workspace sync was not
  promoted to a project gate because an unrelated `tau2-bench` Git fetch
  failed with HTTP early EOF.
- Installed the local `acsl-c` package into the Prime venv without dependency
  changes and created the checked target link
  `/workspace/acsl-c -> /mnt/c/Users/stanley/Desktop/verified-rl-envs/environments/acsl-c`.
- Ran Prime-RL's real v0.9.0 CLI dry-run against `configs/train.toml` with
  dashboard disabled. It exited successfully and wrote resolved trainer,
  inference, and orchestrator JSON configs. The resolved files confirm
  Qwen/Qwen2.5-Coder-7B-Instruct, GRPO, 2,048-token sequences, the train split,
  and the pinned ACSL toolchain identifier.
- Restarted the WSL Docker daemon and revalidated the preserved image digest
  `sha256:5da598c4fa7f1e4210412822f3c3942764baa0057e85070ab5d3b1fadd1ac9dc`,
  Frama-C/Why3/Alt-Ergo/Z3 versions, and UID 10001. The original image still
  cannot write `/workspace`; that is why the hardened Dockerfile rebuild was
  attempted rather than silently treated as final.
- The hardened rebuild reached the final opam graph and installed
  `alt-ergo` and its parsers, but the Windows C: volume fell to zero free
  space during the remaining Why3/Frama-C links. The build was interrupted,
  WSL was shut down/restarted, and only the exact stopped intermediate build
  container was removed. Both validated image tags remain intact. A new image
  digest and final replay therefore remain pending until storage is expanded.
- Wrote `artifacts/preflight_2026-09-10.json`. It reports valid 221/47/48/316
  splits, `container_judge_ready=true`, `prime_stack_ready=true`,
  `gpu_topology_ready=false`, and `production_ready=false`; the latter is
  expected because this WSL host exposes zero NVIDIA GPUs.
- Final local checks passed: 27 pytest tests, Python compileall, manifest hash
  `dab491f6dc60f4b2940f3f105ab22554a737b2eb42b3078b09056608400f3c57`, and
  `git diff --check`.

## Session 2026-09-09 — bounded stochastic rollout-shape probe

- Used the connected Tesla T4 to sample four stochastic candidates for each of
  eight validation tasks (32 rows total) with the pinned Qwen2.5-Coder-7B
  revision `4858886f896bd05db823557fc5cbc4ac28342af7`.
- Decoding was temperature 0.7, top-p 0.95, and a 256-token completion cap;
  per-sample seeds were derived from base seed 1337. The artifact contained
  2,242 completion tokens and 26 unique completions across eight task IDs.
- Records are explicitly `verifier_scored: false`: this is a
  generation-diversity/shape probe only. No pass rate, reward, or RL lift is
  inferred until every candidate is replayed by the pinned Docker/Frama-C
  judge.
- Artifact fingerprint in the Colab session: 21,193 bytes,
  SHA-256 `716433753af3722f6d39e34f4ed42b695e5fd8cfd24ee7d7c611ca9590f7ed98`.
- A Drive mount failed with Colab's `credential propagation was unsuccessful`
  error, and invoking `files.download` did not produce a file in the Windows
  Downloads directory. The raw artifact is therefore session-only; the
  command, counts, revision, and failure mode are recorded in
  `COLAB_BASELINE_2026-09-09.json` for an auditable rerun.
- Added the reusable generation-only entry point
  `environments/acsl-c/scripts/colab_generate_rollout_samples.py` so a future
  Docker-capable GPU host can produce the same candidate shape before scoring.

## Session 2026-09-09 — batched long-context rollout memory probe

- Used the connected Tesla T4 to measure four simultaneous Qwen2.5-Coder-7B
  candidates against the longest validation skeleton (`casp_eval.jsonl` index 9).
- The probe used a 1,632-token prompt (5,020 characters), `max_new_tokens=256`,
  `min_new_tokens=128`, temperature 0.7, top-p 0.95, and completed in 78.217
  seconds.
- Peak reserved memory was 7.27 GiB (7.421 GiB used, 7.142 GiB free), so
  generation-only four-sample rollout batching fits comfortably in the 16 GiB
  T4 budget.
- This is capacity evidence only. It does not establish QLoRA optimizer
  headroom, GRPO throughput, vLLM serving, or verifier-scored training
  correctness; those remain production-topology gates.

## Session 2026-09-09 — generation warning cleanup and reproducibility audit

- Confirmed on the live T4 that Unsloth's loaded model carries a stale
  `generation_config.max_length=32768`. Clearing that field immediately after
  load removes Transformers' conflicting-length warning while preserving the
  explicit `max_new_tokens` limits used by every capture.
- Applied the same fix to the deterministic baseline generator, stochastic
  rollout sampler, and memory probe; Ruff, formatting, `git diff --check`, and
  the WSL ACSL-C suite remain clean (**21 passed**).
- Corrected the Colab runbook command to use the sampler's actual flags
  (`--max-tasks` and `--num-samples`), restoring copy/paste reproducibility.
- Replayed the spectest fixture with the locally installed Frama-C 33.0 /
  Alt-Ergo + Z3 toolchain: the reference case executed and fully proved; the
  deliberately bad case executed but timed out, so it was correctly retained
  as `rejected: false` infrastructure/inconclusive evidence rather than being
  promoted to a clean negative label.

## Session 2026-09-09 — production preflight command

- Added `scripts/preflight.py`, a read-only JSON preflight for split counts,
  Python, Frama-C/prover binaries, Docker health, and an optional Prime-RL
  checkout. It exits 2 when production readiness is false instead of silently
  allowing a claim-bearing run to start.
- Under the configured WSL opam switch, the report confirms
  `local_judge_ready: true` with Frama-C 33.0, Alt-Ergo 2.6.3, Z3 4.8.12, and
  the expected 222/47/48/317 split counts. It correctly reports
  `production_ready: false` because Docker and the Prime-RL checkout are
  absent.

## Session 2026-09-09/10 — pinned Docker judge and complete reference replay

- Installed Docker Engine 29.1.3 in WSL Ubuntu 24.04, started its daemon, and
  passed the upstream `hello-world` engine smoke.
- Fixed the Dockerfile's collision with Ubuntu 24.04's pre-existing UID 1000 by
  assigning the unprivileged `opam` runtime user UID 10001. The first image
  build completed as `sha256:5da598c4fa7f1e4210412822f3c3942764baa0057e85070ab5d3b1fadd1ac9dc`
  and asserted Frama-C 33.0, Why3 1.8.2, Alt-Ergo 2.6.3, Z3 4.8.12, and uv
  0.12.5 inside the image.
- The image passed the handcrafted round-trip: the expected reference proved
  7/7 goals, while the two deliberately hard/incomplete examples produced
  parseable partial verdicts.
- Added `scripts/replay_references.py`, a resumable manifest-locked replay with
  per-record JSONL evidence, summary statistics, exact tool versions, and a
  nonzero exit when any selected reference fails.
- The first 317-reference replay found `casp:75` reproducibly timing out on one
  goal at 20 seconds. It proved at 60 seconds, demonstrating a policy mismatch,
  so an explicit `data/replay_exclusions.jsonl` ledger now quarantines it.
- A four-worker replay of the resulting 316 references showed a different,
  non-reproducible timeout on a 112-goal task; that task passed the earlier run
  and a cold single-task rerun. Concurrency is therefore now recorded in replay
  policy and is not used to establish reference eligibility.
- The authoritative one-worker replay passed all **316/316** eligible
  references: **5,205/5,205** goals and **1,264/1,264** RTE goals, with zero
  timeouts. Aggregate solver-duration was 622.519 seconds. Evidence is under
  `environments/acsl-c/artifacts/`.
- Rebuilt the manifest as 221 train / 47 validation / 48 test / 316 all, with
  22 exclusions. Added ADR-013 to preserve the cold-serial eligibility rule.
- Checked out Prime-RL v0.9.0 at exact commit
  `ab5de8fff44b2c4a5c85e24b6e6e3f7d57eee7b1` and all pinned submodules,
  including Verifiers `b2e4e8157783b2c0dffc7821044c87f29f1c3ccf`.
- Added three preflight tests; the ACSL-C suite is now **24 passed**.

## Session 2026-09-10 — Colab GPU / verifier boundary re-checked

- Re-read the user's live Colab notebook rather than assuming the runtime had
  disconnected. The managed runtime is connected to one Tesla T4 (15,360 MiB,
  compute capability 7.5), with Python 3.13.15, Torch 2.11.0+cu128, and CUDA
  12.8.
- The notebook has already loaded the pinned 4-bit
  `unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit` model, completed the 47-task
  deterministic validation capture, completed the 8-task × 4-sample rollout
  probe, and passed a 1,632-token-prompt / 256-token / four-way batch at 7.27
  GiB peak reserved memory.
- The same diagnostic explicitly reports `docker=None` and `frama-c=None` in
  the managed runtime. This is an environment boundary, not a GPU limitation:
  Colab is the model-compute plane; the existing pinned Docker image is the
  verifier/reward plane.
- Clarified `docs/COLAB_RUNBOOK.md` and `docs/PLAN.md`: rebuilding the image is
  optional hardening for the writable `/workspace` behavior and is not a
  prerequisite for further Colab generation or bounded QLoRA experiments.
- Retried the notebook's `files.download` cell for the 21,193-byte rollout
  artifact while the T4 remained connected. Colab marked that cell execution
  unsuccessful and no browser download event was observed; the runtime itself
  stayed connected. The artifact therefore remains session-only until the user
  downloads it manually or Drive/local-runtime persistence is repaired.
- Rechecked the upstream Prime-RL scaling/inference documentation. It explicitly
  supports one-GPU trainer and inference component checks, describes
  single-GPU runs as useful for debugging/small experiments, and documents CPU
  optimizer/full offload, activation checkpointing/offload, fused LM-head
  chunking, and inference KV-cache offload. Added `docs/ONE_GPU_PLAN.md` with a
  serial one-GPU on-policy strategy and a separate, higher-risk concurrent
  colocated strategy. Neither is silently treated as equivalent to the
  asynchronous two-GPU topology.

- Added `docs/ENVIRONMENT_VALIDATION.md` to make the release boundary explicit:
  task problems come from re-verified CASP source pairs and deterministic
  skeletons; prompts are only the model-facing interface. The document defines
  required environment gates and executable adversarial suites for reward
  hacking, verifier integrity, credit assignment, prompt extraction, cache,
  isolation, and reproducibility. Long multi-seed training is now documented as
  optional research evidence rather than an environment-correctness gate.

- Added `docs/ENVIRONMENT_HUB_RESEARCH.md`, a cited comparison of Prime-RL /
  Verifiers and Hugging Face OpenEnv requirements, plus the distinction between
  environment-release evidence and an optional training-study claim.
- Extended that comparison with NVIDIA NeMo Gym's current contribution guide:
  manifest validation and verifier fixtures are local correctness gates, while
  example rollouts, reward profiling, and training-based validation are listed
  as optional publication evidence.
- Added deduplicated per-source/verdict transition metadata
  (`acsl_verdict_history`) to agent traces. This records causal edit state for
  credit-assignment diagnostics without storing full model outputs.
- Added tests for prompt/skeleton provenance, malformed/fenced extraction,
  fake-verifier text, solver-timeout non-caching, and deduplicated failed-edit
  transitions. The WSL suite passes **32 tests**; Python bytecode compilation
  also passes. The actual Frama-C negative spectest fixture still requires a
  Docker-capable judge execution before it can be promoted to evidence.

- Completed the bounded serial one-GPU canary on the managed Colab Tesla T4 after
  explicitly reinstalling packages following reconnect. Qwen2.5-Coder-7B in
  4-bit with LoRA completed a real forward/backward/optimizer step: loss
  `0.6463377476 -> 0.3429369628`, 20,185,088 trainable parameters, 6.246 GiB
  peak reserved, and a saved adapter manifest.
- Reloaded that adapter in a fresh model object and generated successfully
  (`CHECKPOINT_RELOAD_OK`), peaking at 9.047 GiB. A two-rollout, one-update serial
  generation/training plumbing loop also passed (`SERIAL_PLUMBING_OK`) with loss
  `0.6564837694 -> 0.6398609877`, 9.512 GiB peak reserved, and rewards explicitly
  marked `stub_not_verifier` because Colab exposes neither Docker nor Frama-C.
- Added `docs/COLAB_SERIAL_CANARY.md` with the reconnect bootstrap, exact gates,
  interpretation rules, and the recorded GPU evidence. Async Prime-RL placement
  remains an optional scaling/orchestration test; it is not an environment
  correctness prerequisite.
- Hardened verdict-cache invalidation: `verification_key` now includes a digest
  of the exact `verify_script.py` runner, so subprocess/parser policy changes
  cannot silently reuse old verdicts. Added a regression test; the full ACSL-C
  suite now passes **34 tests**.
- Hardened WP-report parsing against truthy malformed fields: only real JSON
  booleans can mark a goal as passed, malformed timeout values set `parse_ok`
  false, and a malformed report cannot become an all-goals proof. Added two
  parser regressions; the full suite remains **34 passed**.

## Session 2026-09-10 — environment release gate closed

- Corrected the earlier Docker diagnosis: Docker Engine 29.1.3 and the pinned
  judge image were already present in WSL; starting the daemon and using the
  non-interactive sudo fallback made the container gate operational. Native
  Frama-C 33.0, Alt-Ergo 2.6.3, and Z3 4.8.12 were also present in the pinned
  opam switch.
- Split publication readiness from optional two-GPU asynchronous-training
  readiness in preflight schema v3. The live report now has native judge,
  container judge, exact Prime stack, and `environment_release_ready` all true;
  only local two-GPU async topology is false, and the default release preflight
  exits successfully.
- Ran a real native taskset smoke: a reference scored `(1,1,1,1)` and an ACSL
  annotation tamper scored `(0,0,0,0)` before invoking the prover.
- Added and executed accepted/rejected Frama-C fixtures. Under the deterministic
  Qed policy, the accepted control proved and the wrong body produced one clean
  unknown goal; both declared expectations matched without crash or timeout.
- The first official Verifiers v1 Docker validation exposed an integration bug:
  generic `run_uv_script` attempted a runtime uv upgrade in the unprivileged
  judge and failed before Frama-C. The dependency-free runner now executes with
  the image's pinned `python3`, under a fresh unpredictable filename that is
  removed after scoring. The repeated official validation passed 3/3 gold tasks
  in fresh containers.
- Release configs now use `allow = []`, `/workspace`, bounded CPU/memory/time,
  and model-independent final scoring. A live Docker probe confirmed direct
  network egress is blocked, the host workspace is absent, and the reference
  proves 5/5 serialized goals.
- Disabled Frama-C's implicit WP cache (`-wp-cache none`) because the project
  already has a fully policy-keyed SQLite verdict cache. Bumped the runner
  policy ID to 3 and reran Docker, negative-case, Prime dry-run, and Verifiers
  validation gates successfully.
- Bundled the canonical corpus shards, split manifest, and exclusion ledger in
  the wheel. An isolated wheel target loaded a test task without a repository
  data path. Final wheel: 115,219 bytes, SHA-256
  `34fc1e7f91f8e863e90bdf5beaf8c1f6a37af3794e8d0d845427103dbbe33d63`.
- Extended the credit-assignment fixture through valid → failed edit → restored
  source and retained all three deduplicated verdict transitions. The full
  suite passes **35 tests**.
- Added the machine-readable release record, publication checklist, and an
  extensive blog draft. The environment-infrastructure claim is complete; the
  remaining steps are owner-controlled licensing, public repository/image/hub
  publication, or optional paper-level learning experiments.
- A final public-release license audit found that CASP's dataset card delegates
  rights checking to the underlying The Stack 1/2 sources. The cached
  `CASP_source_files` records contain only `file_content` and `goals`, so the
  current derived rows cannot be mapped back to per-file repository licenses.
  Technical validation is complete, but public redistribution is blocked until
  written permission, reconstructed provenance, or a replacement corpus exists.
  Added `CASP_LICENSE_REQUEST_DRAFT.md`; no email was sent.

## Session 2026-09-11 — publication path and novelty boundary

- Reframed the single CASP licensing blocker into an explicit data-pack
  architecture. Public v0.1 will bundle a project-authored, human-reviewed
  `core-v1`; CASP will remain a non-bundled, user-supplied research adapter
  unless permission or per-record provenance is recovered. The validated
  316-task replay remains environment research evidence, not public-corpus
  evidence.
- Confirmed from the CASP paper that CASP was still a strong engineering seed:
  it contains 506 verified C/ACSL pairs and is larger and more pair-oriented
  than the seven earlier ACSL collections it compares. The choice was
  technically sound even though the reduced public schema is insufficient for
  redistribution.
- Confirmed from The Stack v2's official card that source records normally
  carry repository, path, Software Heritage IDs, and detected-license fields,
  and that original license/attribution terms apply. Those fields are absent
  from the CASP snapshot used here; CASP's repair stage also makes blind
  content-hash reconstruction unreliable.
- Identified the maintained, MIT-licensed ACSL by Example repository as a
  useful attributed auxiliary pack, but not a sufficient sole benchmark due to
  its size, pedagogical purpose, and likely model familiarity. SV-COMP and
  older ACSL corpora remain future source-by-source adapters, not shortcuts.
- Updated the literature boundary. VeCoGen is the closest C predecessor and
  already performs iterative LLM generation/repair with Frama-C feedback.
  Verifier-reward RL also exists for Dafny and Lean, and a recent vericoding
  benchmark spans Dafny, Verus/Rust, and Lean. The intended claim is therefore
  about an early reusable **C/ACSL RL environment package**, not the first
  LLM-to-verifier system.
- Confirmed Prime's current Hub workflow: new environments should target
  Verifiers v1; the Hub is a Python package registry and showcase; `prime env
  push --visibility=PRIVATE` permits a private clean-install smoke before
  public visibility.
- Added `docs/PUBLICATION_STRATEGY.md` and `docs/RELATED_WORK.md`; synchronized
  the status, plan, publication checklist, decision log, environment validation,
  README, and blog draft. Added ADR-014 for the public data-pack decision and
  corrected ADR-003 to reflect the direct pinned-Python runner actually used.
- Proposed Core-64 as the public v0.1 target, preceded by a 16-task vertical
  slice. Splits must be by semantic/derivation family, every record must carry
  explicit provenance and review metadata, and the public wheel needs an
  automated payload audit that rejects CASP-derived content.
- Audited the seven source families in CASP's comparison table at pinned
  upstream revisions. ACSL by Example is explicitly MIT; X509-parser offers a
  BSD or GPLv2 choice; the WP tutorial combines CC BY-NC-SA and MIT text without
  clear file scope; Frama-C Problems, ACSL Proved, and the VeCoGen repository
  containing VecoSet expose no root license at the audited commits. VerKer is
  based on Linux kernel functions and needs exact per-file/source-plus-
  annotation rights analysis. The SoSy-Lab ACSL/SV-COMP repository is mixed
  and requires per-file SPDX/upstream joins.
- Added `docs/ACSL_SOURCE_LICENSE_AUDIT.md` with pinned commit links, a reuse
  matrix, source-specific recommendations, required provenance fields, and a
  staged external-pack roadmap. The resulting policy is to use licensed
  sources as visible, separately attributed packs rather than summing CASP's
  historical file counts into one anonymous corpus.

## Session 2026-09-11 — public Core-v1 implementation and release staging

- Added dataset-neutral pack selection, explicit public stable IDs, a
  fail-closed provenance schema, and a wheel-payload audit. The default install
  now loads `core-v1`; CASP requires an explicit research data path and is not
  included in the public wheel.
- Authored a 16-task vertical slice, replayed every reference and negative,
  then expanded the generator to Core-64 only after those gates passed. The
  frozen family-isolated split is 33 train / 15 validation / 16 test.
- Final Core-v1 replay under Frama-C 33.0, Why3 1.8.2, Alt-Ergo 2.6.3, and Z3
  4.8.12 proved 64/64 references, 296/296 total obligations, and 84/84 RTE
  obligations with zero solver timeouts.
- Ran two distinct negative diagnostics. The exact external-prover policy
  denied full proof to every wrong candidate but timed out on invalid goals;
  that artifact remains diagnostic only. The deterministic WP+RTE/Qed pass
  cleanly rejected 64/64 wrong programs with zero timeouts and is the declared
  negative evidence gate.
- Added the strict Verifiers v1 `load_taskset(config)` and
  `load_environment(config)` entry points. A clean wheel install from
  site-packages loads all 64 tasks and constructs the standard single-agent
  environment without a checkout-relative data path.
- Renamed the public umbrella to **Formally Verified Code RL**, the Prime/Python
  distribution to **Formally Verified C** (`formally-verified-c`), and the
  planned dataset mirror to `formally-verified-c-core-v1`. The technical
  `acsl_c` namespace remains as a compatibility alias.
- Added Apache-2.0 licensing, NOTICE, CITATION.cff, SECURITY.md,
  CONTRIBUTING.md, package metadata, a Hugging Face-compatible dataset card,
  and `core-v1-public-release-evidence.json`.
- The full suite now passes 42 tests. The final wheel is 41,975 bytes at
  SHA-256 `aa0de5d2931e293a13b9f066a7057c64a0a1e45eb28a1c9b08a7e0ac26d543a3`;
  the public payload audit confirms Core-v1 is bundled and CASP data are not.
- Authenticated GitHub as `stanleyngugi` and Prime as `stanley-ngugi` for the
  private-first publication flow. No supplied credential was written to the
  repository.
