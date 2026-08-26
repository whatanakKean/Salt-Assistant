from salt_assistant.validator import validate


def test_valid_state_passes():
    result = validate("nginx:\n  pkg.installed: []\n", "install nginx")
    assert result.passed


def test_dangerous_module_is_blocked():
    result = validate("change:\n  cmd.run:\n    - name: rm -rf /\n", "remove files")
    assert not result.passed
    assert any("not allowed" in error for error in result.errors)


def test_secret_pattern_is_blocked():
    result = validate("config:\n  file.managed:\n    - password: unsafe\n", "configure a file")
    assert not result.passed


def test_service_restart_module_is_allowed():
    result = validate(
        "restart_nginx:\n  module.run:\n  - name: service.restart\n    m_name: nginx\n",
        "restart nginx",
    )
    assert result.passed


def test_arbitrary_module_run_is_blocked():
    result = validate(
        "change:\n  module.run:\n  - name: file.delete\n    path: /tmp/file\n",
        "delete a file",
    )
    assert not result.passed
