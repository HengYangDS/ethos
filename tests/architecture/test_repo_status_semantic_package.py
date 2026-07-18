from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO_ADAPTER = ROOT / "packages/ethos/src/ethos/adapters/repo"


def test_repo_status_binding_helpers_live_inside_status_semantic_package() -> None:
    """Repo status bindings live under the status semantic package, not suffix-flat."""
    assert not (REPO_ADAPTER / "status.py").exists()
    assert not (REPO_ADAPTER / "status_bindings.py").exists()
    assert (REPO_ADAPTER / "status/__init__.py").is_file()
    assert (REPO_ADAPTER / "status/core.py").is_file()
    assert (REPO_ADAPTER / "status/bindings.py").is_file()
