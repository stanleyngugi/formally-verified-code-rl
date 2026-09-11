import json
import statistics
from pathlib import Path

d = Path(__file__).parent.parent / "data"
rows = [
    json.loads(line)
    for line in (d / "casp_train.jsonl").read_text().splitlines()
    if line.strip()
]
print("train rows:", len(rows))
print("sample keys:", sorted(rows[0].keys()))
vcs = [r["vc_estimate"] for r in rows]
print("vc_estimate min/median/max:", min(vcs), statistics.median(vcs), max(vcs))
rep = json.loads((d / "ingest_report.json").read_text())
print("quarantined flips:", len(rep["flips_quarantined"]))
statuses = {}
for r in rows:
    statuses[r.get("verification", {}).get("status")] = (
        statuses.get(r.get("verification", {}).get("status"), 0) + 1
    )
print("verification statuses:", statuses)
