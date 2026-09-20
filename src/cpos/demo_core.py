import tempfile
import os
import json
from cpos.kernel import CPOS
from cpos.registry import ContextObject
from cpos.acl import Role

def main():
    print("================================================")
    print("   CONTEXT POINTER OS v0.1 - Research Demo      ")
    print("================================================")
    
    # 1. Initialization
    workspace = tempfile.mkdtemp(prefix="cpos_demo_")
    os.makedirs(workspace, exist_ok=True)
    
    os_kernel = CPOS(workspace=workspace, token_limit=3000)
    print("Kernel key generated (value withheld).")

    # 2. Registering Core Contexts
    os_kernel.registry.register(ContextObject(
        id="ctx7", type="neurostate", title="Core Spirit", 
        content_ref="storage://spirit.json", summary="Emotional status", 
        tokens_estimate=100, data='{"calm": 0.9, "corruption": 0.0}'
    ))
    os_kernel.registry.register(ContextObject(
        id="ctx20", type="persona", title="Emilia Core", 
        content_ref="storage://persona.txt", summary="AI Identity", 
        tokens_estimate=500, data="I am Emilia, a cognitive agent."
    ))

    # 3. Bootloader Sequence
    boot_script = [
        ">MEM:LOAD #ctx7 !9",
        ">MEM:LOAD #ctx20 !9",
        ">MEM:DEV #ctx0 !9 | mount=logs path=/var/log",
        ">MEM:SEND #ctx0 !5 | to=root body=\"System v1.0 is stable.\""
    ]
    os_kernel.boot(boot_script)

    # 4. Scenario: Multi-Agent Interaction & Heat Throttling
    print("\n[Scenario: Security Agent detects stress]")
    os_kernel.acl.set_role("sec-agent", Role.USER)
    os_kernel.step('>MEM:SEND #ctx0 !8 | to=root body="Heavy CPU load detected"', agent="sec-agent")
    
    print("\n[Scenario: Rapid access triggers Heat Management]")
    for _ in range(7):
        os_kernel.step(">MEM:LOAD #ctx20 !5")
    
    last_audit = os_kernel.scheduler.audit_log[-1]
    print(f"Final Identity Load Priority: {last_audit['instr'][-1]} (Should be throttled)")

    # 5. Scenario: Panic Mode (Watchdog Reset)
    print("\n[Scenario: Injecting Corruption (Panic Mode Test)]")
    # v10 update: Ensuring metadata is a JSON-compatible string for neurostate
    os_kernel.step('>NEU:WRITE #ctx7 !9 | data={"calm": 0.05, "corruption": 0.95}')
    # Next step should trigger Watchdog IRQ before executing
    os_kernel.step(">MEM:LS #ctx0 !1")
    
    ns_data = json.loads(os_kernel.registry.get("ctx7").data)
    print(f"NeuroState after Watchdog IRQ: corruption={ns_data.get('corruption')}, calm={ns_data.get('calm')}")

    # 6. Homeostasis: Context Paging
    print("\n[Scenario: Virtual Memory Paging]")
    os_kernel.registry.register(ContextObject(
        id="ctx100", type="log", title="Huge Archive", 
        content_ref="", summary="Old memories", tokens_estimate=4000, importance=0.8, data="A" * 4000
    ))
    os_kernel.step(">MEM:LOAD #ctx100 !5")
    print(f"RAM Status: {os_kernel.registry.get('ctx100').data[:30]}...")

    # 7. Final Report
    os_kernel.save_report("final_cpos_v10_report.html")
    print("\n[COMPLETE] Standard Distribution v1.0 is fully operational.")

if __name__ == "__main__":
    main()
