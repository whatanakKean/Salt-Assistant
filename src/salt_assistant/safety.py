import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import PipelineResult


def state_hash(state: str) -> str:
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def write_audit(result: PipelineResult, path: Path) -> None:
    record: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "tool_version": "0.1.0",
        "prompt": result.prompt,
        "target": result.target,
        "context_source": result.context.source,
        "context_minions": result.context.minions,
        "state_hash": state_hash(result.state),
        "validation": result.validation.as_dict(),
        "dry_run": result.dry_run,
        "status": result.status,
    }
    with path.open("a", encoding="utf-8") as audit_file:
        audit_file.write(json.dumps(record, sort_keys=True) + "\n")
