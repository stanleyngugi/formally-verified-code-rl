#!/usr/bin/env bash
echo "=== judge ==="
grep -E "PKG_FAIL|OPAM_MISSING" /tmp/judge_setup.log 2>/dev/null | sort -u
tail -3 /tmp/judge_setup.log 2>/dev/null
pgrep -f "opam install" >/dev/null && echo "OPAM_BUILD_RUNNING" || echo "OPAM_BUILD_NOT_RUNNING"
command -v opam && opam --version 2>/dev/null
eval $(opam env 2>/dev/null) 2>/dev/null
frama-c -version 2>/dev/null || echo "no frama-c yet"
z3 --version 2>/dev/null | head -1
echo "=== stack ==="
tail -3 /tmp/stack_setup.log 2>/dev/null
ls /workspace/prime-rl/pyproject.toml 2>/dev/null && echo PRL_OK
ls /workspace/native-verify/environments/native_verify_seq/native_verify_seq.py 2>/dev/null && echo NV_OK
