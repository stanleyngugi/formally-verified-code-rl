# Security policy

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting for
`stanleyngugi/formally-verified-code-rl`. Do not open a public issue for a vulnerability
that could expose a host, sandbox, credential, or training worker.

Include the affected version, reproduction steps, expected impact, and any
suggested mitigation. Reports involving untrusted C preprocessing, sandbox
escape, cache poisoning, parser fail-open behavior, or network-policy bypass
are especially important.

## Supported versions

Security fixes are applied to the latest published release. Research-only
corpora and historical experiment configurations are not production services.

## Trust boundary

Model-generated C is untrusted and must be judged in a Docker or Prime sandbox.
The subprocess runtime is only for trusted local diagnostics. The project
trusts the pinned Frama-C/Why3/SMT toolchain and does not claim those components
are themselves formally verified.
