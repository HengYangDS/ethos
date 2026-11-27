"""Runtime materialization semantic and physical ownership contracts."""

from importlib import import_module


def test_python_path_identity_has_one_semantic_owner() -> None:
    """Runtime construction and observation consume one Python path semantics."""
    effect = import_module("ethos.adapters.repo.runtime.materialization.effect")
    environment = import_module("ethos.adapters.repo.runtime.materialization.python_environment")
    image = import_module("ethos.adapters.repo.runtime.materialization.python_image")

    assert effect.same_python_path is environment.same_python_path
    assert image.same_python_path is environment.same_python_path
    assert image.python_path_within is environment.python_path_within
    assert image.python_image_source_capable is environment.python_image_source_capable
