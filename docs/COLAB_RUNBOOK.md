# Colab runbook for the ACSL-C project

This document records what a managed Colab GPU can establish, what it cannot
establish, and the exact procedure for repeating the measurements. It is an
operational companion to `EXPERIMENT_PROTOCOL.md`, not a claim of RL training
results.

## What the current T4 established

The managed runtime used a single Tesla T4 with 15,360 MiB VRAM, Python
3.13.15, Torch 2.11.0+cu128, CUDA 12.8, and compute capability 7.5. The
installed stack was Unsloth 2026.9.3, TRL 0.24.0, bitsandbytes 0.50.2, and
Transformers 5.5.0.

The fresh-process probe in `environments/acsl-c/scripts/colab_memory_probe.py`
performed all of the following: pinned the resolved Hugging Face revision,
loaded 4-bit weights, generated 128 tokens, attached LoRA adapters, executed a
real forward/backward/AdamW step, checked finite loss and gradients, and wrote
append-only JSONL. It never executes generated C.

| Model / context | Load used | Generation peak reserved | LoRA optimizer peak reserved | Result |
|---|---:|---:|---:|---|
| Qwen2.5-Coder-7B, 2,048 tokens | 5.39 GiB | 5.33 GiB | 7.61 GiB | passed |
| Qwen2.5-Coder-14B, 1,024 tokens | 9.58 GiB | 9.48 GiB | 12.16 GiB | passed |

The 14B result is a bounded feasibility result, not a recommendation to start
full GRPO at 1,024 tokens. GRPO needs several completions, rollout KV caches,
optimizer state, and framework overhead simultaneously. Start with 7B for the
claim-bearing pipeline; treat 14B as an optional single-GPU ablation after the
7B canary. Re-probe at the exact context, group size, and generation length
before changing that decision.

## Runtime topology decision

Use managed Colab notebook cells for package installation, model probes,
baseline generation, and small QLoRA experiments. Do not attempt to create an
SSH tunnel or remote-control shell inside a managed runtime. Colab's supported
remote option is a local runtime backed by a machine the user controls; that is
the route for Docker, Frama-C, and Prime-RL experiments.

The repository's Prime-RL configuration assumes the production sandbox and a
multi-GPU topology. A one-T4 Colab run cannot validate that configuration. It
can validate model memory, prompt formatting, output capture, and local helper
scripts, but those results must not be labelled Prime-RL training evidence.

## Important: the Docker rebuild is not a Colab prerequisite

The Docker image is the verification plane, not the model-compute plane. The
original pinned image `verified-rl-envs/framac:33.0` already exists at digest
`sha256:5da598c4fa7f1e4210412822f3c3942764baa0057e85070ab5d3b1fadd1ac9dc`
and passed the complete 316-reference replay (5,205/5,205 WP+RTE goals,
1,264/1,264 RTE goals, zero timeouts). That image is sufficient for replay and
for the eventual reward audit. A second image build is only an optional
hardening/release step to make `/workspace` writable for the unprivileged
runtime user; it is not needed to load Qwen, generate candidates, or run a
bounded QLoRA experiment in Colab. Because the local Windows volume is nearly
full, that rebuild is intentionally deferred.

The practical split is therefore:

| Plane | Best current location | What it can establish |
| --- | --- | --- |
| Model compute | Managed Colab T4 | Qwen loading, memory limits, generation, prompt/output capture, small QLoRA steps |
| Verification | Existing pinned Docker image on a Docker-capable host | Frama-C/Why3/Alt-Ergo/Z3 verdicts, reward values, spectest evidence |
| Claim-bearing RL | Linux GPU host with Prime-RL's supported topology | inference + orchestrator + trainer canary, checkpoint resume, three-seed GRPO |

Colab candidates should be saved as append-only JSONL with model revision,
decoding parameters, task IDs, and hashes. They can then be copied to the
Docker-capable verifier host and replayed without rerunning the model. A Colab
local runtime backed by such a host is also valid; a normal managed runtime is
not a Docker daemon or a Frama-C installation.

For one-GPU learning experiments, follow `docs/ONE_GPU_PLAN.md`. The preferred
T4 strategy is serial time-sharing: generate a small rollout batch, release the
generation model, perform a short LoRA update, save a checkpoint, and repeat.
This uses the GPU productively without requiring simultaneous 7B trainer and
vLLM copies. Mark these artifacts `topology=single_gpu_serial`; they are valid
ablations but are not asynchronous Prime-RL throughput evidence.

## Repeatable notebook cells

1. Select a T4 runtime and run the diagnostic cell (`nvidia-smi`, Python, Torch,
   CUDA, GPU count).
2. Install the versions used by the probe:

   ```python
   %pip install -q --upgrade --no-cache-dir unsloth unsloth_zoo trl bitsandbytes
   ```

3. Upload the sanitized project archive and the probe script. Extract the
   archive and print the split manifest; expected counts are train 221,
   validation 47, test 48, all 316.
4. Run one probe per fresh process:

   ```python
   !python /content/colab_memory_probe.py \
       --model unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit \
       --sequence-length 2048 \
       --output /content/colab_probe_results.jsonl
   ```

5. Delete notebook model variables and call `torch.cuda.empty_cache()` before
   probing another model. Keep each model's JSONL output and the resolved
   revision.
