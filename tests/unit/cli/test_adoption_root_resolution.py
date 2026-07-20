"""CLI regressions for fail-closed explicit adoption-root resolution."""

from pathlib import Path

import pytest

from tests.support.ethos_cli_runner import run_ethos_blocked


@pytest.mark.parametrize("target_kind", ["missing", "not_directory"])
def test_adopt_apply_rejects_unusable_root_without_traceback(
    tmp_path: Path,
    target_kind: str,
) -> None:
    target = tmp_path / target_kind
    if target_kind == "not_directory":
        target.write_text("not a repository\n", encoding="utf-8")

    payload = run_ethos_blocked(
        "adopt",
        "--root",
        target.as_posix(),
        "--apply",
        "--authorize",
        "--expect-head",
        "untracked",
        "--json",
    )

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert "git_repository_missing" in payload["required_gaps"]
    assert not (target / ".ethos" / "profile.toml").exists()
