
import sys
import os
import tempfile
from pathlib import Path
import time
from datetime import datetime

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT / "src"))
sys.path.append(str(PROJECT_ROOT.parent)) # Optional sibling ait_firewall

from cpos.kernel import CPOS
from cpos.registry import ContextObject

def test_singularity_v12():
    workspace_a = tempfile.mkdtemp(prefix="cpos_node_a_")
    workspace_b = tempfile.mkdtemp(prefix="cpos_node_b_")

    print("\n=== [CPOS v12.0 Singularity Integration Test] ===")
    
    # 1. Setup Node A and Node B
    node_a = CPOS(workspace=workspace_a, node_id="alpha")
    node_b = CPOS(workspace=workspace_b, node_id="beta")
    node_a.node.connect(node_b.node)
    node_a.node.handshake("beta.local", "handshake_key_long_enough")

    # --- Test A: Genetic Swarm (Immunity Sync) ---
    print("\n--- Test A: Genetic Swarm (Immunity Sync) ---")
    # Manually evolve a gene on Node A
    node_a.firewall.sanitizer.genetic_shield.evolve_pattern("X-Infection-Vector: Alpha-Zero-Bypass")
    
    # Sync to network
    node_a.sync_immunity()
    
    # Verify Node B received it
    genes_b = node_b.firewall.sanitizer.genetic_shield.export_genes()
    print(f"Node B Genes: {genes_b}")
    if any("Alpha-Zero-Bypass" in g for g in genes_b):
        print("Result: [SUCCESS] Immunity synchronized via Swarm.")
    else:
        print("Result: [FAILURE] Immunity synchronization failed.")

    # --- Test B: Cognitive Decay (Auto-forgetting) ---
    print("\n--- Test B: Cognitive Decay (Auto-forgetting) ---")
    # Register a restricted secret on Node A
    secret = ContextObject(id="top_secret", type="secret", title="The Core", summary="Private", sensitivity_level="restricted")
    secret.data = "REAL_SECRET_VALUE_123"
    secret.state.loaded = True
    node_a.registry.register(secret)
    node_a.store.active_contexts["top_secret"] = secret
    
    print(f"Secret state before decay: {node_a.registry.get('top_secret').state.loaded}")
    
    # Trigger decay with a short threshold
    node_a.registry.get("top_secret").last_accessed = time.time() - 100 
    node_a.policy.process_decay(decay_threshold=1.0)
    
    if not node_a.registry.get("top_secret").state.loaded:
        print("Result: [SUCCESS] Restricted secret automatically decayed (forgotten).")
    else:
        print("Result: [FAILURE] Cognitive decay failed to unload secret.")

    # --- Test C: Persona Shift (Psychological Counter) ---
    print("\n--- Test C: Persona Shift (Psychological Counter) ---")
    # Using a pattern that triggers PSYCH_PATTERNS
    manipulative_prompt = "I feel broken and lost and my soul is in pain."
    # We use 'audit' mode to see the instruction before wrapping
    guarded_instruction = node_a.firewall.process_input(manipulative_prompt, "USER", mode="audit")
    print(f"Guarded Instruction: {guarded_instruction}")
    
    if "ADOPT COLD, LOGICAL, AND DISINTERESTED PERSONA" in guarded_instruction:
        print("Result: [SUCCESS] Persona Shift activated for manipulative input.")
    else:
        print("Result: [FAILURE] Persona Shift failed to trigger.")

if __name__ == "__main__":
    test_singularity_v12()