6. Save results outside `/content` (Drive or a downloaded artifact). Managed
   runtime files disappear when the runtime is reclaimed, even though notebook
   cells and outputs remain in Drive.

## Baseline generation result (2026-09-09)

The first reproducible generation run used the validation IDs from
`split_manifest.json` and therefore read `casp_eval.jsonl`. The training file
does not contain those validation records. With deterministic decoding and a
512-token cap, Qwen2.5-Coder-7B first produced an 8-task smoke artifact (1,001
completion tokens; 5,697-byte JSONL), then a complete 47-task validation
artifact (7,010 completion tokens; 36,458-byte JSONL), all at Hugging Face
revision `4858886f896bd05db823557fc5cbc4ac28342af7`. The per-task metadata,
IDs, commands, and artifact sizes are recorded in
`docs/COLAB_BASELINE_2026-09-09.json`.

The raw JSONL is intentionally treated as an experiment artifact, not as a
verification result. It must be replayed through the pinned Docker/Frama-C
executor before any pass rate or reward is reported. The generator now fails
early when a data file and split have no matching IDs, preventing a silent
zero-byte baseline after a reclaimed runtime or an incorrect CASP file.

When the file is downloaded, validate its provenance before replaying it:

```bash
python environments/acsl-c/scripts/validate_baseline.py \
  --baseline qwen25_coder7b_validation_baseline.jsonl \
  --split-manifest environments/acsl-c/data/split_manifest.json \
  --split validation
```

## Bounded stochastic rollout-shape probe

To check candidate diversity before provisioning the production judge, run the
generation-only sampler on a fresh T4 process:

```bash
python /content/colab_generate_rollout_samples.py \
  --model unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit \
  --data /content/verified-rl-envs/environments/acsl-c/data/casp_eval.jsonl \
  --split-manifest /content/verified-rl-envs/environments/acsl-c/data/split_manifest.json \
  --split validation --max-tasks 8 --num-samples 4 \
  --max-new-tokens 256 --temperature 0.7 --top-p 0.95 --seed 1337 \
  --output /content/qwen25_coder7b_validation_rollouts_x4.jsonl
```

The 2026-09-09 run produced 32 rows, 26 unique completions, and 2,242
completion tokens at revision
`4858886f896bd05db823557fc5cbc4ac28342af7`. Its 21,193-byte artifact has
SHA-256 `716433753af3722f6d39e34f4ed42b695e5fd8cfd24ee7d7c611ca9590f7ed98`.
Every row is marked `verifier_scored: false`; replay candidates with
`execute_spectests.py`/the production Verifiers runtime before computing any
reward or pass-rate statistic. This confirms decoding and diversity plumbing
only, and is not a substitute for a GRPO canary.

Managed Colab storage is ephemeral. In this run, Drive mounting failed with
`credential propagation was unsuccessful` and browser-triggered download did
not create a local file, so the raw JSONL could not be promoted to a durable
repository artifact. Preserve it by downloading from the notebook UI while
the runtime is alive, or rerun the command on a Docker-capable host.

### Batched memory result

On the same T4, a four-candidate batch using the longest validation skeleton
(1,632 prompt tokens) and 256 generated tokens peaked at 7.27 GiB reserved,
leaving about 7.14 GiB free. This makes Qwen2.5-Coder-7B a practical
generation-only rollout choice for a 16 GiB T4, including four-way sampling.
Do not extrapolate this result to QLoRA optimizer memory, GRPO, vLLM, or
Frama-C execution; each still needs a claim-bearing production run.

## What remains outside Colab

- Replay Colab candidate artifacts inside the existing pinned Docker image with
  Frama-C 33.0 and record verifier-scored rewards. (No image rebuild is needed
  for this.)
- Optionally rebuild a hardened image with a writable `/workspace` and publish
  a new digest; this is a release-quality improvement, not a blocker for Colab
  generation or for using the preserved image.
- Run executed negative spectests and independently validate their labels.
- Perform base traces, a 1–2 step canary, and three-seed GRPO on the supported
  Prime-RL GPU topology.
- Freeze validation-based checkpoint selection and run the fresh 48-task test
  once.

## Production preflight

Before starting a Docker/Prime-RL host, run the repository's read-only
preflight. It checks the split counts, pinned local judge binaries, Docker
health, and an optional Prime-RL checkout; exit code 2 means that production
readiness is not yet established.

```bash
eval "$(opam env --switch=ocaml-4.14 --set-switch)"
uv run python environments/acsl-c/scripts/preflight.py \
  --prime-root /workspace/prime-rl
```

The command must report `local_judge_ready: true` and
`production_ready: true` before the image digest and `rl --dry-run` gates.
It never installs packages or mutates the repository, so it is safe to run
after reconnecting a host or recovering a preempted VM.

## Model selection rule

Qwen2.5-Coder-7B is the default because it is code-specialized and has ample
measured headroom on the T4. Qwen2.5-Coder-14B is the largest code-specialized
candidate that passed this bounded 4-bit/LoRA probe, but its 12.16 GiB peak
leaves little room for multi-sample GRPO. Qwen3-Coder-30B-A3B is not a T4
candidate: its 4-bit weights alone are approximately the full usable VRAM,
before activations and optimizer state. A Qwen3 general model is a different
ablation, not a drop-in replacement for the code-specialized baseline.
