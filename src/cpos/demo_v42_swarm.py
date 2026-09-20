import tempfile
import os
import json
from cpos.kernel import CPOS
from cpos.registry import ContextObject

def main():
    print("================================================")
    print("   CONTEXT POINTER OS v4.2 - Swarm Dispatch      ")
    print("================================================")
    
    workspace = tempfile.mkdtemp(prefix="cpos_demo_")
    os.makedirs(workspace, exist_ok=True)
    
    os_kernel = CPOS(workspace=workspace)
    
    # 1. Setup Specialized Personas for the Swarm
    os_kernel.registry.register(ContextObject(
        id="persona_coder", type="persona", title="Python Expert", summary="S", data="D"
    ))
    os_kernel.registry.register(ContextObject(
        id="persona_security", type="persona", title="Security Auditor", summary="S", data="D"
    ))
    os_kernel.registry.register(ContextObject(
        id="persona_ux", type="persona", title="UX Designer", summary="S", data="D"
    ))

    # 2. Execute Swarm Task (SWARM)
    print("\n[Scenario: Collective Intelligence Analysis]")
    # Command the swarm to analyze a complex request
    res = os_kernel.step(
        '>MEM:SWARM #ctx0 !9 | nodes="persona_coder,persona_security,persona_ux" task="Optimize the cognitive kernel for multi-node latency"',
        agent="root"
    )
    
    print("\n--- Swarm Collective Intelligence Output ---")
    print(res['result'])

    # 3. Verify in Monitor
    print("\n[Monitor View]")
    os_kernel.monitor()

    # 4. Final Report
    os_kernel.save_report("v42_swarm_report.html")
    print("\n[COMPLETE] CPOS v4.2 Swarm Task Dispatch verified.")

if __name__ == "__main__":
    main()
