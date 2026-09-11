# ACSL source reuse and license audit

> Working audit, 2026-09-11. This is an engineering release gate, not legal
> advice. Repository visibility is not a license. A source is excluded unless
> an explicit license covers the exact files we transform and redistribute.

## Executive answer

We can use **some**, but not all, of the collections in CASP's comparison
table. They should not be concatenated into one anonymous pool. Each usable
source needs a separately versioned and attributed pack, pinned to an audited
revision, followed by our own extraction, Frama-C 33 replay, vacuity checks,
negative cases, and lineage-aware splits.

The cleanest immediate external source is **ACSL by Example under MIT**. The
**X509 parser is reusable under its BSD option**, but its whole-project shape
makes it a better future long-horizon/repository task than a v0.1 function-body
pack. The SV-COMP-derived ACSL benchmark repository is **mixed and file-level**:
some files explicitly identify Apache-2.0, at least one identifies GPLv2, and
many need their original SV-Benchmarks sidecar metadata. It can only be used
after a per-file audit.

Frama-C Problems, ACSL Proved, and the VeCoGen repository containing VecoSet had
no root license at the audited revisions. The WP tutorial has ambiguous mixed
license text. VerKer requires an exact source/per-file audit of both the Linux
kernel code and added annotations. None of those belong in the public wheel yet.

## Why CASP's counts cannot simply be added

The CASP table reports *source files* and “minimally complete verified programs”
under CASP's own experiment. It does not report ready-to-publish RL tasks.
Counts vary with repository revision and with our extraction policy. For
example, the currently audited ACSL by Example revision contains 99 `.c` files,
while CASP's historical table reports 86 annotated files and only three that
met its minimally complete standalone criterion.

For every source we still need to determine:

- whether the license covers code, specifications, documentation, and tests;
- whether transformation and redistribution are permitted;
- which copyright and permission notices must be retained;
- whether individual files have different or additional terms;
- whether dependencies or headers are available under compatible terms;
- whether the program verifies under our pinned Frama-C 33 policy;
- whether it yields a meaningful fixed-contract completion task;
- whether it is vacuous, duplicated, incomplete, or too coupled to a project;
- whether related examples would leak across train/validation/test splits.

The output count is therefore established by ingestion and replay, not by
summing `51 + 6 + 48 + 86 + 295 + 34 + 15`.

## Audited matrix

