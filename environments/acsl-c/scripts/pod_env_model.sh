#!/usr/bin/env bash
uv pip install --python /tmp/prl_venv/bin/python --no-deps -e /workspace/acsl-c >> /tmp/model_dl.log 2>&1
/tmp/prl_venv/bin/python -c "from acsl_c.taskset import AcslCTaskset; print('ENV_IMPORT_OK')" >> /tmp/model_dl.log 2>&1
/tmp/prl_venv/bin/python -c "
from huggingface_hub import snapshot_download
p = snapshot_download('Qwen/Qwen2.5-Coder-1.5B-Instruct')
print('MODEL_AT', p)
" >> /tmp/model_dl.log 2>&1
echo "SETUP_DONE" >> /tmp/model_dl.log
