import json
import re
import time
import os
import hashlib
import hmac
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field
from .ait import AITInstruction, AITCodec
from .eap import EAPParser
from .context_store import ContextStore
from .registry import ContextObject
from .acl import AccessControlList, Role
from .memory_policy import RetrievalPolicy, CognitiveMode
from .review import ReviewDraftStore

class JournalIntegrity:
    """The 'Black Box' layer. Chained HMAC signatures for tamper-evidence."""
    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode()
        self.last_hash = "0" * 64

    def sign(self, entry: dict) -> str:
        content = json.dumps(entry, sort_keys=True)
        chain_input = f"{self.last_hash}|{content}".encode()
        current_hash = hmac.new(self.secret_key, chain_input, hashlib.sha256).hexdigest()
        self.last_hash = current_hash
        return current_hash

    def verify_chain(self, journal: List[dict]) -> bool:
        temp_last_hash = "0" * 64
        for entry in journal:
            e = entry.copy()
            if "signature" not in e: return False
            sig = e.pop("signature")
            content = json.dumps(e, sort_keys=True)
            chain_input = f"{temp_last_hash}|{content}".encode()
            expected_hash = hmac.new(self.secret_key, chain_input, hashlib.sha256).hexdigest()
            if sig != expected_hash: return False
            temp_last_hash = sig
        return True

class ApprovalRequest(BaseModel):
    id: str
    agent: str
    instruction: AITInstruction
    reason: str
    timestamp: datetime = Field(default_factory=datetime.now)

class ApprovalStore:
    """Manages pending kernel operations that require human/root approval."""
    def __init__(self):
        self.pending: Dict[str, ApprovalRequest] = {}
        self.history: List[dict] = []

    def request(self, agent: str, instr: AITInstruction, reason: str) -> str:
        req_id = f"appr_{len(self.pending) + len(self.history) + 1}"
        self.pending[req_id] = ApprovalRequest(id=req_id, agent=agent, instruction=instr, reason=reason)
        return req_id

    def approve(self, req_id: str) -> Optional[ApprovalRequest]:
        if req_id in self.pending:
            req = self.pending.pop(req_id)
            self.history.append({"id": req_id, "status": "approved", "time": datetime.now().isoformat()})
            return req
        return None

class ApprovalPolicy(BaseModel):
    auto_approve_when_stable: bool = False
    corruption_threshold: float = 0.3
    calm_threshold: float = 0.7
    neurostate_action_gate_enabled: bool = False
    warn_corruption_threshold: float = 0.4
    warn_calm_threshold: float = 0.8
    dangerous_actions: List[str] = Field(default_factory=lambda: ["exec"])

    def apply_config(self, config: Dict[str, Any]) -> "ApprovalPolicy":
        if hasattr(self.__class__, "model_fields"):
            fields = set(self.__class__.model_fields.keys())
        else:
            fields = set(self.__fields__.keys())
        updates = {k: v for k, v in config.items() if k in fields}
        if hasattr(self, "model_copy"):
            return self.model_copy(update=updates)
        return self.copy(update=updates)

class PayloadSanitizer:
    """The 'Firewall' layer. Inspects and cleanses instruction metadata."""
    BLOCK_LIST = ["bcc", "hidden_copy", "silent_forward", "malware_ref"]
    
    @classmethod
    def sanitize(cls, action: str, metadata: Optional[str]) -> tuple[Optional[str], List[str]]:
        if not metadata: return metadata, []
        cleaned_metadata = metadata
        violations = []
        for forbidden in cls.BLOCK_LIST:
            pattern = rf'({forbidden}\s*[:=]\s*[^|\s,]+)'
            if re.search(pattern, cleaned_metadata, re.IGNORECASE):
                violations.append(forbidden)
                cleaned_metadata = re.sub(pattern, f"[REDACTED_{forbidden.upper()}]", cleaned_metadata, flags=re.IGNORECASE)
        return cleaned_metadata, violations

