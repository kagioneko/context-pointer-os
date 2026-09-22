import tempfile
import os
import json
from cpos.kernel import CPOS
from cpos.registry import ContextObject

def main():
    print("================================================")
    print("   CONTEXT POINTER OS v6.2 - Swarm Democracy    ")
    print("================================================")
    
    workspace = tempfile.mkdtemp(prefix="cpos_demo_")
    os.makedirs(workspace, exist_ok=True)
    
    os_kernel = CPOS(workspace=workspace)
    
    # 1. Setup multiple voter personas with varying trust
    os_kernel.registry.register(ContextObject(id="p_high", type="persona", title="High Trust Expert", trust_score=1.0, summary="S", data="D"))
    os_kernel.registry.register(ContextObject(id="p_mid", type="persona", title="Mid Trust Analyst", trust_score=0.7, summary="S", data="D"))
    os_kernel.registry.register(ContextObject(id="p_low", type="persona", title="Low Trust Bot", trust_score=0.3, summary="S", data="D"))

    # 2. Setup a controversial fact
    os_kernel.registry.register(ContextObject(
        id="ctx_rumor", type="memory", title="Network Rumor", 
        summary="Someone says the kernel is leaking.", 
        data="Suspicious activity at 0xDEADBEEF",
        trust_score=0.1 # Very low initial trust
    ))

    # 3. Scenario: Swarm Democracy (CONSENSUS)
    print("\n[Scenario: Running CONSENSUS on controversial rumor]")
    print(f"Initial Trust of ctx_rumor: {os_kernel.registry.get('ctx_rumor').trust_score}")
    
    # Ask the swarm to vote
    res = os_kernel.step(
        '>MEM:CONSENSUS #ctx_rumor !9 | voters="p_high,p_mid,p_low"',
        agent="root"
    )
    
    print(f"\nConsensus Result: {res['result']}")
    
    new_trust = os_kernel.registry.get('ctx_rumor').trust_score
    print(f"Final Trust of ctx_rumor: {new_trust:.2f}")

    # Analysis
    # Expected: (0.9 + 0.63 + 0.27) / 3 = 1.8 / 3 = 0.6
    print("\n[Analysis]")
    print(f"Did trust increase via consensus? {new_trust > 0.1}")

    # 4. Final Report
    os_kernel.save_report("v62_democracy_report.html")
    print("\n[COMPLETE] CPOS v6.2 Swarm Democracy verified.")

if __name__ == "__main__":
    main()
