#!/usr/bin/env bash
export PATH=$HOME/.local/bin:$PATH
uv pip install --python /tmp/prl_venv/bin/python --no-deps -e /workspace/acsl-c >> /tmp/env_install.log 2>&1
echo "PIP_EXIT=$?" >> /tmp/env_install.log
/tmp/prl_venv/bin/python - <<'EOF' >> /tmp/env_install.log 2>&1
import os
os.chdir("/workspace/acsl-c")
from acsl_c.taskset import AcslCTaskset, AcslCTasksetConfig
cfg = AcslCTasksetConfig(data_dir="/workspace/acsl-c/data", max_tasks=4)
ts = AcslCTaskset(config=cfg)
tasks = list(ts.load())
print("TASKS_LOADED", len(tasks))
print("SMOKE_TASK_OK", tasks[0].data.mode, tasks[0].data.vc_estimate)
EOF
echo "ENV_SETUP_DONE" >> /tmp/env_install.log
