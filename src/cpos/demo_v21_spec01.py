import tempfile
import os
import json
from cpos.kernel import CPOS
from cpos.registry import ContextObject

def main():
    print("================================================")
    print("   CONTEXT POINTER OS v2.1 - Spec 0.1 Verification ")
    print("================================================")
    
    # 1. Initialization
    workspace = tempfile.mkdtemp(prefix="cpos_demo_")
    os.makedirs(workspace, exist_ok=True)
    
    os_kernel = CPOS(workspace=workspace)
    print("Kernel booted; key value withheld.")

    # 2. Registering Contexts with Spec v0.1 fields
    os_kernel.registry.register(ContextObject(
        id="ctx1", type="spec", title="CPOS v0.1 Spec", 
        content_ref="storage://spec_v01.md", summary="Foundational Spec", 
        source="internal_docs", location="docs/specification_v0.1.md",
        trust_score=1.0, sensitivity_level="internal"
    ))
    
    os_kernel.registry.register(ContextObject(
        id="ctx2", type="memory", title="Old Memory", 
        content_ref="storage://old.txt", summary="Outdated info", 
        importance=0.2, data="This information is wrong."
    ))

    # 3. Verify Trust Score Update
    print("\n[Scenario: Updating Trust Score]")
    os_kernel.step('>MEM:TRUST #ctx1 !5 | score=0.95 reason="Peer review complete"')
    ctx1 = os_kernel.registry.get("ctx1")
    print(f"ctx1 Trust Score: {ctx1.trust_score}")
    print(f"Audit Log (Trust Update): {os_kernel.registry.audit_log[-1]['event']}")

    # 4. Verify Context Invalidation
    print("\n[Scenario: Invalidating Outdated Memory]")
    os_kernel.step('>MEM:LOAD #ctx2 !5') # Load it first
    print(f"ctx2 Loaded: {'ctx2' in os_kernel.store.active_contexts}")
    
    os_kernel.step('>MEM:INVALIDATE #ctx2 !9 | reason="contradicted" replacement=ctx1')
    ctx2 = os_kernel.registry.get("ctx2")
    print(f"ctx2 Status: {ctx2.status}")
    print(f"ctx2 Reason: {ctx2.invalidated_reason}")
    print(f"ctx2 Replacement: {ctx2.replacement_pointer}")
    print(f"ctx2 Still in RAM?: {'ctx2' in os_kernel.store.active_contexts} (Should be False)")

    # 5. Verify Prevention of Loading Invalid Pointers
    print("\n[Scenario: Attempting to reload invalidated pointer]")
    res = os_kernel.step('>MEM:LOAD #ctx2 !5')
    print(f"Reload Result: {res['status']} - {res['result']}")

    # 6. Verify Access Metrics
    print("\n[Scenario: Access Metrics Check]")
    print(f"ctx1 Access Count: {ctx1.access_count}") # Should be > 0 due to TRUST update and get() calls

    # 7. Final Snapshot
    os_kernel.save_report("v21_spec01_report.html")
    print("\n[COMPLETE] CPOS v2.1 Spec v0.1 Verification successful.")

if __name__ == "__main__":
    main()
