#!/usr/bin/env bash
export UV_PROJECT_ENVIRONMENT=/tmp/prl_venv
export PATH=$HOME/.local/bin:$PATH
cd /workspace/prime-rl
uv sync --all-extras >> /tmp/prl_sync.log 2>&1
echo "SYNC_EXIT=$?" >> /tmp/prl_sync.log
/tmp/prl_venv/bin/python -c "import verifiers.v1; print('V1_OK')" >> /tmp/prl_sync.log 2>&1
echo "PRL_SYNC_DONE" >> /tmp/prl_sync.log
