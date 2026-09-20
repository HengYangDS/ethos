"""Resolve native artifact entrypoints without granting authority to unbound tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.artifact_entrypoints import generated_artifact_entrypoint_audit

if TYPE_CHECKING:
    from pathlib import Path


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.mark.parametrize(
    ("document", "verdict"),
    [
        ("[tool.pixi.tasks\npackage = 'uv build --out-dir dist/wheel'\n", "block"),
        ("[project]\nname = 'sample'\n", "pass"),
        ("[tool.pixi]\ntasks = 'not-a-table'\n", "pass"),
        ("[tool.pixi.tasks]\na = 'echo ok'\n", "pass"),
        ("[tool.pixi.tasks]\na = ['echo', 'ok']\n", "pass"),
        ("[tool.pixi.tasks]\na = 7\n", "pass"),
        ("[tool.pixi.tasks.a]\ncmd = 'echo ok'\n", "pass"),
        ("[tool.pixi.tasks.a]\ncommand = ['echo', 'ok']\n", "pass"),
        ("[tool.pixi.tasks.a]\nother = 'ignored'\n", "pass"),
    ],
)
def test_entrypoint_audit_handles_every_public_pixi_task_shape(
    tmp_path: Path, document: str, verdict: str
) -> None:
    _write(tmp_path, "pyproject.toml", document)

    assert generated_artifact_entrypoint_audit(tmp_path)["verdict"] == verdict


@pytest.mark.parametrize(
    ("relative", "text", "gap"),
    [
        (
            ".config/checks/pytest/pytest.toml",
            '[pytest]\ncache_dir = ".pytest_cache"\n',
            "generated_artifact_entrypoint_pytest_cache_unrouted",
        ),
        *(
            (".config/checks/pytest/pytest.toml", document, gap)
            for document, gap in (
                ("[pytest]\ncache_dir='build/runtime/tool-cache/pytest'\n", ""),
                (
                    "[pytest]\ncache_dir='other'\n",
                    "generated_artifact_entrypoint_pytest_cache_unrouted",
                ),
                ("[pytest]\n", "generated_artifact_entrypoint_pytest_cache_unrouted"),
                ("[pytest]\ncache_dir=[]\n", "generated_artifact_entrypoint_pytest_cache_unrouted"),
                ("[pytest\n", "generated_artifact_entrypoint_pytest_config_invalid"),
            )
        ),
        ("tools/ci/scripts/with-python-runtime.sh", "python3 -c 'print(1)'\n", ""),
        *(
            ("tools/ci/scripts/package.sh", script, gap)
            for script, gap in (
                ("uv build\n", "generated_artifact_entrypoint"),
                ('OUT=build/artifacts/wheel\nuv build --out-dir "$OUT"\n', ""),
                ('uv build --out-dir "$MISSING"\n', "generated_artifact_entrypoint"),
                ("rm -rf dist/ .ruff_cache\n", ""),
            )
        ),
        (
            "tools/ci/scripts/quality.sh",
            "ruff check src\n",
            "generated_artifact_entrypoint_ruff_cache_unrouted",
        ),
        (
            "tools/ci/scripts/imports.sh",
            "lint-imports\n",
            "generated_artifact_entrypoint_import_linter_cache_unrouted",
        ),
        (
            "tools/ci/scripts/gitlab.sh",
            "gitlab-ci-local --file .gitlab-ci.yml\n",
            "generated_artifact_entrypoint_gitlab_state_unrouted",
        ),
        (
            "tools/ci/scripts/cache.sh",
            "mkdir .ruff_cache\n",
            "generated_artifact_entrypoint_denied_root_cache",
        ),
    ],
)
def test_entrypoint_audit_fails_closed_for_unrouted_public_tools(
    tmp_path: Path, relative: str, text: str, gap: str
) -> None:
    _write(tmp_path, relative, text)

    report = generated_artifact_entrypoint_audit(tmp_path)

    assert report["verdict"] == ("block" if gap else "pass")
    assert not gap or any(str(item).startswith(gap) for item in report["required_gaps"])
