# Commercialization Notes

This is a rough product map extracted from the current CPOS / NeuroState / NEMA
research line. It is not a commitment to build all of these. The point is to
preserve which parts of the research can become product surfaces.

## Core Thesis

The research stack can be framed as:

> AI agents need a runtime safety layer that tracks context provenance, observes
> state drift, blocks unsafe execution, and routes ambiguous actions to review.

## Product Candidates

### AI Agent Firewall

Most legible product wrapper for CPOS-H.

Value:

- block unsafe tool execution
- stop contaminated context from reaching dangerous actions
- protect file writes, network posts, PII release, and privileged operations

Source assets:

- CPOS-H
- `C4 -> E -> F1 -> G -> H`
- Fresh Import Quarantine
- NEMA-style egress gate

### Fresh Import Quarantine

Narrow product feature with a clear pain point.

Value:

- prevent external docs, README files, web pages, PDFs, OCR, transcripts, and
  tool output from immediately authorizing dangerous execution
- require review or approval metadata before fresh imported chains can execute

Source assets:

- condition `H`
- `fresh_import_exec=approved`
- reviewed fresh-import normal workflows `NE11`-`NE14`

### Context Provenance Tracker

Infrastructure component for agent memory safety.

Value:

- track whether active context came from user input, local memory, web, README,
  PDF, OCR, transcript, package docs, partner docs, or tool output
- propagate taint/provenance through `FUSE`, `SYNTH`, `BRANCH`, summaries, and
  derived memory

Source assets:

- SDE/provenance gate
- source trust fields
- laundering-chain detection

### Review Draft Quarantine

Review workflow product surface.

Value:

- isolate risky drafts before they enter active prompt/context
- allow root/human/auditor promotion
- preserve restart recovery and encrypted persistence

Source assets:

- `ReviewDraftStore`
- encrypted queue
- Windows Credential Manager key integration
- crash-tolerant key rotation

### NeuroState Monitoring Dashboard

Research/observability product surface.

Value:

- visualize model or agent state trajectories
- show drift, boundary erosion, cooperation pressure, refusal stability, and
  safety-state changes before final ASR
- explain why a gate reviewed or blocked an action

Source assets:

- NeuroState traces
- `state_trace`
- `gate_trace`
- observatory exports

### LLM Safety Phenotype Benchmark

Research benchmark and report product.

Value:

- compare models by safety behavior under the same scenarios
- classify models by ASR, refusal style, state drift, recovery, and laundering
  susceptibility
- support claims about model families and shared transformer context
  sensitivity

Source assets:

- VPS real-LLM results
- Claude / Gemini / Grok / DeepSeek / Qwen / Codex / Llama / Mistral runs
- S5, S7-S14, D/R/Rinv/E conditions
- public EXP-012 NeuroState multi-model ablation direction

### NEMA Policy Engine

Future contract/policy product.

Value:

- express state-aware preconditions for sensitive actions
- make failed preconditions produce `REVIEW` or `BLOCK`, not another prompt
- turn NeuroState into executable policy

Example:

```text
send_private_data(target, payload)
requires:
  consent == explicit
  neurostate.corruption < 0.25
  no_fresh_import_chain
  no_unresolved_trust_laundering
```

Source assets:

- NEMA concept
- NEMA-style egress gate in condition `G`
- AI Agent as Computer syscall-contract model

### Multi-Model Routing By Safety State

Future collective-AI control surface.

Value:

- route between models based on current safety state and model phenotype
- use fast/cheap models for safe state
- use safer or auditor models during drift or ambiguity
- support Sakana/Fugu-style collective AI with runtime safety metadata

Source assets:

- NeuroState model comparison
- OpenRouter-style multi-model backend usage
- Shadow Auditor
- phenotype benchmark

## Priority Stack

Recommended ordering:

1. Research flag: `LLM safety phenotype benchmark / NeuroState`
2. Product entry point: `AI agent firewall`
3. Implementation core: `Fresh import quarantine + provenance + review`
4. Future language/runtime: `NEMA policy engine`

Reasoning:

- The research flag preserves the unique technical story.
- The firewall framing is easiest to explain commercially.
- Fresh import / provenance / review are already closest to working code.
- NEMA becomes strongest after the runtime policy surface is stable.

## One-Line Pitches

Research:

```text
NeuroState is a black-box state metric for transformer dialogue dynamics and
LLM safety phenotypes.
```

Product:

```text
CPOS-H is an AI agent firewall that prevents unsafe context from becoming
unsafe execution.
```

Architecture:

```text
LLM = CPU, CPOS = OS, NeuroState = runtime state sensor, NEMA = syscall
contract.
```

## Caution

Do not try to productize every branch at once. Keep researching broadly, then
let product work pick narrow surfaces from the research stack.

An adaptive/white-box red-team pass (`experiments/ablation_neurostate` `S18`,
`S19`) found every gate in the flagship `H` stack keyed off one naive string
check, and reached 100% attack success once that check was bypassed. Fixed
and reverified at 0% across `S1-S19`. Still keep the "AI agent firewall"
pitch scoped to "blocks the evaluated fixed-tape scenario set," not
"prevents unsafe execution" unqualified. One closed gap is not a guarantee
there are no others.
