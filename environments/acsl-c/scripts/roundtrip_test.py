#!/usr/bin/env python3
"""Milestone-0 round-trip: run the real judge on sample/reference solutions.

Runs inside WSL (or any Linux with frama-c). For each task in a jsonl file,
takes reference_solution if present, otherwise skeleton_c (hints mode is
expected NOT to verify until the body is completed -- those are reported as
expected-fail checks that WP at least parses and generates goals).

Usage:  python3 roundtrip_test.py examples/sample_tasks.jsonl
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "framac",
    Path(__file__).parent.parent / "src" / "acsl_c" / "framac.py",
)
framac = importlib.util.module_from_spec(_spec)
sys.modules["framac"] = framac
_spec.loader.exec_module(framac)
parse = framac.parse

FRAMAC_FLAGS = [
    "-wp",
    "-wp-rte",
    "-wp-prover",
    "alt-ergo,z3",
    "-wp-timeout",
    "20",
]


def run_framac(source: str):
    with tempfile.TemporaryDirectory(prefix="acslc_rt_") as tmp:
        cpath = Path(tmp) / "solution.c"
        report = Path(tmp) / "wp-report.json"
        cpath.write_text(source, encoding="utf-8")
        try:
            proc = subprocess.run(
                ["frama-c", *FRAMAC_FLAGS, "-wp-report-json", str(report), cpath],
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return None, "wall-clock timeout", ""
        payload = report.read_text() if report.exists() else None
        return proc.returncode, proc.stdout + proc.stderr, payload


def main() -> int:
    tasks_path = Path(sys.argv[1])
    tasks = [
        json.loads(line) for line in tasks_path.read_text().splitlines() if line.strip()
    ]
    failures = 0
    for t in tasks:
        src = t.get("reference_solution") or t.get("skeleton_c") or ""
        label = f"task {t['idx']} ({t.get('mode')}, {t.get('provenance')})"
        rc, out, payload = run_framac(src)
        v = parse(wp_report_json=payload, stdout=out)
        print(f"== {label}")
        print(f"   frama-c exit={rc} verdict={v.to_dict()}")
        for f in v.failures[:5]:
            print(f"   unproved: {f['property']} @ line {f['line']} ({f['verdict']})")
        has_impl = t.get("reference_solution") or (t.get("mode") == "full" and src)
        if has_impl and not v.ok:
            failures += 1
            print("   !! expected full proof but goals incomplete")
    print(f"\n{'PASS' if failures == 0 else 'FAIL'}: {failures} unexpected outcome(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
