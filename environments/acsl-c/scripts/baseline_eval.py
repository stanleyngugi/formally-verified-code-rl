"""Historical direct-API baseline utility.

This invokes Frama-C on the host and is retained only to reproduce the 2026-08-24
baseline. New evaluations must use the containerized Prime/Verifiers configs.

Conservative by design: sequential calls, small n, usage logged per call.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from acsl_c.framac import parse
from acsl_c.integrity import check_fixed_task_integrity

API_URL = "https://api.cerebras.ai/v1/chat/completions"
FRAMAC_FLAGS = [
    "-wp",
    "-wp-rte",
    "-wp-cache",
    "none",
    "-wp-prover",
    "alt-ergo,z3",
    "-wp-timeout",
    "20",
]
FENCE_RE = re.compile(r"```[a-zA-Z]*\n([\s\S]*?)```")


def load_key():
    return open(os.path.expanduser("~/.cerebras_api_key")).read().strip()


def chat(model, messages, key, max_tokens=None):
    if max_tokens is None:
        max_tokens = 8192 if "gpt-oss" in model else 4096
    body = {
        "model": model,
        "max_completion_tokens": max_tokens,
        "temperature": 0.2,
        "top_p": 1,
        "messages": messages,
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": "verified-rl-envs/0.1",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                resp = json.loads(r.read())
            return resp
        except (OSError, TimeoutError, json.JSONDecodeError) as e:
            wait = 5 * (attempt + 1)
            print(f"    retry in {wait}s ({type(e).__name__})")
            time.sleep(wait)
    return None


def extract_code(text: str) -> str:
    m = FENCE_RE.search(text or "")
    code = m.group(1) if m else (text or "")
    return code.strip()


def verify(source: str):
    import tempfile

    with tempfile.TemporaryDirectory(prefix="eval_") as tmp:
        cpath = Path(tmp) / "solution.c"
        report = Path(tmp) / "r.json"
        cpath.write_text(source, encoding="utf-8")
        try:
            proc = subprocess_run(
                ["frama-c", *FRAMAC_FLAGS, "-wp-report-json", str(report), str(cpath)],
                timeout=300,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return parse(stdout=""), f"crash:{exc}"
        payload = report.read_text() if report.exists() else None
        v = parse(wp_report_json=payload, stdout=proc.stdout)
        diagnostics = proc.stdout[-1500:]
        return v, diagnostics


def subprocess_run(argv, timeout):
    return subprocess.run(
        argv, capture_output=True, text=True, timeout=timeout, check=False
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["gpt-oss-120b", "gemma-4-31b"])
    ap.add_argument("-n", "--num-tasks", type=int, default=12)
    ap.add_argument("--slice", choices=["easy", "hard"], default="easy")
    ap.add_argument("--out", default=str(ROOT / "data" / "baselines"))
    ap.add_argument(
        "--unsafe-host-execution",
        action="store_true",
        help="acknowledge that untrusted model-generated C will reach the host preprocessor",
    )
    args = ap.parse_args()

    if not args.unsafe_host_execution:
        ap.error(
            "refusing host execution; use configs/agentic_eval_v0_9.toml or "
            "explicitly pass --unsafe-host-execution for historical reproduction"
        )

    key = load_key()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    eval_path = ROOT / "data" / "casp_eval.jsonl"
    tasks = [
        json.loads(line) for line in eval_path.read_text().splitlines() if line.strip()
    ]
    tasks.sort(key=lambda t: t.get("vc_estimate", 0))
    if args.slice == "hard":
        tasks = tasks[-args.num_tasks :]
    else:
        tasks = tasks[: args.num_tasks]
    print(f"{len(tasks)} eval tasks (lowest vc_estimate first)")

    all_results = {}
    total_usage = 0
    for model in args.models:
        results = []
        print(f"\n===== {model} =====")
        for t in tasks:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert in formally verified C programming using "
                        "ACSL annotations. Complete the C function body so that ALL "
                        "ACSL annotations verify under Frama-C WP. Do not modify the "
                        "annotations. Output ONLY the complete contents of a .c file."
                    ),
                },
                {
                    "role": "user",
                    "content": "Complete this annotated C function so every ACSL annotation "
                    "verifies:\n\n```c\n" + t["skeleton_c"] + "\n```",
                },
            ]
            resp = chat(model, messages, key)
            if resp is None:
                results.append({"idx": t["idx"], "error": "api-failed"})
                continue
            usage = resp.get("usage", {})
            total_usage += usage.get("total_tokens", 0)
            content = resp["choices"][0]["message"].get("content") or ""
            code = extract_code(content)
            integrity = check_fixed_task_integrity(code, t["skeleton_c"])
            if integrity.ok:
                v, _diagnostics = verify(code)
            else:
                # Do not feed a changed problem statement to the host preprocessor.
                v, _diagnostics = parse(stdout=""), "integrity failure"
            row = {
                "idx": t["idx"],
                "vc_estimate": t.get("vc_estimate"),
                "integrity": integrity.ok,
                "gate": int(
                    integrity.ok
                    and v.parse_ok
                    and v.crash is None
                    and v.goals_total > 0
                ),
                "vc_fraction": round(v.fraction, 3) if integrity.ok else 0.0,
                "full_proof": int(integrity.ok and v.ok),
                "goals": f"{v.goals_proved}/{v.goals_total}",
                "tokens": usage.get("total_tokens"),
            }
            results.append(row)
            print(
                f"  task {t['idx']:>3} vc={t.get('vc_estimate')}: "
                f"{row['goals']} goals, frac={row['vc_fraction']}, "
                f"full={row['full_proof']}"
            )
            time.sleep(1.5)

        fulls = sum(r["full_proof"] for r in results if "error" not in r)
        gates = sum(r["gate"] for r in results if "error" not in r)
        fracs = [r["vc_fraction"] for r in results if "error" not in r]
        valid = len([r for r in results if "error" not in r])
        summary = {
            "model": model,
            "tasks": valid,
            "gate_rate": round(gates / valid, 3) if valid else None,
            "full_proof_rate": round(fulls / valid, 3) if valid else None,
            "mean_vc_fraction": round(sum(fracs) / valid, 3) if valid else None,
            "tokens_used": sum(r.get("tokens") or 0 for r in results),
        }
        print(f"  SUMMARY {summary}")
        all_results[model] = {"summary": summary, "results": results}

    (out_dir / f"baseline_{int(time.time())}.json").write_text(
        json.dumps(all_results, indent=2), encoding="utf-8"
    )
    print(f"\ntotal tokens: {total_usage}")
    print(f"saved -> {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
