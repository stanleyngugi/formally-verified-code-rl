# Contributing

Contributions are welcome, especially independently reviewed ACSL tasks,
reward-hacking fixtures, provenance-preserving source adapters, and verifier
reproducibility improvements.

Before proposing a task:

1. Preserve an explicit source URL, immutable revision, source path, copyright
   notice, and SPDX license identifier.
2. Keep contracts and all non-target code immutable in fixed-contract mode.
3. Include at least one plausible wrong implementation that parses and
   compiles but fails proof.
4. Keep every derivation/template family in one split.
5. Replay the reference with WP+RTE and run the negative evidence gate.
6. Do not add CASP-derived source to the public wheel without record-level
   clearance.

Run the package checks from `environments/acsl-c` in Linux/WSL:

```bash
python -m pytest -q
python scripts/audit_public_pack.py --pack-dir data/packs/core-v1
```

Production changes must preserve fail-closed behavior for malformed reports,
zero goals, crashes, timeouts, contract tampering, and sandbox failures.
