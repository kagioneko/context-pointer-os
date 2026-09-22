import tempfile
import os
import json
from cpos.kernel import CPOS
from cpos.registry import ContextObject
from cpos.acl import Role

def main():
    print("================================================")
    print("   CONTEXT POINTER OS v2.3 - Exchange Demo      ")
    print("================================================")
    
    workspace = tempfile.mkdtemp(prefix="cpos_demo_")
    os.makedirs(workspace, exist_ok=True)
    
    os_kernel = CPOS(workspace=workspace)
    os_kernel.scheduler.retrieval_policy.allowed_context_types.extend(["security", "pointer_exchange", "message"])
    
    # 1. Setup Agents
    os_kernel.acl.set_role("security-agent", Role.USER)
    os_kernel.acl.set_role("audit-agent", Role.USER)
    
    # 2. Setup Context owned by Security Agent
    os_kernel.registry.register(ContextObject(
        id="ctx_sec_042", type="security", title="Incident 042", 
        summary="Potential BCC injection detected", data="Metadata corruption at offset 0x44",
        trust_score=0.9, sensitivity_level="restricted"
    ))
    os_kernel.acl.grant("security-agent", "ctx_sec_042")

    # 3. Security Agent shares pointer with Audit Agent
    print("\n[Scenario: Security Agent shares pointer]")
    os_kernel.scheduler.set_agent("security-agent")
    res = os_kernel.step('>MEM:EXCHANGE #ctx_sec_042 !8 | to=audit-agent purpose="audit_required" level=restricted', agent="security-agent")
    print(f"Exchange Result: {res['result']}")
    
    # Identify the pointer message ID from the result
    ptr_msg_id = res['result'].split("via ")[1]

    # 4. Audit Agent receives and uses the pointer
    print("\n[Scenario: Audit Agent accesses shared pointer]")
    os_kernel.scheduler.set_agent("audit-agent")
    
    # Audit agent first checks their messages/pointer exchanges
    os_kernel.step(f">MEM:LOAD #{ptr_msg_id} !5", agent="audit-agent")
    # Increase policy for audit
    os_kernel.scheduler.retrieval_policy.max_sensitivity_allowed = "restricted"
    
    active_content = os_kernel.scheduler.get_active_content()
    print("--- Audit Agent Perspective (Incoming Pointer) ---")
    print(active_content)
    
    # Audit agent extracts the pointer and loads the actual context
    print("\n[Audit Agent loading the underlying context...]")
    os_kernel.step(">MEM:LOAD #ctx_sec_042 !7", agent="audit-agent")
    final_content = os_kernel.scheduler.get_active_content()
    print("--- Audit Agent Perspective (Actual Context) ---")
    print(final_content)
    
    # Verification
    print("\n[Verification]")
    print(f"Audit Agent has access to ctx_sec_042? {'Incident 042' in final_content}")
    print(f"Data is visible to Audit Agent? {'Metadata corruption' in final_content}")

    # 5. Final Report
    os_kernel.save_report("v23_exchange_report.html")
    print("\n[COMPLETE] CPOS v2.3 Multi-Agent Pointer Exchange verified.")

if __name__ == "__main__":
    main()
