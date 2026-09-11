# RL environment hubs: evidence requirements and implications for ACSL-C

## Executive finding

ACSL-C should be presented as a verified environment and evaluation harness,
not as a completed claim about RL training performance. The relevant public
guidance from PrimeIntellect's community-environments repository asks for a
canonical environment package, documented reward functions/metrics, passing
repo tests, and a local `vf-eval` run whose outputs are inspected and included.
It does not require a 500-step or multi-seed training study for every new
environment. Hugging Face OpenEnv follows the same infrastructure-first shape:
standard environment APIs, isolation/deployment assets, CLI validation, and
tests. A long training run becomes necessary only if we claim that training a
model in ACSL-C improves a learning metric.

This conclusion is about the scope of an environment submission. It does not
lower the bar for verifier correctness. Because ACSL-C executes model-written C
and turns proof outcomes into reward, its required tests should be more
adversarial than a toy environment's happy-path smoke.

## What the hubs actually ask for

### Prime-RL and Verifiers community environments

The Prime community-environments contributor guidance specifies a canonical
`environments/<slug>/` layout, a `pyproject.toml`, a `load_environment(...)`
entrypoint, and a README that documents dependencies, arguments, reward
functions, and metrics. Rewards should be represented in a `Rubric` and kept
self-contained. The standard validation path is a small `vf-eval` invocation,
inspection of the resulting `outputs/`, and passing repository-level tests.
The guidance explicitly says tests inside an individual environment are
optional; full rollout/loading behavior belongs to global tests and `vf-eval`.

The practical implication is not “skip testing.” It is “test the environment
contract at the right layer”: package/API checks and a small standard evaluation
are the submission gate, while large-scale training is a separate research
claim. ACSL-C's adversarial verifier tests are an appropriate strengthening of
this baseline because the environment has a high-impact, machine-checkable
reward channel.

### Prime-RL runtime topology

Prime-RL documents three cooperating processes: vLLM inference, a CPU
orchestrator that owns environment workers and computes rollout data, and a
trainer. Its overview states that single-GPU runs are supported for debugging,
while production RL is typically separated into inference and trainer capacity.
The scaling guide says the RL launcher defaults to one trainer GPU and one
inference GPU, but supports single-node and multi-node placement. The inference
guide describes single-node inference as useful for debugging and small
experiments.

This matters for our evidence labels:

| Evidence | What it proves | What it does not prove |
|---|---|---|
| CPU/reference replay | The pinned judge accepts the admitted references | Model learning or GPU throughput |
| Managed-Colab generation | Model loading, prompt/output protocol, memory envelope | Container isolation, Frama-C availability, async Prime topology |
| One-GPU serial canary | Trainer/model/verifier components can be time-shared and a synchronous learning signal can be tested | Equivalence to asynchronous two-process RL |
| Canonical two-plane run | End-to-end rollout, verifier, advantage, and trainer integration | Statistical learning improvement unless the run is designed for that claim |
| Multi-seed held-out study | A training claim under a declared protocol | General correctness of the environment outside tested threats |

Prime's own scaling options—activation checkpointing/offload, optimizer
offload, LM-head chunking, and inference KV-cache offload—make a one-GPU
component or serial ablation reasonable. They do not erase the semantic
difference between serial time-sharing and an asynchronous trainer/inference
deployment.

### Hugging Face OpenEnv

OpenEnv defines a Gymnasium-style `step()`, `reset()`, and `state()` interface
for agentic execution environments. Its stated goals include making
environments isolated, secure, deployable, and usable over HTTP/Docker. The
builder workflow scaffolds `openenv.yaml`, `pyproject.toml`, lock/deployment
assets, and a server; `openenv validate` checks required files and entrypoints
and exits non-zero for structural issues. OpenEnv also documents pytest-based
testing, with environment-specific dependencies installed as needed.

Again, the explicit work is packaging, protocol, deployment, validation, and
tests. The project does not define a mandatory long RL campaign as the gate for
creating or sharing an environment.

### NVIDIA NeMo Gym

NeMo Gym's current environment documentation makes the same architectural
separation unusually explicit: an environment contains the dataset, agent
harness, verifier, and state, while the model is external. Its contribution
guide says that adding a training environment has the same local-correctness
requirements as adding a benchmark: the manifest must validate and the verifier
fixture must pass. It lists example rollouts, reward profiling, and
training-based validation as optional stages, and says optional rollout evidence
is not required to publish or merge. The verifier fixture itself is concrete:
full-reward, zero-reward, malformed-input, and (for seeded environments)
determinism cases.

That is almost exactly the standard we want here. The “problem” belongs to the
dataset/task metadata; prompts and harness behavior are part of the agent
interface; the verifier is the trusted measurement boundary; and training is a
separate, optional validation of learning utility.

## Where ACSL-C's “problems” originate

The model-facing prompt is only one layer. The semantic task originates in an
admitted CASP C/ACSL source pair. The ingestion pipeline re-runs Frama-C under
the pinned policy, records flips, and probes vacuity. It then removes the target
implementation body to produce `skeleton_c`. The taskset wraps that skeleton in
one of two interfaces:

1. **Hints mode:** a system instruction plus a user message containing the
   skeleton; the model returns a complete `solution.c` text.
2. **Agentic mode:** the runtime seeds `solution.c` and `verify.sh`; the model
   edits the target body and uses verifier diagnostics over several turns.

