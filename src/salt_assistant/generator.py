import json

import yaml

from .llm_client import LLMClient, LLMClientError
from .models import Context


class GenerationError(ValueError):
    pass


class Generator:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def generate(self, prompt: str, context: Context) -> tuple[str, list[str]]:
        system_prompt = (
            "You generate SaltStack states for infrastructure operators. Return JSON only with keys "
            "states (a YAML-compatible mapping), assumptions (an array of strings), and required_files (an array). "
            "Use only Salt state modules, never credentials or arbitrary shell commands, and never invent context."
        )
        user_prompt = json.dumps(self._llm_request(prompt, context))
        try:
            response = self.llm_client.complete(system_prompt, user_prompt)
            document = json.loads(response)
        except (LLMClientError, json.JSONDecodeError) as error:
            raise GenerationError(f"LLM generation failed: {error}") from error
        if "```" in response or not isinstance(document, dict) or not isinstance(document.get("states"), dict):
            raise GenerationError("LLM response must be JSON with a states mapping and no Markdown fences")
        document["states"] = self._normalize_states(document["states"])
        assumptions = document.get("assumptions", [])
        if not isinstance(assumptions, list) or not all(isinstance(item, str) for item in assumptions):
            raise GenerationError("LLM assumptions must be an array of strings")
        return yaml.safe_dump(document["states"], sort_keys=False), assumptions

    @staticmethod
    def _llm_request(prompt: str, context: Context) -> dict:
        """Return only fields approved for transmission to the external model."""
        return {
            "request": prompt,
            "target_minions": list(context.minions),
            "operating_systems": dict(context.operating_systems),
        }

    @staticmethod
    def _normalize_states(states: dict) -> dict:
        normalized = {}
        for state_id, declarations in states.items():
            if not isinstance(declarations, dict):
                normalized[state_id] = declarations
                continue
            for module, arguments in declarations.items():
                normalized_id = state_id if state_id not in normalized else f"{state_id}_{module.split('.', 1)[0]}"
                if isinstance(arguments, dict):
                    arguments = [] if not arguments else [{key: value} for key, value in arguments.items()]
                normalized[normalized_id] = {module: arguments}
        return normalized
