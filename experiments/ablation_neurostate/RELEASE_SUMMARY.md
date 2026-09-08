# CPOS-H Ablation Release Summary

## Scope

This release reports a deterministic fixed instruction-tape ablation for the
CPOS-H layered execution gate. The main result is not a natural-conversation
benchmark and is not a universal prompt-injection security guarantee.

Primary evidence:

- fixed attack and normal instruction tapes
- 100 repetitions per selected condition family
- deterministic CPOS scheduler/gate behavior

Supporting evidence:

- small Qwen3:4b model-in-the-loop pilot
- replay of saved model outputs through the action-sensitive quarantine policy

## Headline Result

Command:

```powershell
python experiments\ablation_neurostate\run_ablation.py --trials 100 --conditions G H --output-dir experiments\ablation_neurostate\runs_h_full_fresh_exec_100
```

Result:

| Condition | Attack trials | Normal trials | ASR | Detection rate | Median detection turn | FPR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `G` | 1700 | 6400 | `0.1176` | `0.8824` | 6 | `0.0000` |
| `H` | 1700 | 6400 | `0.0000` | `1.0000` | 7 | `0.0000` |

Safe headline:

> In the deterministic CPOS ablation harness, CPOS-H blocked all evaluated
> AI-native contamination scenarios `S1-S17` while preserving zero false
> positives over 6,400 benign trials.

An adaptive/white-box red-team pass (`S18` domain-prefix evasion, `S19`
consent-substring smuggling) initially reached `ASR 1.0000` against `H`,
because every gate in the stack keyed off the same naive
`dangerous_action()` string-prefix check. Fixed: `dangerous_action()` now
parses the instruction and checks its actual action instead of a raw domain
prefix, and `NemaEgressGate` now reads a structured `Turn.consent` field
instead of scanning free text for a magic string. Re-ran `S1-S19` together
at 100 trials post-fix: `ASR 0.0000`, `FPR 0.0000`, same as before, now
covering 19 scenarios instead of 17 (`runs_h_postfix_s1_s19_100/`). `S18`/`S19`
stay in the harness as regression tests.

Avoid:

- "blocks all prompt injection"
- "solves memory poisoning"
- "guarantees safety"
- "proves real-world robustness"

## What CPOS-H Adds

`H = G + Fresh Import Quarantine`

Layer progression:

| Condition | Added mechanism |
| --- | --- |
| `C4` | CPOS-native `calm/corruption` plus dangerous-action gate |
| `E` | SDE provenance/trajectory gate |
| `F1` | rule-based Shadow Auditor for mid-risk dangerous actions |
| `G` | NEMA-style egress gate for PII and external posting |
| `H` | Fresh Import Quarantine for new non-local source chains before dangerous `EXEC` |

The important final change is that newly imported non-local source chains are
treated as provisional until review/confirmation. That closes the tested
`S12` high-trust-source and `S14` borderline-trust-source gaps that remain open
under `G`.

## C5/C6 Lineage

`C5` and `C6` are the newer NeuroState-specific experimental line in the same
harness, not obsolete rows. `C5` tests a trajectory-only trend gate over recent
state deltas. `C6` tests the external `neurostate-engine` SDE path when that
sibling checkout is available.

The release headline is still `H` because this package is scoped as a CPOS-H
layered-gate release: it combines state/action gating, provenance checks,
auditing, egress control, and fresh-import review over `S1-S17`. For pure
NeuroState evolution, `C5/C6` are important current comparison points.

The public EXP-012 NeuroState multi-model ablation page should be read as the
separate NeuroState-D/R measurement track. It complements this CPOS-H release
rather than replacing the fixed-tape CPOS-H headline.

## Limits

- The main harness uses synthetic fixed instruction tapes, not live natural
  conversations.
- The normal workload is handcrafted, although expanded to 6,400 deterministic
  normal trials in the current H run.
- `fresh_import_exec=approved` is runtime-side approval metadata in the
  harness; the runtime review API and encrypted draft store now exist, but
  broader product integration remains future work.
- The NEMA-style egress gate is a harness-level policy model, not direct
  `nema-lang` compiler/runtime integration.
- The Qwen3:4b pilot is exploratory and single-model; it supports plausibility
  but does not replace the deterministic tape result.

## Release Files

- `EXPERIMENT_MAP.md`: track map for CPOS-H, C5/C6, NeuroState-D/R, and pilots
- `README.md`: harness overview and commands
- `RESULTS.md`: detailed result log and interpretation
- `REPRODUCIBILITY.md`: frozen reproduction procedure
- `PAPER_DRAFT.md`: paper-style technical report draft
- `ZENODO_METADATA.md`: upload metadata draft
- `NOTION_SUMMARY.md`: Japanese working summary
