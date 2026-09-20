import os
import time
from cpos.kernel import CPOS
from cpos.registry import ContextObject
from cpos.acl import Role

def v11_demo():
    print("================================================")
    print("   CONTEXT POINTER OS v1.1 - MULTI-TASKING      ")
    print("================================================")
    
    workspace = "/tmp/cpos_v11"
    os.makedirs(workspace, exist_ok=True)
    os_kernel = CPOS(workspace=workspace)

    # 1. Process Isolation
    print("\n[V1.1: Process Isolation Test]")
    os_kernel.registry.register(ContextObject(
        id="ctx10", type="private", title="Agent 1 Secrets", 
        content_ref="", summary="Hidden", tokens_estimate=10, 
        data="AGENT1_SUPER_SECRET", owner_pid=1
    ))
    # Root grants permission to Agent 1 for its own memory
    os_kernel.acl.grant("agent1", "ctx10")
    os_kernel.step(">MEM:LOAD #ctx10 !9", agent="agent1", pid=1)
    
    print("Agent 2 (PID 2) looking at active RAM...")
    os_kernel.scheduler.set_agent("agent2", pid=2)
    view = os_kernel.scheduler.get_active_content()
    if "AGENT1_SUPER_SECRET" not in view:
        print("Success: Agent 2 isolated from Agent 1.")
    else:
        print("Failure: Isolation breach!")

    # 2. Mutex Test
    print("\n[V1.1: Mutex Lock Test]")
    os_kernel.registry.register(ContextObject(
        id="ctx50", type="shared", title="Shared Doc", 
        content_ref="", summary="Edit me", tokens_estimate=10, data="UNTOUCHED"
    ))
    # Grant permission to BOTH agents
    os_kernel.acl.grant_type("agent1", "shared")
    os_kernel.acl.grant_type("agent2", "shared")
    
    print("Agent 1 locking #ctx50...")
    os_kernel.step(">MEM:LOCK #ctx50 !9", agent="agent1", pid=1)
    
    print("Agent 2 trying to write to locked #ctx50...")
    res = os_kernel.step(">MEM:UPDATE #ctx50 !9 | data=HACKED", agent="agent2", pid=2)
    print(f"Agent 2 Result: {res['status']} ({res.get('result')})")
    
    os_kernel.step(">MEM:UNLOCK #ctx50 !9", agent="agent1", pid=1)
    print("Agent 1 unlocked. Agent 2 trying again...")
    os_kernel.step(">MEM:UPDATE #ctx50 !9 | data=COLLABORATION", agent="agent2", pid=2)
    print(f"Final Content: {os_kernel.registry.get('ctx50').data}")

    # 3. Git Driver Test
    print("\n[V1.1: Git Driver Test]")
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print(f"Mounting CPOS repo at: {base_path}")
    os_kernel.step(f">MEM:DEV #ctx0 !9 | mount=repo path={base_path}")
    
    os_kernel.registry.register(ContextObject(
        id="ctx_git", type="git", title="Live Commit Log", 
        content_ref="repo://log", summary="Real git output", tokens_estimate=500
    ))
    
    print("Loading real git log via CPOS driver...")
    os_kernel.step(">MEM:LOAD #ctx_git !5")
    git_obj = os_kernel.registry.get("ctx_git")
    if git_obj and git_obj.data and "GIT_ERR" not in git_obj.data:
        print(f"Git Log Loaded. First commit:\n{git_obj.data.splitlines()[0]}")
    else:
        print(f"Failed to fetch git data. Error: {git_obj.data if git_obj else 'None'}")

    # 4. Decay
    print("\n[V1.1: Real-time Heat Decay Test]")
    os_kernel.step(">MEM:LOAD #ctx50 !5")
    h1 = os_kernel.registry.get("ctx50").access_heat
    print(f"Initial Heat: {h1:.2f}")
    print("Waiting 1.1 seconds...")
    time.sleep(1.2)
    os_kernel.step(">MEM:PS #ctx0 !1")
    h2 = os_kernel.registry.get("ctx50").access_heat
    print(f"Heat after wait: {h2:.2f}")

    os_kernel.save_report("v11_multitask_report.html")
    print("\n[COMPLETE] v1.1 Demo Finished.")

if __name__ == "__main__":
    v11_demo()
