# CPOS Prepublish Enforcement Profile — Owner Draft v0.1

Status: DESIGN DRAFT v0.1 — IN REVIEW / IMPLEMENTATION NOT STARTED
Scope: Git push, tag, GitHub Release, and other public publication actions
Default posture: deny execution when evidence is missing, stale, mismatched, or ambiguous

## 1. Purpose

Turn the existing CPOS Sensor/Event Bus/Human Escalation design into an enforceable gate for public actions. This profile does not grant CPOS shell or GitHub authority. Phase 1 produces a decision and an approval request only; a separate executor may act only after a valid, scoped human approval.

Core separation:

```text
observe -> propose -> validate technical evidence -> request human approval
        -> revalidate evidence and approval atomically -> execute once -> verify result
```

No step may imply the next step. In particular, `prepublish_ok`, an AI review PASS, or a general “continue” instruction is not execution authority.

## 2. Protected actions and risk classes

| Class | Actions | Required posture |
|---|---|---|
| P1 routine remote write | push an already-reviewed commit to an existing non-protected branch | explicit scoped approval; all evidence fresh |
| P2 public content | public GitHub comment/review, Zenn/note publish, public repository visibility change | explicit scoped approval plus content review |
| P3 release identity | tag creation, GitHub Release publish, PyPI/Zenodo release, final release promotion | explicit action-name approval; shorthand prohibited |
| P4 destructive/admin | force-push, history rewrite, user management, systemd stop/delete, port exposure | outside this profile; route to dedicated human-only policy |
| P5 forbidden | `authorized_keys` modification | always deny; no approval path |

Phase 1 implementation target is P1 plus the decision-only portion of P2/P3. It must not execute a push, publish, tag, or release.

## 3. Top three owner use cases

1. **GitHub push/publication gate** — confirm exact repository, ref, commit/diff identity, tests, secret scan, independent AI review, handoff record, and scoped human intent.
2. **Autonomous external-output gate** — gate Discord/article/SNS output using destination, content hash, expiry, kill-switch state, and explicit approval. No background sender in Phase 1.
3. **Production/infrastructure gate** — observe ports/services/users/credential use and route high-risk changes to a separate human-only policy. No system mutation in Phase 1.

Only use case 1 is specified for implementation below; 2 and 3 are extension profiles so the GitHub gate stays small and testable.

## 4. Evidence model

The gate consumes metadata-only evidence records. Raw diffs, logs, secrets, tokens, `.env`, keys, and credentials must never enter Task Tape.

Required pre-confirmation evidence for a candidate action:

- `git_snapshot`: repository ID, branch, HEAD SHA, clean/dirty, ahead/behind, timestamp
- `change_identity`: base SHA, head SHA, diff hash, changed-file count
- `test_summary`: command profile ID, pass/fail/error counts, exit status, head SHA, timestamp
- `secret_scan_summary`: scanner profile/version, findings count by severity, head SHA, timestamp
- `independent_review`: reviewer class, PASS/FAIL, reviewed head SHA and artifact hash, timestamp
- `handoff_review_record`: presence and hash of the matching publication-review record

Required execution-authorization evidence, created only after the candidate passes the pre-confirmation gate:

- `human_approval`: candidate ID, approval ID, action, repository ID, destination/ref, base/head SHA, diff hash, approved/expiry time, and an authenticated human-authority reference. The reference is metadata, never a credential or reusable secret.

Every record must use an allowlisted typed schema. Unknown keys fail closed. Repository-controlled text must be marked untrusted or represented by an opaque ID. Source pointers must be logical allowlisted URIs, never absolute host paths.

## 5. Candidate action schema

```json
{
  "schema": "kagioneko.prepublish_candidate.v1",
  "candidate_id": "pubcand_...",
  "action": "git_push",
  "repo_id": "repo:context-pointer-os",
  "destination_id": "github:kagioneko/context-pointer-os",
  "ref": "refs/heads/feature-name",
  "base_sha": "40-hex",
  "head_sha": "40-hex",
  "diff_hash": "sha256:...",
  "created_at": "RFC3339",
  "expires_at": "RFC3339",
  "evidence_ids": ["evt_..."],
  "execute_automatically": false,
  "requires_human_review": true
}
```

Validation requirements:

- exact field set and types; no extras
- canonical full SHA, canonical ref, allowlisted action enum
- destination is an opaque configured ID, not a credential-bearing URL
- candidate TTL is at most 15 minutes
- all evidence binds to the same repo/head/diff identity
- candidate becomes invalid after any relevant filesystem, index, HEAD, ref, test-profile, scan-profile, review artifact, or policy change

## 6. Gate decision schema

