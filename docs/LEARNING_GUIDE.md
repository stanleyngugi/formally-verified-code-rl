# Learning Guide: Verified Reinforcement Learning for Code

> Living draft. Last substantial revision: 2026-09-09. This is the teaching
> spine for the project; update it whenever the implementation or our
> understanding changes.

## 1. What we are building

The project trains a language model to produce C programs that a formal verifier
can prove correct. The immediate task is deliberately narrower than “write any
correct program”: the dataset supplies a C function signature and ACSL
specification, and the model fills only the function body.

The loop is:

```text
task + fixed ACSL contract
        ↓
model proposes a C function body
        ↓
Frama-C/WP generates mathematical proof obligations
        ↓
Alt-Ergo and Z3 try to discharge the obligations
        ↓
proof progress becomes an RL reward
        ↓
GRPO updates the model toward proposals with higher reward
```

The key idea is that unit tests check selected examples, while a deductive proof
checks every input covered by the assumptions. The important qualification is
“covered by the assumptions”: a weak, contradictory, or vacuous specification
can make useless code easy to prove. A proof is only as useful as its statement.

## 2. The formal-verification layer

### 2.1 ACSL contracts

ACSL is a specification language embedded in C comments. A simple contract is:

```c
/*@
  requires x >= 0;
  ensures \result * \result <= x;
  ensures x < (\result + 1) * (\result + 1);
*/
int isqrt(int x) {
  // implementation to synthesize
}
```

- `requires` is the precondition: what callers must establish.
- `ensures` is the postcondition: what the function promises on return.
- `assigns` defines the permitted memory footprint.
- loop invariants describe facts true before and after every iteration.
- a loop variant is a non-negative quantity that decreases, proving termination.

The contract is not a test. It denotes a logical implication: if the
precondition and the language semantics hold, the postcondition must hold.

### 2.2 Weakest preconditions and verification conditions

Frama-C's WP plug-in works backward from the desired postcondition through the
program. Informally, for a statement `S` and desired result `Q`, the weakest
precondition `wp(S, Q)` is the least condition that must hold before `S` to make
`Q` true afterward.

For an assignment:

```text
wp(x = e, Q(x)) = Q(e)
```

For a conditional:

```text
wp(if b then S1 else S2, Q)
  = (b  ⇒ wp(S1, Q)) ∧ (¬b ⇒ wp(S2, Q))
```

Loops cannot generally be unrolled forever, so they need invariants. The
verifier creates obligations such as:

1. the invariant holds before the loop;
2. one iteration preserves it;
3. invariant plus loop exit implies the postcondition;
4. the variant proves termination;
5. every operation satisfies run-time safety conditions.

This explains why a solution may prove 18/20 goals: most of its reasoning is
right, but perhaps one invariant is too weak and one array access is not proved
in bounds.

### 2.3 WP versus RTE

`-wp-rte` asks Frama-C to generate run-time error obligations in addition to
functional correctness goals. These include integer division by zero, invalid
pointer access, and some overflow conditions under the configured C model.
Without RTE goals, a function could satisfy a mathematical postcondition only
because its C execution has undefined behavior.

### 2.4 What “verified” means here

The trusted chain contains Frama-C's C semantics and VC generator, its Why3
translation, the SMT solvers, the pinned binaries, and our parsing/scoring code.
The current project is therefore a Level-1 SMT-backed verification system, not a
small-kernel proof assistant whose proof objects are independently replayed.

The honest claim is:

> Under the pinned Frama-C semantics and supplied ACSL contract, all generated
> WP and RTE obligations were reported proved by the configured solvers.

That is strong and useful. It is not the same as proving that the ACSL contract
captures the stakeholder's real intention.

## 3. Specification quality and reward hacking

### 3.1 Vacuity

Suppose the precondition is contradictory:

```c
/*@ requires x > 0 && x < 0; ensures \result == 42; */
```

