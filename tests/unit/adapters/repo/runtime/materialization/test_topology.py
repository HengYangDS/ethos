"""Runtime materialization semantic and physical ownership contracts."""

from importlib import import_module

from tests.support.runtime_scenarios import REPOSITORY_ROOT


def test_runtime_materialization_uses_semantic_subpackage_without_flat_incumbent() -> None:
    """Require one physical owner for each runtime-materialization concept."""
    modules = {
        "dependency_supply": (
            "prepare_locked_requirements",
            "install_locked_runtime",
            "project_dependency_supply",
        ),
        "input_resolution": (
            "is_selected_runtime_source",
            "resolve_runtime_wheel",
            "require_runtime_wheel_provenance",
        ),
        "python_environment": (
            "observe_python_facts",
            "observe_runtime_environment",
            "python_image_source_capable",
            "require_python_image_source",
        ),
        "python_image": ("materialize_python_image", "render_console_script"),
        "effect": ("materialize_runtime",),
    }
    for module_name, public_names in modules.items():
        module = import_module(f"ethos.adapters.repo.runtime.materialization.{module_name}")
        assert all(hasattr(module, name) for name in public_names)
    assert not (REPOSITORY_ROOT / "src/ethos/adapters/repo/hook_runtime_install.py").exists()
    assert not (REPOSITORY_ROOT / "tools/ci/delivery/supply.py").exists()


def test_python_path_identity_has_one_semantic_owner() -> None:
    """Runtime construction and observation consume one Python path semantics."""
    effect = import_module("ethos.adapters.repo.runtime.materialization.effect")
    environment = import_module("ethos.adapters.repo.runtime.materialization.python_environment")
    image = import_module("ethos.adapters.repo.runtime.materialization.python_image")

    assert effect.same_python_path is environment.same_python_path
    assert image.same_python_path is environment.same_python_path
    assert image.python_path_within is environment.python_path_within
    assert image.python_image_source_capable is environment.python_image_source_capable
    assert not hasattr(effect, "_same_runtime_path")
