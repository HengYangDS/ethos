"""Runtime materialization semantic and physical ownership contracts."""

from importlib import import_module

from tests.support.runtime_scenarios import REPOSITORY_ROOT


def test_runtime_materialization_uses_semantic_subpackage_without_flat_incumbent() -> None:
    """Require one physical owner for each runtime-materialization concept."""
    modules = {
        "input_resolution": (
            "resolve_runtime_wheel",
            "require_runtime_wheel_provenance",
            "resolve_owned_interpreter",
        ),
        "python_environment": ("observe_python_facts", "observe_runtime_environment"),
        "python_image": ("materialize_python_image", "render_console_script"),
        "effect": ("materialize_runtime",),
    }
    for module_name, public_names in modules.items():
        module = import_module(f"ethos.adapters.repo.runtime.materialization.{module_name}")
        assert all(hasattr(module, name) for name in public_names)
    assert not (REPOSITORY_ROOT / "src/ethos/adapters/repo/hook_runtime_install.py").exists()
