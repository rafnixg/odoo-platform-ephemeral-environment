import pytest
from pydantic import ValidationError

from mini_runbot.domain.validation import CreateBuildRequest


@pytest.mark.parametrize("module", ["../escape", "UPPER", "bad-name", "x/y"])
def test_rejects_unsafe_module_names(module: str) -> None:
    with pytest.raises(ValidationError):
        CreateBuildRequest(repository="custom", ref="16.0", modules=[module])


@pytest.mark.parametrize("ref", ["../main", "/main", "main..evil", "main\\evil", "main/"])
def test_rejects_unsafe_refs(ref: str) -> None:
    with pytest.raises(ValidationError):
        CreateBuildRequest(repository="custom", ref=ref, modules=["base"])

