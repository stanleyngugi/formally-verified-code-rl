# Baseline Results — Cerebras free tier (Aug 2026)

Judge: Frama-C 33.0 WP+RTE, alt-ergo+z3, 20s/goal.
Task pool: casp_eval.jsonl (48 tasks). Hints mode: complete function body under
fixed ACSL annotations. Score = 0.10*gate + 0.50*vc_fraction + 0.20*full_proof
(spec_strength neutral until spectests land).

## Easy slice (12 lowest-vC tasks, vc 4–8)

| model | gate | full_proof | mean frac |
|---|---|---|---|
| gpt-oss-120b | 83.3% | 83.3% | 83.3% |
| gemma-4-31b | 91.7% | 91.7% | 91.7% |

Both near-ceiling; easy tasks don't discriminate. (gpt-oss ran with an early
2048-token budget here; see artifact note below.)

## Hard slice (8 highest-vC tasks, vc 37–114)

| model | gate | full_proof | mean frac |
|---|---|---|---|
| gpt-oss-120b | 100% | **87.5%** | 93.4% |
| gemma-4-31b | 100% | 62.5% | **95.9%** |

### Findings

1. **Token-budget artifact caught by the reward itself.** With max_tokens=2048,
   gpt-oss scored three "0/0 goals" — reasoning tokens consumed the budget and
   code was truncated mid-output. At 8192 it jumped 62.5% -> 87.5%, including a
   full 112-goal verification (vc=114 task). Lesson: reasoning models need
   headroom, and our gate metric (goals_total > 0) flags truncation instantly.
2. **The staged reward discriminates exactly as designed.** On identical hard
   tasks, gemma produces valid annotated C that misses a few goals (42/43,
   9/12, 100/106) -> high dense reward (94–98% frac) but no full-proof bonus.
   This is precisely the partial-credit signal GRPO needs to learn from.
3. **Both models are far above the naive floor** on hints-mode completion of
   real-world annotated C. The interesting training frontier is not "can the
   model write annotations" but: harder synthesis modes (full mode from NL
   spec), spec *strength* (spectest-gated), and consistency under sampling.

## Spend

~60k tokens across all experiments (~4 runs + connectivity tests) — well under
$1 of the $4 credit. Per-run cost at n=12/slice/model is ~15–20k tokens.

## Raw data

data/baselines/baseline_*.json (per-task goals, fractions, token usage).
