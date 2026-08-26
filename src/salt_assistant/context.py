from datetime import UTC, datetime

from .salt_client import SaltClient
from .models import Context


class ContextProvider:
    """Collects minimized context from a live Salt environment."""

    def __init__(self, salt_client: SaltClient | None = None):
        self.salt_client = salt_client or SaltClient()

    def collect(self, target: str) -> Context:
        minions, operating_systems = self.salt_client.collect_context(target)
        return Context(
            source="salt (live)",
            collected_at=datetime.now(UTC).isoformat(),
            minions=minions,
            roles={},
            operating_systems=operating_systems,
        )
