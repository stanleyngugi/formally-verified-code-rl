# One-GPU execution plan

This project can make useful progress with one GPU. The two-GPU setting in
`configs/train.toml` is the canonical Prime-RL *asynchronous/scaling* placement
(one GPU for the trainer and one for vLLM inference); it is not a prerequisite
for environment correctness or for a first learning-signal experiment.

The distinction is between **topology** and **experiment validity**:

- A two-GPU Prime-RL run keeps trainer and inference live concurrently. It is
  the high-throughput, asynchronous configuration closest to the framework's
  production design and is required only when we want to test that topology,
  throughput, or asynchronous/off-policy behavior.
- A one-GPU run must either use a smaller model, aggressively offload memory,
  or time-share the GPU. It is slower and has different pipeline semantics, but
  it can still validate the environment, reward, optimizer, checkpointing, and
  learning signal.

Prime-RL's current upstream documentation explicitly supports one GPU for
trainer-only and inference-only checks, and describes single-GPU runs as
suitable for debugging and small experiments. It separately says that the
ordinary end-to-end example uses one inference GPU plus one trainer GPU. The
exact v0.9.0 checkout used by this repository must still be dry-run and smoke
tested before any Prime launch; current `main` documentation is evidence for
the strategy, not a substitute for validating the pinned commit.

For this repository, the serial path is the primary early learning test. It
time-shares generation and training, keeps verification on CPU/Docker, and
uses the same taskset, reward code, checkpoint format, and artifact schema. It
does not claim asynchronous throughput or equivalence to the two-GPU launcher.

## What can fit on one T4

The live managed Colab runtime has one Tesla T4 with 15,360 MiB VRAM. Our
measurements show:

| Workload | Measured result | Interpretation |
| --- | ---: | --- |
| Qwen2.5-Coder-7B 4-bit load | 5.39 GiB | Fits comfortably |
| Qwen2.5-Coder-7B four-way generation on the longest prompt | 7.27 GiB peak reserved | Good generation-only headroom |
| Qwen2.5-Coder-7B QLoRA optimizer step | 7.61 GiB peak in the prior fresh-process probe | Feasible as a bounded one-step/short-run test |
| Qwen2.5-Coder-14B 4-bit + LoRA | 12.16 GiB peak in the prior probe | Feasible as a tightly budgeted ablation, not the default GRPO model |

These numbers do not imply that two independent 7B copies (trainer plus vLLM)
will fit at the same settings. The trainer and vLLM copies have different
allocators, KV-cache requirements, and framework overhead. A concurrent
7B/7B colocated run on a 16 GiB T4 must be measured, not assumed.

## One-GPU strategies, from safest to most ambitious

### 1. Component gates on one GPU

Run the Prime trainer alone with fake or pre-recorded data, then run the
inference server alone. Keep the orchestrator and Frama-C verifier on CPU. This
validates the exact v0.9.0 installation, model adapter, LoRA path, checkpoint
format, and inference API without pretending that a complete asynchronous RL
pipeline ran.

This is the first one-GPU gate because Prime's own setup documentation treats
the trainer and inference entrypoints as independently testable one-GPU
components. The repository should record these as `component_smoke`, not as an
RL improvement.

### 2. Serial one-GPU on-policy loop (recommended and sufficient for the first learning test)

Use one process at a time on the GPU:

1. Load the current policy in a generation implementation (Transformers or a
   deliberately small vLLM instance).
2. Generate a small group of rollouts and write them append-only to disk.
3. Release the generation model and call `torch.cuda.empty_cache()`.
4. Load the trainable LoRA policy, perform one or a few gradient steps using
   those rollouts, and save a checkpoint.
5. Release the trainer, update the generation model from that checkpoint, and
   repeat.

The verifier can run concurrently on CPU or on a separate Docker-capable host.
With no rollout queue left over from an old policy, this is a synchronous
on-policy ablation. It is slow because generation and training cannot overlap,
but it avoids requiring two model copies in 16 GiB. The artifact must include
`topology = "single_gpu_serial"`, a policy/checkpoint ID for every rollout, and
the time spent in each phase.

