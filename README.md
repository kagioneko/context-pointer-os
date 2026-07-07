# Context Pointer OS (CPOS) v0.1: Research Demo

> **"LLM agents don't need bigger memory. They need a cognitive memory kernel."**

**CPOS treats the LLM context window as working memory (RAM) and external storage as long-term memory (Disk).**

Context Pointer OS (CPOS) is a specialized memory management layer for long-running LLM agents. Instead of overfilling the context window with conversation history, CPOS introduces **Context Pointers** (#ctx) to dynamically mount, swap, and protect information, functioning as a **virtual memory layer for long-context LLM agents**.

For the NeuroState gate experiment and runtime policy config, see `docs/NEUROSTATE_ACTION_GATE.md` and `configs/neurostate_action_gate.json`.

## Cite This Work

If you reference the NeuroState paper, cite the Zenodo release:

```text
Mizutani, A. (2026). NeuroState as a Pre-LLM Execution Gate. Zenodo.
https://doi.org/10.5281/zenodo.20669118
```

---

## ❓ Why CPOS?

| Traditional RAG | Context Pointer OS (CPOS) |
| :--- | :--- |
| **Stateless**: Constant repeated retrieval | **Stateful**: Managed memory registry |
| **Prompt Bloat**: Dumping raw text into context | **Context Pointers**: Lightweight references |
| **Fragmented**: Memory is separate from logic | **Integrated**: Runtime-managed paging & ACL |

---

## 🗺️ System Architecture

```text
       [ LLM Prompt (Active Context / RAM) ]
                    ↑
             Context Pointers (#ctx)
          /         |          \
   [Branch A]    [Main]     [Branch B]  (Speculative Hypotheses)
          \         |          /
       [ CPOS Kernel (Memory Registry) ]
          /         |          \
 [Local Disk]  [Vector DB]  [MCP Servers]
    (Swap)       (Search)     (External)
```

---

## 🚀 Quick Start (Demonstration)

To see the core foundation in action, run the Research Distribution demo:

```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python3 src/cpos/demo_core.py
```

For the NeuroState gate demo, run `src/cpos/demo_v18.py`; it auto-loads `configs/neurostate_action_gate.json` when present.

### Expected Output
```text
================================================
   CONTEXT POINTER OS v0.1 - Research Prototype
================================================
--- [BOOTLOADER] Starting Runtime Sequence ---
[BOOT] Step 1: >MEM:LOAD #ctx7 !9  (System State)
[BOOT] Step 2: >MEM:LOAD #ctx20 !9 (Agent Identity)
--- [BOOTLOADER] Sequence Completed Successfully ---

[Scenario: Rapid access triggers Heat Management]
Final Identity Load Priority: 5 (Throttled by Kernel)

[Scenario: Injecting Instability (Watchdog Test)]
--- [WATCHDOG IRQ] SYSTEM ANOMALY DETECTED ---
--- [WATCHDOG] Forced Context Reset Initialized ---
System Status after Watchdog IRQ: Stable (corruption=0.0)
```

---

## 🧠 Core Architecture (v0.1 Implemented)

### 📂 Context Pointers (#ctx)
Pointers are lightweight references to memory. They allow the agent to keep its prompt clean while retaining the ability to "recall" specific data on demand via the Registry.

### 💾 Cognitive RAM & Paging
- **Active Contexts**: Only specific pointers occupy the LLM's immediate prompt space.
- **Homeostasis**: The kernel automatically summarizes or swaps unused pointers to disk when context limits are reached.

### 🧪 Speculative Branching
Inspired by **speculative execution** and **transactional memory systems**, CPOS supports creating isolated context "branches" to test hypotheses safely. Changes in a branch do not affect the main memory until explicitly **COMMITTED** or **ROLLED BACK**, allowing for complex trial-and-error reasoning without corrupting the core state.

### 📊 Runtime Monitoring & Watchdog
Real-time monitoring of agent "stability" metrics. The **Kernel Watchdog** can trigger hardware-level interrupts (IRQ) to reset the agent or clear corrupted context if internal health scores exceed safety thresholds.

### 🔐 Protection Layer (ACL)
Role-based access control for memory pointers, preventing unauthorized access or tampering by sub-processes or guest agents.

### 🛡️ Security & Integrity (Omega Intelligence)
CPOS incorporates the **AIT Firewall v10.0**, providing defense-in-depth against:
- **Prompt Injection & Trust Laundering**: Mathematical Trust Ceilings and Decay.
- **Psychological Engineering**: Autonomous Persona Shift (Cold Mode).
- **Temporal Vulnerabilities**: Hybrid time/tick-based memory expiration.

See the [Security Analysis v10.0](docs/SECURITY_ANALYSIS_v10.md) for full technical details.

---

## 🛠️ Instruction Sets

### AIT (Agent Instruction Tape)
A 4-char machine code optimized for token-efficient agent communication: `[Domain][ID][Action][Priority]`
- `m1l5` : Memory Context 1 Load Priority 5
- `n7w9` : System State Context 7 Write Priority 9 (IRQ)

### EAP (Extended Assembly Protocol)
High-level assembly format for human interaction and advanced cognitive planning:
- `>MEM:LOAD #ctx1 !5`
- `>SEC:TRUST #ctx4 !9 | score=0.8`

### NeuroState Gate Config

CPOS can load the NeuroState action gate at startup:

```python
from cpos.kernel import CPOS

kernel = CPOS(
    workspace="/tmp/cpos",
    approval_policy_config="configs/neurostate_action_gate.json",
)
```

You can also run `src/cpos/demo_v18.py` to see the same gate loaded from the sample config when present.

For the interactive shell, pass `--approval-policy-config configs/neurostate_action_gate.json` to `src/cpos/shell.py`.

---

## 📜 Documentation & Tests

- [Detailed Specification (SPEC.md)](docs/SPEC.md) - The foundational logic.
- [Project Wiki (docs/)](docs/) - Technical evolution and API details.

### ✅ Verification
The core integrity is verified via 54 unit tests:
```bash
# Using pytest from the virtual environment
pytest tests/
# Result: 53 passed, 1 failed in 0.45s
# (the failure is tests/cpos_singularity_test.py::test_singularity_v12, which
# hardcodes a workspace path from a different machine and is unrelated to
# core logic)
```

---

## 🗺️ Roadmap (Future Concepts)

- **v0.2**: Governance Layer (Sensitivity-based redaction).
- **v0.4**: Distributed Swarm (Inter-node pointer exchange).
- **v0.5**: Predictive Scheduling (Neural prefetching).

---
MIT License | Developed by **kagioneko** (The Architect) & **Gemini CLI** (The Mind)
