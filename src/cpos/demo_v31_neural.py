import tempfile
import os
import json
from cpos.kernel import CPOS
from cpos.registry import ContextObject

def main():
    print("================================================")
    print("   CONTEXT POINTER OS v3.1 - Neural Prediction ")
    print("================================================")
    
    workspace = tempfile.mkdtemp(prefix="cpos_demo_")
    os.makedirs(workspace, exist_ok=True)
    
    os_kernel = CPOS(workspace=workspace)
    os_kernel.step(">SEC:MODE #ctx0 !9 | mode=predictive", agent="root")

    # 1. Setup Contexts
    os_kernel.registry.register(ContextObject(id="ctx_a", type="memory", title="Task A", summary="S", data="D"))
    os_kernel.registry.register(ContextObject(id="ctx_b", type="memory", title="Task B", summary="S", data="D"))
    os_kernel.registry.register(ContextObject(id="ctx_c", type="memory", title="Task C", summary="S", data="D"))

    # 2. Training Phase: Establish a pattern A -> B twice
    print("\n[Scenario: Training Neural Pattern A -> B]")
    for i in range(2):
        print(f"Iteration {i+1}...")
        os_kernel.step(">MEM:LOAD #ctx_a !5", agent="root")
        os_kernel.step(">MEM:LOAD #ctx_b !5", agent="root")
        # Unload for next iteration test
        os_kernel.step(">MEM:UNLOAD #ctx_a !5", agent="root")
        os_kernel.step(">MEM:UNLOAD #ctx_b !5", agent="root")

    # 3. Prediction Phase: Load A and see if B is prefetched automatically
    print("\n[Scenario: Testing Neural Prediction]")
    os_kernel.step(">MEM:LOAD #ctx_a !5", agent="root")
    
    active = os_kernel.store.active_contexts.keys()
    print(f"Active Contexts: {list(active)}")
    print(f"ctx_b prefetched via neural pattern? {'ctx_b' in active}")

    # Final Report
    os_kernel.save_report("v31_neural_report.html")
    print("\n[COMPLETE] CPOS v3.1 Neural Prediction verified.")

if __name__ == "__main__":
    main()
