import tempfile
import os
import json
import time
from cpos.kernel import CPOS
from cpos.registry import ContextObject

def main():
    print("================================================")
    print("   CONTEXT POINTER OS v3.0 - Cognitive Modes    ")
    print("================================================")
    
    workspace = tempfile.mkdtemp(prefix="cpos_demo_")
    os.makedirs(workspace, exist_ok=True)
    
    os_kernel = CPOS(workspace=workspace)
    
    # 1. Setup Contexts for Predictive and Autonomous modes
    # Spec and related Code (for Predictive)
    os_kernel.registry.register(ContextObject(
        id="ctx_spec_app", type="spec", title="App Spec", 
        summary="Spec summary", data="SPEC_DATA"
    ))
    os_kernel.registry.register(ContextObject(
        id="ctx_code_app", type="code", title="App Code", 
        summary="Code summary", data="CODE_DATA"
    ))
    
    # Stale context with source (for Autonomous)
    os_kernel.registry.register(ContextObject(
        id="ctx_stale", type="memory", title="Old Info", 
        summary="Stale summary", data="OLD_VALUE",
        status="stale", source="github_api:repo"
    ))

    # --- Scenario 1: NORMAL MODE ---
    print("\n[Scenario: Normal Mode (On-Demand)]")
    os_kernel.step(">SEC:MODE #ctx0 !9 | mode=normal", agent="root")
    os_kernel.step(">MEM:LOAD #ctx_spec_app !5", agent="root")
    
    active = os_kernel.store.active_contexts.keys()
    print(f"Active Contexts: {list(active)}")
    print(f"Predictive load occurred? {'ctx_code_app' in active}")

    # --- Scenario 2: PREDICTIVE MODE ---
    print("\n[Scenario: Predictive Mode (Prefetching)]")
    os_kernel.step(">SEC:MODE #ctx0 !9 | mode=predictive", agent="root")
    # Unload first
    os_kernel.step(">MEM:UNLOAD #ctx_spec_app !5", agent="root")
    os_kernel.step(">MEM:UNLOAD #ctx_code_app !5", agent="root")
    
    # Trigger load of spec
    os_kernel.step(">MEM:LOAD #ctx_spec_app !5", agent="root")
    
    active_pred = os_kernel.store.active_contexts.keys()
    print(f"Active Contexts (Predictive): {list(active_pred)}")
    print(f"Predictive load of related code occurred? {'ctx_code_app' in active_pred}")

    # --- Scenario 3: AUTONOMOUS MODE ---
    print("\n[Scenario: Autonomous Mode (Self-Healing)]")
    os_kernel.step(">SEC:MODE #ctx0 !9 | mode=autonomous", agent="root")
    
    print(f"Initial status of ctx_stale: {os_kernel.registry.get('ctx_stale').status}")
    
    # Trigger system ticks
    print("Action: Running system ticks...")
    os_kernel.step(">MEM:LS #ctx0 !1", agent="root")
    
    final_status = os_kernel.registry.get('ctx_stale').status
    print(f"Final status of ctx_stale: {final_status}")
    print(f"Self-healing successful? {final_status == 'active'}")

    # Final Report
    os_kernel.save_report("v30_modes_report.html")
    print("\n[COMPLETE] CPOS v3.0 Cognitive Modes verified.")

if __name__ == "__main__":
    main()
