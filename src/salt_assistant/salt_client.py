import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


class SaltClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class SaltPreview:
    passed: bool
    output: str
    minions_affected: int


class SaltClient:
    def __init__(self, command: str = "salt", timeout: int = 30, file_root: str | None = None, config_dir: str | None = None):
        self.command = command
        self.timeout = timeout
        self.file_root = Path(file_root) if file_root else None
        self.config_dir = config_dir

    def resolve_target(self, target: str) -> list[str]:
        try:
            response = self._run(self._salt_args(["-C", target, "test.ping", "--out=json"]))
        except SaltClientError as error:
            if "{}" in str(error):
                raise SaltClientError(
                    f"Target {target!r} matched no reachable minions. "
                    "Run 'salt-key -L' or 'salt '*' test.ping' to inspect available targets."
                ) from error
            raise
        try:
            data = json.loads(response)
        except json.JSONDecodeError as error:
            raise SaltClientError("Salt returned non-JSON target data") from error
        minions = sorted(str(minion) for minion, reachable in data.items() if reachable)
        if not minions:
            raise SaltClientError(
                f"Target {target!r} matched no reachable minions. "
                "Run 'salt-key -L' or 'salt '*' test.ping' to inspect available targets."
            )
        return minions

    def collect_context(self, target: str) -> tuple[list[str], dict[str, str]]:
        minions = self.resolve_target(target)
        if not minions:
            return [], {}
        response = self._run(self._salt_args(["-C", target, "grains.item", "os", "--out=json"]))
        try:
            data = json.loads(response)
        except json.JSONDecodeError as error:
            raise SaltClientError("Salt returned non-JSON grain data") from error
        operating_systems = {
            str(minion): str(values.get("os", "unknown"))
            for minion, values in data.items()
            if isinstance(values, dict)
        }
        return minions, operating_systems

    def test_state(self, target: str, state: str) -> SaltPreview:
        if self.file_root is None:
            raise SaltClientError("SALT_FILE_ROOT is required for real Salt test mode")
        state_path = self.file_root / "salt_assistant_preview.sls"
        self._write_state(state_path, state)
        try:
            output = self._run(self._salt_args(["-C", target, "state.sls", "salt_assistant_preview", "test=True"]))
        finally:
            state_path.unlink(missing_ok=True)
        minions = self.resolve_target(target)
        return SaltPreview(passed=True, output=output, minions_affected=len(minions))

    def apply_state(self, target: str, state: str) -> str:
        if self.file_root is None:
            raise SaltClientError("SALT_FILE_ROOT is required for real execution")
        state_path = self.file_root / "salt_assistant_apply.sls"
        self._write_state(state_path, state)
        try:
            return self._run(self._salt_args(["-C", target, "state.sls", "salt_assistant_apply", "test=False"]))
        finally:
            state_path.unlink(missing_ok=True)

    def _run(self, command: list[str]) -> str:
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=self.timeout, check=False)
        except FileNotFoundError as error:
            raise SaltClientError(f"Salt command not found: {self.command}") from error
        except subprocess.TimeoutExpired as error:
            raise SaltClientError(f"Salt command timed out after {self.timeout}s") from error
        if completed.returncode != 0:
            details = [value.strip() for value in (completed.stderr, completed.stdout) if value.strip()]
            detail = "\n".join(details) or "unknown Salt error"
            raise SaltClientError(detail)
        return completed.stdout

    def _salt_args(self, arguments: list[str]) -> list[str]:
        command = [self.command]
        if self.config_dir:
            command.extend(["-c", self.config_dir])
        return command + arguments

    def _write_state(self, path: Path, state: str) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(state, encoding="utf-8")
        except OSError as error:
            raise SaltClientError(f"Salt file root is not writable: {path.parent}: {error}") from error