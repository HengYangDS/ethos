from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

from tools.ci.repository_hygiene import audit

ROOT = Path(__file__).resolve().parents[2]


def _initialize_repository(repo: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)


def _write_policy(repo: Path) -> None:
    policy = repo / ".config/checks/repository-hygiene/policy.toml"
    policy.parent.mkdir(parents=True)
    policy.write_text(
        """max_tracked_bytes = 1048576
text_suffixes = [".json", ".md", ".py", ".sh"]
text_names = ["README.md"]
root_host_residue = [".DS_Store", "Thumbs.db", "Desktop.ini"]
""",
        encoding="utf-8",
    )


def test_repository_hygiene_is_one_python_nox_owner() -> None:
    policy = (ROOT / ".config/checks/repository-hygiene/policy.toml").read_text(encoding="utf-8")
    tools = (ROOT / "system/tools.toml").read_text(encoding="utf-8")
    sessions = (ROOT / "tools/ci/sessions.py").read_text(encoding="utf-8")

    assert "root_host_residue = [" in policy
    assert '".DS_Store"' in policy
    assert 'concern = "repository_hygiene"' in tools
    assert 'gate = "uv run --frozen --offline python -m nox -s repository_hygiene"' in tools
    assert "def repository_hygiene(session)" in sessions
    assert '"--ignore-noqa"' in sessions
    coverage = (ROOT / ".config/checks/coverage/coverage.ini").read_text(encoding="utf-8")
    assert "exclude_lines =\n" in coverage
    assert not (ROOT / "tools/ci/scripts/run-repository-hygiene.sh").exists()


def test_full_proof_includes_the_repository_hygiene_owner_once() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    full = declaration["proof_sets"]["full"]
    gates = {item["id"]: item for item in declaration["gates"]}

    assert full.count("repository-hygiene") == 1
    assert gates["repository-hygiene"]["command"] == [
        "{python}",
        "-m",
        "nox",
        "-s",
        "repository_hygiene",
    ]


def test_repository_hygiene_rejects_global_ignored_ds_store(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_policy(repo)
    _initialize_repository(repo)
    (repo / ".DS_Store").write_bytes(b"host-local residue")

    failures = audit(repo)

    assert ".DS_Store: host-local root residue is not repository truth; remove it" in failures


def test_repository_hygiene_rejects_source_suppressions(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_policy(repo)
    source = repo / "module.py"
    source.write_text("value = call()  # noqa: F821\n", encoding="utf-8")
    _initialize_repository(repo)

    failures = audit(repo)

    assert "module.py:1: forbidden quality suppression: noqa" in failures


def test_repository_hygiene_rejects_shellcheck_disable(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_policy(repo)
    script = repo / "check.sh"
    script.write_text(
        "#!/bin/sh\n# shellcheck disable=SC2086\nprintf '%s\\n' ok\n",
        encoding="utf-8",
    )
    _initialize_repository(repo)

    failures = audit(repo)

    assert "check.sh:2: forbidden quality suppression: shellcheck-disable" in failures


def test_repository_hygiene_rejects_format_and_coverage_suppressions(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_policy(repo)
    source = repo / "module.py"
    source.write_text(
        "# fmt: off\nvalue = 1  # pragma: no cover\n# fmt: on\n",
        encoding="utf-8",
    )
    _initialize_repository(repo)

    failures = audit(repo)

    assert "module.py:1: forbidden quality suppression: format-off" in failures
    assert "module.py:2: forbidden quality suppression: coverage-ignore" in failures
    assert "module.py:3: forbidden quality suppression: format-on" in failures
