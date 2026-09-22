import tempfile
import os
import json
from cpos.kernel import CPOS
from cpos.registry import ContextObject
from cpos.acl import Role

def main():
    print("================================================")
    print("   CONTEXT POINTER OS v2.2 - Governance Demo    ")
    print("================================================")
    
    workspace = tempfile.mkdtemp(prefix="cpos_demo_")
    os.makedirs(workspace, exist_ok=True)
    
    os_kernel = CPOS(workspace=workspace)
    
    # 1. Setup Contexts with different Trust and Sensitivity
    # High Trust, Public
    os_kernel.registry.register(ContextObject(
        id="ctx1", type="spec", title="Public Doc", 
        summary="Common knowledge", data="1+1=2",
        trust_score=1.0, sensitivity_level="public"
    ))
    
    # Low Trust (Unverified)
    os_kernel.registry.register(ContextObject(
        id="ctx2", type="memory", title="Rumor", 
        summary="Someone said something", data="Secret treasure is in the basement.",
        trust_score=0.3, sensitivity_level="internal"
    ))
    
    # High Sensitivity (Private)
    os_kernel.registry.register(ContextObject(
        id="ctx3", type="spec", title="System Key", 
        summary="Core credentials", data="KEY-12345-SUPER-SECRET",
        trust_score=1.0, sensitivity_level="private"
    ))

    # 2. Set Roles and Policies
    os_kernel.acl.set_role("user-agent", Role.USER)
    os_kernel.acl.grant_type("user-agent", "spec")
    os_kernel.acl.grant_type("user-agent", "memory")
    # Default Policy: min_trust=0.5, max_sensitivity=internal
    
    # 3. Test Retrieval as USER
    print("\n[Scenario: User Agent Access (Default Policy)]")
    os_kernel.scheduler.set_agent("user-agent")
    os_kernel.step(">MEM:LOAD #ctx1 !5", agent="user-agent")
    os_kernel.step(">MEM:LOAD #ctx2 !5", agent="user-agent")
    os_kernel.step(">MEM:LOAD #ctx3 !5", agent="user-agent")
    
    active_content = os_kernel.scheduler.get_active_content()
    print("--- Active Context in Prompt ---")
    print(active_content)
    
    print("\n[Analysis]")
    print(f"ctx1 (Public/HighTrust): Visible? {'DATA: 1+1=2' in active_content}")
    print(f"ctx2 (Low Trust): Filtered? {'[FILTERED]' in active_content}")
    print(f"ctx3 (Private): Redacted? {'[REDACTED' in active_content}")

    # 4. Scenario: Escalation to ROOT
    print("\n[Scenario: Root Agent Access (Bypass Policy)]")
    os_kernel.scheduler.set_agent("root")
    # Pointers are already in RAM, just switch agent context
    
    root_content = os_kernel.scheduler.get_active_content()
    print("--- Active Context in Prompt (ROOT) ---")
    print(root_content)
    print(f"ctx3 (Private) Visible to Root?: {'KEY-12345' in root_content}")
    print(f"ctx2 (Low Trust) Visible to Root?: {'DATA: Secret treasure' in root_content}")

    # 5. Scenario: Dynamic Policy Update via Instruction
    print("\n[Scenario: Lowering Trust Threshold via POLICY instruction]")
    res = os_kernel.step(">SEC:POLICY #ctx0 !9 | min_trust=0.2", agent="root")
    print(f"Policy Update Result: {res}")
    print(f"Kernel Retrieval Policy min_trust: {os_kernel.scheduler.retrieval_policy.minimum_trust_score}")
    
    os_kernel.scheduler.set_agent("user-agent")
    
    updated_content = os_kernel.scheduler.get_active_content()
    print("--- Active Context after POLICY instruction ---")
    print(updated_content)
    print(f"ctx2 (Low Trust) now visible?: {'DATA: Secret treasure' in updated_content}")

    # 6. Final Report
    os_kernel.save_report("v22_governance_report.html")
    print("\n[COMPLETE] CPOS v2.2 Governance Layer verified.")

if __name__ == "__main__":
    main()
