from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_repository_hygiene_policy_owns_hidden_root_residue_gate() -> None:
    policy = (ROOT / ".config/checks/repository-hygiene/policy.toml").read_text(encoding="utf-8")
    runner = (ROOT / "tools/ci/scripts/run-repository-hygiene.sh").read_text(encoding="utf-8")
    tools = (ROOT / "system/tools.toml").read_text(encoding="utf-8")

    assert "root_host_residue = [" in policy
    assert '".DS_Store"' in policy
    assert '"Thumbs.db"' in policy
    assert '"Desktop.ini"' in policy
    assert 'POLICY_PATH = Path(".config/checks/repository-hygiene/policy.toml")' in runner
    assert "host-local root residue is not repository truth" in runner
    assert 'concern = "repository_hygiene"' in tools
    assert 'config = ".config/checks/repository-hygiene/policy.toml"' in tools


def test_repository_hygiene_rejects_global_ignored_ds_store(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".config/checks/repository-hygiene").mkdir(parents=True)
    (repo / "tools/ci/scripts").mkdir(parents=True)
    shutil.copy2(
        ROOT / ".config/checks/repository-hygiene/policy.toml",
        repo / ".config/checks/repository-hygiene/policy.toml",
    )
    runner = repo / "tools/ci/scripts/run-repository-hygiene.sh"
    shutil.copy2(ROOT / "tools/ci/scripts/run-repository-hygiene.sh", runner)

    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    (repo / ".DS_Store").write_bytes(b"host-local residue")

    completed = subprocess.run(
        ["tools/ci/scripts/run-repository-hygiene.sh"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert ".DS_Store: host-local root residue is not repository truth; remove it" in (
        completed.stdout + completed.stderr
    )