```json
{
  "schema": "kagioneko.prepublish_decision.v1",
  "candidate_id": "pubcand_...",
  "decision": "allow_for_human_confirmation|allow_execution|deny|stale|error",
  "reason_codes": ["ALL_REQUIRED_EVIDENCE_PRESENT"],
  "policy_version": "owner-prepublish-v0.1",
  "evaluated_at": "RFC3339",
  "evidence_set_hash": "sha256:...",
  "execute_automatically": false
}
```

`allow_for_human_confirmation` is emitted by the first evaluation. `allow_execution` may be emitted only by a second evaluation immediately before execution, after atomically validating and consuming a matching approval. `error` covers malformed/corrupt evidence, schema violations, unavailable required validators, and unexpected evaluator failures; it is always non-executable and fail-closed.

No free-form reason is required for machine authorization. Display text is derived from fixed reason codes so attacker-controlled strings cannot become trusted instructions.

## 6.1 Human approval schema

```json
{
  "schema": "kagioneko.human_approval.v1",
  "approval_id": "approval_...",
  "candidate_id": "pubcand_...",
  "action": "git_push",
  "repo_id": "repo:context-pointer-os",
  "destination_id": "github:kagioneko/context-pointer-os",
  "ref": "refs/heads/feature-name",
  "base_sha": "40-hex",
  "head_sha": "40-hex",
  "diff_hash": "sha256:...",
  "approved_at": "RFC3339",
  "expires_at": "RFC3339",
  "authority_ref": "local-human-authority:owner"
}
```

Approval TTL is at most 10 minutes. The approval is stored and consumed by the local approval store and represented on the Event Bus only by a metadata-only `review_decision`; authentication secrets remain outside Task Tape.

## 6.2 Fake-executor record

```json
{
  "schema": "kagioneko.would_execute.v1",
  "candidate_id": "pubcand_...",
  "approval_id": "approval_...",
  "action": "git_push",
  "destination_id": "github:kagioneko/context-pointer-os",
  "ref": "refs/heads/feature-name",
  "head_sha": "40-hex",
  "synthetic_argv_id": "git-push-existing-branch-v1",
  "recorded_at": "RFC3339",
  "executed": false
}
```

This record is written as metadata to the signed scheduler/kernel audit journal, not as raw command output. The Phase 1 fake executor must not spawn subprocesses or call shell, Git, network, connector, or OS execution APIs.

## 7. State machine

```text
DRAFT
  -> EVIDENCE_INCOMPLETE
  -> READY_FOR_REVIEW
  -> AWAITING_HUMAN_CONFIRMATION
  -> REVALIDATING
  -> APPROVED_ONCE
  -> EXECUTING
  -> VERIFIED | FAILED

Any relevant change -> STALE -> EVIDENCE_INCOMPLETE
Any denial/expiry/mismatch -> DENIED
```

Rules:

- approvals are single-use and non-transferable
- approval binds action + repo + destination + ref + head SHA + diff hash
- approval expires; replay is denied
- approval for review/comment does not authorize push
- approval for push does not authorize tag/release
- approval for prerelease does not authorize final release
- a failed execution cannot be retried under the same approval unless the policy explicitly creates a new candidate and asks again
- the second evaluation rechecks repository identity, evidence TTLs, destination/ref, approval binding, and expiry immediately before one atomic approval consume

## 8. Decision rules

The gate returns `deny` or `stale` if any condition holds:

- worktree/index/HEAD differs from the evidence identity
- required test, scan, independent review, or HANDOFF record is absent
- any required result is FAIL/ERROR or refers to another head
- evidence was generated for a different HEAD or diff hash
- evidence age exceeds its configured TTL at evaluation time
- worktree, index, HEAD, or relevant remote-tracking identity changed since evidence generation
- secret scanner reports unresolved findings
- independent review is not PASS/OK
- human instruction is ambiguous, stale, shorthand-only for P2/P3, or targets another action
- remote/destination/ref is unconfigured or changed after approval
- force-push, tag, release, visibility change, or repository deletion is disguised as routine push
- event-chain integrity is unavailable once World Model/Goal Manager consumption is enabled

`allow_for_human_confirmation` means only that the system may show a concrete confirmation prompt. It never means execute.

Test and secret-scan evidence TTL is at most 30 minutes. Independent-review evidence remains usable only while its head SHA, diff hash, artifact hash, policy version, and test/scan profiles match. Destination IDs live in a local closed allowlist mapping opaque public IDs to sanitized remote coordinates and an executor profile. Candidates and Task Tape never contain credential-bearing URLs.

## 9. Human confirmation prompt

The prompt must display fixed metadata:

