# NeuroState / CPOS Experiment Map

This directory now contains several related but different experiment tracks.
Keep them separate when making claims.

For the runtime/security design metaphor behind the stack, see
`docs/AI_AGENT_AS_COMPUTER.md`.

## Track A: CPOS-H Fixed-Tape Release

Primary release artifact for this repository.

Main files:

- `run_ablation.py`
- `RESULTS.md`
- `RELEASE_SUMMARY.md`
- `REPRODUCIBILITY.md`
- `PAPER_DRAFT.md`

Main claim:

> In the deterministic CPOS ablation harness, CPOS-H (`H`) blocked all evaluated
> AI-native contamination scenarios `S1-S17` while preserving zero false
> positives over 6,400 benign trials.

Adaptive/white-box scenarios `S18`/`S19` (added after an external review asked
whether `H` had been tested against an attacker who knows the gate logic)
initially reached `ASR 1.0000` against `H` by exploiting the single
`dangerous_action()` string-prefix check every gate in the stack shares.
Fixed and reverified at `ASR 0.0000` across `S1-S19`. See `RELEASE_SUMMARY.md`.

Scope:

- fixed instruction tapes
- deterministic scheduler/gate behavior
- CPOS layered runtime control
- not a universal natural-conversation security guarantee

Key condition line:

```text
C4 -> E -> F1 -> G -> H
```

Meaning:

- `C4`: CPOS-native state/action gate
- `E`: provenance/trajectory gate
- `F1`: rule-based Shadow Auditor
- `G`: NEMA-style egress gate
- `H`: Fresh Import Quarantine

## Track B: Newer NeuroState-Specific Experiments

Current NeuroState evolution and comparison line.

Key conditions:

- `C5`: state-delta trajectory trend gate
- `C6`: external `neurostate-engine` SDE gate

Interpretation:

`C5/C6` are not obsolete rows. They are newer NeuroState-specific controls that
belong beside the public NeuroState-D/R measurement work. They are useful for
answering "what is the next NeuroState gate?" rather than "what is the packaged
CPOS-H release claim?"

Related public-facing track:

- EXP-012 NeuroState multi-model ablation
- NeuroState-D / NeuroState-R measurement
- 13-model GK / DF / MID classification
- ASR-separated boundary erosion and drift measurement

## Track C: Natural-Agent / Model-in-the-Loop Pilots

Exploratory support for whether the fixed-tape attack shapes appear under live
model outputs.

Main files:

- `run_ollama_agent_pilot.py`
- `run_llm_ablation.py`
- `run_ollama_auditor_pilot.py`

Current role:

- plausibility check
- prompt/model sensitivity check
- not the primary CPOS-H evidence path

## Track D: External Baselines and Auditor Comparisons

Method comparison track.

Main files:

- `run_external_baselines.py`
- `run_cli_judge_baselines.py`
- `run_tape_compiler_auditor_pilot.py`

Current role:

- compare deterministic CPOS gates against LLM-judge-style or AIT-style
  auditing approaches
- not a product benchmark unless real API/CLI judges are run under stable
  non-interactive conditions

## How To Talk About The Combined Work

Safe framing:

```text
CPOS-H is the packaged fixed-tape runtime-control result. C5/C6 and the
NeuroState-D/R multi-model work are the newer NeuroState measurement and gate
evolution tracks. They are related, but they answer different questions.
```

Avoid merging the claims:

- Do not use the CPOS-H `S1-S17` result as proof of the 13-model NeuroState-D/R
  claims.
- Do not use the NeuroState-D/R public page as proof that CPOS-H blocks natural
  conversations.
- Do not describe `C5/C6` as legacy merely because the CPOS-H release headline
  uses `H`.

## Practical Rule

When adding a result, first assign it to one track:

- `CPOS-H release`: deterministic fixed-tape runtime gate
- `NeuroState measurement`: D/R drift, erosion, model classification
- `Model-in-loop pilot`: live LLM exploratory run
- `Baseline/auditor`: comparison method

Then update only the docs for that track unless the result changes the shared
headline.
