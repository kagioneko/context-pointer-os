import json
import uuid
import copy
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable, Tuple
from .registry import ContextObject
from .storage import DeviceDriver
from .cognitive_events import (
    SENSOR_EVENT_SCHEMA,
    build_sensor_event,
    task_tape_sink,
)

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
        # path format: src/cpos/scheduler.py
        import os
        base = "/home/mayutama/context-pointer-os"
        full_path = os.path.join(base, path)
        
        if os.path.exists(full_path) and full_path.endswith(".py"):
            with open(full_path, "r") as f:
                code = f.read()
            
            file_name = os.path.basename(path)
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

class GitSensorPolicyError(Exception):
    """Raised when a Git sensor call violates the read-only command allowlist."""

class GitGateway(ExternalGateway):
    """[CPOS Phase 1] Read-only Git sensor.

    Observes repository metadata (branch, clean/dirty, ahead/behind, HEAD commit)
    and mounts it as a `sensor` context pointer. It never mutates a repository:
    every git invocation must match a frozen read-only argv template, runs with a
    scrubbed environment, and no network subcommand is reachable at all.

    Observations are emitted as `kagioneko.sensor_event.v1` records
    (`docs/EVENT_BUS_AND_WORLD_MODEL_SPEC.md`) and persisted metadata-only: no
    commit subject, author name, diff, or command output is ever stored. Branch
    names remain repository-controlled free text, so they are clamped, flagged,
    and `trust_score` stays below 1.0 so a Git observation can never satisfy the
    `exec` trust gate on its own.
    """

    SENSOR_SOURCE = "git_sensor"

    # `sensor_event_type` vocabulary from the Sensor spec that Phase 1 emits.
    # `tag_created` and `remote_secret_risk_detected` are deliberately not
    # emitted: no tag and no remote URL is read, see docs/GIT_SENSOR_PHASE1.md.
    SENSOR_EVENT_TYPES = frozenset({
        "git_clean", "git_dirty", "git_ahead", "git_behind",
        "git_state_changed", "git_sensor_unavailable",
    })

    # Full argv tuples, not just subcommands. Anything not listed is rejected.
    READ_ONLY_TEMPLATES = frozenset({
        ("rev-parse", "--is-inside-work-tree"),
        ("rev-parse", "--abbrev-ref", "HEAD"),
        ("rev-parse", "HEAD"),
        ("status", "--porcelain=v1"),
        ("rev-list", "--left-right", "--count", "@{upstream}...HEAD"),
        # Commit timestamp only. Subject and author are repository-controlled
        # free text and are not read at all, so they cannot be persisted.
        ("log", "-1", "--pretty=format:%ct"),
    })

    # Structural fields compared between polls to detect a change event.
    TRACKED_FIELDS = (
        "branch", "head_short", "detached", "dirty", "dirty_count",
        "untracked_count", "ahead", "behind", "upstream_tracked", "commit_ts",
    )

    # Direct observation of the local work tree.
    CONFIDENCE_LOCAL = 1.0
    # Derived from the already-fetched upstream ref. No network call is made,
    # so ahead/behind can lag the real remote.
    CONFIDENCE_UPSTREAM = 0.8

    MAX_TEXT_LEN = 200
    SAFE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")

    def __init__(
        self,
        repos: Optional[Dict[str, str]] = None,
        trust_score: float = 0.6,
        timeout: float = 5.0,
        git_binary: str = "git",
    ):
        # Repo paths are never taken from the pointer string, only from this
        # allowlist, so a crafted pointer cannot walk into an arbitrary repo.
        self.repos: Dict[str, str] = {}
        self.trust_score = min(trust_score, 0.99)
        self.timeout = timeout
        self.git_binary = git_binary
        self.subscribers: List[Callable[[dict], None]] = []
        self._last: Dict[str, dict] = {}
        for key, path in (repos or {}).items():
            self.add_repo(key, path)

    # --- configuration -------------------------------------------------

    def add_repo(self, key: str, path: str) -> str:
        if not self.SAFE_KEY.match(key):
            raise ValueError(f"invalid repo key: {key!r}")
        resolved = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(resolved):
            raise ValueError(f"repo path is not a directory: {resolved}")
        self.repos[key] = resolved
        return resolved

    def attach_registry(self, registry) -> None:
        """Bind the Event Bus adapter: sensor events onto the CPOS Task Tape."""
        self.subscribers.append(
            task_tape_sink(registry, pointer_id_for=self._pointer_id_for_event)
        )

    # --- event emission ------------------------------------------------

    @staticmethod
    def _pointer_id_for_event(event: dict) -> str:
        subject = event.get("subject", "")
        if subject.startswith("repo:"):
            key = subject.split(":", 1)[1]
            if key:
                return f"git_{key}"
        return "git_sensor"

    def _publish(self, event: dict) -> None:
        for sub in list(self.subscribers):
            try:
                sub(event)
            except Exception as exc:  # a bad subscriber must not break the poll
                print(f"--- [GIT SENSOR] subscriber error: {exc} ---")

    def _emit(self, **kwargs) -> dict:
        event = build_sensor_event(source=self.SENSOR_SOURCE, **kwargs)
        self._publish(event)
        return event

    def _emit_unavailable(self, repo_key: str, reason: str) -> None:
        """A sensor fault, not an observation of the repository."""
        self._emit(
            sensor_event_type="git_sensor_unavailable",
            subject=f"repo:{repo_key}" if repo_key else "repo:",
            summary=f"git sensor could not read '{repo_key}': {reason}",
            risk="medium",
            confidence=self.CONFIDENCE_LOCAL,
            source_of_truth=[p] if (p := self.repos.get(repo_key)) else [],
            suggested_next_action="check_sensor_configuration",
        )

    # --- read-only execution chokepoint --------------------------------

    def _git_env(self) -> Dict[str, str]:
        # Built from scratch rather than inherited, so GIT_DIR / GIT_WORK_TREE /
        # GIT_INDEX_FILE from the ambient environment cannot redirect the sensor.
        return {
            "PATH": os.environ.get("PATH", os.defpath),
            "LANG": "C",
            "LC_ALL": "C",
            # Without this, `git status` refreshes and rewrites .git/index, and
            # the read-only claim would be false.
            "GIT_OPTIONAL_LOCKS": "0",
            # A malicious repo must not be able to alias a read-only subcommand
            # into something else via user or system config.
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            # No credential prompts, no authentication attempts.
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "",
            "SSH_ASKPASS": "",
        }

    def _run_git(self, repo_path: str, args: List[str]) -> Tuple[int, str, str]:
        key = tuple(args)
        if key not in self.READ_ONLY_TEMPLATES:
            raise GitSensorPolicyError(f"git argv not in read-only allowlist: {key!r}")
        try:
            proc = subprocess.run(
                [self.git_binary, *args],
                cwd=repo_path,
                shell=False,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=self._git_env(),
            )
        except subprocess.TimeoutExpired:
            return 124, "", "git call timed out"
        except FileNotFoundError:
            return 127, "", "git binary not found"
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()

    # --- text handling -------------------------------------------------

    @classmethod
    def _clamp(cls, text: Optional[str]) -> Optional[str]:
        """Strip control characters and bound the length of repo-controlled text."""
        if text is None:
            return None
        cleaned = "".join(" " if (ord(c) < 32 or ord(c) == 127) else c for c in text)
        cleaned = " ".join(cleaned.split())
        if len(cleaned) > cls.MAX_TEXT_LEN:
            cleaned = cleaned[: cls.MAX_TEXT_LEN] + "...[TRUNCATED]"
        return cleaned

    # --- observation derivation ----------------------------------------

    @staticmethod
    def _state_summary(obs: dict) -> str:
        state = "dirty" if obs["dirty"] else "clean"
        parts = [f"{obs['branch'] or 'detached HEAD'} {state}"]
        if obs["dirty"]:
            parts.append(f"{obs['dirty_count']} changed path(s)")
        if obs["upstream_tracked"]:
            parts.append(f"ahead {obs['ahead']}, behind {obs['behind']}")
        else:
            parts.append("no upstream")
        return ", ".join(parts)

    def _derive_events(self, obs: dict, changed: List[str]) -> List[dict]:
        """Map one reading onto the Sensor spec's git event vocabulary.

        One record per distinct observation, so `sensor_event_type` always
        carries a concrete term from the published vocabulary rather than a
        compound state.
        """
        subject = f"repo:{obs['repo']}"
        truth = [self.repos[obs["repo"]]] if obs["repo"] in self.repos else []
        summary = self._state_summary(obs)
        events: List[dict] = []

        if obs["dirty"]:
            events.append({
                "sensor_event_type": "git_dirty",
                "summary": summary,
                # Untracked paths are unclassified artifacts rather than
                # in-progress edits to known files.
                "risk": "medium" if obs["untracked_count"] else "low",
                "confidence": self.CONFIDENCE_LOCAL,
                "suggested_next_action": "review_working_tree",
            })
        else:
            events.append({
                "sensor_event_type": "git_clean",
                "summary": summary,
                "risk": "low",
                "confidence": self.CONFIDENCE_LOCAL,
                "suggested_next_action": "continue_observing",
            })

        if obs["ahead"]:
            events.append({
                "sensor_event_type": "git_ahead",
                "summary": f"{obs['ahead']} local commit(s) not on upstream",
                "risk": "low",
                "confidence": self.CONFIDENCE_UPSTREAM,
                # Push is a confirmed action per the Sensor spec, never a
                # consequence of observing this event.
                "suggested_next_action": "confirm_before_push",
            })
        if obs["behind"]:
            events.append({
                "sensor_event_type": "git_behind",
                "summary": f"{obs['behind']} upstream commit(s) not local",
                "risk": "low",
                "confidence": self.CONFIDENCE_UPSTREAM,
                "suggested_next_action": "refresh_from_source_of_truth",
            })
        if changed:
            events.append({
                "sensor_event_type": "git_state_changed",
                "summary": f"changed since last reading: {', '.join(changed)}",
                "risk": "low",
                "confidence": self.CONFIDENCE_LOCAL,
                "suggested_next_action": "refresh_world_model",
            })

        return [
            build_sensor_event(
                source=self.SENSOR_SOURCE,
                subject=subject,
                source_of_truth=truth,
                observed_at=obs["observed_at"],
                observation=obs,
                # Nothing Phase 1 observes reaches a Human Escalation trigger:
                # no credential exposure check, no push, tag, or release action.
                requires_human_review=False,
                **fields,
            )
            for fields in events
        ]

    # --- sampling ------------------------------------------------------

    def snapshot(self, repo_key: str) -> Optional[dict]:
        """Take one read-only, metadata-only reading of a registered repository."""
        repo_path = self.repos.get(repo_key)
        if not repo_path:
            self._emit_unavailable(repo_key, "unregistered repo key")
            return None

        rc, out, err = self._run_git(repo_path, ["rev-parse", "--is-inside-work-tree"])
        if rc != 0 or out != "true":
            self._emit_unavailable(repo_key, "not a git work tree")
            return None

        obs: Dict[str, Any] = {
            "repo": repo_key,
            "observed_at": datetime.now(timezone.utc).astimezone().isoformat(),
            "branch": None,
            "detached": False,
            "head_short": None,
            "dirty": False,
            "dirty_count": 0,
            "untracked_count": 0,
            "upstream_tracked": False,
            "ahead": None,
            "behind": None,
            "commit_ts": None,
        }

        rc, out, _ = self._run_git(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"])
        if rc == 0:
            if out == "HEAD":
                obs["detached"] = True
            else:
                # Repository-controlled free text, kept as a state label.
                obs["branch"] = self._clamp(out)

        rc, out, _ = self._run_git(repo_path, ["rev-parse", "HEAD"])
        if rc == 0 and out:
            # Short hash only: identity without carrying the full object name.
            obs["head_short"] = out[:12]

        rc, out, _ = self._run_git(repo_path, ["status", "--porcelain=v1"])
        if rc == 0:
            # Counts only. Path names are never retained.
            lines = [ln for ln in out.splitlines() if ln.strip()]
            obs["dirty_count"] = len(lines)
            obs["untracked_count"] = sum(1 for ln in lines if ln.startswith("??"))
            obs["dirty"] = bool(lines)

        rc, out, _ = self._run_git(
            repo_path, ["rev-list", "--left-right", "--count", "@{upstream}...HEAD"]
        )
        if rc == 0 and out:
            parts = out.split()
            if len(parts) == 2 and all(p.isdigit() for p in parts):
                # left = commits only upstream has (behind), right = only HEAD has (ahead).
                obs["behind"] = int(parts[0])
                obs["ahead"] = int(parts[1])
                obs["upstream_tracked"] = True

        rc, out, _ = self._run_git(repo_path, ["log", "-1", "--pretty=format:%ct"])
        if rc == 0 and out:
            try:
                obs["commit_ts"] = int(out)
            except ValueError:
                obs["commit_ts"] = None

        previous = self._last.get(repo_key)
        changed = (
            [f for f in self.TRACKED_FIELDS if previous.get(f) != obs.get(f)]
            if previous is not None else []
        )
        # The Task Tape holds evidence of repository state, not a record of
        # every sample. An unchanged reading emits nothing, so polling cannot
        # turn the tape into a log. The mounted pointer still refreshes.
        if previous is None or changed:
            for event in self._derive_events(obs, changed):
                self._publish(event)
        self._last[repo_key] = obs
        return obs

    # --- pointer mounting ----------------------------------------------

    def fetch_object(self, path: str) -> Optional[ContextObject]:
        # path format: <repo_key>
        repo_key = path.strip("/").split("/")[0]
        if not repo_key or not self.SAFE_KEY.match(repo_key):
            self._emit_unavailable(repo_key, "malformed repo key")
            return None

        obs = self.snapshot(repo_key)
        if obs is None:
            return None

        state = "dirty" if obs["dirty"] else "clean"
        branch_label = obs["branch"] or ("detached HEAD" if obs["detached"] else "unknown")
        primary = "git_dirty" if obs["dirty"] else "git_clean"

        return ContextObject(
            id=f"git_{repo_key}",
            type="sensor",
            title=f"Git Sensor: {repo_key}",
            # Deliberately structural. Repository free text is not narrated here.
            summary=(
                f"Read-only Git observation of '{repo_key}': "
                f"{state}, {obs['dirty_count']} changed path(s)."
            ),
            # Metadata only: state labels, counts, a short hash, timestamps.
            data=json.dumps(obs, sort_keys=True),
            source=f"git_sensor:{repo_key}",
            location=self.repos[repo_key],
            trust_score=self.trust_score,
            sensitivity_level="internal",
            metadata={
                "gateway": "git",
                "sensor_path": repo_key,
                "read_only": True,
                "schema": SENSOR_EVENT_SCHEMA,
                "sensor_source": self.SENSOR_SOURCE,
                "sensor_event_type": primary,
                # Persisted record carries no commit subject, author name,
                # path name, diff, or command output.
                "metadata_only": True,
                "free_text_stored": False,
                # Branch names are written by whoever wrote the repository.
                "untrusted_text": True,
                "repo_controlled_fields": ["branch"],
                "branch_label": branch_label,
                "upstream_tracked": obs["upstream_tracked"],
                "requires_human_review": False,
                "execute_automatically": False,
            },
        )

class GatewayManager:
    """The 'Bridge Controller'. Manages external cognitive gateways."""

    def __init__(self):
        self.gateways: Dict[str, ExternalGateway] = {
            "github": MockGitHubGateway(),
            "mcp": MCPGateway(),
            "env": EnvironmentalGateway(),
            "src": SourceGateway(), # [CPOS v8.0] Source Code Access
            # Registered with an empty repo allowlist: discoverable but inert
            # until a caller explicitly adds a repository.
            "git": GitGateway()
        }
        self.registry = None

    def attach_registry(self, registry):
        """Wire the kernel event log into any gateway that emits events."""
        self.registry = registry
        for gw in self.gateways.values():
            if hasattr(gw, "attach_registry"):
                gw.attach_registry(registry)

    def register_gateway(self, name: str, gateway: ExternalGateway):
        self.gateways[name] = gateway
        if self.registry is not None and hasattr(gateway, "attach_registry"):
            gateway.attach_registry(self.registry)
        print(f"--- [GATEWAY] Registered Cognitive Gateway: {name} ---")

    def resolve(self, gateway_name: str, path: str) -> Optional[ContextObject]:
        """Resolves an external path to a ContextObject using the registered gateway."""
        if gateway_name in self.gateways:
            print(f"--- [GATEWAY] Resolving {path} via {gateway_name} ---")
            return self.gateways[gateway_name].fetch_object(path)
        return None
