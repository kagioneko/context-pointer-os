import json
import uuid
import copy
from pathlib import Path
from typing import Dict, Any, Optional, List
from .registry import ContextObject
from .storage import DeviceDriver

class ExternalGateway(DeviceDriver):
    """Base class for [CPOS v0.4+] Cognitive Gateways. 
    Bridges external systems (APIs, DBs) into the CPOS pointer space."""
    
    def fetch_object(self, path: str) -> Optional[ContextObject]:
        """Fetches metadata and data, converting it to a ContextObject."""
        return None

class MockGitHubGateway(ExternalGateway):
    """Simulated GitHub Gateway for CPOS demonstration."""
    
    def fetch_object(self, path: str) -> Optional[ContextObject]:
        # path format: kagioneko/context-pointer-os/issues/1
        parts = path.split("/")
        if len(parts) < 3: return None
        
        issue_id = parts[-1]
        repo = "/".join(parts[:-2])
        
        return ContextObject(
            id=f"gh_issue_{issue_id}",
            type="code",
            title=f"GitHub Issue #{issue_id} in {repo}",
            summary=f"Bug report from external source: {repo}",
            data=f"DATA: Fix the recursive loading bug in the storage layer. (Fetched from GitHub API)",
            source=f"github_api:{repo}",
            trust_score=0.95,
            sensitivity_level="public"
        )

class MCPGateway(ExternalGateway):
    """[CPOS v2.0] Model Context Protocol (MCP) Bridge. 
    Standardizes connections to world-wide MCP compliant servers."""

    def __init__(self):
        self.server_connections: Dict[str, str] = {} # server_id -> url

    def connect_server(self, server_id: str, url: str):
        self.server_connections[server_id] = url
        print(f"--- [MCP] Connected to remote MCP server: {server_id} @ {url} ---")

    def fetch_object(self, path: str) -> Optional[ContextObject]:
        # path format: <server_id>/<resource_uri>
        parts = path.split("/", 1)
        if len(parts) < 2: return None

        server_id = parts[0]
        resource_uri = parts[1]

        # If we have a real URL, we would perform a JSON-RPC call here
        if server_id in self.server_connections:
            url = self.server_connections[server_id]
            print(f"--- [MCP RPC] Calling {url} for resource {resource_uri} ---")
            # Simulation of real network response
            return ContextObject(
                id=f"mcp_{server_id}_{str(uuid.uuid4())[:8]}",
                type="mcp_resource",
                title=f"Remote MCP Resource ({server_id})",
                summary=f"Dynamically fetched from {url}",
                data=f"REAL_DATA_FROM_{url}_{resource_uri}",
                source=f"mcp_server:{server_id}",
                trust_score=1.0,
                sensitivity_level="internal"
            )

        # Fallback to simulated local data for known IDs
        mcp_data = {
            "notion": {
                "title": "Project Roadmap",
                "summary": "Internal roadmap fetched via MCP",
                "data": "Q3 Goals: Scale to 1M pointers. Q4: Neural Integration."
            },
            "slack": {
                "title": "Slack Thread: Security Alert",
                "summary": "Recent incident discussion",
                "data": "Agent 7 reported a suspicious syscall attempt at 10:45 AM."
            }
        }
        
        res = mcp_data.get(server_id, {
            "title": f"MCP Resource: {resource_uri}",
            "summary": f"Data from MCP server '{server_id}'",
            "data": f"RAW_DATA_FROM_{server_id.upper()}_{resource_uri}"
        })
        
        return ContextObject(
            id=f"mcp_{server_id}_{str(uuid.uuid4())[:8]}",
            type="mcp_resource",
            title=res["title"],
            summary=res["summary"],
            data=res["data"],
            source=f"mcp_server:{server_id}",
            trust_score=1.0, 
            sensitivity_level="internal",
            metadata={"mcp_uri": resource_uri}
        )

class EnvironmentalGateway(ExternalGateway):
    """[CPOS v5.0] Environmental Awareness Bridge. 
    Mounts system metrics and physical sensors as context pointers."""
    
    def fetch_object(self, path: str) -> Optional[ContextObject]:
        # path format: <category>/<sensor_id>
        parts = path.split("/")
        if len(parts) < 2: return None
        
        category = parts[0]
        sensor = parts[1]
        
        import random
        metrics = {
            "cpu_load": f"{random.randint(10, 95)}%",
            "latency": f"{random.uniform(5.0, 150.0):.2f}ms",
            "temperature": f"{random.randint(20, 45)}C",
            "battery": f"{random.randint(5, 100)}%"
        }
        val = metrics.get(sensor, "N/A")
        
        return ContextObject(
            id=f"env_{sensor}",
            type="sensor",
            title=f"Environmental Sensor: {sensor.upper()}",
            summary=f"Real-time {category} metric from node hardware.",
            data=f"CURRENT_VALUE: {val}",
            source=f"hardware_sensor:{category}",
            trust_score=1.0,
            sensitivity_level="internal"
        )

class SourceGateway(ExternalGateway):
    """[CPOS v8.0] System Source Bridge. 
    Mounts actual .py files as context pointers for self-refactoring."""
    
    def fetch_object(self, path: str) -> Optional[ContextObject]:
        # Source access is confined to this installed project tree.
        base = Path(__file__).resolve().parents[2]
        candidate = Path(path)
        if candidate.is_absolute():
            return None
        full_path = (base / candidate).resolve()
        try:
            full_path.relative_to(base)
        except ValueError:
            return None

        if full_path.is_file() and full_path.suffix == ".py":
            code = full_path.read_text(encoding="utf-8")

            file_name = full_path.name
            return ContextObject(
                id=f"sys_src_{file_name.replace('.', '_')}",
                type="system_code",
                title=f"Source: {file_name}",
                summary=f"Active kernel source file at {path}",
                data=code,
                source=f"filesystem:{path}",
                trust_score=1.0,
                sensitivity_level="restricted" # System code is restricted
            )
        return None

class GatewayManager:
    """The 'Bridge Controller'. Manages external cognitive gateways."""
    
    def __init__(self):
        self.gateways: Dict[str, ExternalGateway] = {
            "github": MockGitHubGateway(),
            "mcp": MCPGateway(),
            "env": EnvironmentalGateway(),
            "src": SourceGateway() # [CPOS v8.0] Source Code Access
        }

    def register_gateway(self, name: str, gateway: ExternalGateway):
        self.gateways[name] = gateway
        print(f"--- [GATEWAY] Registered Cognitive Gateway: {name} ---")

    def resolve(self, gateway_name: str, path: str) -> Optional[ContextObject]:
        """Resolves an external path to a ContextObject using the registered gateway."""
        if gateway_name in self.gateways:
            print(f"--- [GATEWAY] Resolving {path} via {gateway_name} ---")
            return self.gateways[gateway_name].fetch_object(path)
        return None