This path is not the same algorithmic throughput regime as asynchronous
Prime-RL, but it is a valid synchronous/on-policy experiment. It should be
reported as the primary `single_gpu_serial` ablation. It can answer the most
important early questions: does the ACSL reward produce nonzero advantages,
does loss remain finite, do checkpoints resume, and do verified validation
completions improve?

### 3. Concurrent colocated trainer and inference

Run the trainer and inference service on the same physical GPU. This can be
useful with a 0.6B–1.5B model or a very small LoRA configuration. For the 7B T4
case, attempt it only after measuring both processes independently and setting a
hard memory budget. Use one or two rollouts per task, short contexts, and a low
vLLM `gpu_memory_utilization` value. If either process triggers OOM or allocator
fragmentation, fall back to the serial loop; do not repeatedly retry an OOM
inside the managed runtime.

Concurrent colocated execution preserves more of the Prime process structure,
but it is the riskiest option for this hardware and is not required to make
scientific progress.

### 4. CPU/offload-assisted one-GPU training

Prime-RL documents several memory levers that are directly relevant here:

- CPU optimizer-state offload (enabled by default in current documentation).
- Full CPU offload of gradients, FP32 masters, and optimizer state.
- Activation checkpointing and activation offload.
- Fused LM-head token chunking to avoid materializing the full vocabulary logits
  tensor.
- Inference KV-cache offload.

These reduce VRAM at a throughput cost. On a T4, combine them with LoRA,
gradient accumulation, microbatch size 1, sequence length 1,024–2,048, a small
rollout group (2–4), and a completion cap of 256–512 tokens. Change one memory
lever at a time and retain peak allocated/reserved memory and wall-clock
measurements in the experiment artifact.

## Configuration policy

Do not invent a `num_infer_gpus = 0` setting and assume the v0.9.0 launcher will
interpret it as colocated mode. The launcher normally allocates inference GPUs
first and trainer GPUs next, and the exact pinned release should be checked for
its minimums. For this reason the repository will maintain two explicit paths:

1. `configs/train.toml`: canonical two-GPU Prime-RL run.
2. A future `configs/one_gpu_*.toml` or standalone serial runner: explicitly
   marked as a one-GPU ablation, with no claim that it reproduces asynchronous
   throughput.

Before making the latter a formal config, validate the exact v0.9.0 schema with
`rl --dry-run`, then run the component gates and a one-step canary. If the
launcher cannot represent serial time-sharing, the serial runner should remain
outside Prime's launcher and use the same taskset/reward package and artifact
schema.

## Recommendation for this project

The managed Colab T4 serial canary is now complete (see
`docs/COLAB_SERIAL_CANARY.md`). Continue with the claim-bearing verifier-backed
serial loop; do not block that work on an asynchronous two-GPU layout:

1. Preserve the existing Qwen2.5-Coder-7B generation artifacts.
2. Run a short serial LoRA/GRPO-compatible loop on a small train slice. The
   model/trainer/checkpoint plumbing canary is complete; during reward plumbing,
   recorded verifier fixtures may stand in for the remote judge, but every
   claim-bearing reward must be recomputed by the pinned Frama-C image.
3. Replay every real candidate through the existing pinned Frama-C image before
   calculating reward or pass rate.
4. Validate checkpoint/resume and a no-update control run.
5. Only if we want to test async integration or scaling, run the same
   seed/task subset through canonical Prime-RL with a second GPU and compare
   reward, KL, throughput, and verified pass rate against the serial run.

The one-GPU run is therefore a productive engineering and learning experiment,
not a consolation prize. The only things it cannot honestly claim are the
throughput and asynchronous-system properties of the two-GPU production
topology.

## Sources and caveat

The strategy follows Prime-RL's upstream scaling, inference, and overview
documentation. Those pages document one-GPU component/debug runs, single-node
inference, CPU optimizer/activation offload, and KV-cache offload. The
repository remains pinned to Prime-RL v0.9.0, so every proposed key must be
validated against that exact checkout before launch.

- https://github.com/PrimeIntellect-ai/prime-rl/blob/main/docs/overview.md
- https://github.com/PrimeIntellect-ai/prime-rl/blob/main/docs/scaling.md
- https://github.com/PrimeIntellect-ai/prime-rl/blob/main/docs/inference.md
