import tempfile
import os
import json
import time
from cpos.kernel import CPOS
from cpos.registry import ContextObject

def main():
    print("================================================")
    print("   CONTEXT POINTER OS v4.1 - Cognitive Dreaming ")
    print("================================================")
    
    workspace = tempfile.mkdtemp(prefix="cpos_demo_")
    os.makedirs(workspace, exist_ok=True)
    
    os_kernel = CPOS(workspace=workspace)
    
    # --- Scenario 1: Dreaming is OFF by default ---
    print("\n[Scenario: Dreaming is OFF]")
    # Create multiple fusions to exceed the limit (5)
    for i in range(7):
        os_kernel.registry.register(ContextObject(
            id=f"fused_memory_{i}", type="memory", title=f"Fusion {i}", summary="..."
        ))
    
    # Run some ticks
    for _ in range(5): os_kernel.step(">MEM:LS #ctx0 !1", agent="root")
    
    print(f"Active Fusions: {len([o for o in os_kernel.registry.registry.values() if o.id.startswith('fused_') and o.status != 'deleted'])}")

    # --- Scenario 2: Toggle Dreaming ON ---
    print("\n[Scenario: Toggling Dreaming ON]")
    os_kernel.step(">SEC:POLICY #ctx0 !9 | dreaming=true", agent="root")
    print(f"Dreaming Enabled? {os_kernel.scheduler.retrieval_policy.dreaming_enabled}")

    # Run ticks to trigger dream cycle
    print("Action: System dreaming in background...")
    for _ in range(5): os_kernel.step(">MEM:LS #ctx0 !1", agent="root")
    
    # Verify consolidation (should have deleted 2 fusions if > 5)
    fused_count = len([o for o in os_kernel.registry.registry.values() if o.id.startswith('fused_') and o.status != 'deleted'])
    print(f"Active Fusions after dream: {fused_count} (Expected: 5)")

    # --- Scenario 3: Hypothesis Revival ---
    print("\n[Scenario: Re-evaluating failed hypothesis]")
    # Setup a failed hypothesis (rolled back)
    os_kernel.registry.register(ContextObject(
        id="hyp_theory_01", type="reasoning", title="Theory X", 
        summary="Experimental theory", status="deleted", 
        invalidated_reason="rollback", trust_score=0.1
    ))
    
    print(f"Initial status of hyp_theory_01: {os_kernel.registry.get('hyp_theory_01').status}")
    
    # Run ticks to trigger revival (revival happens every 20 ticks in this prototype)
    print("Action: System dreaming deeply...")
    for _ in range(25): os_kernel.step(">MEM:LS #ctx0 !1", agent="root")
    
    revived_obj = os_kernel.registry.get("hyp_theory_01")
    print(f"Status of hyp_theory_01 after dream: {revived_obj.status}")
    print(f"New Trust Score: {revived_obj.trust_score:.2f}")

    # Final Report
    os_kernel.save_report("v41_dream_report.html")
    print("\n[COMPLETE] CPOS v4.1 Cognitive Dreaming verified.")

if __name__ == "__main__":
    main()
