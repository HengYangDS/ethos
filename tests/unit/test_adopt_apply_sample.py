from __future__ import annotations

from pathlib import Path

from ethos_adopt import adoption_plan, detect_repo_profile


def test_detect_repo_profile_for_python_package(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")

    assert detect_repo_profile(tmp_path) == "python-package"


def test_adopt_apply_writes_expected_files(tmp_path: Path) -> None:
    result = adoption_plan(tmp_path, apply=True)

    assert result["applied"] is True
    assert (tmp_path / ".ethos/project.toml").exists()
    assert f'name = "{tmp_path.name}"' in (tmp_path / ".ethos/project.toml").read_text(
        encoding="utf-8"
    )
    assert (tmp_path / ".ethos/state/.gitignore").read_text(encoding="utf-8").startswith("*")
