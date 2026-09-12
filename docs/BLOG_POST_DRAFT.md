# Formally Verified C: training code models against proofs, not just tests

> Publication draft for the first release of
> [Formally Verified Code RL](https://github.com/stanleyngugi/formally-verified-code-rl).
> This article focuses on the concrete C/ACSL environment. Verus and Dafny are
> future sibling environments, not capabilities claimed by this release.

## The short version

I built **Formally Verified C**, a reusable reinforcement-learning and evaluation
environment in which a model completes C functions under fixed ACSL contracts.
The score is computed by Frama-C's weakest-precondition engine and
runtime-error analysis, not by trusting model-written tests or a textual claim
that the answer is correct.

The initial public Core-v1 release is deliberately modest in dataset size and
strong in infrastructure evidence:

- 64 project-authored, Apache-2.0 tasks with family-isolated train,
  validation, and test splits;
- 64/64 reference implementations formally discharged under the pinned judge,
  covering 296/296 proof goals and 84/84 runtime-safety goals with no solver
  timeouts;
- 64/64 deliberately wrong but parseable implementations rejected by a
  deterministic negative gate;
- a fail-closed result parser, immutable-contract checks, a policy-keyed cache,
  container isolation, and multi-turn trace history;
- a Verifiers v1 package that was pushed privately, pulled into a clean
  directory, audited, installed from that exact downloaded source, and tested
  42/42 before its public listing;
- no CASP-derived task payload in the public package or Hub source archive.

This is an environment release, not a claim that one GRPO run created a new
state-of-the-art C model. The environment is the instrument that makes such
training research possible and auditable.

## One project, one concrete first environment

The umbrella project is **Formally Verified Code RL**. Its purpose is broader
than any one programming language: build RL environments around semantic
judges that can establish program properties over a modeled input domain.
The first—and currently implemented—environment is **Formally Verified C**.

That naming boundary matters. `formally-verified-code-rl` is the engineering
repository and long-term research program. `formally-verified-c` is an
independently versioned package and Prime environment. Future work may add
siblings such as `formally-verified-verus` and `formally-verified-dafny`, but
those should earn their own evidence rather than inheriting the C
environment's claims.

Most code-reinforcement-learning environments ask a model to write a program,
run a suite of tests, and use the pass rate as reward. That is useful, but a test
suite samples behavior. A program can pass every sampled input and still be
wrong elsewhere.

This project explores a different judge: deductive verification. The first
environment, Formally Verified C, gives a model a C function with a fixed ACSL contract and
asks it to complete only the implementation body. Frama-C's WP plugin generates
proof obligations, including runtime-error obligations, and sends them to
pinned automated provers. The reward comes from the independently parsed proof
result—not from the model's claim that its code is correct.

I would describe this carefully as follows: “To our knowledge, Formally Verified C is among
the earliest open RL environment packages for generating C implementations
from fixed ACSL contracts, with reward computed from Frama-C WP and
runtime-error proof obligations in an isolated, version-pinned judge.” A dated
September 2026 literature pass found adjacent verifier-reward work in Dafny and
Lean, broad vericoding benchmarks in Dafny, Verus/Rust, and Lean, and VeCoGen—the
closest C predecessor—which already performs iterative LLM generation and
repair with Frama-C feedback. What the search did not find was a directly
comparable public C/ACSL/Frama-C **RL environment package**. That search is
evidence, not proof of nonexistence, so “the first” or “the only one” would be
needlessly brittle. The contribution is an installable taskset, isolated and
reproducible scoring, an auditable data boundary, staged reward, multi-turn
lifecycle, and explicit defenses against common reward-hacking paths—not the
first ever connection between an LLM and Frama-C.

## Where the problems come from

The prompts do not invent the problems. During environment development, each
research task started from a CASP C/ACSL source record. Ingestion ran the
complete source under the pinned Frama-C policy, probed for vacuous or
inconclusive specifications, and recorded why rejected records were
quarantined. For an admitted task, the target body was removed and replaced by
a TODO. The remaining file—contract, declarations, includes, and non-target
code—became the immutable problem statement.

That corpus was technically excellent for finding engineering failures, but
the snapshot did not preserve the original repository, path, revision, author,
and license for each Stack-derived record. The public v0.1 therefore uses a
separately versioned, project-authored core corpus with explicit provenance;
CASP remains a non-bundled research adapter pending permission or provenance
recovery. In other words, the data boundary fails closed for the same reason
the proof parser does: a convenient “open” label is not evidence of a specific
redistribution right.

The prompt is only an interface over that task. A single-turn model returns the
complete C file. In agentic mode, a bash harness seeds `solution.c`, gives the
agent a diagnostic `verify.sh`, and permits iterative edits. In both cases the
final source is rescored by the environment's own runner. Editing `verify.sh`,
printing a fake success message, or changing the contract does not create proof
reward.

The pipeline is:

```text
admitted source record
  -> pinned replay and vacuity filtering
  -> deterministic body-removal transformation
  -> prompt or agent workspace
  -> candidate C source
  -> immutable-context integrity gate
  -> isolated Frama-C WP + RTE
  -> fail-closed verdict parser
  -> staged reward and diagnostics
```

### What a task actually looks like

A task contains a complete translation unit with an ACSL contract and one
target function body removed. Conceptually, it looks like this:

```c
/*@ requires x >= -1000 && x <= 1000;
    ensures \result == x + 1;
    assigns \nothing;
*/
int increment(int x) {
  /* TODO: complete this body */
}
```

The model must return the completed C file. The fixed-contract integrity layer
checks that annotations, declarations, includes, and non-target code have not
changed. Only then does the judge invoke Frama-C. This prevents an apparently
successful but meaningless answer such as weakening `ensures` to `\true`,
deleting the contract, or replacing the task with an easier function.

Core-v1 is not 64 arbitrary row-level mutations randomly scattered across
splits. Every task has a semantic family and a derivation family, and related
variants remain within one split. That reduces the easiest form of train/test
leakage while keeping this small first corpus useful for smoke training,
environment evaluation, and adversarial testing.

## Why a staged reward

A binary proof reward is truthful but sparse. ACSL-C exposes four components:

1. a parse/compile/non-empty-proof gate;
2. the fraction of generated verification conditions proved;
3. an all-goals full-proof indicator; and
4. a specification-strength guard.

The released default weights are:

```text
0.10 * parse_compile_and_nonempty_goal_gate
+ 0.50 * proved_verification_condition_fraction
+ 0.20 * all_goals_fully_proved
+ 0.20 * fixed_specification_integrity
```

The components are intentionally not interchangeable. The gate prevents a
zero-goal or malformed report from earning credit. Fractional VC progress gives
a learner a denser signal. Full proof distinguishes complete semantic success
from partial progress. The integrity term prevents reward from being earned by
changing the problem. A timeout, process crash, missing JSON report, malformed
Boolean, or empty goal set is a failure—not partial proof.

For the released fixed-contract task family, specification strength means that
all annotations and all code outside the target body remain unchanged. The
model cannot earn an easier proof by deleting or weakening the postcondition.
A future full-specification-synthesis family would need stronger semantic tests;
that mode is deliberately disabled even though the executor contract now has a
clean accepted control and rejected negative fixture.

Operational metrics—timeouts, crashes, failed goals, source digests, and the
per-turn verdict history—stay separate from reward. This matters for credit
assignment: a trace can show a proof becoming invalid and later being restored,
instead of hiding the sequence behind one final scalar.

## What had to be hardened

Formal verification does not automatically make an RL environment safe. The
judge still has an attack surface:

- A malformed JSON field such as the string `"false"` must never be treated as
  Boolean success.
- A crash, timeout, missing report, or zero-goal report must fail closed.
- A cached verdict must be invalidated when the source, solver policy, timeout,
  toolchain, or exact runner script changes.
- Model-controlled code and preprocessor directives must not run on the host.
- The final judge must ignore agent-edited diagnostic scripts.
- Concurrent workers must not corrupt or cross-contaminate the verdict cache.

The release runner therefore executes in a bounded container with an empty
network allow-list. A smoke probe confirmed both that direct egress is blocked
and that the host workspace is absent. The verifier runner is written only for
the scoring call under an unpredictable temporary name and then removed. The
project's own SQLite/WAL cache is fully policy-keyed, so Frama-C's separate
implicit WP cache is disabled for clearer reproducibility.

One integration bug justified this level of testing. Verifiers' generic
PEP-723 helper tries to prepare and upgrade `uv` before running a script. That
is reasonable for arbitrary dependency-bearing scripts, but this judge runner
has no third-party dependencies and the hardened image runs as an unprivileged
user. The preparation attempted package-manager access and failed before
Frama-C started. Executing the dependency-free runner with the image's pinned
system Python removed that unnecessary network/install dependency. The same
official model-free validation then passed 3/3 tasks in fresh containers.

### The release artifact was tested as an outsider would receive it

The final publication process found three problems that ordinary
in-repository testing would have missed.

First, Prime's source uploader reads the `.gitignore` located inside the
environment directory, not the umbrella repository's root ignore file. The
first private source archive therefore included research-only directories even
though the wheel itself was clean. A dedicated environment-level publication
boundary now excludes research shards, quarantine files, local baselines,
historical artifacts, and CASP-derived records. The corrected archive contains
only Core-v1 under its data directory.

Second, Prime does not copy an arbitrary root `LICENSE` file into its source
archive. Package metadata that referred to that physical file could build in
the repository but not from a clean Hub pull. The package now uses the SPDX
license expression `Apache-2.0`; the canonical repository retains the complete
license text. A later clean pull built successfully.

Third, several tests still addressed the private CASP research split. They
passed locally and failed correctly in the public-only archive. Those tests now
exercise the bundled Core-v1 manifest, so the exact source downloaded from the
Hub passes all 42 tests without private data. These are mundane packaging bugs,
but finding them is part of what “reproducible environment” should mean.

## Evidence at release time

The public v0.1 evidence as of 2026-09-11 is:

- Core-v1 contains 64 project-authored Apache-2.0 tasks: 33 train, 15
  validation, and 16 test, with derivation families confined to one split.
- All 64 references prove: 296/296 proof obligations and 84/84 runtime-error
  obligations, with zero solver timeouts.
- All 64 deliberately wrong implementations parse and compile, then fail the
  deterministic WP+RTE/Qed negative gate with zero timeouts.
- The clean wheel exports the Verifiers v1 package loaders, loads Core-v1 from
  site-packages, and contains no CASP-derived task payload.
- The local suite passes 42 tests across parsing, integrity, task loading,
  provenance, payload auditing, spectests, caching, concurrency, preflight
  behavior, and trace history.

The earlier research-engineering evidence remains useful but is not the public
corpus claim:

- The CASP research split contains 221 training, 47 validation, and 48 fresh
  test tasks: 316 admitted tasks total, with 22 exclusions recorded.
- A cold serial replay proved all 316 references: 5,205/5,205 proof goals and
  1,264/1,264 runtime-error goals, with zero solver timeouts.
- The judge image is pinned at
  `sha256:b7d7111eac04eb09405842b64af5084f671c8815f90a3d9ea7f5de92f0bcd593`.
- Prime-RL v0.9.0 and its exact vendored Verifiers revision resolve the training
  configuration in a dry-run.
- Verifiers v1 model-free validation passes 3/3 gold tasks through Docker.
- That CASP-derived corpus is not bundled or redistributed in the public wheel.

The public compact record is
[`core-v1-public-release-evidence.json`](https://github.com/stanleyngugi/formally-verified-code-rl/blob/main/environments/acsl-c/artifacts/core-v1-public-release-evidence.json).
It records dataset, manifest, proof, negative-test, test-suite, and wheel
digests. The older `release_evidence_2026-09-10.json` is explicitly a
research-engineering record for the non-public CASP adapter and must not be
cited as the public corpus count.

## What the Colab GPU established—and did not establish

The model side was tested on a 16 GB-class Tesla T4. A 4-bit
Qwen2.5-Coder-7B model with LoRA completed generation plus optimizer steps, and
a serial two-rollout/one-update plumbing canary completed under the memory
budget. A 14B 4-bit model also fit a shorter 1,024-token probe, but 7B at 2,048
tokens leaves substantially more headroom for rollout generation and is the
more practical default.

Those experiments establish feasibility, not learning. The serial plumbing
rewards were explicitly labelled `stub_not_verifier` because managed Colab did
not host the Docker judge. There is no claim here that GRPO improved proof rate.
Making that claim would require frozen checkpoint selection, verifier-scored
rollouts, multiple seeds, and a one-time held-out test evaluation.

This distinction is useful beyond this project. An environment can be correct,
publishable infrastructure without already proving that a particular training
algorithm improves a particular model. Prime Intellect's
[community environments](https://github.com/PrimeIntellect-ai/community-environments)
and Hugging Face's [OpenEnv](https://huggingface.co/blog/openenv) both frame the
environment as a reusable task/reward interface. A training paper is a consumer
of that interface, not a prerequisite for defining it.

## What comes next

The clean data boundary is now implemented. Core-v1, its replay and negative
evidence, and the CASP-excluding wheel audit all pass. GitHub is the canonical
engineering record, GHCR holds the judge by digest, and Prime's Environments
Hub provides the installable package and discovery page. Both listings are
public, and an anonymous Docker pull of the immutable judge digest succeeds.
Before changing the listings to public, I pulled Prime v0.1.6 into a pristine
directory: its source and secret audits passed, its full Linux suite passed
42/42 tests, and its
public loader constructed the requested taskset. I inspected a second pristine
pull before importing its modules and confirmed that the archive itself
contained neither bytecode nor research-only payloads.

The CASP permission/provenance request continues in parallel. If it is resolved,
the 316-task validated corpus can become a separately versioned expansion pack
rather than silently changing the public core.

The optional research track is more ambitious: compare single-turn and
multi-turn solving at matched token budgets, study which partial VC signals
produce useful credit assignment, and run a controlled multi-seed GRPO study
against the untouched test split. A second environment could then apply the
same architecture to Verus and Rust.

The broader idea is simple: when a domain has a trustworthy automated prover,
we can train models against proof obligations rather than only against examples.
The hard part is not calling the prover. It is building the data, isolation,
reward semantics, and evidence discipline around it so that “verified reward”
means what it says.

## Try the released environment

The three publication surfaces have different jobs:

- [GitHub](https://github.com/stanleyngugi/formally-verified-code-rl) is the
  canonical source, design history, evidence, and issue tracker.
- [Prime Intellect Environments Hub](https://app.primeintellect.ai/dashboard/environments/stanley-ngugi/formally-verified-c)
  is the installable Verifiers v1 environment and discovery page.
- [Hugging Face](https://huggingface.co/datasets/stan4u/formally-verified-c-core-v1)
  mirrors the exact redistributable Core-v1 data and dataset card.

With Python 3.11–3.13 and `uv`/Prime installed:

```bash
prime env install stanley-ngugi/formally-verified-c
```

The recommended environment package is v0.1.6. Core-v1 remains dataset v0.1.4
because the two intervening package releases changed runtime identity and
archive hygiene, not any task record or split.

For source development:

```bash
git clone https://github.com/stanleyngugi/formally-verified-code-rl.git
cd formally-verified-code-rl/environments/acsl-c
uv sync --extra test
uv run pytest -q
```

The pinned judge image is published as
`ghcr.io/stanleyngugi/formally-verified-c-judge:0.1.4`. The immutable release
reference is `ghcr.io/stanleyngugi/formally-verified-c-judge@sha256:b7d7111eac04eb09405842b64af5084f671c8815f90a3d9ea7f5de92f0bcd593`.

## What this release claims—and what it does not

It is reasonable to say:

- this is a technically validated, reusable RL/evaluation environment for C
  completion under fixed ACSL contracts;
- successful reward is backed by Frama-C WP+RTE proof obligations under the
  declared pinned policy;
- the public Core-v1 references and negative controls pass the published
  machine-verification gates;
- to our knowledge, this is among the earliest open C/ACSL/Frama-C RL
  environment packages of this form.

It would be wrong to say:

- the verifier stack itself is formally verified;
- C outside the modeled subset or behaviors outside the ACSL/Frama-C semantics
  are automatically covered;
- Core-v1 has already received independent expert review;
- the 64 tasks represent comprehensive real-world C development;
- a particular RL algorithm or model has been shown to improve from training;
- no related system exists anywhere because a literature search did not find
  an identical package.

The trusted computing base includes Frama-C's models and VC generator, Why3,
the selected automated provers, the container/runtime boundary, and the
environment's result parser. The release calls this “machine-reviewed and
machine-verified,” invites independent expert review, and treats that review as
a future evidence upgrade rather than silently assuming it.

## A practical roadmap beyond the launch

The next C milestones are higher-value task diversity, real multi-function and
long-horizon problems, independent expert review, richer non-vacuity checks,
and controlled comparisons of single-turn versus agentic repair. If CASP's
record-level provenance or permission becomes sufficient, its already replayed
316-task research corpus can become an explicitly attributed expansion pack;
it will not silently replace Core-v1.

Only after the environment and evaluation protocol are frozen does a larger
GRPO study become scientifically useful: multiple seeds, verifier-scored
rollouts, frozen checkpoint selection, matched compute, and one-time held-out
evaluation. Scaling async inference across more GPUs is a throughput project,
not a prerequisite for the correctness of this release.

Beyond C, the umbrella project can apply the same discipline to Verus and
Dafny: independent package names, pinned semantic judges, language-specific
integrity policies, isolated data packs, executable negative cases, and honest
claim boundaries. The reusable idea is not “Frama-C everywhere.” It is the
release method: treat the prover, task transformation, reward parser, runtime,
data rights, and evidence as one auditable system.
