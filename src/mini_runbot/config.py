import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    builds_root: Path

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            database_url=os.getenv("MINI_RUNBOT_DATABASE_URL", "sqlite:///./mini_runbot.db"),
            builds_root=Path(os.getenv("MINI_RUNBOT_BUILDS_ROOT", "./builds")),
        )

