# Colab serial one-GPU canary

This runbook is the reproducible, bounded GPU check for ACSL-C. It is deliberately
separate from the verifier/reward plane: a managed Colab runtime currently has a
Tesla T4 but no Docker daemon and no `frama-c` executable, so it cannot establish
claim-bearing ACSL rewards. Use the pinned judge image for that claim. Colab is
useful for model loading, generation, adapter training, checkpoint integrity, and
serial orchestration plumbing.

## Why this is serial

The first learning test does not require Prime-RL's asynchronous two-process
topology. A serial loop is the smallest useful experiment: generate a bounded
batch, score it in the authoritative judge when available, then perform an update.
Async is reserved for a later test of process placement, throughput, queueing,
back-pressure, and failure recovery. Do not make async a release gate for the
environment itself.

## Bootstrap after every reconnect

Notebook output survives a Colab reconnect, but the Python process and packages do
not. Always run an explicit bootstrap cell before interpreting old output:

```python
%pip install -q --upgrade --no-cache-dir unsloth unsloth_zoo trl bitsandbytes
import unsloth, trl, bitsandbytes as bnb, transformers
print(unsloth.__version__, trl.__version__, bnb.__version__, transformers.__version__)
```

The managed image may report a non-fatal `gcsfs`/`fsspec` version conflict. Record
the versions in the manifest; for a durable benchmark, replace the ad-hoc install
with a pinned requirements cell or a custom image.

## Checks and interpretation

1. **Runtime health.** Record `nvidia-smi`, Python, Torch/CUDA, GPU count, and
   whether `docker` and `frama-c` are present. One T4 has 15,360 MiB; this is enough
   for Qwen2.5-Coder-7B in 4-bit with LoRA at short context lengths.
2. **Model health.** Load
   `unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit` at a fixed revision and run a
   deterministic one-to-four sample generation. Set
   `model.generation_config.max_length = None` and pass one source of generation
   arguments to avoid Transformers 5.x precedence warnings.
3. **Trainer canary.** Attach LoRA/QLoRA, run one finite forward/backward/optimizer
   step on two tiny prompt-completion pairs, assert that the loss is finite, and
   save the adapter plus a manifest containing model revision, versions, memory,
   loss-before/after, and file hashes.
4. **Checkpoint reload.** Delete the model, empty CUDA cache, reload from the
   adapter directory, and generate once. This catches missing tokenizer/config
   files and non-reloadable checkpoints.
5. **Serial plumbing.** Generate two bounded rollouts, write JSONL rows with a
   `verifier_scored` flag and explicit reward source, then perform one update. A
   `stub_not_verifier` reward is plumbing-only evidence and must never be reported
   as an ACSL success rate.

## Results recorded on 2026-09-10

- Runtime: one Tesla T4, 15,360 MiB, compute capability 7.5; Python 3.13.15;
  Torch 2.11.0+cu128; CUDA 12.8.
- Trainer: `GPU_TRAINER_CANARY_OK`; two rows; 20,185,088 trainable parameters;
  loss `0.6463377476 -> 0.3429369628`; 111.49 seconds; 6.246 GiB peak reserved.
- Checkpoint: `CHECKPOINT_RELOAD_OK`; adapter reloaded and generated output;
  33.39 seconds; 9.047 GiB peak reserved; manifest SHA-256
  `51c6796787c794fe088b5cdf963049255478a2861d7108283b7921f5e5c79d88`.
- Serial plumbing: `SERIAL_PLUMBING_OK`; two generated rollouts and one update;
  loss `0.6564837694 -> 0.6398609877`; 4.04 seconds; 9.512 GiB peak reserved;
  reward source `stub_not_verifier`, `verifier_scored=false`.

These results prove that the one-GPU model/trainer/checkpoint path fits and that
the serial control flow is executable. They do **not** prove verifier correctness,
reward validity, resistance to reward hacking, or a training improvement claim.

## Next claim-bearing run

Run the same serial loop with the pinned Docker judge available. Each row should
carry the environment/image digest, judge version, source hash, timeout policy,
verdict history, and reward components. Start with 2--4 tasks × 2 rollouts, then
add a no-update control. Only after those records are valid should a larger
multi-seed training study be considered. Test the async Prime-RL topology later,
as an orchestration/scaling experiment, not as a prerequisite for releasing the
environment.
