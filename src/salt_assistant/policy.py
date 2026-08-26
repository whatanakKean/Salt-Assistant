from .models import Context, ValidationResult


def validate_context(context: Context, max_minions: int) -> ValidationResult:
    result = ValidationResult(passed=True)
    if len(context.minions) > max_minions:
        result.passed = False
        result.risk_level = "high"
        result.errors.append(
            f"Target resolves to {len(context.minions)} minions, exceeding the policy limit of {max_minions}."
        )
    if not context.minions:
        result.passed = False
        result.risk_level = "medium"
        result.errors.append("Target resolved to no reachable minions.")
    return result