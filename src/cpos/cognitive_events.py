"""[CPOS Phase 1] Sensor event envelope and Task Tape adapter.

Implements only the part of `docs/EVENT_BUS_AND_WORLD_MODEL_SPEC.md` and
`docs/SENSOR_AND_GOAL_MANAGER_SPEC.md` that the Git sensor needs: the
`kagioneko.sensor_event.v1` record shape, its safety invariants, and the
adapter that writes conforming records onto the CPOS Task Tape.

Out of scope here: the Goal Manager, the World Model, and the other
`kagioneko.cognitive_event.v1` event types. This module exists so the
Event Bus boundary is a named seam rather than an implicit one, not to
start those components.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

SENSOR_EVENT_SCHEMA = "kagioneko.sensor_event.v1"

# Task Tape event name for a recorded sensor observation, from the
# "Suggested CPOS event names" list in the Event Bus spec.
TAPE_SENSOR_EVENT = "cognitive_sensor_event_recorded"

RISK_LEVELS = ("low", "medium", "high", "critical")

# Every field the Event Bus spec pins to a fixed value for a metadata-only
# sensor record. These are invariants of the Phase 1 sensor layer, not
# per-event choices, so the builder sets them and the validator enforces them.
SAFETY_INVARIANTS = {
    "metadata_only": True,
    "raw_request_stored": False,
    "raw_diff_stored": False,
    "raw_outputs_stored": False,
    "secret_values_stored": False,
    "execute_automatically": False,
}

REQUIRED_FIELDS = (
    "schema", "event_id", "event_type", "sensor_event_type", "source",
    "observed_at", "subject", "summary", "risk", "confidence",
    "source_of_truth", "requires_human_review", "suggested_next_action",
)

# The spec's core rule is that events are evidence pointers, not evidence
# dumps. An observation payload carrying any of these substrings in a key is
# a raw-output log leaking into the tape, so it is rejected at the boundary.
DENIED_OBSERVATION_KEY_PARTS = (
    "raw", "stdout", "stderr", "diff", "patch", "body", "content",
    "secret", "token", "password", "credential", "key", "env",
)


class SensorEventContractError(ValueError):
    """A record does not conform to `kagioneko.sensor_event.v1`."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def build_sensor_event(
    *,
    sensor_event_type: str,
    source: str,
    subject: str,
    summary: str,
    risk: str = "low",
    confidence: float = 1.0,
    source_of_truth: Optional[List[str]] = None,
    requires_human_review: bool = False,
    suggested_next_action: str = "continue_observing",
    observed_at: Optional[str] = None,
    observation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build one `kagioneko.sensor_event.v1` record.

    `observation` is an additive extension: the spec envelope has no slot for
    the state labels and counts it tells sensors to store, so they live in a
    sub-object rather than being flattened into fields the spec names.
    """
    event = {
        "schema": SENSOR_EVENT_SCHEMA,
        "event_id": f"sensor_evt_{uuid.uuid4().hex[:16]}",
        # Constant per the Event Bus spec: the concrete observation goes in
        # `sensor_event_type`, never in `event_type`.
        "event_type": "sensor_event",
        "sensor_event_type": sensor_event_type,
        "source": source,
        "observed_at": observed_at or _now_iso(),
        "subject": subject,
        "summary": summary,
        "risk": risk,
        "confidence": confidence,
        "source_of_truth": list(source_of_truth or []),
        "requires_human_review": requires_human_review,
        "suggested_next_action": suggested_next_action,
        **SAFETY_INVARIANTS,
    }
    if observation is not None:
        event["observation"] = dict(observation)
    validate_sensor_event(event)
    return event


def validate_sensor_event(event: Dict[str, Any]) -> None:
    """Reject anything that is not a conforming metadata-only sensor record."""
    missing = [f for f in REQUIRED_FIELDS if f not in event]
    if missing:
        raise SensorEventContractError(f"missing required fields: {missing}")
    if event["schema"] != SENSOR_EVENT_SCHEMA:
        raise SensorEventContractError(f"unexpected schema: {event['schema']!r}")
    if event["event_type"] != "sensor_event":
        raise SensorEventContractError(
            f"event_type must be 'sensor_event', got {event['event_type']!r}"
        )
    if not event["sensor_event_type"]:
        raise SensorEventContractError("sensor_event_type must be concrete")
    if not event["source"]:
        raise SensorEventContractError("source must name a concrete sensor")
    if event["risk"] not in RISK_LEVELS:
        raise SensorEventContractError(f"unknown risk level: {event['risk']!r}")
    if not 0.0 <= float(event["confidence"]) <= 1.0:
        raise SensorEventContractError("confidence must be within 0.0..1.0")
    for field, expected in SAFETY_INVARIANTS.items():
        if event.get(field) is not expected:
            raise SensorEventContractError(
                f"safety field {field} must be {expected}, got {event.get(field)!r}"
            )
    for key in (event.get("observation") or {}):
        lowered = key.lower()
        if any(part in lowered for part in DENIED_OBSERVATION_KEY_PARTS):
            raise SensorEventContractError(
                f"observation key {key!r} looks like raw evidence, not metadata"
            )


def task_tape_sink(registry, pointer_id_for: Any = None):
    """Adapter: publish conforming sensor events onto the CPOS Task Tape.

    Phase 1 substrate is `registry.audit_log` via `registry._log_event`, which
    the Event Bus spec permits as a first persistence substrate. The record
    written is the sensor envelope itself, so swapping the substrate later does
    not change the contract. Non-conforming records are refused rather than
    written, which keeps the tape evidence metadata instead of an output log.
    """
    def _sink(event: Dict[str, Any]) -> None:
        validate_sensor_event(event)
        pointer_id = (
            pointer_id_for(event) if callable(pointer_id_for)
            else (pointer_id_for or event["source"])
        )
        registry._log_event(TAPE_SENSOR_EVENT, pointer_id, event)
    return _sink
