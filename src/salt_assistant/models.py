from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Context:
    source: str
    collected_at: str
    minions: list[str]
    roles: dict[str, list[str]]
    operating_systems: dict[str, str]


@dataclass
class ValidationResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    risk_level: str = "low"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineResult:
    status: str
    prompt: str
    target: str
    context: Context
    state: str
    validation: ValidationResult
    dry_run: dict[str, Any]
    assumptions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["context"] = asdict(self.context)
        result["validation"] = self.validation.as_dict()
        return result
