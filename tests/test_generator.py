import pytest

from salt_assistant.context import ContextProvider
from salt_assistant.generator import GenerationError, Generator


class FakeLLM:
    def complete(self, system_prompt, user_prompt):
        return '{"states": {"nginx": {"pkg.installed": []}}, "assumptions": []}'


def test_llm_request_contains_only_allowlisted_context():
    context = ContextProvider(FakeSalt()).collect("*")
    request = Generator._llm_request("install nginx", context)
    assert set(request) == {"request", "target_minions", "operating_systems"}
    assert "source" not in request


class MultiModuleLLM:
    def complete(self, system_prompt, user_prompt):
        return '{"states": {"nginx": {"pkg.installed": {}, "service.running": {"enable": true}}}, "assumptions": []}'


class FakeSalt:
    def collect_context(self, target):
        return ["web1"], {"web1": "Ubuntu"}


def test_package_state_is_generated_from_llm():
    state, _ = Generator(FakeLLM()).generate("install nginx", ContextProvider(FakeSalt()).collect("*"))
    assert "pkg.installed" in state


def test_multi_module_state_is_split_for_salt():
    state, _ = Generator(MultiModuleLLM()).generate("install nginx", ContextProvider(FakeSalt()).collect("*"))
    assert "nginx:" in state
    assert "nginx_service:" in state
    assert "pkg.installed: []" in state


def test_invalid_llm_response_is_blocked():
    class InvalidLLM:
        def complete(self, system_prompt, user_prompt):
            return "not json"

    with pytest.raises(GenerationError):
        Generator(InvalidLLM()).generate("install nginx", ContextProvider(FakeSalt()).collect("*"))