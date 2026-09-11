#!/usr/bin/env bash
eval $(opam env)
cd /mnt/c/Users/stanley/Desktop/verified-rl-envs/environments/acsl-c
OUT_DIR="data_regenerated_$(date +%Y%m%d_%H%M%S)"
exec /tmp/acslc-venv/bin/python scripts/ingest_casp.py --out-dir "$OUT_DIR" --vacuity-check > /tmp/ingest_full.log 2>&1
