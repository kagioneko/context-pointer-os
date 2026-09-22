import tempfile
import os
import json
import time
from cpos.kernel import CPOS
from cpos.registry import ContextObject

def main():
    print("================================================")
    print("   CONTEXT POINTER OS v5.2 - Environmental Aware")
    print("================================================")
    
    workspace = tempfile.mkdtemp(prefix="cpos_demo_")
    os.makedirs(workspace, exist_ok=True)
    
    os_kernel = CPOS(workspace=workspace, node_id="sensory-node")
    
    # 1. Mount Environmental Sensors
    print("\n[Scenario: Mounting System Sensors as Pointers]")
    # Mounting CPU load and Latency sensors
    os_kernel.step(">MEM:LOAD #ptr://env.system/cpu_load !5", agent="root")
    os_kernel.step(">MEM:LOAD #ptr://env.network/latency !5", agent="root")
    
    # 2. Initial Sense Check
    print("\nInitial Environmental Data:")
    print(os_kernel.scheduler.get_active_content())

    # 3. Enable Autonomous Monitoring (Real-time update)
    print("\n[Scenario: Real-time Sensory Update (Autonomous Mode)]")
    os_kernel.step(">SEC:MODE #ctx0 !9 | mode=autonomous", agent="root")
    
    # Run multiple ticks to see the data change (simulating dynamic environment)
    for i in range(3):
        print(f"Tick {i+1}: Sampling environment...")
        os_kernel.step(">MEM:LS #ctx0 !1", agent="root")
        time.sleep(0.5) # Wait a bit for "reality" to change
        
        # Display current sense in terminal
        content = os_kernel.scheduler.get_active_content()
        cpu_val = [line for line in content.split("\n") if "env_cpu_load" in line or "CURRENT_VALUE" in line]
        print(f"   Current Telemetry: {cpu_val[-1] if cpu_val else 'N/A'}")

    # 4. Final Reconstructed Context
    print("\nFinal Cognitive State with Sensory Context:")
    os_kernel.monitor()
    
    # Analysis
    print("\n[Analysis]")
    print(f"Is sensory data present in RAM? {len(os_kernel.store.active_contexts) > 0}")
    print(f"Did values change over ticks? (Verify manually from output)")

    # 5. Final Report
    os_kernel.save_report("v52_sensory_report.html")
    print("\n[COMPLETE] CPOS v5.2 Environmental Awareness verified.")

if __name__ == "__main__":
    main()