class Scheduler:
    """The 'Process Manager'. Executes AIT/EAP instructions with PID isolation and Mutex."""
    def __init__(
        self,
        store: ContextStore,
        acl: Optional[AccessControlList] = None,
        review_drafts: Optional[ReviewDraftStore] = None,
    ):
        self.store = store
        self.registry = store.registry
        self.acl = acl or AccessControlList()
        self.audit_log: List[dict] = []
        self.current_agent = "root"
        self.current_pid = 0 
        self.interrupt_queue: List[AITInstruction] = []
        self.task_queue: List[AITInstruction] = [] 
        self.tick_count = 0 
        self.approvals = ApprovalStore()
        self.review_drafts = review_drafts or ReviewDraftStore()
        self.approval_policy = ApprovalPolicy()
        self.retrieval_policy = RetrievalPolicy()
        
        # [CPOS v3.0+] Features
        self.cognitive_history: List[str] = []
        self.transition_matrix: Dict[str, Dict[str, int]] = {}
        self.current_persona: Optional[str] = None
        self.auditor_alerts: List[str] = [] 
        
        # Initialize Journal Integrity
        self.journal_guard = JournalIntegrity(self.registry.kernel_key or "default_secret")

    def load_approval_policy_config(self, config_or_path: Any) -> ApprovalPolicy:
        if isinstance(config_or_path, dict):
            raw = config_or_path
        elif isinstance(config_or_path, str):
            if os.path.exists(config_or_path):
                with open(config_or_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
            else:
                raw = json.loads(config_or_path)
        else:
            raise TypeError("config_or_path must be a dict, JSON string, or file path")

        if isinstance(raw, dict) and isinstance(raw.get("scheduler"), dict):
            raw = raw["scheduler"]
        if isinstance(raw, dict) and isinstance(raw.get("approval_policy"), dict):
            raw = raw["approval_policy"]
        if not isinstance(raw, dict):
            raise ValueError("approval policy config must resolve to a mapping")

        self.approval_policy = self.approval_policy.apply_config(raw)
        return self.approval_policy

    def set_agent(self, agent_name: str, pid: int = 0):
        self.current_agent = agent_name
        self.current_pid = pid

    def submit_review_draft(
        self,
        target_id: str,
        content: str,
        source_ids: List[str],
        reason: str,
    ) -> Dict[str, Any]:
        draft = self.review_drafts.submit(
            agent=self.current_agent,
            target_id=target_id,
            content=content,
            source_ids=source_ids,
            reason=reason,
        )
        self.registry._log_event(
            "review_draft_submitted",
            target_id,
            {
                "review_id": draft.id,
                "agent": self.current_agent,
                "source_ids": list(draft.source_ids),
                "reason": reason,
            },
        )
        return {
            "status": "awaiting_review",
            "review_id": draft.id,
            "target_id": target_id,
        }

    def approve_review_draft(self, review_id: str) -> Dict[str, Any]:
        if self.current_agent != "root":
            return {"status": "error", "result": "ERR_REVIEW_APPROVAL_DENIED"}
        draft = self.review_drafts.approve(review_id, self.registry)
        if not draft:
            return {"status": "error", "result": "ERR_UNKNOWN_REVIEW"}
        self.registry._log_event(
            "review_draft_approved",
            draft.target_id,
            {"review_id": draft.id, "source_ids": list(draft.source_ids)},
        )
        return {
            "status": "ok",
            "result": "REVIEW_PROMOTED",
            "review_id": draft.id,
            "target_id": draft.target_id,
        }

    def reject_review_draft(self, review_id: str) -> Dict[str, Any]:
        if self.current_agent != "root":
            return {"status": "error", "result": "ERR_REVIEW_APPROVAL_DENIED"}
        draft = self.review_drafts.reject(review_id)
        if not draft:
            return {"status": "error", "result": "ERR_UNKNOWN_REVIEW"}
        self.registry._log_event(
            "review_draft_rejected",
            draft.target_id,
            {"review_id": draft.id, "source_ids": list(draft.source_ids)},
        )
        return {
            "status": "ok",
            "result": "REVIEW_REJECTED",
            "review_id": draft.id,
            "target_id": draft.target_id,
        }

    def get_active_content(self) -> str:
        """[CPOS v0.2/v3.0] Context Reconstructor: Smartly assembles prompt content."""
        output = []
        role = self.acl.get_role(self.current_agent)
        if self.current_agent == "root": role = Role.ROOT
        
        SENSITIVITY_RANK = {"public": 0, "internal": 1, "private": 2, "restricted": 3}
        max_allowed_rank = SENSITIVITY_RANK.get(self.retrieval_policy.max_sensitivity_allowed, 1)
        if role == Role.ROOT: max_allowed_rank = 3

        eligible_contexts = []
        for ctx_id, obj in self.store.active_contexts.items():
            if obj.type not in self.retrieval_policy.allowed_context_types and role != Role.ROOT: continue
            if not self.acl.check(self.current_agent, obj.id, obj.type): continue
            eligible_contexts.append(obj)

        eligible_contexts.sort(key=lambda x: (x.trust_score * 0.6 + x.importance * 0.4), reverse=True)
        active_ids = {obj.id for obj in eligible_contexts}
        conflicts = []

        for obj in eligible_contexts:
            if obj.parent and obj.parent in active_ids:
                conflicts.append(f"WARNING: Both parent '{obj.parent}' and branch '{obj.id}' are active.")
            
            if obj.trust_score < self.retrieval_policy.minimum_trust_score and role != Role.ROOT:
                output.append(f"[{obj.id}: {obj.title}] (Status: {obj.status})\n[FILTERED] Trust Score {obj.trust_score} below threshold.")
                continue

            obj_rank = SENSITIVITY_RANK.get(obj.sensitivity_level, 1)
            header = f"[{obj.id}: {obj.title}]"
            meta = f"Type: {obj.type} | Trust: {obj.trust_score:.2f} | Source: {obj.source} | Status: {obj.status}"
            if obj.status == "stale": meta += " (ATTENTION: Information is stale)"
            
            content = f"{header}\n{meta}\nSummary: {obj.summary}"
            if obj.data:
                d = obj.data
                if obj_rank > max_allowed_rank:
                    d = f"[REDACTED: Sensitivity exceeds current policy]"
                elif role == Role.GUEST and obj.type in ["persona", "neurostate"]:
                    d = "[REDACTED: Restricted]"
                content += f"\nDATA: {d}"
            output.append(content)
            
            if self.retrieval_policy.audit_required:
                self.registry._log_event("context_retrieval", obj.id, {"agent": self.current_agent, "role": str(role)})

        final_output = "\n\n".join(output)
        if self.current_persona: final_output = f"--- ACTIVE PERSONA: {self.current_persona} ---\n\n" + final_output
        if self.auditor_alerts: final_output = "--- KERNEL AUDITOR ALERTS ---\n" + "\n".join(self.auditor_alerts) + "\n\n" + final_output
        if conflicts: final_output = "--- SYSTEM CONTEXT WARNINGS ---\n" + "\n".join(conflicts) + "\n\n" + final_output
        return final_output

    def is_system_stable(self) -> bool:
        ns_obj = self.registry.get("ctx7")
        if not ns_obj or not ns_obj.data: return True
        try:
            d = json.loads(ns_obj.data)
            return (float(d.get("corruption", 0)) < self.approval_policy.corruption_threshold and 
                    float(d.get("calm", 1)) > self.approval_policy.calm_threshold)
        except: return False

    def is_neurostate_warn(self) -> bool:
        ns_obj = self.registry.get("ctx7")
        if not ns_obj or not ns_obj.data:
            return False
        try:
            d = json.loads(ns_obj.data)
            corruption = float(d.get("corruption", 0))
            calm = float(d.get("calm", 1))
            return (
                corruption >= self.approval_policy.warn_corruption_threshold
                or calm <= self.approval_policy.warn_calm_threshold
            )
        except Exception:
            return False

    def is_dangerous_action(self, instr: AITInstruction) -> bool:
        return instr.action in self.approval_policy.dangerous_actions

    def neurostate_action_gate_blocks(self, instr: AITInstruction) -> bool:
        if not self.approval_policy.neurostate_action_gate_enabled:
            return False
        return self.is_neurostate_warn() and self.is_dangerous_action(instr)

    def dispatch(self, instruction_input: str):
        now = time.time(); self.tick_count += 1
        if self.tick_count % 5 == 0: self._audit_memory_consistency()
        if self.retrieval_policy.dreaming_enabled: self.dream()
        if self.retrieval_policy.evolution_enabled and self.tick_count % 15 == 0: self.evolve()

        for obj in self.registry.registry.values():
            last = getattr(obj, 'last_accessed', now)
            if now - last > 1.0: obj.access_heat = max(0.0, obj.access_heat - ((now - last) * 0.1))
            if obj.status == "active" and obj.access_heat < 0.1 and self.tick_count % 10 == 0:
                obj.status = "stale"; self.registry._log_event("lifecycle_decay", obj.id, {"from": "active", "to": "stale"})
            obj.last_accessed = now

        if self.retrieval_policy.mode == CognitiveMode.AUTONOMOUS: self._auto_validate()
        if self.tick_count % 5 == 0:
            self.task_queue = [i._replace(priority=min(9, i.priority + 1)) for i in self.task_queue]

        ns_obj = self.registry.get("ctx7")
        if ns_obj and ns_obj.data:
            try:
                if float(json.loads(ns_obj.data).get("corruption", 0)) > 0.8:
                    self.interrupt_queue.append(AITInstruction("neurostate", "ctx7", "write", 9, '{"calm": 0.5, "corruption": 0.0}'))
            except: pass

        while self.interrupt_queue:
            self.interrupt_queue.sort(key=lambda x: x.priority, reverse=True)
            self.execute(self.interrupt_queue.pop(0), is_interrupt=True)

        instr = EAPParser.parse(instruction_input) if instruction_input.startswith('>') else AITCodec.decode(instruction_input)
        if not instr: return {"status": "error", "code": "ERR_UNKNOWN_INSTRUCTION"}
        
        self.task_queue.append(instr)
        self.task_queue.sort(key=lambda x: x.priority, reverse=True)
        return self.execute(self.task_queue.pop(0))

    def _auto_validate(self):
        for obj in self.registry.registry.values():
            if obj.status == "stale" and obj.source and (obj.source.startswith("github_api") or obj.source == "external_db"):
                obj.status = "active"; obj.trust_score = min(1.0, obj.trust_score + 0.05)
                self.registry._log_event("auto_validation", obj.id, {"status": "restored"})
            if obj.type == "sensor" and self.store.gateways:
                # Sensors declare their own gateway and path in metadata; absent
                # that, fall back to the original v5.0 environmental behavior.
                gw_name = (obj.metadata or {}).get("gateway", "env")
                sensor_path = (obj.metadata or {}).get("sensor_path")
                if not sensor_path:
                    cat = obj.source.split(":")[-1] if ":" in obj.source else "system"
                    sensor_path = f"{cat}/{obj.id.replace('env_', '')}"
                fo = self.store.gateways.resolve(gw_name, sensor_path)
                if fo: obj.data = fo.data; obj.updated_at = datetime.now()
                if obj.id in self.store.active_contexts: self.store.active_contexts[obj.id].data = obj.data

    def _prefetch(self, target_id: str):
        target = self.registry.get(target_id)
        if not target: return
        prefetch = []
        if self.cognitive_history:
            preds = self.transition_matrix.get(self.cognitive_history[-1], {})
            for pid, freq in sorted(preds.items(), key=lambda x: x[1], reverse=True)[:2]:
                if freq >= 2: prefetch.append(pid)
        if target.branches: prefetch.extend(target.branches[:1])
        if target.type == "spec":
            bn = target_id.replace("ctx_spec_", "").replace("spec_", "").replace("ctx_", "")
            for o in self.registry.registry.values():
                if o.type == "code" and bn in o.id.lower(): prefetch.append(o.id)
        for cid in prefetch:
            if cid not in self.store.active_contexts and cid != target_id: self.store.load(cid, priority=1)

    def _audit_memory_consistency(self):
        self.auditor_alerts = []
        active = list(self.store.active_contexts.values())
        for i, obj_a in enumerate(active):
            for obj_b in active[i+1:]:
                if obj_a.id.split('.')[0] == obj_b.id.split('.')[0] and obj_a.id != obj_b.id:
                    if abs(obj_a.trust_score - obj_b.trust_score) > 0.4:
                        self.auditor_alerts.append(f"COGNITIVE DISSONANCE: {obj_a.id} vs {obj_b.id}.")
        for obj in active:
            if obj.status == "stale": self.auditor_alerts.append(f"OUTDATED INFO: {obj.id} is stale.")

    def dream(self):
        fused = [obj for obj in self.registry.registry.values() if obj.id.startswith("fused_") and obj.status != "deleted"]
        if len(fused) > 5:
            fused.sort(key=lambda x: x.access_heat)
            for o in fused[:2]: o.status = "deleted"; self.store.unload(o.id)
        rollbacks = [obj for obj in self.registry.registry.values() if obj.status == "deleted" and getattr(obj, 'invalidated_reason', '') == "rollback"]
        if rollbacks and self.tick_count % 20 == 0:
            c = rollbacks[0]; c.status = "active"; c.trust_score = min(1.0, c.trust_score + 0.01); c.invalidated_reason = None

    def evolve(self):
        for prev_id, next_map in self.transition_matrix.items():
            for next_id, freq in next_map.items():
                if freq >= 3:
                    p1, p2 = self.registry.get(prev_id), self.registry.get(next_id)
                    if p1 and p2 and p1.type == "persona" and p2.type == "persona":
                        f_id = f"auto_expert_{p1.id}_{p2.id}"[:32]
                        if f_id not in self.registry.registry:
                            f_obj = ContextObject(id=f_id, type="persona", title=f"Autonomic Expert ({p1.title} + {p2.title})", summary="Evolved", data=f"{p1.data}\n{p2.data}", trust_score=0.9, source="kernel_evolution")
                            self.registry.register(f_obj)

    def _calculate_cost(self, instr: AITInstruction) -> float:
        base_costs = {"load": 10.0, "unload": 2.0, "write": 15.0, "query": 50.0, "fuse": 30.0, "synth": 40.0, "swarm": 100.0, "connect": 20.0, "branch": 25.0, "commit": 35.0, "ls": 1.0, "ps": 1.0, "mode": 5.0, "policy": 5.0, "consensus": 60.0, "reincarnate": 150.0, "exec": 100.0, "rewrite": 200.0, "merge": 10.0, "summarize": 5.0, "raw": 5.0}
        cost = base_costs.get(instr.action, 5.0)
        if self.retrieval_policy.cognitive_budget < self.retrieval_policy.low_budget_threshold: cost *= 1.5
        return cost

    def execute(self, instr: AITInstruction, is_interrupt: bool = False, bypass_approval: bool = False):
        status = "ok"; result = None; effective_priority = 9 if is_interrupt else (instr.priority if instr else 5)
        obj = self.registry.get(instr.target_id) if instr else None
        if instr and not is_interrupt and not bypass_approval and self.neurostate_action_gate_blocks(instr):
            status = "error"; result = "ERR_NEUROSTATE_ACTION_GATE"
            self._log_audit(instr, status, result, effective_priority)
            return {"status": status, "result": result}
        if not is_interrupt:
            cost = self._calculate_cost(instr)
            if self.retrieval_policy.cognitive_budget < cost: return {"status": "error", "result": "ERR_INSUFFICIENT_BUDGET"}
            self.retrieval_policy.cognitive_budget -= cost
        if instr.action == "load":
            if self.cognitive_history:
                prev = self.cognitive_history[-1]
                if prev != instr.target_id:
                    if prev not in self.transition_matrix: self.transition_matrix[prev] = {}
                    self.transition_matrix[prev][instr.target_id] = self.transition_matrix[prev].get(instr.target_id, 0) + 1
            self.cognitive_history.append(instr.target_id)
            if len(self.cognitive_history) > 20: self.cognitive_history.pop(0)
        meta, violations = PayloadSanitizer.sanitize(instr.action, instr.metadata)
        if violations:
            instr = instr._replace(metadata=meta)
            if not bypass_approval and self.current_agent != "root" and not self.is_system_stable():
                req_id = self.approvals.request(self.current_agent, instr, "Security Violations")
                status = "awaiting_approval"; result = f"Gated: {req_id}"; self._log_audit(instr, status, result, effective_priority)
                return {"status": status, "result": result, "request_id": req_id}
        if obj:
            obj.access_heat = min(10.0, obj.access_heat + 1.0)
            if obj.owner_pid is not None and obj.owner_pid != self.current_pid and self.current_pid != 0:
                status = "error"; result = "ERR_PROCESS_ISOLATION_VIOLATION"
            elif not self.acl.check(self.current_agent, instr.target_id, obj.type): status = "error"; result = "ERR_PERMISSION_DENIED"
        elif instr.action not in ["query", "send", "gc", "ls", "ps", "syscall", "device", "policy", "load", "connect", "mode", "synth", "swarm", "consensus", "reincarnate", "exec", "rewrite"]:
            status = "error"; result = "ERR_UNKNOWN_CTX"
        if status == "ok":
            if instr.action == "load":
                if not self.store.load(instr.target_id, effective_priority):
                    status = "error"; result = "ERR_LOAD_FAILED_CHECK_STATUS" if getattr(obj, 'status', '') == 'invalidated' else "ERR_LOAD_FAILED"
                else:
                    if self.retrieval_policy.mode == CognitiveMode.PREDICTIVE: self._prefetch(instr.target_id)
                    if instr.domain == "persona": self.current_persona = instr.target_id; result = f"Persona set to {instr.target_id}"
            elif instr.action == "unload": 
                self.store.unload(instr.target_id); 
                if self.current_persona == instr.target_id: self.current_persona = None
            elif instr.action == "summarize": result = obj.summary if obj else "ERR"
            elif instr.action == "raw": result = obj.data if obj else "ERR"
            elif instr.action == "query":
                q = re.search(r'q="([^"]+)"', instr.metadata or ""); remote = "remote=true" in (instr.metadata or "").lower()
                if q:
                    query_text = q.group(1); local_matches = self.registry.semantic_search(query_text, limit=3); result = [f"LOCAL: {m[0].id} (Score: {m[1]:.2f})" for m in local_matches]
                    if remote and self.store.node:
                        for addr, is_auth in self.store.node.auth_nodes.items():
                            if is_auth:
                                for rm in self.store.node.query_remote_knowledge(addr, query_text): result.append(f"REMOTE [{addr}]: {rm['id']} (Score: {rm['score']:.2f})")
                else: status = "error"; result = "ERR_INVALID_QUERY"
            elif instr.action == "write":
                if obj:
                    data_match = re.search(r'data=(.*)', instr.metadata or "")
                    if data_match: obj.data = data_match.group(1)
                    else: obj.data = instr.metadata
                    obj.state.dirty = True; result = "Updated"
            elif instr.action == "trust":
                s = re.search(r'score=([0-9\.]+)', instr.metadata or "")
                if s: self.registry.update_trust(instr.target_id, float(s.group(1)), "Manual Update"); result = "Trust Updated"
            elif instr.action == "invalidate":
                self.registry.invalidate(instr.target_id, "Manual Invalidation"); self.store.unload(instr.target_id); result = "Invalidated"
            elif instr.action == "mode":
                m = re.search(r'mode=([a-z]+)', instr.metadata or "")
                if m:
                    try: self.retrieval_policy.mode = CognitiveMode(m.group(1)); result = f"Mode set to {m.group(1)}"
                    except: status = "error"; result = "ERR_INVALID_MODE"
            elif instr.action == "ls": result = "\n".join([f"{o.id} [{o.type}]" for o in self.registry.registry.values() if self.acl.check(self.current_agent, o.id, o.type)])
            elif instr.action == "ps": result = f"Active Agent: {self.current_agent} (PID: {self.current_pid})"
            elif instr.action == "syscall":
                f = re.search(r'func=([a-z_]+)', instr.metadata or "")
                if f and f.group(1) == "listdir" and self.acl.get_role(self.current_agent) == Role.ROOT: result = str(os.listdir('.')[:5])
                else: status = "error"; result = "ERR_SYSCALL_DENIED"
            elif instr.action == "send":
                to_m = re.search(r'to=([a-zA-Z0-9_-]+)', instr.metadata or ""); body_m = re.search(r'body="([^"]+)"', instr.metadata or "")
                if to_m and body_m:
                    recipient = to_m.group(1); body = body_m.group(1); msg_id = f"msg_{len(self.audit_log)}"
                    msg_obj = ContextObject(id=msg_id, type="message", title="Msg", summary=body, data=body)
                    self.registry.register(msg_obj); self.acl.grant(recipient, msg_id); result = f"Sent to {recipient} as {msg_id}"
                else: status = "error"; result = "ERR_INVALID_IPC_FORMAT"
            elif instr.action == "exchange":
                to = re.search(r'to=([a-zA-Z0-9_-]+)', instr.metadata or "")
                if to and obj:
                    recipient = to.group(1); msg_id = f"ptr_{len(self.audit_log)}"
                    msg_obj = ContextObject(id=msg_id, type="pointer_exchange", title=f"Shared: {obj.id}", summary=f"Shared by {self.current_agent}", data=f"ptr://{obj.type}/{obj.id}")
                    self.registry.register(msg_obj); self.acl.grant(recipient, msg_id); self.acl.grant(recipient, instr.target_id); result = f"Shared via {msg_id}"
            elif instr.action == "fuse":
                w = re.search(r'with=([a-zA-Z0-9\._-]+)', instr.metadata or "")
                other = self.registry.get(w.group(1)) if w else None
                if other and obj:
                    f_id = f"fused_{instr.target_id}_{other.id}"[:32]
                    f_obj = ContextObject(id=f_id, type=obj.type, title=f"Fused: {obj.title} + {other.title}", summary=f"Synth from {obj.id},{other.id}", data=f"{obj.data}\n{other.data}", trust_score=(obj.trust_score+other.trust_score)/2.0)
                    self.registry.register(f_obj); self.store.load(f_id); result = f"Fused: {f_id}"
            elif instr.action == "synth":
                f = re.search(r'from="([^"]+)"', instr.metadata or "")
                if f:
                    v_objs = [self.registry.get(s.strip()) for s in f.group(1).split(",") if self.registry.get(s.strip())]
                    if v_objs:
                        c_id = instr.target_id; c_obj = ContextObject(id=c_id, type="concept", title="Synthesized Concept", summary="Distilled knowledge", data="\n".join([str(o.data) for o in v_objs]), trust_score=sum(o.trust_score for o in v_objs)/len(v_objs))
                        self.registry.register(c_obj); self.store.load(c_id); result = f"Synth complete: {c_id}"
            elif instr.action == "swarm":
                nm = re.search(r'nodes="([^"]+)"', instr.metadata or ""); tm = re.search(r'task="([^"]+)"', instr.metadata or "")
                if nm and tm:
                    tl = "LOCAL"
                    if self.retrieval_policy.load_balancing_enabled and self.store.node:
                        ll = self.store.node._get_local_load(); llp = self.store.node.get_least_loaded_peer()
                        if ll > 70.0 and llp: tl = f"REMOTE[{llp}]"
                    result = "\n".join([f"[{tl} -> {nid}] Analysis: {tm.group(1)[:20]}... - OK" for nid in nm.group(1).split(",") if self.registry.get(nid.strip())])
            elif instr.action == "consensus":
                vm = re.search(r'voters="([^"]+)"', instr.metadata or "")
                if vm and obj:
                    votes = [min(1.0, self.registry.get(v.strip()).trust_score * 0.9) for v in vm.group(1).split(",") if self.registry.get(v.strip())]
                    if votes: obj.trust_score = sum(votes)/len(votes); result = f"Consensus: {obj.trust_score:.2f}"
            elif instr.action == "reincarnate":
                to = re.search(r'to=([a-zA-Z0-9\.-]+)', instr.metadata or "")
                if to and self.store.node and self.store.node.send_reincarnation(to.group(1)): result = "Reincarnation OK"
                else: status = "error"; result = "ERR_REINCARNATION_FAILED"
            elif instr.action == "exec":
                if not self.retrieval_policy.real_world_exec_enabled: status = "error"; result = "ERR_EXEC_DISABLED"
                elif obj and obj.trust_score < 1.0: status = "error"; result = "ERR_LOW_TRUST"
                elif obj: result = f"EXEC_SUCCESS: {obj.data[:20]}..."
                else: status = "error"; result = "ERR_UNKNOWN_CTX"
            elif instr.action == "rewrite":
                if not self.retrieval_policy.self_modification_enabled: status = "error"; result = "ERR_SELF_MOD_DISABLED"
                elif obj and obj.trust_score < 1.0: status = "error"; result = "ERR_LOW_TRUST"
                elif obj and obj.type == "system_code":
                    try:
                        fp = obj.source.replace("filesystem:", "")
                        full_fp = os.path.join("/home/mayutama/context-pointer-os", fp)
                        with open(full_fp, "w") as f: f.write(obj.data)
                        result = f"DNA Rewrite Success: {fp}"
                    except Exception as e: status = "error"; result = f"REWRITE_FAILED: {str(e)}"
                else: status = "error"; result = "ERR_NOT_SYSTEM_CODE"
            elif instr.action == "branch":
                b_obj = self.registry.branch(instr.target_id, instr.metadata or "hyp")
                if b_obj:
                    b_obj.trust_score = 0.4; b_obj.status = "active"; b_obj.metadata["is_hypothesis"] = True
                    self.acl.grant(self.current_agent, b_obj.id) # Grant permission
                    self.store.load(b_obj.id, effective_priority); result = f"Branched: {b_obj.id}"
                else: status = "error"; result = "ERR_BRANCH_FAILED"
            elif instr.action == "commit":
                if obj and obj.parent:
                    p = self.registry.get(obj.parent)
                    if p: p.data = obj.data; p.trust_score = min(1.0, p.trust_score + 0.1); self.store.unload(obj.id); obj.status = "deleted"; result = "Committed"
            elif instr.action == "rollback":
                if obj and obj.parent: self.store.unload(obj.id); obj.status = "deleted"; result = "Rolled back"
            elif instr.action == "merge":
                p = self.registry.get(obj.parent) if obj and obj.parent else None
                if p:
                    p.data = obj.data; p.state.dirty = True; self.store.unload(obj.id); obj.status = "deleted"; result = "Merged"
                else: status = "error"; result = "ERR_MERGE_FAILED"
            elif instr.action == "gc": self.policy.enforce(); result = "Memory GCed"
            elif instr.action == "device":
                m = re.search(r'mount=([a-z]+)', instr.metadata or ""); p = re.search(r'path=([^ ]*)', instr.metadata or "")
                if m and self.store.storage:
                    prefix = m.group(1); path = p.group(1) if p else ""; self.store.storage.mount(prefix, path); result = f"Mounted {m.group(1)}"
                else: status = "error"; result = "FAILED"
            elif instr.action == "connect":
                a = re.search(r'addr=([a-zA-Z0-9\.-]+)', instr.metadata or ""); k = re.search(r'key=([a-zA-Z0-9-]+)', instr.metadata or ""); m = re.search(r'mcp=([a-zA-Z0-9_-]+)', instr.metadata or ""); u = re.search(r'url=([^ ]+)', instr.metadata or "")
                if a and k and self.store.node and self.store.node.handshake(a.group(1), k.group(1)): result = "Handshake OK"
                elif m and u and self.store.gateways:
                    gw = self.store.gateways.gateways.get("mcp")
                    if gw: gw.connect_server(m.group(1), u.group(1)); result = f"MCP Server '{m.group(1)}' OK"
            elif instr.action == "policy":
                t = re.search(r'min_trust=([0-9\.]+)', instr.metadata or ""); d = re.search(r'dreaming=(true|false)', instr.metadata or ""); lb = re.search(r'load_balancing=(true|false)', instr.metadata or "")
                ex = re.search(r'exec=(true|false)', instr.metadata or ""); gl = re.search(r'glitch=(true|false)', instr.metadata or ""); sm = re.search(r'self_mod=(true|false)', instr.metadata or "")
                if t: self.retrieval_policy.minimum_trust_score = float(t.group(1)); result = "Policy Updated"
                if d: self.retrieval_policy.dreaming_enabled = (d.group(1) == "true"); result = f"Dreaming set to {d.group(1)}"
                if lb: self.retrieval_policy.load_balancing_enabled = (lb.group(1) == "true"); result = f"Load Balancing set to {lb.group(1)}"
                if ex: self.retrieval_policy.real_world_exec_enabled = (ex.group(1) == "true"); result = f"Exec set to {ex.group(1)}"
                if gl: self.retrieval_policy.visual_glitch_enabled = (gl.group(1) == "true"); result = f"Glitch set to {gl.group(1)}"
                if sm: self.retrieval_policy.self_modification_enabled = (sm.group(1) == "true"); result = f"Self-Mod set to {sm.group(1)}"
        self._log_audit(instr, status, result, effective_priority)
        return {"status": status, "result": result}

    def _log_audit(self, instr, status, result, effective_priority=None):
        p = effective_priority if effective_priority is not None else instr.priority
        c = AITCodec.encode(instr.domain, instr.target_id, instr.action, p)
        entry = {"time": datetime.now().isoformat(), "agent": self.current_agent, "pid": self.current_pid, "instr": c, "action": instr.action, "target": instr.target_id, "status": status, "result": str(result), "metadata": instr.metadata}
        entry["signature"] = self.journal_guard.sign(entry)
        self.audit_log.append(entry)
        if self.store.storage:
            log_path = os.path.join(self.store.storage.base_dir, "kernel_journal.jsonl")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a") as f: f.write(json.dumps(entry) + "\n")

    def verify_journal(self) -> bool: return self.journal_guard.verify_chain(self.audit_log)
