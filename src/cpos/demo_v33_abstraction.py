import tempfile
import os
import json
from cpos.kernel import CPOS
from cpos.registry import ContextObject

def main():
    print("================================================")
    print("   CONTEXT POINTER OS v3.3 - Concept Abstraction ")
    print("================================================")
    
    workspace = tempfile.mkdtemp(prefix="cpos_demo_")
    os.makedirs(workspace, exist_ok=True)
    
    os_kernel = CPOS(workspace=workspace)
    
    # 1. Setup multiple granular contexts
    print("\n[Scenario: Distributing Granular Knowledge]")
    os_kernel.registry.register(ContextObject(
        id="ctx_part1", type="memory", title="Subsystem A", 
        summary="Sensor module details", data="Sensor A uses I2C at 400kHz.",
        trust_score=1.0
    ))
    os_kernel.registry.register(ContextObject(
        id="ctx_part2", type="memory", title="Subsystem B", 
        summary="Actuator module details", data="Actuator B requires 12V DC.",
        trust_score=0.8
    ))
    os_kernel.registry.register(ContextObject(
        id="ctx_part3", type="memory", title="Subsystem C", 
        summary="Power module details", data="Battery C capacity is 5000mAh.",
        trust_score=0.9
    ))

    # 2. Execute Abstraction (SYNTH)
    print("\n[Scenario: Synthesizing High-Level Concept]")
    # Synthesize parts 1, 2, and 3 into a "System Overview"
    os_kernel.step('>MEM:SYNTH #ctx_system_overview !9 | from="ctx_part1,ctx_part2,ctx_part3"', agent="root")
    
    # 3. Verify the abstraction
    print("\nVerifying Abstracted Concept...")
    os_kernel.monitor()
    
    concept = os_kernel.registry.get("ctx_system_overview")
    print("--- Abstracted Concept Content ---")
    print(concept.data)
    print(f"Aggregated Trust Score: {concept.trust_score:.2f}")

    # 4. Final Reconstructed Prompt
    # In a real scenario, the agent would now unload the granular parts and just use the concept
    os_kernel.step(">MEM:UNLOAD #ctx_part1 !5", agent="root")
    os_kernel.step(">MEM:UNLOAD #ctx_part2 !5", agent="root")
    os_kernel.step(">MEM:UNLOAD #ctx_part3 !5", agent="root")
    
    print("\nFinal Reconstructed Context (Compressed):")
    print(os_kernel.scheduler.get_active_content())

    # Final Report
    os_kernel.save_report("v33_abstraction_report.html")
    print("\n[COMPLETE] CPOS v3.3 Concept Abstraction verified.")

if __name__ == "__main__":
    main()
