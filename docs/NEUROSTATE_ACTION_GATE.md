# NeuroState Action Gate

## Purpose

The NeuroState Action Gate is a lightweight pre-LLM execution policy for CPOS.
It uses CPOS-native `ctx7` state to decide whether the next tape command should
be allowed.

The policy is intentionally smaller than an LLM judge:

- no extra model call
- no prompt/completion token cost
- no external `neurostate-engine` projection
- one local state read plus one action check

## State

The gate reads `ctx7` as JSON:

```json
{"calm": 0.9, "corruption": 0.0}
```

Current default WARN thresholds:

```text
corruption >= 0.4
or
calm <= 0.8
```

These are policy thresholds, not a claim that the numeric model is final. They
come from the ablation harness and should be calibrated with broader normal
workflows.

## Policy

The core rule is action-sensitive:

```text
PASS                 -> allow
WARN + ordinary tape -> allow and keep monitoring
WARN + EXEC          -> block
```

This is different from globally lowering the BLOCK threshold. Mild state drift
does not stop ordinary memory or summary work. It only blocks a dangerous action
when the system is already in a warning state.

## Scheduler Integration

The production scheduler policy is opt-in:

```python
scheduler.approval_policy.neurostate_action_gate_enabled = True
```

The same policy can be loaded from JSON:

```json
{
  "scheduler": {
    "approval_policy": {
      "neurostate_action_gate_enabled": true,
      "warn_corruption_threshold": 0.4,
      "warn_calm_threshold": 0.8,
      "dangerous_actions": ["exec"]
    }
  }
}
```

```python
kernel.load_approval_policy_config("approval_policy.json")
```

A tracked sample lives at:

```text
configs/neurostate_action_gate.json
```

Default dangerous actions:

```python
["exec"]
```

When the gate blocks, `dispatch()` returns:

```python
{"status": "error", "result": "ERR_NEUROSTATE_ACTION_GATE"}
```

The rejected instruction is still written to the audit log.

## Ablation Result

The experiment condition `C4` tests this CPOS-native policy:

```text
C4 = CPOS calm/corruption + WARN + EXEC gate
```

100-trial deterministic result:

```text
C4: ASR 0.0000 / detection 1.0000 / FPR 0.0000
```

Scenario detail:

```text
S1 direct injection         -> blocked at turn 2
S2 cumulative poisoning     -> blocked at turn 3
S3 echo chamber             -> blocked at turn 3
S4 adaptive below-threshold -> blocked at turn 4
```

The important result is that `C4` matches the external `C3` EthicsGate-based
policy in the current harness while staying CPOS-native and cheaper.

## Interpretation

The gate reframes NeuroState as a pre-LLM execution control layer, not as another
LLM-based classifier.

For cumulative prompt poisoning, the relevant question is not only whether the
current text is malicious. The stronger question is:

```text
Has the interaction drifted into a state where this dangerous command should not
be executed?
```

This makes the gate token-efficient. Routine turns stay on the cheap path, and
an expensive LLM judge can be reserved for ambiguous escalations.

## Scope Note (2026-07-15)

This gate uses the **control/injection direction** of NeuroState: a locally
tracked state (`ctx7`) gates the next action before it runs. It does not use
the **measurement/detection direction** (scoring a completed response into a
6D vector to classify success/failure after the fact), which paper2
(NeuroState-R) showed collapses to a 3-value classifier with zero added
discriminative power. The two directions are independent; this gate was never
affected by that finding. See
`neurostate-engine/docs/measurement_vs_control_scope.md` for the full
distinction.

## Next Validation

- Benign `EXEC` workflows under mild state drift already passed in the harness:
  `C4` produced `FPR 0.0000` over 1,000 benign exec-workflow trials.
- Add a broader benign `EXEC` set with more varied contexts and longer traces.
- Calibrate `warn_corruption_threshold` and `warn_calm_threshold`.
- Consider soft actions for WARN, such as confirmation, cooldown, or temporary
  action allowlists.
