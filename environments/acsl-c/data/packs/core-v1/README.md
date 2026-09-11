---
license: apache-2.0
language:
  - en
tags:
  - reinforcement-learning
  - formal-verification
  - code
  - c
  - acsl
  - frama-c
task_categories:
  - text-generation
pretty_name: Formally Verified C Core-v1
size_categories:
  - n<1K
---

# Formally Verified C Core-v1

Core-v1 is a project-authored set of 64 fixed-contract C/ACSL function
completion tasks for reinforcement-learning environment development and model
evaluation. A model receives a complete C translation unit whose target body is
replaced by a TODO. The unchanged ACSL contract and surrounding source define
the problem; Frama-C WP+RTE supplies the executable reward signal.

## Contents

- 33 training tasks
- 15 validation tasks
- 16 held-out test tasks
- one reference implementation and at least one plausible wrong implementation
  per task
- record-level source hashes, license, origin, transformation, semantic family,
  derivation family, and review state

Semantic and derivation families are isolated to one split. This prevents a
template variant from appearing in both training and evaluation.

## Machine-verification evidence

Under Frama-C 33.0 (Arsenic), Why3 1.8.2, Alt-Ergo 2.6.3, and Z3 4.8.12:

- 64/64 reference implementations proved;
- 296/296 proof obligations discharged;
- 84/84 runtime-error obligations discharged;
- zero reference solver timeouts; and
- 64/64 deliberately wrong implementations rejected by the deterministic
  Frama-C WP+RTE/Qed negative pass, with zero timeouts.

The repository includes the per-task JSONL evidence and a compact release
manifest. These are machine-verification results, not an independent human
review and not evidence that any RL algorithm improves a model.

## Schema

The primary file is `tasks.jsonl`. Important fields include `stable_id`,
`skeleton_c`, `reference_solution`, `negative_cases`, `semantic_family`,
`derivation_family`, `source_repository_url`, `source_revision`,
`source_content_sha256`, `license_spdx`, and `review_status`.

`manifest.json` defines the frozen family-isolated splits and records the task
file checksum.

## License and provenance

Core-v1 was authored for this project and is licensed under Apache-2.0.
Its deterministic generator is
`environments/acsl-c/scripts/build_core_v1.py` in the canonical repository.

Core-v1 contains no CASP-derived C, skeleton, or reference implementation. The
larger CASP corpus used during local environment engineering remains an
explicit, non-bundled research adapter because the snapshot available to this
project does not retain sufficient per-file origin and license metadata for
public redistribution.

## Intended use and limitations

Core-v1 is a compact environment seed and release test pack. It is not a
comprehensive C verification benchmark, does not represent production C code,
and should not be used to claim state-of-the-art model performance. The trusted
computing base includes Frama-C, Why3, the selected SMT solvers, the judge
runner, and the sandbox runtime.

Canonical repository: <https://github.com/stanleyngugi/formally-verified-code-rl>
