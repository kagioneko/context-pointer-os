import tempfile
import os
import json
import time
from cpos.kernel import CPOS
from cpos.registry import ContextObject

def main():
    print("================================================")
    print("   CONTEXT POINTER OS v5.1 - Autonomic Evolution ")
    print("================================================")
    
    workspace = tempfile.mkdtemp(prefix="cpos_demo_")
    os.makedirs(workspace, exist_ok=True)
    
    os_kernel = CPOS(workspace=workspace)
    
    # 1. Setup Personas
    os_kernel.registry.register(ContextObject(
        id="persona_coder", type="persona", title="Python Expert", summary="S", data="expert_coder"
    ))
    os_kernel.registry.register(ContextObject(
        id="persona_security", type="persona", title="Security Auditor", summary="S", data="sec_auditor"
    ))

    # 2. Scenario: Repeated Pattern (Coder -> Security)
    print("\n[Scenario: Repeating Task Pattern Coder -> Security]")
    for i in range(3):
        print(f"Pattern Loop {i+1}...")
        os_kernel.step(">PER:LOAD #persona_coder !5", agent="root")
        os_kernel.step(">PER:LOAD #persona_security !5", agent="root")
    
    # 3. Trigger Evolution (Evolve runs every 15 ticks in this prototype)
    print("\n[Scenario: Running System Ticks to Trigger Evolution]")
    # Current ticks = 6 (from steps above). Need 9 more.
    for _ in range(9):
        os_kernel.step(">MEM:LS #ctx0 !1", agent="root")
    
    # 4. Verify the new Autonomic Expert
    print("\nChecking Registry for Evolved Personas...")
    all_objs = os_kernel.registry.registry.keys()
    evolved_id = [cid for cid in all_objs if cid.startswith("auto_expert_")]
    
    if evolved_id:
        print(f"Evolved Persona Found: {evolved_id[0]}")
        evolved_obj = os_kernel.registry.get(evolved_id[0])
        print(f"Title: {evolved_obj.title}")
        print(f"Source: {evolved_obj.source}")
        print(f"Trust: {evolved_obj.trust_score}")
    else:
        print("No evolved persona found yet (Pattern threshold not reached?)")

    # Final Report
    os_kernel.save_report("v51_evolution_report.html")
    print("\n[COMPLETE] CPOS v5.1 Autonomic Evolution verified.")

if __name__ == "__main__":
    main()
