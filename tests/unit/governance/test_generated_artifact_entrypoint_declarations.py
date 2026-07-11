from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy.artifacts import generated_artifact_entrypoint_audit

if TYPE_CHECKING:
    from pathlib import Path


def _write_pyproject(root: Path, body: str) -> None:
    root.joinpath("pyproject.toml").write_text(body, encoding="utf-8")


def test_pyproject_declarative_cleanup_and_ignore_paths_are_not_producers(
    tmp_path: Path,
) -> None:
    _write_pyproject(
        tmp_path,
        """
[tool.adopter.local_state]
cleanup_paths = [
  ".mypy_cache",
  ".pytest_cache",
  ".ruff_cache",
  "dist",
]
gitignore_patterns = [
  "dist/",
]
markdown_ignore_globs = [
  "dist/**",
]

[tool.ruff]
extend-exclude = ["dist"]
""",
    )

    audit = generated_artifact_entrypoint_audit(tmp_path)

    assert audit["ok"] is True
    assert audit["required_gaps"] == []


def test_pyproject_executable_task_still_blocks_denied_generated_home(
    tmp_path: Path,
) -> None:
    _write_pyproject(
        tmp_path,
        """
[tool.pixi.tasks]
package = "uv build --out-dir dist/python"
""",
    )

    audit = generated_artifact_entrypoint_audit(tmp_path)

    assert audit["ok"] is False
    assert audit["required_gaps"] == [
        "generated_artifact_entrypoint_denied_generated_home:pyproject.toml:dist/"
    ]


def test_pyproject_structured_task_command_is_audited(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        """
[tool.pixi.tasks]
package = { cmd = ["uv", "build", "--out-dir", "dist/python"] }
""",
    )

    audit = generated_artifact_entrypoint_audit(tmp_path)

    assert audit["ok"] is False
    assert audit["required_gaps"] == [
        "generated_artifact_entrypoint_denied_generated_home:pyproject.toml:dist/"
    ]


def test_malformed_pyproject_falls_back_to_conservative_text_audit(
    tmp_path: Path,
) -> None:
    _write_pyproject(
        tmp_path,
        '[tool.pixi.tasks\npackage = "uv build --out-dir dist/python"\n',
    )

    audit = generated_artifact_entrypoint_audit(tmp_path)

    assert audit["ok"] is False
    assert audit["required_gaps"] == [
        "generated_artifact_entrypoint_denied_generated_home:pyproject.toml:dist/"
    ]