No legal call exists, so every implementation satisfies the contract. Another
failure is a postcondition too weak to characterize the desired behavior, such
as saying only that `max(a,b) >= a` while omitting the corresponding relation to
`b` or equality to an input.

Our first CASP ingestion found that 61 of 399 locally verified candidates
(15.3%) still verified after replacing function bodies with trivial stubs. Those
records were quarantined. This was evidence, not a theoretical concern.

The vacuity probe is conservative. Passing it does not prove semantic
completeness; it only rules out one particularly damaging class of weak specs.

### 3.2 Fixed-annotation integrity

In hints mode, the annotation is ground truth. The model may edit the target
function body, including loop annotations inside that body, but may not edit:

- the contract;
- includes or declarations;
- the function signature;
- other functions or global code.

The integrity checker masks strings and comments, identifies real C function
bodies, and compares everything outside the target body. It separately hashes
ACSL annotations. An integrity failure makes every reward component zero.

This closes a classic verifier-game: delete a difficult postcondition, obtain a
perfect proof on an easier program, and receive reward for solving the wrong
problem.

### 3.3 Negative spectests

For future full specification synthesis, structural integrity is unavailable
because the model itself writes the contract. The leading approach is to create
“impossible” input/output behaviors and require the candidate specification to
reject them. A strong spec accepts intended behaviors and excludes bad ones.

This is inspired by SpecRL. It is not fully implemented here yet. The code
therefore disables full-mode training by default and assigns no speculative
strength credit to unexecuted spectests. This is an example of a sound stub: an
unimplemented defense cannot silently masquerade as a working reward.

## 4. The reinforcement-learning layer

### 4.1 A rollout and its reward

A rollout is one model attempt at one task. In single-turn mode the model emits a
complete source file. In agentic mode it can inspect `solution.c`, edit it, run
`./verify.sh`, read failures, and try again.

The reward is currently:

```text
R = 0.10 gate
  + 0.50 proved_VCs / total_VCs
  + 0.20 all_VCs_proved
  + 0.20 specification_strength
```

For fixed-annotation hints tasks, specification strength is the binary integrity
result. Any integrity failure zeros all components, so the weighted expression
is only evaluated for a submission to the original problem.

Why dense partial credit matters: a binary all-or-nothing reward treats 0/40 and
39/40 proved goals identically. VC fraction exposes useful progress. Why the
binary full-proof bonus remains: it preserves a sharp preference for actually
finishing the proof.

### 4.2 GRPO intuition

Group Relative Policy Optimization samples a group of completions for the same
prompt. If their rewards are `r_1 ... r_G`, a basic group-relative advantage is:

```text
A_i = r_i - mean(r_1 ... r_G)
```

The optimizer raises the likelihood of above-group-average actions and lowers
the likelihood of below-average ones. This avoids training a separate learned
value model, but it creates practical constraints:

- if every member has the same reward, the group has almost no learning signal;
- task difficulty must be mixed carefully, because easy and hard batches are
  not comparable as a raw learning curve;
- group size trades exploration and memory/throughput;
- completion length can interact with loss normalization and induce bias;
- solver timeouts add noise and must be monitored separately from logical
  failures.

The old 12-step smoke moved from reward 0.375 to 0.875, but tasks were streamed
in difficulty-correlated order. It proves the pipeline can train; it does not by
itself prove the model learned.

### 4.3 Why three seeds and a held-out test matter

RL curves are noisy. A convincing claim needs independent random seeds and a
test set that was never used to tune prompts, rewards, hyperparameters, or
checkpoint selection. This repository now treats the historical evaluation set
as `validation`, because it has already influenced development, and carves a
fresh stratified `test` split from the old training pool.

The scientific unit is not “the last training step looked high.” It is the
difference between a frozen base model and selected trained checkpoints on the
same held-out examples, with uncertainty intervals and task-level paired data.

## 5. Prime-RL and Verifiers architecture

