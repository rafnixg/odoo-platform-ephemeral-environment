from importlib.resources import files
from pathlib import Path

import yaml


def test_runtime_resources_are_packaged() -> None:
    package = files("mini_runbot")

    assert package.joinpath("templates/compose.yaml.j2").is_file()
    assert package.joinpath("resources/config.example.yaml").is_file()
    assert package.joinpath("web/index.html").is_file()


def test_bundled_and_repository_example_configs_match() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    root_example = yaml.safe_load(
        (repository_root / "config.example.yaml").read_text(encoding="utf-8")
    )
    bundled_example = yaml.safe_load(
        files("mini_runbot")
        .joinpath("resources/config.example.yaml")
        .read_text(encoding="utf-8")
    )

    assert bundled_example == root_example
