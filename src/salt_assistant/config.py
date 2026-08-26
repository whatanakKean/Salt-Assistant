import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name and name not in os.environ:
            os.environ[name] = value


@dataclass(frozen=True)
class Settings:
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_timeout: int = 60
    salt_command: str = "salt"
    salt_config_dir: str | None = None
    salt_file_root: str | None = None
    state_output_dir: str = "salt/states"
    audit_log: str = "logs/salt-assistant.log"
    salt_timeout: int = 30
    max_minions_affected: int = 50

    @classmethod
    def from_environment(cls) -> "Settings":
        _load_dotenv()
        required = {
            "OPENAI_BASE_URL": os.getenv("OPENAI_BASE_URL"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "OPENAI_MODEL": os.getenv("OPENAI_MODEL"),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"Missing required LLM configuration: {', '.join(missing)}")
        return cls(
            llm_base_url=required["OPENAI_BASE_URL"].rstrip("/"),
            llm_api_key=required["OPENAI_API_KEY"],
            llm_model=required["OPENAI_MODEL"],
            llm_timeout=int(os.getenv("LLM_TIMEOUT", "60")),
            salt_command=os.getenv("SALT_COMMAND", "salt"),
            salt_config_dir=os.getenv("SALT_CONFIG_DIR") or None,
            salt_file_root=os.getenv("SALT_FILE_ROOT") or None,
            state_output_dir=os.getenv("SALT_STATE_DIR", "salt/states"),
            audit_log=os.getenv("AUDIT_LOG", "logs/salt-assistant.log"),
            salt_timeout=int(os.getenv("SALT_TIMEOUT", "30")),
            max_minions_affected=int(os.getenv("MAX_MINIONS_AFFECTED", "50")),
        )