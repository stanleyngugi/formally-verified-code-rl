# Research Findings (historical snapshot)

Collected 2026-08-24. Every claim sourced. This file is the evidence base for DECISIONS.md.

> Some upstream API notes are preserved as historical context. Use
> `RESEARCH_REFRESH_2026-09-09.md` for the current compatibility target and
> recommendations.

---

## 1. The formal verification landscape (context)

From prior research session (`code_verification_semantic_links.md` on user's machine +
web confirmation):

- C is the only mainstream language with a complete verified chain: CompCert 3.17
  (Feb 2026, Rocq 9.1) + VST separation logic. CompCert qualified for DO-178C credit on
  ATR 42/72 avionics (March 2026). Stops at assembly; CakeML (HOL4) goes to concrete
  machine code but is not a mainstream language.
- SMT-backed auto-active verifiers (Dafny, Verus, Frama-C/WP) give deterministic,
  push-button verdicts — the property that makes them usable as RL judges.
- ITPs (Lean/Coq/Isabelle) host the deepest artifacts but lack code-relevant
  formalizations in Lean and need tactic search; their sparseness as judges is a missing
  library problem, fixable later (lean-smt reconstruction, grind/bv_decide automation).
- VerusBelt (PLDI 2026, Distinguished Paper + Artifact): semantic foundation for Verus
  proof-oriented types in Iris/Rocq.

## 2. RL with verifier rewards: prior art (all confirmed working)

| Work | Venue/Date | Language | Key result | Source |
|---|---|---|---|---|
| ReForm | TMLR 2026 / arXiv 2507.16331 | Dafny | RL w/ verifier feedback; 0.5B models beat frontier proprietary models on DafnyComp | mlanthology.org/tmlr/2026/yan2026tmlr-re |
| MIT thesis (Max Tan) | arXiv 2605.30914, May 2026 | Dafny, Lean | GRPO-RLVR raised verified reward 2.2%→58.1%; documented **specification hacking** as central failure mode; multi-turn after filtering: 9.7%→31.1%. Goedel-Code-Prover cited: decomposition + online Lean rewards work | arxiv.org/html/2605.30914v1 |
| ANCORA | arXiv 2604.27644, Apr 2026 | Verus | Self-play Proposer/Solver; Qwen2.5-Coder-3B → 81.5% pass@1 on Dafny2Verus; ~200 GPU-hours on 2×A100 | arxiv.org/html/2604.27644 |
| SpecRL | arXiv 2604.05820 | Dafny | Negative tests ("spectests") = fine-grained spec-completeness reward; beats binary rewards across model sizes | arxiv.org/html/2604.05820v1 |
| PREFACE | ACM (FPGA/SPL?) 2025 | Dafny→C HLS | Small RL prompt-agent + frozen LLM; up to +21% verification success | dl.acm.org/doi/10.1145/3716368.3735300 |
| AutoACSL | arXiv 2606.20969, Jun 2026 | **C/ACSL** | LLM+CPG static analysis+Frama-C/WP feedback loop: 96% full-proof ratio (Gemini-3), +24.7–51.7% over baselines | arxiv.org/html/2606.20969 |
| AlphaVerus / SAFE / VeRuSyn | 2025-2026 | Rust/Verus | Bootstrapped tree search; VeRuSyn scaled to 6.9M verified Rust programs | cited in SpecRL related work |
| AxDafny | arXiv 2606.32007 | Dafny | Agentic repair: 92.7% on DafnyBench; verification success ≠ runtime test performance | arxiv 2606.32007 |
| ExecVerify | ACL 2026 | — | Stepwise verifiable rewards from execution traces | aclanthology.org/2026.acl-long.631 |

**Key lessons distilled:**
1. Specification/reward hacking against weak specs is THE failure mode. Mitigations:
   spectests (SpecRL), subset-implication spec-strength checks (ReForm/Clover),
   task filtering (MIT).
2. Binary verify/fail reward is too sparse. Winning recipes use staged rewards:
   parse → compile → % VCs → spec strength.
3. Verifier diagnostics and named failed obligations are the current dense feedback
   channel. Genuine model/counterexample extraction remains future work.
4. Empirical judge success rates: Dafny ≈82%, Verus/Rust ≈44%, Lean ≈27% (VeriCoding
   benchmark, via MIT thesis) — automation depth drives learnability.

## 3. Prime Intellect verifiers v1 (the harness we build on)

Sources: github.com/PrimeIntellect-ai/verifiers (README, docs/environments.md,
verifiers/v1/GUIDE.md highlights, docs/byo-harness.md),
primeintellect.ai/blog/verifiers-v1 (July 2026), lab-cookbook guide 02.

Architecture: `Taskset (data + scoring) × Harness (rollout driver) × Runtime
(subprocess/docker/modal)`. Same env drives eval + RL training (prime-rl) + synthetic
data gen.

Confirmed API surface:
- Scaffold: `uv run init my-task-v1` or `prime env init --v1`.
- Typed tasks: subclass `vf.TaskData` (per-row fields), `vf.Task[Data]`;
  taskset subclasses `vf.Taskset[Task, Config]`, exports class via `__all__`.
- `load_tasks(split="train"|"eval")` returns list/generator/HF Dataset.
- Scoring decorators on the taskset/task class: `@vf.reward(weight=…)`,
  `@vf.group_reward`, `@vf.metric`, `@vf.stop`, plus lifecycle `@vf.setup`,
  `@vf.update`, `@vf.cleanup`.
- Reward functions are async; arguments injected by name: `task`, `trace`, `runtime`,
  `state`. `trace.assistant_messages[-1].content` = last model output.
