"""Adoption plans the invoking release's Mise pin, and the exit removes only that key."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.adoption as adoption_effect
import ethos.application.adoption as adoption_requests
from ethos.adapters.repo.adoption import adoption_plan
from ethos.adapters.repo.git import current_head
from ethos.adapters.repo.hook.exit_plan import exit_preview
from ethos.adapters.toolchain.mise import MISE_CONFIG
from ethos.application.adoption import adopt_repository
from ethos.repository.release.identity import build_identity
from ethos.repository.release.pin import PIN_KEY
from ethos.repository.release.pin import bare_entry
from tests.support.governed_repository import init_git_repo
from tests.support.repository_exit import adopted_with_own_hooks
from tests.support.repository_exit import apply_exit

if TYPE_CHECKING:
    from pathlib import Path

RELEASE = "0.2.0-beta.11"
ENTRY = bare_entry(RELEASE)
PIN = ENTRY.splitlines()[1]
SETTING = ENTRY.partition("\n\n")[2]
OWN = '# The project\'s own tools.\n[tools]\nnode = "26.13.1"\n\n[tasks.check]\nrun = "true"\n'
PINNED_OWN = OWN.replace("\n\n", f"\n{PIN}\n\n") + f"\n{SETTING}"
OPTIONS = ENTRY.replace(f'"{RELEASE}"', f'{{ version = "{RELEASE}", os = ["linux"] }}')
HTTP = f'[tools."http:ethos"]\nversion = "{RELEASE}"\nurl = "https://example.invalid/a"\n'


def _text(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


@pytest.mark.parametrize(
    ("existing", "action", "planned"),
    [
        pytest.param(None, "create", ENTRY, id="no-mise-config"),
        pytest.param(ENTRY, "keep_existing", ENTRY, id="exact-pin"),
        pytest.param(OWN, "extend_existing", PINNED_OWN, id="own-tools"),
        pytest.param(HTTP, "skip_existing_nonempty", None, id="http-table"),
        pytest.param(
            bare_entry("0.2.0-beta.10"), "skip_existing_nonempty", None, id="other-version"
        ),
        pytest.param(OPTIONS, "skip_existing_nonempty", None, id="options-form"),
    ],
)
def test_adoption_plans_the_pin_as_one_previewed_step(
    tmp_path: Path, existing: str | None, action: str, planned: str | None
) -> None:
    """The step names the Mise configuration and a diff that only adds; another pin conflicts."""
    target = tmp_path / MISE_CONFIG
    if existing is not None:
        target.parent.mkdir(parents=True)
        target.write_text(existing, encoding="utf-8")

    preview = adoption_plan(tmp_path, release=RELEASE)
    step = preview["write_plan"][-1]
    applied = adoption_plan(tmp_path, apply=True, release=RELEASE)

    assert (step["path"], step["action"], step["conflict"]) == (MISE_CONFIG, action, not planned)
    assert (f"+{PIN}" in step["diff"]) is (action in {"create", "extend_existing"})
    assert not [line for line in step["diff"][2:] if line.startswith("-")]
    conflict = f"adoption_conflict:{MISE_CONFIG}"
    assert (conflict in preview["required_gaps"], preview["relock"]) == (not planned, False)
    assert (applied["applied"], applied["relock"]) == (
        bool(planned),
        planned not in {None, existing},
    )
    assert _text(target) == (planned or existing)
    assert (tmp_path / ".ethos/profile.toml").exists() is bool(planned)


def test_a_failed_adoption_removes_the_directories_it_made(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fresh repository keeps no Mise directory when the plan's postcondition fails."""

    def failed(_root: Path) -> None:
        raise OSError(RELEASE)

    monkeypatch.setattr(adoption_effect, "_verify_native_postcondition", failed)
    root = tmp_path / "repo"
    root.mkdir()

    with pytest.raises(OSError, match=RELEASE):
        adoption_plan(root, apply=True, release=RELEASE)

    assert list(root.iterdir()) == []


@pytest.mark.parametrize("kind", ["release", "development"])
def test_an_applied_pin_is_followed_by_the_relock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """A release build writes its own pin and names `mise lock`; a development build plans none."""
    repo = init_git_repo(tmp_path / "repo")
    release = kind == "release"
    build = build_identity(
        product=RELEASE, source_commit="a" * 40, source_tree="b" * 40, release=release
    )
    monkeypatch.setattr(adoption_requests, "invoking_build_identity", lambda: build)

    preview = adopt_repository(repo)
    request = {"apply": True, "authorize": True, "expect_head": current_head(repo)}
    applied = adopt_repository(repo, **request, expect_plan_digest=preview.data["plan_digest"])
    again = adopt_repository(repo, **request)

    status = f"ethos status --root {repo} --json"
    assert preview.data["pin"] == (RELEASE if release else "none:development_build")
    assert (MISE_CONFIG in preview.data["planned_files"]) is release
    assert _text(repo / MISE_CONFIG) == (ENTRY if release else None)
    assert applied.next_action == ("mise lock" if release else status), applied.to_dict()
    assert (applied.next.kind, again.next_action) == (
        "instruction" if release else "command",
        status,
    )


@pytest.mark.parametrize(
    ("config", "after"),
    [
        pytest.param(PINNED_OWN, OWN + f"\n{SETTING}", id="own-pin"),
        pytest.param(OPTIONS, None, id="options-form"),
    ],
)
def test_an_exit_removes_only_the_pin_that_adoption_wrote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config: str, after: str | None
) -> None:
    """The preview names the key; the apply keeps every other line, the setting and each file."""
    repo, _common, _before = adopted_with_own_hooks(tmp_path, monkeypatch)
    adoption_plan(repo, apply=True, release=RELEASE)
    (repo / MISE_CONFIG).write_text(config, encoding="utf-8")
    profile = _text(repo / ".ethos/profile.toml")

    pin = exit_preview(repo)["pin"]
    result = apply_exit(repo)

    assert pin == (after and {"path": MISE_CONFIG, "key": PIN_KEY, "after": after})
    assert (result.state, result.data["pin"]) == ("applied", pin), result.to_dict()
    assert (_text(repo / MISE_CONFIG), _text(repo / ".ethos/profile.toml")) == (
        after or config,
        profile,
    )
    assert exit_preview(repo)["pin"] is None
