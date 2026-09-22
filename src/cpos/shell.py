import os
import sys
import argparse

if __package__ in (None, ""):
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from cpos.kernel import CPOS
    from cpos.registry import ContextObject
else:
    from .kernel import CPOS
    from .registry import ContextObject

class CognitiveShell:
    """[CPOS v3.0] The 'Interactive Kernel Interface'. 
    Supports real-time monitoring and advanced cognitive synthesis commands."""
    
    def __init__(self, kernel: CPOS):
        self.kernel = kernel
        self.current_agent = "root"
        self.current_pid = 0
        self.monitor_enabled = True

    def start(self):
        # ANSI Colors
        CYAN = "\033[96m"; GREEN = "\033[92m"; YELLOW = "\033[93m"; BOLD = "\033[1m"; RESET = "\033[0m"
        
        print("\n" + "="*60)
        print(f"{BOLD}{CYAN}   CONTEXT POINTER OS - INTERACTIVE SHELL v3.0{RESET}")
        print(f"{YELLOW}   Cognitive Synthesis / Dynamic Persona Support{RESET}")
        print("   Type 'exit' to quit, 'monitor' to toggle, 'help' for info.")
        print("="*60)
        
        while True:
            try:
                if self.monitor_enabled:
                    self.kernel.monitor()
                
                prompt = f"{BOLD}{GREEN}{self.current_agent}@cpos{RESET}:{BOLD}{CYAN}/# {RESET}"
                line = input(prompt).strip()
                
                if not line: continue
                if line.lower() in ["exit", "quit"]: break
                
                if line.lower() == "help":
                    self._print_help()
                    continue
                
                if line.lower() == "monitor":
                    self.monitor_enabled = not self.monitor_enabled
                    print(f"Monitor {'ENABLED' if self.monitor_enabled else 'DISABLED'}")
                    continue

                if line.startswith("su "):
                    parts = line.split(" ")
                    if len(parts) > 1:
                        self.current_agent = parts[1]
                        print(f"Logged in as {self.current_agent}")
                    continue

                # Execute EAP instruction
                res = self.kernel.step(line, agent=self.current_agent, pid=self.current_pid)
                
                if res["status"] == "ok":
                    if res.get("result"):
                        print(f"\n{BOLD}[KERNEL OUTPUT]{RESET}\n{res['result']}\n")
                    else:
                        print(f"\n{BOLD}[KERNEL OK]{RESET}\n")
                else:
                    print(f"\n{BOLD}\033[91m[KERNEL ERROR]{RESET} {res.get('result') or res.get('code')}\n")
                    
            except EOFError:
                print("\nInput closed.")
                break
            except KeyboardInterrupt:
                print("\nInterrupted.")
                break
            except Exception as e:
                print(f"\033[91mShell Error: {str(e)}\033[0m")

    def _print_help(self):
        print("\n" + "-"*40)
        print("Available Commands:")
        print("  >MEM:LOAD #ID !PRIO      - Load a context")
        print("  >MEM:QUERY #0 !5 | q=\"Q\" - Semantic search")
        print("  >PER:FUSE #ID !9 | with=ID - Merge personas")
        print("  >SEC:MODE !9 | mode=MODE - Switch mode")
        print("  monitor                  - Toggle real-time view")
        print("  su AGENT                 - Switch current user")
        print("  exit                     - Shut down kernel")
        print("-"*40 + "\n")

def main():
    parser = argparse.ArgumentParser(description="CPOS interactive shell")
    parser.add_argument("--workspace", default="/tmp/cpos_v30_interactive", help="Workspace directory")
    parser.add_argument("--node-id", default="local-brain", help="Kernel node ID")
    parser.add_argument("--domain", default="local", help="Kernel domain")
    parser.add_argument("--approval-policy-config", default=None, help="Approval policy JSON file or JSON string")
    args = parser.parse_args()

    workspace = args.workspace
    # A shell workspace may contain durable state selected by the user.
    # Creating the directory is safe; silently deleting its contents is not.
    os.makedirs(workspace, exist_ok=True)

    kernel = CPOS(
        workspace,
        node_id=args.node_id,
        domain=args.domain,
        approval_policy_config=args.approval_policy_config,
    )
    
    # Pre-register some fun personas for the user to play with
    kernel.registry.register(ContextObject(
        id="persona_coder", type="persona", title="Python Expert", summary="Coding bot", data="expert_coder"
    ))
    kernel.registry.register(ContextObject(
        id="persona_hacker", type="persona", title="Security Specialist", summary="Pen-tester bot", data="sec_hacker"
    ))
    
    shell = CognitiveShell(kernel)
    shell.start()

if __name__ == "__main__":
    main()
