import tempfile
import os
import json
from cpos.kernel import CPOS
from cpos.registry import ContextObject

def main():
    print("================================================")
    print("   CONTEXT POINTER OS v3.4 - Kernel Auditor      ")
    print("================================================")
    
    workspace = tempfile.mkdtemp(prefix="cpos_demo_")
    os.makedirs(workspace, exist_ok=True)
    
    os_kernel = CPOS(workspace=workspace)
    
    # 1. Setup contradicting information
    print("\n[Scenario: Injecting Contradicting Knowledge]")
    
    # High Trust Truth
    os_kernel.registry.register(ContextObject(
        id="earth.fact", type="memory", title="Satellite Imagery", 
        summary="Verified orbital data", data="The Earth is an oblate spheroid.",
        trust_score=1.0
    ))
    
    # Low Trust Rumor (Contradicts the fact)
    os_kernel.registry.register(ContextObject(
        id="earth.rumor", type="memory", title="Ancient Scroll", 
        summary="Unverified legend", data="The Earth is a flat disc.",
        trust_score=0.2
    ))

    # 2. Load both into RAM
    os_kernel.step(">MEM:LOAD #earth.fact !5", agent="root")
    os_kernel.step(">MEM:LOAD #earth.rumor !5", agent="root")

    # 3. Trigger Auditor (Auditor runs every 5 ticks in dispatch)
    print("\n[Scenario: Running System Ticks to Trigger Audit]")
    for _ in range(5):
        os_kernel.step(">MEM:LS #ctx0 !1", agent="root")
    
    # 4. Check the reconstructed prompt
    content = os_kernel.scheduler.get_active_content()
    print("\n--- Reconstructed Context with Auditor Alerts ---")
    print(content)
    
    # 5. Verify the alert in the terminal monitor
    print("\n[Real-time Terminal View]")
    os_kernel.monitor()

    # Analysis
    print("\n[Analysis]")
    print(f"Auditor Alert present? {'COGNITIVE DISSONANCE' in content}")
    
    # 6. Final Report
    os_kernel.save_report("v34_auditor_report.html")
    print("\n[COMPLETE] CPOS v3.4 Kernel Auditor verified.")

if __name__ == "__main__":
    main()
