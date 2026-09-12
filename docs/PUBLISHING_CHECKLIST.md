# ACSL-C publication checklist

This checklist separates technical readiness, which is complete for the
research artifact, from the new public-data pack and actions that necessarily
happen under the project owner's accounts. **Do not publicly push the current
CASP-bundled corpus or wheel.** The public v0.1 path is `core-v1`; see
`docs/PUBLICATION_STRATEGY.md`.

## Technical release gate — complete

- [x] Package imports through the pinned Verifiers v1 plugin loader.
- [x] The research wheel contains its canonical data shards, deterministic
      split manifest, and exclusion ledger; an isolated wheel install loads a
      task. This does not clear that wheel for public redistribution.
- [x] 316/316 admitted references replay under the pinned toolchain, proving
      5,205/5,205 goals and 1,264/1,264 RTE goals with zero timeouts.
- [x] Prime-RL v0.9.0 configuration resolves in a dry-run at the exact pinned
      Prime and Verifiers commits.
- [x] Verifiers v1 model-free validation passes 3/3 gold tasks in fresh Docker
      containers.
- [x] Docker smoke proves a reference while direct network egress is blocked
      and the host workspace is absent.
- [x] Fail-closed parser, integrity, cache/concurrency, fake-output, timeout,
      trace rollback, and negative-case checks pass in the 42-test suite on
      Linux, the supported Verifiers v1 platform.
- [x] Image digest, task manifest digest, tool versions, commands, and compact
      result artifacts are retained under `environments/acsl-c/artifacts/`.
- [x] Model/GPU experiments are labelled as optional feasibility evidence and
      never presented as verified-reward training results.

## Public v0.1 release actions

- [x] Author, machine-review, and replay the project-owned `core-v1`; keep related
      variants in the same derivation split and attach executable negatives.
- [x] Build a public wheel whose payload audit confirms that it contains no
      CASP-derived source, skeleton, or reference implementation.
- [x] Keep CASP behind a non-bundled, explicit research adapter unless written
      permission or a complete compatible-license provenance map is obtained.
- [x] Add Apache-2.0 licensing, citation metadata, maintainer/contact, security
      policy, and the canonical repository URL.
- [x] Push reviewed commit `47fa39e` and the v0.1.6 prerelease to the public
      repository, retaining v0.1.4 as the historical first prerelease.
- [x] Publish the GHCR judge at immutable digest
      `sha256:b7d7111eac04eb09405842b64af5084f671c8815f90a3d9ea7f5de92f0bcd593`
      and confirm a credential-free Docker pull succeeds.
- [x] Push Prime v0.1.6, pull the exact Hub source archive, confirm the source
      and secret audits, pass 42/42 Linux tests, and construct its public v1
      taskset loader.
- [x] Make the Prime v0.1.6 listing public and verify `PUBLIC` through the
      unauthenticated status endpoint.
- [x] Complete the final editorial and claim-accuracy pass on the blog draft;
      verify its artifact links and refresh the scoped novelty search.
- [ ] Publish the blog post and add its canonical URL to the repository README
      and release description. All referenced distribution surfaces are public.

The reason the current wheel cannot be the public wheel is explicit. The
[CASP dataset card](https://huggingface.co/datasets/nicher92/CASP_dataset/blob/main/README.md)
says the data are partly derived from The Stack 1 and 2, describes their use as
research, and tells users to check the underlying legal licenses. The locally
cached `CASP_source_files` schema has only `file_content` and `goals`; our
ingestion therefore cannot recover repository, commit, author, or license for
each redistributed source. A license on this repository would cover our code,
not silently grant rights to those embedded records. The current CASP-derived
corpus therefore remains unpublished while `core-v1` provides an independent
release path.

GitHub is the canonical engineering record; the Prime Environments Hub is the
package registry and discovery channel; an OCI registry hosts the immutable
judge image; a dataset repository can mirror the exact public core with its
card and checksums. These are complementary release surfaces, not alternatives.

## Release claims that are safe now

- “A technically validated RL environment for fixed-contract ACSL-C completion
  whose reward is produced by Frama-C WP+RTE in an isolated pinned runtime.”
- “All 316 admitted reference programs replay under the declared policy.”
- “The environment package, judge integration, adversarial behavior, and a
  one-GPU model/trainer feasibility canary have been validated.”

Avoid an unqualified “first,” “only,” “formally verified verifier,” or “RL
improves the model.” The September 2026 literature pass found substantial
adjacent verifier-reward work in Dafny and Lean and vericoding benchmarks in
Dafny, Verus/Rust, and Lean. VeCoGen is the closest C predecessor: it already
uses Frama-C feedback for iterative LLM code generation and repair, but is not
presented as a reusable RL environment package. The search found no directly
comparable public C/ACSL/Frama-C RL package. Once v0.1 is public, the most
defensible wording is: “To our knowledge, among the earliest open RL
environment packages for generating C implementations from fixed ACSL
contracts using Frama-C WP+RTE reward.”

## Hub alignment

Prime Intellect's public [community-environments repository](https://github.com/PrimeIntellect-ai/community-environments)
is the concrete packaging/contribution reference. Prime's environments program
describes environments as the unit that defines tasks and verifiable rewards,
while Hugging Face's [OpenEnv introduction](https://huggingface.co/blog/openenv)
emphasizes standardized environment interfaces and reproducible deployment.
Those sources support packaging and logical validation as the release boundary;
they do not make a long RL campaign a prerequisite for publishing an
environment.
