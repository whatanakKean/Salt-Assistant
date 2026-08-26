from unittest.mock import patch

import pytest

from salt_assistant.salt_client import SaltClient, SaltClientError


def test_target_resolution_uses_salt_json():
    with patch.object(SaltClient, "_run", return_value='{"web2": true, "web1": true}'):
        assert SaltClient().resolve_target("web*") == ["web1", "web2"]


def test_target_resolution_rejects_empty_result():
    with patch.object(SaltClient, "_run", return_value="{}"):
        with pytest.raises(SaltClientError, match="matched no reachable minions"):
            SaltClient().resolve_target("web*")