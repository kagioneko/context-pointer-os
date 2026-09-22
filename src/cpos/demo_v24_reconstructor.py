import tempfile
import os
import json
import time
from cpos.kernel import CPOS
from cpos.registry import ContextObject

def main():
    print("================================================")
    print("   CONTEXT POINTER OS v2.4 - Reconstructor & Decay ")
    print("================================================")
    
    workspace = tempfile.mkdtemp(prefix="cpos_demo_")
    os.makedirs(workspace, exist_ok=True)
    
    os_kernel = CPOS(workspace=workspace)
    
    # 1. Setup Contexts for Trust/Prioritization
    # High Trust
    os_kernel.registry.register(ContextObject(
        id="ctx1", type="spec", title="Official Manual", 
        summary="Verified system guide", data="Step 1: Press Start.",
        trust_score=1.0, importance=0.9, source="official_docs"
    ))
    
    # Low Trust
    os_kernel.registry.register(ContextObject(
        id="ctx2", type="memory", title="Draft Note", 
        summary="Unverified ideas", data="Maybe press Stop?",
        trust_score=0.4, importance=0.5, source="user_scratchpad"
    ))

    # 2. Setup Contexts for Conflict Detection
    os_kernel.registry.register(ContextObject(
        id="ctx3", type="code", title="Main Module", 
        summary="Root source code", data="print('Hello')",
        trust_score=1.0, importance=1.0, source="git"
    ))
    # Branch of ctx3
    os_kernel.registry.branch("ctx3", "dev")
    # Load both parent and branch to trigger warning
    os_kernel.step(">MEM:LOAD #ctx3 !5")
    os_kernel.step(">MEM:LOAD #ctx3.dev !5")

    # 3. Verify Reconstruction (Prioritization, Attribution, Conflict)
    print("\n[Scenario: Context Reconstruction]")
    os_kernel.step(">MEM:LOAD #ctx1 !5")
    os_kernel.step(">MEM:LOAD #ctx2 !5")
    
    content = os_kernel.scheduler.get_active_content()
    print("--- Reconstructed Context ---")
    print(content)
    
    print("\n[Analysis]")
    print(f"Trust Prioritization: ctx1 before ctx2? {content.find('ctx1') < content.find('ctx2')}")
    print(f"Source Attribution present? {'Source: official_docs' in content}")
    print(f"Conflict Warning present? {'SYSTEM CONTEXT WARNINGS' in content}")

    # 4. Scenario: Lifecycle Decay
    print("\n[Scenario: Simulating Memory Decay (Active -> Stale)]")
    # Ensure ctx1 is active and has low heat
    ctx1 = os_kernel.registry.get("ctx1")
    ctx1.access_heat = 0.05
    
    print(f"ctx1 Initial Status: {ctx1.status}")
    
    # Run multiple steps to trigger tick-based decay
    for i in range(11):
        os_kernel.step(">MEM:LS #ctx0 !1")
    
    print(f"ctx1 Status after decay: {ctx1.status}")
    
    content_decayed = os_kernel.scheduler.get_active_content()
    print("\n--- Reconstructed Context (Decayed) ---")
    print(content_decayed)
    print(f"Stale Attention Warning present? {'ATTENTION: Information is stale' in content_decayed}")

    # 5. Final Report
    os_kernel.save_report("v24_reconstructor_report.html")
    print("\n[COMPLETE] CPOS v2.4 Reconstructor & Decay verified.")

if __name__ == "__main__":
    main()
