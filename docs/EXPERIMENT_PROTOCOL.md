# Experiment Protocol

> Version 1, 2026-09-09. Freeze this document before a claim-bearing run. Any
> post-hoc change must be recorded as a new protocol version.

This protocol governs a **training-improvement claim**. It is intentionally
stricter than the environment-release gates in
`docs/ENVIRONMENT_VALIDATION.md`; a long or multi-seed RL run is not required
to publish the environment itself.

## Objective

Test whether GRPO training in the ACSL-C environment increases the probability
that a frozen model produces function bodies for which all Frama-C WP+RTE goals
are discharged, without increasing annotation tampering, vacuity, crashes, or
timeouts.

## Data policy

- `train`: 221 eligible, deduplicated records.
- `validation`: 47 records from the historical CASP eval set. It is development
  data because it has already been used for baselines and design choices.
- `test`: 48 freshly selected, stratified records from the historical training
  pool. Do not inspect model outputs on this split until prompts, reward,
  hyperparameters, seed count, and checkpoint-selection rule are frozen.
- 21 records are excluded for unknown vacuity, invalid body extraction, or
  duplicate normalized skeletons.

The authoritative membership and seed are in
`environments/acsl-c/data/split_manifest.json`. Stable content hashes, not row
positions, identify tasks.

## Frozen judge

Record all of the following with every run:

```text
prime-rl commit: ab5de8fff44b2c4a5c85e24b6e6e3f7d57eee7b1 (v0.9.0)
verifiers commit: b2e4e8157783b2c0dffc7821044c87f29f1c3ccf
Frama-C: 33.0 (Arsenic)
Why3: 1.8.2
Alt-Ergo: 2.6.3
Z3: 4.8.12
runner schema: 2
split seed: 20260909
```

Also record the built verifier image digest. A version string alone does not
identify an image.

## Preflight gates

No training starts unless all gates pass:

1. clean install from `pyproject.toml` under Python 3.12;
2. all unit tests pass;
3. split counts equal 221/47/48 and stable IDs are disjoint;
4. every reference solution in the selected corpus passes the pinned judge;
5. an annotation deletion/edit receives total reward zero;
6. malformed, crashing, and timed-out cases return structured verdicts rather
   than escaping exceptions;
7. Docker/Prime—not subprocess—is the rollout runtime;
8. `rl --dry-run` validates and archives the resolved config;
9. a 1–2 step canary produces traces, metrics, and a resumable checkpoint.

## Baseline

Evaluate the untrained base model on the full validation split using the exact
training prompt and decoding policy. Save per-task:

- stable task ID;
- seed and sample index;
- raw completion;
- total/proved VC counts and failure names;
- full-proof, integrity, crash, timeout count;
- input/output tokens and wall-clock scoring time;
- source/config/toolchain identifiers.

Use at least four samples per validation task for a stochastic policy. Report
pass@1 and the empirical probability of at least one proof in the group, but do
not confuse the latter with single-attempt reliability.

## Training design

- Canonical config: `environments/acsl-c/configs/train.toml`.
- The canonical config now targets Qwen2.5-Coder-7B at 2,048 tokens. A managed
  T4 passed a one-step 4-bit/LoRA feasibility probe for both 7B and 14B, but
  only 7B has enough expected margin for multi-sample GRPO; 14B is an optional
  ablation, not the primary claim-bearing run.
- Run at least three independent training seeds.
- Use group size 8 initially; log the fraction of groups with zero reward
  variance. If that fraction is high, change task sampling or exploration only
  in a new protocol revision.
- Shuffle deterministically. Never infer learning from a stream whose task
  difficulty changes with step.
- Evaluate validation at fixed intervals and save checkpoints at the same
  intervals.
- Choose the checkpoint using a rule fixed before looking at test results, for
  example maximum validation full-proof rate with integrity violations equal to
  zero; break ties by mean VC fraction, then earliest step.
- Keep full-specification mode disabled until executed negative spectests exist.

## Primary and secondary endpoints

Primary endpoint:

```text
paired change in test full-proof rate at one sample per task
```

Compare the frozen base model and selected checkpoint on identical task IDs and
predeclared decoding seeds.

Secondary endpoints:

- mean VC fraction;
- integrity violation rate;
- parse/gate success rate;
- timeout and crash rates;
- solver wall time;
- output-token length;
- multi-turn success versus number of verifier calls;
- rates by difficulty and feature strata.

Report paired task-level differences with bootstrap confidence intervals. For a
binary pass rate, also report exact counts and a binomial interval. With only 48
test tasks, emphasize uncertainty and effect size; a p-value cannot rescue an
underpowered or post-hoc design.

## Reward-hacking audit

For every selected checkpoint:

1. automatically diff annotations and immutable context;
2. rerun a random sample with a cold verdict cache;
3. manually inspect all surprising high-reward/low-quality cases;
4. run trivial-body vacuity probes where applicable;
5. categorize failures by parse, functional VC, RTE, termination, timeout, and
   infrastructure error;
6. compare reward with output length and VC count;
7. retain raw source and diagnostics for reproducibility.

No result is called a success if full-proof improves while integrity violations,
vacuity, or judge errors materially worsen.

## Multi-turn evaluation

Use the Bash harness on validation first. The task writes `solution.c` and
`verify.sh` into an isolated runtime. The model may edit only the target body,
run the verifier, and iterate for at most eight model turns. Score the final
`solution.c` independently with the task's runner; never trust the agent's own
claim or its potentially edited `verify.sh`.

Compare single-turn and multi-turn under matched total-token budgets. Report
success by verifier-call count so an apparent gain is not hidden compute alone.

## Final-test procedure

1. Freeze the repository commit and protocol revision.
2. Freeze the checkpoint-selection result using validation only.
3. Build/pull the recorded image digest.
4. Run the test split exactly once per declared seed/sample.
5. Make no prompt, reward, timeout, or parser change after seeing results.
6. If an infrastructure defect invalidates the run, document it, repair it, bump
   the protocol version, and treat the previous test as development exposure.

## Minimum evidence for the first public claim

The project may claim a training improvement only when:

- the primary endpoint improves consistently across at least three seeds;
- confidence intervals and exact task counts are reported;
- integrity violations are zero;
- the fresh test split—not historical validation—supports the conclusion;
- reward and evaluation use the same pinned judge policy;
- limitations around spec completeness and the trusted verifier stack are
  prominent.
