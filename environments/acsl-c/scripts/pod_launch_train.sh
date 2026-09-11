#!/usr/bin/env bash
export PATH=$HOME/.local/bin:$PATH
export UV_PROJECT_ENVIRONMENT=/tmp/prl_venv
cd /workspace/prime-rl
uv run rl @ /workspace/acsl-c/configs/train.toml --dry-run > /tmp/train_dry_run.log 2>&1
uv run rl @ /workspace/acsl-c/configs/train.toml > /tmp/train.log 2>&1
echo "TRAIN_EXIT=$?" >> /tmp/train.log
