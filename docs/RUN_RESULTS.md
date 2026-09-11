# GRPO Smoke Run Results — acsl-c v1 (2026-08-25)

**Historical engineering smoke; not evidence of a causal training improvement.**

## Setup

| Component | Value |
|---|---|
| Pod | RunPod, 1× RTX A4000 16GB, 128 CPU, ~66GB cgroup RAM, Ubuntu 22.04 |
| Judge | frama-c 33.0 + why3 1.8.2 + alt-ergo 2.6.3 (opam), z3 4.8.12 (apt) |
| Model | Qwen/Qwen2.5-Coder-1.5B-Instruct, LoRA |
| Stack | prime-rl main @ 2026-08-24 + single-GPU colocate patches (from native-verify) |
| Env | acsl-c v1 Taskset: CASP hints-mode, 64 tasks, binary full_proof reward |
| Config | configs/grpo_smoke_acslc_16gb.toml: 12 steps, batch 16, group 8 |

## Result

```
Step 1:  Reward 0.375   (2m14s)
Step 9:  Reward 0.4375
Step 10: Reward 0.625
Step 11: Reward 0.750
Step 12: Reward 0.875   (1m43s)
Orchestrator finished in 17m 6s. Error rate 0.0% throughout.
```

Observed batch reward rose **0.375 → 0.875 during the smoke**,
with zero scoring errors — every one of ~190 episodes was judged by real
Frama-C/WP proofs on the pod.

## Honest caveats

1. Tasks stream in dataset order (vc_estimate unshuffled) — part of the rise is
   likely task-mix composition, not pure learning. Fix: shuffle/curriculum by
   vc_estimate before the long run (matches native-verify open-issue #1).
2. n=12 steps is a smoke test; no claim of learning-curve significance.
3. No checkpoint saved ([ckpt] section empty) — add interval config for long runs.
4. Cancelled 27–30% on steps 10–11 (batch-fill cancellations; benign).

## What this establishes

The original architecture reached the judge and optimizer at training time:
model → verifiers v1 harness → Frama-C/WP proof → machine-checked binary
reward → GRPO update. Because difficulty-correlated task order confounds the
curve, this run does not estimate a before/after full-proof lift. Use the current
split manifest and `docs/EXPERIMENT_PROTOCOL.md` for any new claim.

## Pod setup recipe (fresh pod → trained, ~75 min)

1. `pod_setup_judge.sh` (apt deps + opam frama-c build, -j32) — ~15 min
2. `pod_setup_stack.sh` (uv, prime-rl clone + submodule fix via
   `git config --global url.'https://github.com/'.insteadOf 'git@github.com:'`,
   patches from native-verify repo) — ~10 min
3. `sync.sh` (UV_PROJECT_ENVIRONMENT=/tmp/prl_venv uv sync --all-extras) — ~20 min
4. `envinstall.sh` (--no-deps install of /workspace/acsl-c into prl_venv) — 2 min
5. Model download — 1 min
6. Launch: `HF_HUB_OFFLINE=1 uv run rl @ configs/grpo_smoke_acslc_16gb.toml`

## Gotchas hit this session (additions to handoff §7)

| Signature | Cause | Fix |
|---|---|---|
| `tr -d "\r"` double-quoted through PowerShell | deletes literal `r` chars ("expot", "sot") | convert CRLF→LF locally with `[IO.File]::WriteAllText`, scp clean bytes |
| urllib to api.cerebras.ai → HTTP 403 code 1010 | Cloudflare blocks default python UA | send custom User-Agent header |
| uv sync fails: pydantic-config "not a Python project" | empty submodule dir from earlier failed clone | deinit -f, rm .git/modules entry, re-update |
| `/tmp/prl_venv/bin/pip: No such file` | uv venvs ship without pip | `uv pip install --python .../python` |
| opam depext stops: zlib1g-dev missing | frama-c system deps not preinstalled | apt install zlib1g-dev graphviz first, then resume opam install |
