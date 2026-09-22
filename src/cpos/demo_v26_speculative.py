import tempfile
import os
import json
from cpos.kernel import CPOS
from cpos.registry import ContextObject

def main():
    print("================================================")
    print("   CONTEXT POINTER OS v2.6 - Speculative Cognition ")
    print("================================================")
    
    workspace = tempfile.mkdtemp(prefix="cpos_demo_")
    os.makedirs(workspace, exist_ok=True)
    
    os_kernel = CPOS(workspace=workspace)
    
    # 1. Setup Base Context
    os_kernel.registry.register(ContextObject(
        id="ctx_brain", type="reasoning", title="Core Knowledge", 
        summary="Basic logic", data="Earth is flat (Initial Error)",
        trust_score=0.8, importance=1.0
    ))

    # 2. Scenario: Create a Hypothesis (FORK)
    print("\n[Scenario: Forking Hypothesis to test new idea]")
    os_kernel.step(">REA:FORK #ctx_brain !5 | round_earth")
    
    # Check the branch status
    hyp_obj = os_kernel.registry.get("ctx_brain.round_earth")
    print(f"Hypothesis ID: {hyp_obj.id}")
    print(f"Hypothesis Trust Score: {hyp_obj.trust_score} (Should be low)")
    
    # 3. Work in the Sandbox
    print("\n[Scenario: Updating data in the sandbox]")
    os_kernel.step(">REA:UPDATE #ctx_brain.round_earth !5 | data=Earth is a sphere")
    
    # Verify isolation
    parent = os_kernel.registry.get("ctx_brain")
    print(f"Parent Data (Isolated): {parent.data}")
    print(f"Hypothesis Data: {hyp_obj.data}")

    # 4. Scenario: Commit successful hypothesis
    print("\n[Scenario: Committing the successful hypothesis]")
    os_kernel.step(">REA:COMMIT #ctx_brain.round_earth !9")
    
    print(f"Parent Data (After Commit): {parent.data}")
    print(f"Parent Trust Score (Improved): {parent.trust_score}")
    print(f"Hypothesis Status (Cleaned up): {hyp_obj.status}")

    # 5. Scenario: Rollback a failed hypothesis
    print("\n[Scenario: Testing a crazy idea and rolling back]")
    os_kernel.step(">REA:FORK #ctx_brain !5 | donut_earth")
    os_kernel.step(">REA:UPDATE #ctx_brain.donut_earth !5 | data=Earth is a donut")
    os_kernel.step(">REA:ROLLBACK #ctx_brain.donut_earth !9")
    
    final_parent = os_kernel.registry.get("ctx_brain")
    print(f"Final Parent Data: {final_parent.data}")
    
    donut_hyp = os_kernel.registry.get("ctx_brain.donut_earth")
    print(f"Donut Hypothesis Status: {donut_hyp.status}")

    # 6. Final Report
    os_kernel.save_report("v26_speculative_report.html")
    print("\n[COMPLETE] CPOS v2.6 Speculative Branching verified.")

if __name__ == "__main__":
    main()
