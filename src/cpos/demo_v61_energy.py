import tempfile
import os
import json
from cpos.kernel import CPOS
from cpos.registry import ContextObject

def main():
    print("================================================")
    print("   CONTEXT POINTER OS v6.1 - Energy Management  ")
    print("================================================")
    
    workspace = tempfile.mkdtemp(prefix="cpos_demo_")
    os.makedirs(workspace, exist_ok=True)
    
    # Initialize with a tight budget
    os_kernel = CPOS(workspace=workspace, token_limit=5000)
    os_kernel.scheduler.retrieval_policy.cognitive_budget = 150.0 
    os_kernel.scheduler.retrieval_policy.low_budget_threshold = 50.0
    
    print(f"Initial Budget: {os_kernel.scheduler.retrieval_policy.cognitive_budget} units")

    # 1. Register contexts
    os_kernel.registry.register(ContextObject(id="ctx_1", type="memory", title="Fact 1", summary="S", data="D"))
    os_kernel.registry.register(ContextObject(id="ctx_2", type="memory", title="Fact 2", summary="S", data="D"))

    # 2. Run operations and watch budget drain
    print("\n[Scenario: Draining Budget with Operations]")
    
    # Load (Cost: 10)
    os_kernel.step(">MEM:LOAD #ctx_1 !5", agent="root")
    print(f"Budget after LOAD: {os_kernel.scheduler.retrieval_policy.cognitive_budget}")

    # Query (Cost: 50)
    os_kernel.step('>MEM:QUERY #0 !5 | q="test"', agent="root")
    print(f"Budget after QUERY: {os_kernel.scheduler.retrieval_policy.cognitive_budget}")

    # Swarm (Cost: 100) - This should trigger 'low budget' cost increase or fail
    print("\nAttempting high-cost SWARM operation...")
    res = os_kernel.step('>MEM:SWARM #ctx0 !9 | nodes="ctx_1,ctx_2" task="Deep analysis"', agent="root")
    
    if res["status"] == "error":
        print(f"Operation Blocked: {res['result']}")
    else:
        print(f"Operation Success. Remaining Budget: {os_kernel.scheduler.retrieval_policy.cognitive_budget}")

    # 3. Final Report
    os_kernel.save_report("v61_energy_report.html")
    print("\n[COMPLETE] CPOS v6.1 Energy Management verified.")

if __name__ == "__main__":
    main()
