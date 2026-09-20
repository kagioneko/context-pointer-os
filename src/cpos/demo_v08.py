import json
from cpos.registry import ContextRegistry, ContextObject
from cpos.context_store import ContextStore
from cpos.scheduler import Scheduler
from cpos.acl import AccessControlList, Role

def v08_demo():
    print("--- Context Pointer OS Kernel v0.8: Cognitive Resources & Hardening ---")
    
    # 1. Setup
    registry = ContextRegistry()
    registry.register(ContextObject(id="ctx4", type="log", title="Critical Log", content_ref="", summary="Hot Log", tokens_estimate=100))
    
    # Generate Kernel Key
    key = registry.generate_kernel_key()
    print("Kernel key generated (value withheld).")
    
    store = ContextStore(registry)
    scheduler = Scheduler(store)

    # 2. Test Kernel Key Enforcement
    print("\n[V0.8: Hardening - Unauthorized Registry Write]")
    # Forget ctx0 (Registry itself) without key
    res_fail = scheduler.dispatch(">MEM:FORGET #ctx0 !9")
    print(f"Result (No Key): {res_fail['status']} ({res_fail.get('result')})")

    print("\n[V0.8: Hardening - Authorized Registry Write]")
    res_ok = scheduler.dispatch(f">MEM:FORGET #ctx0 !9 | key={key}")
    print(f"Result (With Key): {res_ok['status']} ({res_ok.get('result')})")

    # 3. Test Access Heat (Cognitive Resources)
    print("\n[V0.8: Cognitive Resources - Context Overheating]")
    # Load ctx4 multiple times
    for i in range(7):
        scheduler.dispatch(">MEM:LOAD #ctx4 !5")
    
    obj = registry.get("ctx4")
    print(f"ctx4 Heat Level: {obj.access_heat}")
    
    # Check audit log for throttle (The last load should have been throttled)
    last_load = [a for a in scheduler.audit_log if a['target'] == 'ctx4'][-1]
    print(f"Last Load Priority: {last_load['instr'][-1]} (Original was 5, should be 2 if throttled)")
    
    # 4. Cooling down
    print("\n[V0.8: Cognitive Resources - Cooling Down]")
    scheduler.dispatch(">MEM:SUM #ctx4 !5")
    print(f"ctx4 Heat Level after SUM: {registry.get('ctx4').access_heat}")

if __name__ == "__main__":
    v08_demo()
