from pathlib import Path

import pytest

from mini_runbot.config import Settings
from mini_runbot.domain.errors import ConfigurationError


def test_rejects_duplicate_checkout_targets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "config.yaml"
    config.write_text(
        """
repositories:
  oca:
    url: https://github.com/OCA/e-commerce.git
    target: shared
  custom:
    url: https://github.com/example/custom.git
    target: shared
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("MINI_RUNBOT_CONFIG", str(config))

    with pytest.raises(ConfigurationError, match="use the same target"):
        Settings.from_environment()


def test_rejects_negative_cleanup_interval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "config.yaml"
    config.write_text("cleanup_interval_seconds: -1\n", encoding="utf-8")
    monkeypatch.setenv("MINI_RUNBOT_CONFIG", str(config))

    with pytest.raises(ConfigurationError, match="zero or positive"):
        Settings.from_environment()
