import re
from typing import Any

import yaml

from .models import ValidationResult


ALLOWED_MODULES = {"pkg.installed", "pkg.uptodate", "service.running", "service.dead", "file.managed", "file.replace"}


def validate(state: str, prompt: str) -> ValidationResult:
    result = ValidationResult(passed=True)
    try:
        document = yaml.safe_load(state)
    except yaml.YAMLError as error:
        result.errors.append(f"Invalid YAML: {error}")
        result.passed = False
        return result
    if not isinstance(document, dict) or not document:
        result.errors.append("State must be a non-empty YAML mapping.")
        result.passed = False
        return result
    for state_id, body in document.items():
        if not isinstance(state_id, str) or not isinstance(body, dict):
            result.errors.append(f"State {state_id!r} must map to a state declaration.")
            continue
        for module, arguments in body.items():
            if module not in ALLOWED_MODULES and not _is_allowed_service_restart(module, arguments):
                result.errors.append(f"Module {module!r} is not allowed by the MVP policy.")
    dangerous_patterns = [r"\bcmd\.run\b", r"\bshell\.run\b", r"(?:password|token|secret|private[_ -]?key)\s*:"]
    for pattern in dangerous_patterns:
        if re.search(pattern, state, re.IGNORECASE):
            result.errors.append(f"Potentially unsafe content matched policy: {pattern}")
    if "ssh" in prompt.lower() or result.errors:
        result.risk_level = "high" if "ssh" in prompt.lower() else "medium"
    result.passed = not result.errors
    return result


def _is_allowed_service_restart(module: str, arguments: Any) -> bool:
    if module != "module.run" or not isinstance(arguments, list):
        return False
    values = {key: value for item in arguments if isinstance(item, dict) for key, value in item.items()}
    return values.get("name") == "service.restart" and isinstance(values.get("m_name"), str)
