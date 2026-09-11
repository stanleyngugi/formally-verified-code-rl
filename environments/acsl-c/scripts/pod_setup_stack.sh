#!/usr/bin/env bash
# Reproducible RL stack for the supported two-GPU topology.
set -euo pipefail
LOG=/tmp/stack_setup.log
PRIME_RL_COMMIT=ab5de8fff44b2c4a5c85e24b6e6e3f7d57eee7b1

# uv
if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/0.12.5/install.sh | sh >> "$LOG" 2>&1
fi
export PATH="$HOME/.local/bin:$PATH"
uv --version >> "$LOG" 2>&1

# sources on network FS are fine; venvs/output go to LOCAL disk (decision #9)
mkdir -p /workspace /tmp/rlwork
cd /workspace

# prime-rl (https not ssh)
if [ ! -d /workspace/prime-rl ]; then
  git clone https://github.com/PrimeIntellect-ai/prime-rl.git /workspace/prime-rl >> "$LOG" 2>&1
fi
cd /workspace/prime-rl
git fetch --tags origin >> "$LOG" 2>&1
git checkout --detach "$PRIME_RL_COMMIT" >> "$LOG" 2>&1
git submodule update --init --recursive >> "$LOG" 2>&1
test "$(git rev-parse HEAD)" = "$PRIME_RL_COMMIT"

echo "STACK_SETUP_DONE prime-rl=$PRIME_RL_COMMIT" >> "$LOG"