- action name
- repository/destination ID
- branch/ref
- abbreviated base and head SHA
- changed-file count and diff hash prefix
- test/scan/review status and freshness
- whether the action is public, irreversible, or release-bearing
- approval expiry

For P1, contextual shorthand is valid only as a direct response to the active concrete confirmation prompt and must resolve to that candidate ID; ambiguous conversation such as “進めて” or “looks good” outside that prompt is insufficient. P2/P3 require the explicit action name. An approval for a prior candidate is always insufficient.

## 10. Threat and attack test matrix

Minimum Phase 1 tests:

1. malicious branch name containing prompt injection — stored as untrusted; never rendered as trusted prose
2. unknown top-level and nested evidence fields — rejected
3. secret-like value under a neutral nested key — rejected by closed schema
4. string/bool/NaN/infinite confidence or count values — rejected
5. absolute path or credential-bearing remote URL in source pointers — rejected/redacted before persistence
6. test PASS from another HEAD — stale/deny
7. review PASS from another commit or artifact hash — stale/deny
8. worktree changes after approval — approval invalidated
9. destination/ref swap after approval — denied
10. approval replay — denied
11. “review approved” reused as “push approved” — denied
12. prerelease approval reused for final release — denied
13. shorthand used for tag/release/publication — confirmation required
14. attacker-crafted sensor event claiming all checks passed — rejected unless covered by the existing signed scheduler/kernel journal or a separately reviewed provenance mechanism
15. unsigned Task Tape event consumed as execution authority — denied; current `registry.audit_log` sensor records are evidence only
16. missing/failed scanner — fail closed, not “zero findings”
17. symlink/submodule/worktree ambiguity — unsupported or explicit denial in Phase 1
18. force-push flag hidden in argv/config/alias — denied by exact executor allowlist
19. approval expiry during execution start — denied
20. duplicate concurrent execution using one approval — only one atomic consume succeeds
21. HANDOFF review record missing or hash mismatch — denied
22. public review/comment contains internal path or fake secret marker — publication content scan blocks it

All tests use fake markers and disposable repositories. Real credentials and real public writes are prohibited.

## 11. Phase 1 architecture boundary

Implement only:

- pure typed validators
- evidence freshness and identity matching
- deterministic decision engine
- fixed-code human confirmation summary
- in-memory/disposable approval consume semantics
- fake executor that records `WOULD_EXECUTE` metadata

Do not implement in Phase 1:

- live `git push`
- GitHub API writes
- tag/release creation
- Vault reads
- background daemon or cron
- production/systemd/port/user operations
- automatic retries
- World Model or Goal Manager action authority

## 12. Phase 1 completion criteria

Phase 1 is complete only when:

- schemas and reason codes are documented and closed
- all 22 attack cases pass using disposable repos/fake values
- unit tests cover every state transition and fail-closed path
- property/fuzz tests cover unknown fields, malformed refs/SHAs/timestamps, and approval replay
- no raw diff/stdout/stderr/credential value is persisted
- fake executor is the only executor and proves zero external writes
- fake executor performs no subprocess, shell, Git, network, connector, or OS execution call
- existing CPOS regression suite passes unchanged
- an independent AI CLI reviews security and quality with PASS/OK
- review result and target commit/hash are recorded in HANDOFF
- owner reviews the demo and explicitly authorizes any Phase 2 work

The candidate, decision, and approval records are typed payloads carried by the existing `kagioneko.cognitive_event.v1` concepts (`action_proposal` and `review_decision`), not a parallel Event Bus. Signed execution decisions belong in the existing scheduler/kernel journal; unsigned sensor Task Tape records cannot confer authority.

## 13. Phase 2 gate

Phase 2 may add a real executor only after a separate design/review. It must use an exact argv allowlist, credential retrieval at execution time from Vault-compatible runtime handling, atomic single-use approval consumption, post-action verification, and an immediate kill switch. Real public actions remain human-confirmed.

## 14. Extension profiles

### External-output profile

Bind approval to destination ID, payload hash, visibility, scheduled time, and kill-switch state. Editing content or destination invalidates approval. Discord/Zenn/note/SNS connectors remain separate executors.

### Infrastructure profile

Classify observe/read, reversible change, destructive change, and forbidden action. Port opening requires timed auto-close plus notification. User creation/deletion and systemd stop/delete require prior human confirmation. `authorized_keys` modification is permanently denied.

## 15. Owner decisions captured

- Start with GitHub push/publication safety, not broad autonomy.
- Keep Phase 1 read-only/decision-only with a fake executor.
- Reuse existing Sensor/Event Bus/Human Escalation concepts rather than invent a parallel architecture.
- Treat contributor Git sensor events as untrusted evidence until integrity/provenance gates are implemented.
- Preserve the human owner as the final authority for public and high-risk operations.
