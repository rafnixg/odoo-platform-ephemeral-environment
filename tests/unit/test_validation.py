import pytest
from pydantic import ValidationError

from mini_runbot.domain.validation import CreateBuildRequest, RequestedRepository


@pytest.mark.parametrize("module", ["../escape", "UPPER", "bad-name", "x/y"])
def test_rejects_unsafe_module_names(module: str) -> None:
    with pytest.raises(ValidationError):
        CreateBuildRequest(repository="custom", ref="16.0", modules=[module])


@pytest.mark.parametrize(
    "ref", ["../main", "/main", "-option", "main..evil", "main\\evil", "main/"]
)
def test_rejects_unsafe_refs(ref: str) -> None:
    with pytest.raises(ValidationError):
        CreateBuildRequest(repository="custom", ref=ref, modules=["base"])


def test_accepts_multiple_repositories_with_independent_refs() -> None:
    request = CreateBuildRequest(
        repositories=[
            RequestedRepository(repository="oca", ref="16.0"),
            RequestedRepository(repository="custom", ref="feature/multi"),
        ],
        modules=["base"],
    )

    assert [(item.repository, item.ref) for item in request.selected_repositories] == [
        ("oca", "16.0"),
        ("custom", "feature/multi"),
    ]


def test_rejects_duplicate_repository_aliases() -> None:
    with pytest.raises(ValidationError, match="repository aliases must be unique"):
        CreateBuildRequest(
            repositories=[
                RequestedRepository(repository="custom", ref="16.0"),
                RequestedRepository(repository="custom", ref="feature/other"),
            ],
            modules=["base"],
        )


def test_rejects_mixed_legacy_and_multi_repository_fields() -> None:
    with pytest.raises(ValidationError, match="use either repository/ref or repositories"):
        CreateBuildRequest(
            repository="custom",
            ref="16.0",
            repositories=[RequestedRepository(repository="oca", ref="16.0")],
            modules=["base"],
        )
