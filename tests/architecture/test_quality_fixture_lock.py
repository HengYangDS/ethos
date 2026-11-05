"""The quality fixture's sessions run in the repository's environment, so both locks agree."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/quality-sample/uv.lock"


def _locked(path: Path) -> dict[str, str]:
    """Each locked package's version; the editable project itself has none."""
    packages = tomllib.loads(path.read_text(encoding="utf-8"))["package"]
    return {item["name"]: item["version"] for item in packages if "version" in item}


def test_the_quality_fixture_locks_the_repository_versions() -> None:
    """A lock move that leaves the fixture behind fails here, naming both versions."""
    repository, fixture = _locked(ROOT / "uv.lock"), _locked(FIXTURE)
    shared = sorted(set(fixture) & set(repository))
    assert shared, "the fixture shares no locked package with the repository"
    drift = {
        name: f"fixture {fixture[name]}, repository {repository[name]}"
        for name in shared
        if fixture[name] != repository[name]
    }
    assert drift == {}
