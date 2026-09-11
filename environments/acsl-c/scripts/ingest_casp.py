#!/usr/bin/env python3
"""CASP ingestion (Milestone 1, ADR-008): download, re-verify, emit jsonl.

Runs on Linux/WSL with frama-c in PATH. Steps per ADR-008:
1. pull C sources + ACSL annotations from the CASP HF dataset
2. re-verify EVERY pair under the local pinned toolchain
3. quarantine pairs that no longer verify (record flips, never silent-drop)
4. emit train/eval jsonl in the acsl-c task format with provenance fields

Usage:
  python3 ingest_casp.py --out-dir ../../data --mode both [--limit N]

Requires: datasets (pip), frama-c 33.0, alt-ergo 2.6.3, z3 4.8.12.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from acsl_c.integrity import first_function_body, function_body_spans

FRAMAC_FLAGS = [
    "-wp",
    "-wp-rte",
    "-wp-prover",
    "alt-ergo,z3",
    "-wp-timeout",
    "20",
]

ACSL_RE = re.compile(r"/\*@[\s\S]*?\*/")


def verify(source: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="casp_ingest_") as tmp:
        cpath = Path(tmp) / "pair.c"
        report = Path(tmp) / "wp-report.json"
        cpath.write_text(source, encoding="utf-8")
        t0 = time.time()
        try:
            proc = subprocess.run(
                ["frama-c", *FRAMAC_FLAGS, "-wp-report-json", str(report), cpath],
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "goals": None}
        elapsed = time.time() - t0
        payload = None
        if report.exists():
            try:
                payload = json.loads(report.read_text())
            except json.JSONDecodeError:
                payload = None
        if payload is not None:
            goals = [g for g in payload if isinstance(g, dict) and not g.get("smoke")]
            proved = sum(1 for g in goals if g.get("passed"))
            status = "verified" if goals and proved == len(goals) else "incomplete"
            return {
                "status": status,
                "goals": {"proved": proved, "total": len(goals)},
                "seconds": round(elapsed, 2),
            }
        m = re.search(r"Proved goals:\s*(\d+)\s*/\s*(\d+)", proc.stdout)
        if m:
            proved, total = int(m.group(1)), int(m.group(2))
            return {
                "status": "verified" if total and proved == total else "incomplete",
                "goals": {"proved": proved, "total": total},
                "seconds": round(elapsed, 2),
            }
        return {"status": "unparseable", "goals": None}


def to_task(idx: int, source: str, meta: dict) -> dict | None:
    """Emit a 'hints' task: strip the implementation body, keep annotations."""
    span = first_function_body(source)
    if span is None:
        return None
    body_start, i = span
    skeleton = source[: body_start + 1] + "\n  // TODO: complete\n" + source[i:]
    n_annotations = len(ACSL_RE.findall(source))
    return {
        "data_schema_version": 2,
        "idx": idx,
        "problem": "",
        "mode": "hints",
        "skeleton_c": skeleton,
        "reference_solution": source,
        "has_spectests": False,
        "vc_estimate": max(n_annotations * 2, 4),
        "provenance": f"casp:{meta.get('id', idx)}",
    }


def make_vacuity_probe(source: str) -> str | None:
    """Stub every function body while keeping all ACSL annotations.

    If the stubbed file still fully verifies, the contracts don't constrain
    behavior -> spec is vacuous. Returns None when no function body is found.
    """
    out = source
    spans = []
    for start, end in function_body_spans(source):
        header_start = max(source.rfind(";", 0, start), source.rfind("}", 0, start)) + 1
        header = source[header_start:start]
        body = (
            "" if re.search(r"\bvoid\s+[A-Za-z_]\w*\s*\(", header) else "  return 0;\n"
        )
        spans.append((start, end, body))
    if not spans:
        return None
    for start, end, body in reversed(spans):
        out = out[: start + 1] + "\n" + body + out[end:]
    return out


def check_vacuity(source: str) -> bool | None:
    """True = vacuous (stubbed body still verifies). None = probe failed."""
    probe = make_vacuity_probe(source)
    if probe is None:
        return None
    res = verify(probe)
    if res["status"] == "verified":
        return True
    if res["status"] == "incomplete":
        return False
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="data")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--eval-split-size", type=int, default=48)
    ap.add_argument("--vacuity-check", action="store_true")
    ap.add_argument(
        "--allow-unknown-vacuity",
        action="store_true",
        help="retain tasks whose vacuity probe crashes/times out (unsafe for research runs)",
    )
    args = ap.parse_args()

    from datasets import load_dataset

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    quarantine = out_dir / "quarantine"
    quarantine.mkdir(exist_ok=True)

    print("loading CASP from HF (nicher92/CASP_source_files) ...")
    ds = load_dataset("nicher92/CASP_source_files", split="train")
    rows = list(ds)
    if args.limit:
        rows = rows[: args.limit]
    print(f"{len(rows)} candidate pairs")

    stats = {
        "verified": 0,
        "incomplete": 0,
        "timeout": 0,
        "unparseable": 0,
        "vacuous": 0,
        "vacuity_unknown": 0,
    }
    tasks: list[dict] = []
    flip_log = []
    idx = 0
    for row_index, r in enumerate(rows):
        src = r.get("file_content") or r.get("content") or r.get("code") or ""
        if "/*@" not in src:
            continue
        res = verify(src)
        stats[res["status"]] += 1
        upstream_id = r.get("id") or r.get("hash") or "no-id"
        pair_id = f"{row_index}_{upstream_id}"
        if res["status"] != "verified":
            (quarantine / f"{pair_id}.c").write_text(src, encoding="utf-8")
            flip_log.append({"id": str(pair_id), **res})
            continue
        task = to_task(idx, src, r)
        if task is None:
            continue
        if isinstance(r.get("goals"), int):
            task["vc_estimate"] = max(task["vc_estimate"], r["goals"])
        if args.vacuity_check:
            vac = check_vacuity(src)
            if vac is True:
                stats["vacuous"] += 1
                (quarantine / f"vacuous_{pair_id}.c").write_text(src, encoding="utf-8")
                flip_log.append({"id": str(pair_id), "status": "vacuous-spec"})
                continue
            if vac is None:
                stats["vacuity_unknown"] += 1
                if not args.allow_unknown_vacuity:
                    (quarantine / f"unknown_vacuity_{pair_id}.c").write_text(
                        src, encoding="utf-8"
                    )
                    flip_log.append({"id": str(pair_id), "status": "vacuity-unknown"})
                    continue
            task["non_vacuous"] = (not vac) if vac is not None else "unknown"
        else:
            task["non_vacuous"] = "unknown"
        task["verification"] = res
        tasks.append(task)
        idx += 1
        if idx % 25 == 0:
            print(f"  {idx} verified tasks so far ({stats})")

    eval_n = min(args.eval_split_size, len(tasks) // 5)
    (out_dir / "casp_eval.jsonl").write_text(
        "\n".join(json.dumps(t) for t in tasks[:eval_n]) + "\n", encoding="utf-8"
    )
    (out_dir / "casp_train.jsonl").write_text(
        "\n".join(json.dumps(t) for t in tasks[eval_n:]) + "\n", encoding="utf-8"
    )
    (out_dir / "ingest_report.json").write_text(
        json.dumps({"stats": stats, "flips_quarantined": flip_log}, indent=2),
        encoding="utf-8",
    )
    print(f"\ndone: {len(tasks)} tasks -> {out_dir}/casp_train.jsonl (+eval)")
    print(f"stats: {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