There are four distinct pieces:

1. **Taskset** loads records and constructs typed tasks.
2. **Harness** controls how the model acts. `null` is single-turn text;
   `bash` is a multi-turn coding agent with shell/edit tools.
3. **Runtime** is where tools and the verifier execute. Docker or a Prime
   sandbox isolates untrusted output; subprocess is for trusted local debugging.
4. **Prime-RL orchestrator** samples rollouts, asks the task to score them,
   computes GRPO advantages, and sends training batches to the trainer.

The project pins `prime-rl` v0.9.0 and the exact Verifiers commit vendored by
that release. This is necessary because configuration and Python APIs evolve
quickly. A reproducible environment is a tuple of code commit, model revision,
dataset manifest, container digest, solver versions, config, and seed—not merely
one Python package version.

## 6. Code-reading map

- `environments/acsl-c/src/acsl_c/taskset.py`: task schema, prompts, runtime
  setup, four reward functions, split selection.
- `integrity.py`: lexical masking, function-body localization, immutable-context
  and annotation checks.
- `verify_script.py`: self-contained script executed inside the runtime; invokes
  Frama-C once and emits a compact JSON verdict.
- `framac.py`: converts Frama-C report JSON/stdout into a stable `Verdict`.
- `cache.py`: SQLite/WAL cache keyed by source and the whole verifier identity.
- `spectests.py`: conservative specification-strength policy.
- `scripts/ingest_casp.py`: downloads, re-verifies, probes vacuity, quarantines.
- `scripts/build_splits.py`: deterministic eligibility, deduplication, and split
  manifest.
- `configs/train.toml`: canonical single-turn GRPO experiment (Qwen2.5-Coder-7B,
  conservative 2,048-token context); `grpo_smoke_acslc_16gb.toml` remains the
  historical 1.5B smoke configuration.
- `configs/agentic_eval_v0_9.toml`: multi-turn validation with the Bash harness.

## 7. How to interpret common verifier failures

| Symptom | Likely meaning | First response |
|---|---|---|
| parse failed, 0 goals | malformed C/ACSL or truncated model output | inspect raw completion and stderr |
| most goals prove, invariant goals fail | loop invariant is missing or too weak | derive initialization/preservation/exit facts |
| RTE goal fails | possible undefined behavior | add guards or change implementation |
| timeout | proof search was inconclusive, not necessarily false | simplify code/lemma, inspect specific goal, rerun under policy |
| proof succeeds after annotation change | wrong problem was solved | integrity gate must make reward zero |
| trivial stub verifies | likely weak/vacuous specification | quarantine and strengthen the spec |

## 8. A practical learning path

1. Read one small task and manually translate every ACSL clause into plain
   English.
2. Predict the WP obligations for a branch-only function, then compare with the
   report.
3. Break the implementation in three ways: wrong answer, overflow, annotation
   deletion. Observe that these are different failure classes.
4. Study a loop task and write an invariant containing initialization,
   preservation, bounds, and the relationship to the desired result.
5. Trace one rollout through `Task.setup`, harness actions, runtime execution,
   parser, rewards, and GRPO advantage.
6. Reproduce the base validation evaluation before attempting training.
7. Only after the protocol is frozen, run multiple training seeds and one final
   test evaluation.

### 8.1 What the Colab experiment teaches

The managed T4 is a useful laboratory, not the judge. A 4-bit Qwen2.5-Coder
7B model used about 5.4 GiB for loading and 7.6 GiB at a real LoRA optimizer
step with a 2,048-token context. That leaves practical room for a small
single-process experiment. The 14B probe also completed at 1,024 tokens, but
its 12.16-GiB peak on a 15-GiB T4 leaves too little margin for GRPO's multiple
rollouts and inference cache; that is why 7B is the default.

The baseline generator first produced an empty file when pointed at the
training JSONL: the manifest's validation IDs live in `casp_eval.jsonl`. This
is a useful data-engineering lesson: always validate content-addressed IDs and
fail before loading an expensive model. `validate_baseline.py` checks this
provenance without pretending to verify the generated C.