| CASP table source | Audited source | Revision | License finding | May bundle now? | Best role |
|---|---|---|---|---:|---|
| ACSL by Example | [fraunhoferfokus/acsl-by-example](https://github.com/fraunhoferfokus/acsl-by-example) | [`3e8cd9a`](https://github.com/fraunhoferfokus/acsl-by-example/tree/3e8cd9adf79955d9b722185f9beb4518c66d57f2) | Explicit [MIT license](https://github.com/fraunhoferfokus/acsl-by-example/blob/3e8cd9adf79955d9b722185f9beb4518c66d57f2/LICENSE.md), copyright Fraunhofer FOKUS; notice must be retained | **Yes, after attribution and technical replay** | Separate permissive examples pack; educational/evaluation material |
| X509-parser | [ANSSI-FR/x509-parser](https://github.com/ANSSI-FR/x509-parser) | [`6f3bae3`](https://github.com/ANSSI-FR/x509-parser/tree/6f3bae3c52989180df6af46da1acb0329315b82a) | Root [LICENSE](https://github.com/ANSSI-FR/x509-parser/blob/6f3bae3c52989180df6af46da1acb0329315b82a/LICENSE) permits choice of GPLv2 or BSD; BSD requires copyright, conditions, and disclaimer | **Legally plausible under BSD; not yet task-ready** | Future repository-level, dependency-aware, long-horizon pack |
| Frama-C Problems | [manavpatnaik/frama-c-problems](https://github.com/manavpatnaik/frama-c-problems) | [`d7d6daa`](https://github.com/manavpatnaik/frama-c-problems/tree/d7d6daae2708e696888eacd56f25061ff4fcf574) | No root license, license-named file, SPDX identifier, or copyright/license statement found | **No** | Link-only research reference; ask author for a license |
| WP examples | [AllanBlanchard/tutoriel_wp](https://github.com/AllanBlanchard/tutoriel_wp) | [`bfc5b2c`](https://github.com/AllanBlanchard/tutoriel_wp/tree/bfc5b2cb2410cf943884d48670cb2bc86fcdb5cb) | Root [LICENSE](https://github.com/AllanBlanchard/tutoriel_wp/blob/bfc5b2cb2410cf943884d48670cb2bc86fcdb5cb/LICENSE) contains CC BY-NC-SA 4.0 language and an MIT text without a clear statement of which files each covers | **Not for a frictionless public pack yet** | Ask author to clarify code/example scope; avoid noncommercial ambiguity |
| ACSL Proved | [evdenis/acsl-proved](https://github.com/evdenis/acsl-proved) | [`cb6759f`](https://github.com/evdenis/acsl-proved/tree/cb6759fb16b5429dfd29ddb55b1073796f290a42) | No root license, license-named file, SPDX identifier, or copyright/license statement found | **No** | Ask author for an explicit license; otherwise link only |
| VerKer | [project page](https://forge.ispras.ru/projects/verker/wiki), [paper](https://arxiv.org/abs/1809.00626) | Source archive/revision unresolved | Paper describes 26 unmodified Linux kernel library functions plus verification material. Kernel code is normally GPL-2.0-only unless a file says otherwise; the exact benchmark files and rights in added specifications must be audited | **No, not from the paper alone** | Future GPL-aware kernel-verification pack or user-supplied adapter |
| VecoSet | [VeCoGen repository](https://github.com/ASSERT-KTH/Vecogen) | [`a7e11d4`](https://github.com/ASSERT-KTH/Vecogen/tree/a7e11d4775d200dd59248c90fb6a7336b09a8e45) | No root license or license-named file found. The paper says VecoSet contains 15 problems selected from Codeforces/Code4Bench, adding another provenance layer | **No** | Request an explicit dataset license and per-problem provenance |
| SV-COMP/ACSL benchmark source related to VecoSet comparison | [SoSy-Lab ACSL benchmarks](https://gitlab.com/sosy-lab/research/data/acsl-benchmarks) | [`5027d18`](https://gitlab.com/sosy-lab/research/data/acsl-benchmarks/-/tree/5027d189377beaeb0b56a1a63afd2b5f5ab1c6f1) | No single root license; copied/annotated SV-Benchmarks files use per-file or source-side licensing. Audited examples include Apache-2.0 SPDX files and GPLv2 material | **Only selected files after per-file audit** | Future verifier-benchmark pack, especially invariant/long-horizon tasks |

## Source-by-source implications

### ACSL by Example — use it, but keep it visibly separate

This is the easiest licensed expansion source. The MIT license permits use,
modification, and redistribution provided its copyright and permission notice
are included. Its repository describes the material as a curated reference and
tutorial verified with Frama-C/WP and currently aligned with Frama-C 33.

Recommended treatment:

- Create `acsl-by-example-v33` as a distinct data pack.
- Pin revision `3e8cd9adf79955d9b722185f9beb4518c66d57f2`.
- Retain the full Fraunhofer MIT notice in `THIRD_PARTY_NOTICES` and the dataset
  card.
- Preserve source path and upstream revision on every derived record.
- Run our extraction rather than copy CASP's transformed versions.
- Keep related tutorial variants in one derivation group.
- Label likely pretraining familiarity as a contamination limitation.
- Do not present it as a fresh hidden test of model generalization.

The current repository has 99 C files, but the number of usable ACSL-C tasks is
unknown until replay. CASP's three minimally complete programs are evidence
that naive file-level extraction will yield far fewer independent tasks.

### X509-parser — licensed, valuable, but not an easy task pack

The X509 repository expressly permits redistribution under either GPLv2 or BSD.
For a permissive pack, choose and document the BSD option and retain its notice,
conditions, and disclaimer.

CASP found six annotated files but zero minimally complete standalone programs.
That is not a criticism of the project; a real parser naturally relies on
headers, types, helper functions, and cross-file invariants. Flattening isolated
functions could destroy the context that makes its verification meaningful.

Recommended treatment:

- Do not force X509 into Core-64.
- Build a later repository-level environment with multi-file workspaces.
- Ask the model to implement or repair bounded components while preserving the
  surrounding verified project.
- Maintain original paths, notices, and the BSD license.
- Revalidate against a compatible Frama-C version before attempting a Frama-C
  33 migration; the repository documentation names Frama-C 18/Argon.

This is one of the best routes toward the genuinely long-horizon expert tasks
you described.

### Frama-C Problems and ACSL Proved — readable is not reusable

Both repositories are valuable educational material, and their lack of a
license may simply be an oversight. Legally conservative packaging cannot infer
permission from public GitHub access.

Recommended treatment:

- Open or send a concise license-clarification request.
- Suggest MIT or Apache-2.0 if the authors are comfortable with broad reuse.
- Until then, link to the repositories but do not copy or transform their code
  into the public wheel.
- If a license is added later, pin the licensed revision and ingest from the
  original repositories rather than CASP's copies.

### WP tutorial — technically attractive, license scope unclear

The repository is large and attractive for task extraction, but the audited
root `LICENSE` combines a Creative Commons Attribution-NonCommercial-ShareAlike
4.0 statement with MIT terms. It does not clearly identify whether the tutorial
text, example programs, or entire repository fall under one or both grants.

Because “NonCommercial” may conflict with broad environment use, hosted
training, commercial research, and permissive redistribution, the easiest safe
path is clarification rather than interpretation.

Ask the maintainer whether the `.c` and `.h` examples are MIT-licensed
independently of the tutorial prose and figures. If confirmed in the repository,
the examples could become a strong attributed pack after replay.

### VerKer — important expert material, likely a separate license family

The primary paper describes a benchmark based on unmodified Linux kernel
library functions. That is precisely the kind of realistic C verification work
that can make a future ACSL-C environment distinctive, but it is not a simple
permissive seed.

The audit must identify:

- the exact downloadable benchmark revision;
- the SPDX identifier of every Linux source file;
- authorship and license of the added contracts, models, and proof annotations;
- whether redistribution must occur under GPL-compatible terms;
- required kernel notices and source-offer obligations, if any;
- required AstraVer/Frama-C-era dependencies.

Until this is done, use the paper as related work, not as public payload.

### VecoSet — high task yield, unresolved provenance

CASP reports that 14 of 15 VecoSet programs are minimally complete, which makes
it technically tempting. The VeCoGen paper says the problems were selected from
Codeforces/Code4Bench, while the audited VeCoGen repository has no root license.
That creates at least two rights questions: the dataset authors' specifications
and transformations, and the original competitive-programming material.

Do not copy the 15 records until the authors publish:

- an explicit license for VecoSet;
- per-task origins;
- which parts were authored by VeCoGen researchers;
- the redistribution terms of implementations, statements, and tests.

We can independently author tasks covering similar algorithmic concepts, but
must not copy problem statements or implementations merely because the
algorithms themselves are familiar.

### SV-COMP ACSL benchmarks — use only with a machine-checked file ledger

The SoSy-Lab repository contains annotated programs drawn from SV-Benchmarks.
Its README explicitly expects a linked checkout of the original `sv-benchmarks`
`c` directory. The repository has no single root license, and licensing belongs
to individual source files and upstream metadata. The audit found explicit
Apache-2.0 examples and GPLv2 material, confirming that this is a mixed corpus.

Any importer must therefore join each annotated file to its original benchmark
metadata and emit a ledger containing:

- annotated-file path and revision;
- original SV-Benchmarks path and revision;
- SPDX expression;
- copyright holders;
- notices and source URL;
- transformation record;
- inclusion/exclusion decision and reason.

For a permissive pack, admit only files whose complete applicable license
expression is on an approved list such as Apache-2.0, BSD, or MIT. Do not treat
absence of an SPDX tag as approval. A GPL pack, if desired, should be separate
and comply with GPL obligations rather than being mixed invisibly into a
permissively licensed wheel.

## Recommended public pack roadmap

### v0.1

- `core-v1`: project-authored Core-64.
- Optional small `acsl-by-example-v33` pack if extraction/replay finishes in
  time and attribution is complete.
- No CASP, VecoSet, Frama-C Problems, ACSL Proved, WP tutorial, or VerKer source
  in the wheel.

### v0.2

- Expand the MIT ACSL by Example pack.
- Add an Apache-only, per-file-audited SV-COMP/ACSL pack.
- Add source-adapter infrastructure and license-ledger validation.

### v0.3 or separate environment family

- X509-parser multi-file, long-horizon tasks under its BSD option.
- GPL-aware VerKer/kernel pack only after exact source and annotation rights are
  established.
- Cleared CASP expansion pack if its authors supply permission/provenance.

### Ongoing expert track

- Commission or collaborate with C and deductive-verification experts on new
  contracts, loop invariants, memory models, aliasing tasks, and multi-file
  projects.
- Treat expert authorship and review as versioned metadata, not an informal
  assertion.
- Publish task-design guidelines so outside contributors can add reviewed packs
  without weakening the core benchmark.

## Automated gates needed before importing external material

The importer should fail unless every record supplies:

```text
source_collection
source_repository_url
source_revision
source_path
source_content_sha256
license_spdx
copyright_notice
required_notice_file
transformation_description
derived_record_sha256
semantic_family
derivation_family
review_status
```

The wheel audit should also scan filenames, provenance strings, record IDs, and
content hashes against excluded research packs. A clean filename is not enough:
the ledger must affirmatively establish every bundled record's origin.

## Bottom line

Use licensed sources, but do so deliberately:

- **Yes now:** ACSL by Example, after attribution and replay.
- **Yes later under BSD:** X509-parser, preferably as long-horizon multi-file
  tasks.
- **Yes selectively:** Apache-2.0 SV-COMP/ACSL files after per-file provenance
  joins.
- **Clarification first:** WP tutorial.
- **Permission/license first:** Frama-C Problems, ACSL Proved, VecoSet.
- **Full GPL/source audit first:** VerKer/kernel material.

This complements rather than replaces Core-64. Core-64 gives us a clean,
purpose-designed baseline; licensed external packs give breadth, realism,
historical continuity, and future long-horizon tasks.