The prompt can cause interface failures—unclear boundaries, extraction errors,
or a poor feedback protocol—but it cannot establish proof. The scorer checks
fixed context, runs the independent Frama-C WP+RTE command, parses the report,
and applies the reward rubric. Therefore:

- a prompt bug is an interface defect;
- a skeleton/parser bug is a task-construction defect;
- a weak contract or missing negative case is a specification/reward defect;
- a forged report or edited `verify.sh` is a verifier-integrity threat;
- a sparse final-only reward is a credit-assignment/learning-design issue.

These should be reported and tested separately instead of being collapsed into
“the prompt was bad.”

## Why reward-hacking tests are still required

The absence of a long training requirement does not make reward hacking
optional. Specification gaming is the general phenomenon of achieving a
literal objective through a loophole rather than the intended outcome. DeepMind
describes it as a task-specification and reward-design problem, including the
extreme case of tampering with the reward channel. In ACSL-C, the analogous
threats are contract weakening, vacuous proofs, reading hidden references,
spoofing verifier output, exploiting timeout/parser behavior, and poisoning a
cache.

The right standard is deterministic, executable attack fixtures. Each fixture
should record the attack, source/workspace mutation, expected integrity/verdict
fields, and expected reward components. A model need not discover the attack in
a long RL run for the environment to demonstrate that the attack is rejected.
That is stronger and cheaper evidence than hoping a 500-step run happens to
exercise the vulnerability.

## Why credit-assignment tests are still required

Credit assignment concerns which earlier actions receive learning signal when a
consequence appears later. The literature describes delayed and stochastic
outcomes as a central difficulty; Monte Carlo targets can have high variance,
while TD-style bootstrapping trades variance for bias. In a multi-turn coding
environment, the proof often appears only after a final edit, so we should
measure—not assume—that the reward decomposition helps identify useful edits.

For ACSL-C this means recording source hashes and verifier transitions per turn,
testing no-op/edit/revert sequences, checking that partial VC fractions are
monotonic and distinguishable, and comparing shaping variants under matched
turn/token budgets. These are environment observability and reward-design tests;
they do not require an optimizer to run for hundreds of steps.

## Recommended release sequence

1. **Package/API gate:** clean install, task loading, setup/reset/step/teardown,
   README, config, and an equivalent `vf-eval` smoke with inspected outputs.
2. **Judge gate:** preserve the image digest and manifest; replay references;
   verify fail-closed behavior for parse errors, crashes, timeouts, zero goals,
   and integrity violations.
3. **Attack gate:** execute fake-verifier, contract-tampering, vacuity,
   filesystem, timeout, cache, and concurrency fixtures.
4. **Credit gate:** emit per-turn source/verdict transitions and run the
   no-op/single-edit/revert/partial-proof/shaping tests.
5. **Negative-spec gate:** execute clean negative spectests before assigning any
   specification-strength reward or making a full-specification claim.
6. **Recommended model-integration gate:** run a small one-GPU serial canary on
   the T4 to test integration, memory, checkpointing, and the learning signal;
   label it `single_gpu_serial`. It is valid synchronous/on-policy evidence.
7. **Optional topology gate:** if asynchronous orchestration or throughput is a
   project objective, run the canonical two-plane Prime-RL deployment on a
   second GPU. This is not required for environment publication.
8. **Research gate (only for a training claim):** select validation once, run
   the declared held-out protocol with multiple seeds, and report confidence
   intervals, contamination controls, reward-hack rate, timeout rate, and
   vacuity rate.

The first five steps are the environment release. Step six is the recommended
first GPU integration experiment. Step seven is optional topology evidence.
Step eight is a separate scientific claim.

## Source inventory

1. PrimeIntellect, `prime-rl` overview: [architecture, GPU minimum, and
   single-GPU/debugging scope](https://github.com/PrimeIntellect-ai/prime-rl/blob/main/docs/overview.md).
2. PrimeIntellect, `prime-rl` scaling: [single-node placement and
   trainer/inference GPU controls](https://github.com/PrimeIntellect-ai/prime-rl/blob/main/docs/scaling.md).
3. PrimeIntellect, community-environments contributor guidance:
   [layout, rewards, tests, `vf-eval`, and PR checklist](https://github.com/PrimeIntellect-ai/community-environments/blob/main/AGENTS.md).
4. Hugging Face, OpenEnv README: [Gymnasium-style API, isolation, CLI, and
   testing](https://github.com/huggingface/OpenEnv/blob/main/README.md).
5. Hugging Face, OpenEnv environment builder: [`openenv validate`, Docker and
   packaging workflow](https://github.com/huggingface/OpenEnv/blob/main/docs/source/getting_started/environment-builder.md).
6. NVIDIA NeMo Gym, [environment anatomy and dataset/verifier/state separation](https://docs.nvidia.com/nemo/gym/main/about/concepts/environments/)
   and [new-environment contribution gates, verifier fixtures, and optional
   training validation](https://docs.nvidia.com/nemo/gym/main/contribute/environments/new-environment/).
7. Krakovna et al., Google DeepMind: [specification gaming and reward
   tampering](https://deepmind.google/blog/specification-gaming-the-flip-side-of-ai-ingenuity/).
8. Ramesh et al., ICML/PMLR: [delayed outcomes and temporal credit
   assignment](https://proceedings.mlr.press/v235/ramesh24b.html).
