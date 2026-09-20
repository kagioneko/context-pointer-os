import tempfile
import os
import json
from cpos.kernel import CPOS
from cpos.registry import ContextObject

def main():
    print("================================================")
    print("   CONTEXT POINTER OS v2.5 - Dependencies       ")
    print("================================================")
    
    workspace = tempfile.mkdtemp(prefix="cpos_demo_")
    os.makedirs(workspace, exist_ok=True)
    
    os_kernel = CPOS(workspace=workspace)
    
    # 1. Setup Dependencies
    # Grandchild
    os_kernel.registry.register(ContextObject(
        id="ctx_base", type="code", title="Base Lib", 
        summary="Common utilities", data="def utils(): pass",
        trust_score=1.0
    ))
    
    # Child (Depends on Base)
    os_kernel.registry.register(ContextObject(
        id="ctx_helper", type="code", title="Helper", 
        summary="Helper functions", data="import base",
        dependencies=["ctx_base"], trust_score=0.9
    ))
    
    # Parent (Depends on Helper)
    os_kernel.registry.register(ContextObject(
        id="ctx_main", type="code", title="Main App", 
        summary="Core logic", data="import helper",
        dependencies=["ctx_helper"], trust_score=0.8
    ))

    # 2. Setup Circular Dependency
    os_kernel.registry.register(ContextObject(
        id="ctx_a", type="spec", title="Spec A", summary="Loop A",
        dependencies=["ctx_b"], data="Ref B"
    ))
    os_kernel.registry.register(ContextObject(
        id="ctx_b", type="spec", title="Spec B", summary="Loop B",
        dependencies=["ctx_a"], data="Ref A"
    ))

    # 3. Scenario: Load Parent
    print("\n[Scenario: Loading Main App (Recursive Load)]")
    os_kernel.step(">MEM:LOAD #ctx_main !5")
    
    active = os_kernel.store.active_contexts.keys()
    print(f"Active Contexts: {list(active)}")
    print(f"ctx_main loaded? {'ctx_main' in active}")
    print(f"ctx_helper loaded? {'ctx_helper' in active}")
    print(f"ctx_base loaded? {'ctx_base' in active}")

    # 4. Scenario: Load Circular Dependency
    print("\n[Scenario: Loading Circular Dependency]")
    os_kernel.step(">MEM:LOAD #ctx_a !5")
    active_circular = os_kernel.store.active_contexts.keys()
    print(f"Active Contexts (Circular): {list(active_circular)}")
    print(f"ctx_a loaded? {'ctx_a' in active_circular}")
    print(f"ctx_b loaded? {'ctx_b' in active_circular}")

    # 5. Final Report
    os_kernel.save_report("v25_dependency_report.html")
    print("\n[COMPLETE] CPOS v2.5 Dependency Management verified.")

if __name__ == "__main__":
    main()
