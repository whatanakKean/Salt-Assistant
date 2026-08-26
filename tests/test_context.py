from salt_assistant.context import ContextProvider
from salt_assistant.models import Context
from salt_assistant.policy import validate_context


class FakeSaltClient:
    def collect_context(self, target):
        return ["web1", "web2"], {"web1": "Ubuntu", "web2": "Ubuntu"}


def test_live_context_uses_salt_client():
    context = ContextProvider(FakeSaltClient()).collect("web*")
    assert context.source == "salt (live)"
    assert context.minions == ["web1", "web2"]


def test_context_policy_blocks_empty_target():
    context = Context(source="salt (live)", collected_at="now", minions=[], roles={}, operating_systems={})
    result = validate_context(context, max_minions=50)
    assert not result.passed
