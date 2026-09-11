#!/usr/bin/env bash
eval $(opam env)
for b in frama-c frama-c-config alt-ergo why3 why3config ocamlfind; do
  ln -sf $(command -v $b) /usr/local/bin/$b 2>/dev/null
done
# why3 needs its OCaml lib path; wrap instead of symlink for correctness
cat > /usr/local/bin/why3 <<'EOF'
#!/usr/bin/env bash
export OCAMLLIB=/root/.opam/default/lib
exec /root/.opam/default/bin/why3 "$@"
EOF
chmod +x /usr/local/bin/why3
cp /root/.opam/default/share/why3/why3.conf* /root/.why3.conf 2>/dev/null || true
why3 config detect > /tmp/why3_detect.log 2>&1
grep -c "Prover" /tmp/why3_detect.log >> /tmp/why3_detect.log
cd /workspace/acsl-c
python3 - <<'PYEOF' > /tmp/judge_smoke.log 2>&1
import json, subprocess, tempfile
from pathlib import Path
task = json.loads(Path("data/casp_eval.jsonl").read_text().splitlines()[0])
code = task["reference_solution"] or task["skeleton_c"]
with tempfile.TemporaryDirectory() as tmp:
    c = Path(tmp)/"s.c"; r = Path(tmp)/"r.json"
    c.write_text(code)
    p = subprocess.run(["frama-c","-wp","-wp-rte","-wp-prover","alt-ergo,z3","-wp-timeout","20","-wp-report-json",str(r),str(c)],capture_output=True,text=True,timeout=300)
    print("rc:",p.returncode)
    if r.exists():
        goals=json.loads(r.read_text())
        goals=[g for g in goals if isinstance(g,dict) and not g.get("smoke")]
        proved=sum(1 for g in goals if g.get("passed"))
        print(f"goals {proved}/{len(goals)}")
    else:
        print("no report:", p.stdout[-500:])
PYEOF
echo JUDGE_SMOKE_DONE >> /tmp/judge_smoke.log