Colab has no Docker or Frama-C in the observed managed runtime. Thus a
successful generation cell means “the model emitted text,” not “the program is
correct.” Correctness begins only when the exact captured text is replayed by
the pinned production verifier.

### 8.2 What the production replay teaches

A solver timeout is not the same as a counterexample. It says that the selected
provers did not finish that goal within the policy budget. This distinction
became concrete during the first full-image replay:

- `casp:75` proved 20/21 goals at a 20-second per-goal limit even when run cold
  and alone, but proved 21/21 at 60 seconds. It is logically plausible but is
  not a valid reference for a reward system that always stops at 20 seconds.
- A separate 112-goal task passed one four-worker replay, timed out on another,
  and passed again cold and alone. Competing solver processes changed the
  effective CPU available before the wall-clock limit.
- The final eligibility gate therefore runs one task at a time and records the
  worker count as part of the replay policy. It passed 316/316 references and
  5,205/5,205 goals.

This illustrates three levels of reproducibility. **Logical reproducibility**
fixes the C/ACSL source and prover versions. **Policy reproducibility** also
fixes the prover list, timeout, integer model, and enabled obligations.
**Operational reproducibility** additionally fixes resource-sensitive choices
such as concurrency. Containerizing only the first level is not enough for an
honest RL reward.

The replay exclusion ledger is deliberately separate from the raw corpus. The
source remains available for investigation, while the manifest builder prevents
an unwinnable 20-second task from silently reaching training. If a later image
or policy proves it reliably, the exclusion can be reviewed with both old and
new evidence rather than erasing history.

## 9. Questions this guide should eventually answer better

- Which C integer/overflow model is enforced for every corpus family?
- Can we extract useful counterexamples, not only named failed goals?
- How should impossible behaviors for spectests be generated and independently
  validated?
- Which proof obligations are most predictive of human-perceived task
  difficulty?
- Does multi-turn verifier feedback improve final correctness enough to justify
  its additional token and sandbox cost?
- Can sampled solver results be certificate-checked by a smaller trusted kernel?

## 10. Compact glossary

- **ACSL:** contract language for C used by Frama-C.
- **VC:** verification condition, a logical goal whose proof supports program
  correctness.
- **WP:** weakest-precondition calculus and Frama-C plug-in.
- **RTE:** run-time error obligations.
- **SMT solver:** automated engine for satisfiability modulo theories.
- **Vacuity:** a proof succeeds for reasons that do not establish meaningful
  behavior.
- **Rollout:** one sampled model trajectory on a task.
- **Harness:** program that mediates model actions and tools.
- **Runtime:** isolated machine/process where those actions execute.
- **GRPO:** group-relative policy optimization.
- **Holdout:** data excluded from development and used only for final evaluation.
- **Goodhart's law:** optimizing a proxy can make it cease to reflect the real
  goal.

## Sources for further study

- [Frama-C ACSL overview](https://frama-c.com/acsl.html)
- [Frama-C WP manual](https://frama-c.com/download/wp-manual-27.1-Cobalt.pdf)
- [Frama-C E-ACSL plug-in](https://www.frama-c.com/fc-plugins/e-acsl.html)
- [Prime Verifiers overview](https://github.com/PrimeIntellect-ai/verifiers/blob/main/docs/overview.md)
- [Prime Verifiers training](https://docs.primeintellect.ai/verifiers/training)
- [Prime-RL configuration guide](https://github.com/PrimeIntellect-ai/prime-rl/blob/main/docs/configuration.md)
- [SpecRL](https://arxiv.org/abs/2604.05820)
- [DAPO](https://arxiv.org/abs/2503.14476)
- [Understanding R1-Zero-Like Training / Dr. GRPO](https://arxiv.org/abs/2503.20783)
