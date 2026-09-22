import tempfile
import os
import json
from cpos.kernel import CPOS
from cpos.registry import ContextObject

def main():
    print("================================================")
    print("   CONTEXT POINTER OS v5.0 - Sentient Memory     ")
    print("================================================")
    
    workspace = tempfile.mkdtemp(prefix="cpos_demo_")
    os.makedirs(workspace, exist_ok=True)
    
    os_kernel = CPOS(workspace=workspace)
    
    # 1. Setup Contexts for Semantic Search
    os_kernel.registry.register(ContextObject(
        id="ctx_sec_report", type="security", title="Security Incident 042", 
        summary="A serious BCC injection attempt was blocked by the cognitive firewall.",
        data="Details: Attacker tried to inject 'bcc=admin' into metadata."
    ))
    os_kernel.registry.register(ContextObject(
        id="ctx_app_spec", type="spec", title="Application Specification", 
        summary="Architecture of the distributed agent system.",
        data="Architecture: Nodes A, B, C connected via NodeLink."
    ))
    os_kernel.registry.register(ContextObject(
        id="ctx_user_pref", type="memory", title="User Preferences", 
        summary="User prefers concise answers and dark mode UI.",
        data="Concise: true, Theme: dark"
    ))

    # 2. Setup Persona Pointers
    os_kernel.registry.register(ContextObject(
        id="persona_coder", type="persona", title="Expert Python Coder", 
        summary="Strict, efficient, and emphasizes type safety.",
        data="SYSTEM: You are an expert Python developer. Always use type hints."
    ))
    os_kernel.registry.register(ContextObject(
        id="persona_security", type="persona", title="Cybersecurity Auditor", 
        summary="Paranoid, analytical, focuses on potential vulnerabilities.",
        data="SYSTEM: You are a security auditor. Scan everything for injections."
    ))

    # --- Scenario 1: Semantic Query ---
    print("\n[Scenario: Semantic Search (Query by Meaning)]")
    # Search for something related to "vulnerabilities" or "attack"
    res_query = os_kernel.step('>SEC:QUERY #ctx0 !5 | q="security attack injection"', agent="root")
    print(f"Query Results for 'security attack injection':")
    print(res_query['result'])

    # Search for something related to "system design"
    res_query_2 = os_kernel.step('>MEM:QUERY #ctx0 !5 | q="architecture system design"', agent="root")
    print(f"\nQuery Results for 'architecture system design':")
    print(res_query_2['result'])

    # --- Scenario 2: Dynamic Persona Swapping ---
    print("\n[Scenario: Dynamic Persona Swapping]")

    # Load Coder Persona
    print("Switching to Coder Persona...")
    os_kernel.step(">PER:LOAD #persona_coder !9", agent="root")
    # Also load some context piece
    os_kernel.step(">MEM:LOAD #ctx_app_spec !5", agent="root")
    print(os_kernel.scheduler.get_active_content()[:200] + "...")

    # Load Security Persona
    print("\nSwitching to Security Persona...")
    os_kernel.step(">PER:LOAD #persona_security !9", agent="root")
    # Load security report
    os_kernel.step(">MEM:LOAD #ctx_sec_report !5", agent="root")
    print(os_kernel.scheduler.get_active_content()[:200] + "...")

    # --- Scenario 3: Real-time Monitor (v2.0) ---
    print("\n[Scenario: Sentient Monitor]")
    os_kernel.monitor()

    # --- Scenario 4: Real-world MCP Connectivity ---
    print("\n[Scenario: Connecting to a real MCP Server]")
    # Register a "real" server URL
    os_kernel.step(">SEC:CONNECT #ctx0 !9 | mcp=external_wiki url=https://wiki.example.com/mcp", agent="root")
    
    # Load from the newly registered server
    os_kernel.step(">MEM:LOAD #ptr://mcp.external_wiki/articles/sentience !5", agent="root")
    
    print("\nFinal Reconstructed Content:")
    print(os_kernel.scheduler.get_active_content())

    # Final Report
    os_kernel.save_report("v50_sentient_report.html")
    print("\n[COMPLETE] CPOS v5.0 Sentient Memory verified.")

if __name__ == "__main__":
    main()