- In-runtime scoring offers `runtime.run_uv_script` for dependency-bearing
  PEP-723 scripts, plus direct runtime read/write/exec. ACSL-C deliberately uses
  direct execution with the judge image's pinned `python3`: its runner has no
  third-party Python dependencies, while generic uv preparation attempted a
  package-manager upgrade that correctly failed in the unprivileged,
  network-restricted production image.
- Loaders: `load_taskset(config)` + root `load_environment(config: vf.EnvConfig)`
  returning `vf.Env(taskset=..., harness=...)`.
- Training config TOML: `[[env]] taskset={id=...} harness={id="default",
  runtime={type="docker"}} timeout={scoring=N}`.
- `@vf.reward` may return float or dict[str,float] merged by weight.
- Eval CLI: `uv run eval <taskset-id> -n N -r rollouts`; `validate` runs gold checks
  model-free.
- v0 API deprecated; target v1 only.

Blog example (AdditionTaskset) and cookbook example (ReverseTextTaskset) match the
shapes above — implementation follows them.

## 4. Judge tooling: machine-readable outputs

### Frama-C WP (Phase-1 judge)
Source: WP manual (frama-c.com/download/wp-manual-*.pdf), WP register.ml source
(dill.caelum.ci.dev frama-c 32.0).

- Modern WP emits a per-goal JSON report (option exposed as `-wp-report-json <file>`;
  confirmed in frama-c 32 source: `do_report_json()` writes a JSON list where each
  goal record has keys: `goal`, `property`, `file`, `line`, `function`, `behavior`,
  `smoke`, `passed` (bool), `verdict`, `provers` (name/time/success each), `proved`,
  `timeout`, `unknown`, `failed`, `cached`, optional `subgoals`, `script`.
- Selection flags: `-wp-fct f1,...`, `-wp-prop` (categories @requires @ensures
  @assigns @invariant @assert ...), `-wp-rte` generates runtime-error guards
  (overflow, div-by-zero, OOB) proved alongside.
- Current local prover policy: `-wp-prover alt-ergo,z3`; timeout via
  `-wp-timeout`. cvc5 is absent, and an unknown prover name aborts Frama-C.
- Fallback if JSON flag absent in an installed version: parse stdout summary
  `Proved goals: N / M` (documented format in WP manual).

### Verus (Phase-2 judge)
Source: verus-lang.github.io verus tutorial + attributes reference;
github.com/Beneficial-AI-Foundation/probe-verus src/verification.rs;
verus issue #2330.

- Summary line: `verification results:: N verified, M errors` (regex-parseable
  fallback).
- Machine-readable: JSON output mode exists (`--format json`); failing obligations
  appear under `func-details` including custom `proof_note` text. probe-verus parses
  per-function entries: `verified_functions / failed_functions / unverified_functions`
  with `code-path`, `code-line`, `verified`, `status`.
- Error classes for feedback: "assertion failed", "postcondition not satisfied",
  "precondition not satisfied", "loop invariant not preserved", etc.
- Known operational hazard (issue #2645): Z3 get-model output corruption aborts the
  whole process — sandbox must tolerate non-zero exits and capture stderr.

## 5. Datasets

- **CASP** (arXiv 2508.18798, Hertzberg et al., Nov 2025/June 2025 release):
  506 manually-inspected C + ACSL pairs from The Stack, verified with Frama-C 30
  (WP+RTE, Z3 4.8.12 / Alt-Ergo 2.6 / CVC4 1.8, 500k steps, 60s/goal).
  HF: `nicher92/CASP_source_files`. Phase-1 seed corpus.
- **SV-COMP** benchmarks: thousands of C safety tasks (annual competition set) —
  expansion pool.
- **Dafny2Verus** (274 problems), MBPP-Verified/HumanEval-Verified Verus translations
  (ANCORA), DafnyBench (~782), VeriCoding, VERINA, CLEVER — Phase 2/3 pools.
- AutoACSL pipeline (LLM+CPG→Frama-C loop) can synthesize additional annotated C
  tasks; treat output as candidate data requiring validation (their own numbers show
  why: GSR/FPR high but not perfect).

## 6. Operational constraints found

- Solver/tool version drift changes verdicts (Viper pins Z3 4.8.7 for this reason) →
  pin everything in the docker image; record digests in DECISIONS.md.
- Verification wall-clock dominates throughput → cache results keyed by content hash
  of (source + annotations + toolchain digest); run scoring inside the rollout runtime
  so heavy deps never touch the host (PI's documented pattern).
- Verus can abort on solver misbehavior (issue #2645) → reward function must be
  exception-safe: any tool crash = score 0 with crash recorded as metric, never a
  trainer crash.
- CASP used specific prover versions; re-verify all pairs under our pinned image before
  training (expect a small % to flip) and record flips.

## 7. Empirical findings from our own pipeline (Aug 2026)

- **15.3% of the CASP corpus is vacuous.** 61/399 pairs that verify under
  Frama-C also fully verify when every function body is replaced by a stub —
  their contracts provably constrain nothing. These are exactly the tasks a
  verification-rewarded model would exploit (spec hacking). Our vacuity probe
  quarantines them at ingestion; per ADR-004 r4 they must never enter training.
- CASP also contains "trivially-satisfiable" specs, e.g. `int max(a,b){
  return INT_MAX; }` verifying `\result >= a && \result >= b`. Vacuity probing
  catches the general case; spectests (Milestone 1 remaining item) catch
  satisfiable-but-wrong cases.
- Re-verification under our pinned toolchain flipped 65/464 pairs vs CASP's
  original frama-c 30 runs — confirming ADR-006's version-pinning policy.
- frama-c `-then` flag consumes subsequent args into a second command: putting
  the input file after it silently yields zero goals (bit us once; fixed).
