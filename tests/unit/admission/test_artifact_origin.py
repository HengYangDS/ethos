"""Public origin and deletion admission over real repository preimages."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.patch_admission as patch_owner
from ethos.adapters.admission.patch_admission import patch_admission
from ethos.adapters.admission.patch_admission import staged_artifact_admission
from ethos.repository.policy.artifacts import generated_artifact_topology_report
from ethos.repository.policy.references.observation import deleted_input_gaps
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_active_change
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import start_adopted_work_lane

if TYPE_CHECKING:
    from pathlib import Path


def _prewrite(root: Path, paths: tuple[str, ...], patch: Path | None = None):
    args = ("--patch", patch.as_posix()) if patch else ()
    completed = run_ethos_raw(
        "lane",
        "prewrite",
        *paths,
        *args,
        "--editor-root",
        root.as_posix(),
        "--require-editor-root",
        "--json",
        cwd=root,
    )
    return json.loads(completed.stdout)


@pytest.mark.parametrize("suffix", ["json", "xml", "html"])
def test_authored_format_is_not_generation_evidence(tmp_path: Path, suffix: str) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    relative = f".config/native/settings.{suffix}"
    path = fixture.worktree / relative
    path.parent.mkdir(parents=True)
    path.write_text("{}\n")
    result = _prewrite(fixture.worktree, (relative,))
    assert result["verdict"] == "pass", result
    observed = result["data"]["paths"][0]
    assert observed["origin"] == "unclassified"
    assert observed["existence"] == "present"
    report = generated_artifact_topology_report(
        fixture.worktree,
        ignored_local_paths=frozenset(),
        tracked_untracked_paths=(),
    )
    assert relative not in report["denied_paths"]


@pytest.mark.parametrize("update_consumer", [False, True])
def test_authored_deletion_checks_surviving_native_input(
    tmp_path: Path,
    *,
    update_consumer: bool,
) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    root = fixture.worktree
    relative = ".config/native/settings.json"
    config = root / relative
    config.parent.mkdir(parents=True)
    config.write_text('{"proseWrap":"preserve"}\n')
    package = root / "package.json"
    original = (
        json.dumps(
            {
                "private": True,
                "scripts": {"format": f"prettier --config {relative} README.md"},
                "devDependencies": {"prettier": "3.6.2"},
            }
        )
        + "\n"
    )
    package.write_text(original)
    commit_fixture(root, "declare native configuration")
    config.unlink()
    if update_consumer:
        package.write_text(original.replace(f"--config {relative}", "--no-config"))
    patch = tmp_path / "deletion.patch"
    patch.write_text(git(root, "diff", "--no-ext-diff") + "\n")
    paths = tuple(git(root, "diff", "--name-only").splitlines())
    config.write_text('{"proseWrap":"preserve"}\n')
    package.write_text(original)

    result = _prewrite(root, paths, patch)

    assert result["verdict"] == ("pass" if update_consumer else "block"), result
    if not update_consumer:
        assert any("deleted_input" in gap and relative in gap for gap in result["required_gaps"])
    assert config.read_text() == '{"proseWrap":"preserve"}\n'
    assert package.read_text() == original


def test_declared_output_requires_patch_but_its_source_does_not(tmp_path: Path) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    root = fixture.worktree
    declaration = root / ".config/checks/architecture/projection.toml"
    declaration.parent.mkdir(parents=True)
    declaration.write_text(
        'schema = "ethos-architecture-projection-v1"\n[[projection]]\n'
        'id = "view"\nsource = "model.c4"\noutput = "diagram.mmd"\n'
        'kind = "likec4-to-mermaid"\n',
    )
    (root / "model.c4").write_text('system Example "Example"\n')
    result = _prewrite(root, ("diagram.mmd",))
    assert result["verdict"] == "block", result
    assert result["data"]["paths"][0]["origin"] == "projection"
    assert result["data"]["paths"][0]["existence"] == "absent"
    assert "--patch" in result["next_action"]
    assert root.as_posix() in result["next_action"]
    assert _prewrite(root, ("model.c4",))["verdict"] == "pass"


@pytest.mark.parametrize(
    ("effect", "verdict", "gap"),
    [
        ("regenerate", "pass", ""),
        ("tamper", "block", "generated_projection_drift"),
        ("delete-output", "block", "generated_projection_missing"),
        ("delete-owner", "block", "generated_projection_owner_removed"),
        ("retire", "pass", ""),
        ("disguise", "block", "generated_projection_owner_removed"),
        ("predelete-owner", "block", "generated_projection_owner_removed"),
    ],
)
def test_projection_effect_uses_producer_before_and_after(
    tmp_path: Path,
    effect: str,
    verdict: str,
    gap: str,
) -> None:

    root = init_git_repo(tmp_path / "repo")
    declaration = ".config/checks/architecture/projection.toml"
    source, output = "model.c4", "diagram.mmd"
    files = {
        declaration: 'schema = "ethos-architecture-projection-v1"\n[[projection]]\n'
        'id = "view"\nsource = "model.c4"\noutput = "diagram.mmd"\n'
        'kind = "likec4-to-mermaid"\n',
        source: 'system Example "Example"\n',
        output: "%% Generated from model.c4. Do not edit by hand.\n"
        'flowchart LR\n  Example["Example"]\n',
    }
    for path, text in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    commit_active_change(root)
    head = git(root, "rev-parse", "HEAD")
    mutations: dict[str, dict[str, str | None]] = {
        "regenerate": {
            source: files[source].replace('"Example"', '"Changed"'),
            output: files[output].replace('"Example"', '"Changed"'),
        },
        "tamper": {output: files[output] + "malicious\n"},
        "predelete-owner": {output: files[output] + "malicious\n"},
        "delete-output": {output: None},
        "delete-owner": {declaration: None},
        "retire": {declaration: None, output: None},
        "disguise": {declaration: None, output: "authored now\n"},
    }
    changed = mutations[effect]
    for path, text in changed.items():
        if text is None:
            (root / path).unlink()
        else:
            (root / path).write_text(text)
    patch = git(root, "diff", "--no-ext-diff", "--", *changed) + "\n"
    for path in changed:
        (root / path).write_text(files[path])
    if effect == "predelete-owner":
        (root / declaration).unlink()
    result = patch_admission(
        root=root, requested_paths=tuple(changed), baseline_head=head, patch=patch
    )
    assert result["verdict"] == verdict, result
    if gap:
        assert gap in str(result["reason"]), result
    assert (root / output).read_text() == files[output]


@pytest.mark.parametrize(
    ("command", "dangling", "unknown"),
    [
        ("prettier --config config.json README.md", True, False),
        ("npx prettier --config=config.json README.md", True, False),
        ("prettier --ignore-path config.json README.md", True, False),
        ("prettier --no-config README.md", False, False),
        ("echo prettier --config config.json", False, False),
        ("echo '{}' > config.json", False, False),
        ("prettier --config '$CONFIG' README.md", False, True),
        ("prettier --config config.json --ignore-path one --ignore-path config.json", True, False),
        ("prettier --config '$(get_config)' README.md", False, True),
        ("cd nested && prettier --config config.json README.md", False, True),
        ("env -C nested prettier --config config.json README.md", False, True),
    ],
)
def test_deleted_input_observation_distinguishes_effects(
    command: str,
    *,
    dangling: bool,
    unknown: bool,
) -> None:

    gaps, unavailable = deleted_input_gaps(
        {"package.json": json.dumps({"scripts": {"format": command}})},
        frozenset({"config.json"}),
    )
    assert bool(gaps) is dangling, (gaps, unavailable)
    assert bool(unavailable) is unknown, (gaps, unavailable)


def test_path_only_admission_cannot_erase_a_committed_producer(tmp_path: Path) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    root = fixture.worktree
    declaration = root / ".config/checks/architecture/projection.toml"
    declaration.parent.mkdir(parents=True)
    declaration.write_text(
        'schema = "ethos-architecture-projection-v1"\n[[projection]]\n'
        'id = "view"\nsource = "model.c4"\noutput = "diagram.mmd"\n'
        'kind = "likec4-to-mermaid"\n',
    )
    (root / "model.c4").write_text('system Example "Example"\n')
    (root / "diagram.mmd").write_text("old output\n")
    commit_fixture(root, "declare producer")
    declaration.unlink()
    report = _prewrite(root, ("diagram.mmd",))
    assert report["verdict"] == "block", report
    assert "generated_projection_patch_required" in report["required_gaps"][0], report


def test_repeated_native_ignore_inputs_are_not_last_value_only() -> None:
    gaps, unknown = deleted_input_gaps(
        {
            "package.json": json.dumps(
                {
                    "scripts": {
                        "format": (
                            "prettier --ignore-path config.json --ignore-path retained README.md"
                        ),
                    }
                }
            )
        },
        frozenset({"config.json"}),
    )
    assert gaps == ["deleted_input:config.json:package.json:scripts.format"]
    assert unknown == []


@pytest.mark.parametrize("declaration", ["schema='unknown'", "projection='not-a-list'"])
def test_invalid_projection_ownership_is_unknown(tmp_path: Path, declaration: str) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    root = fixture.worktree
    path = root / ".config/checks/architecture/projection.toml"
    path.parent.mkdir(parents=True)
    path.write_text(declaration)
    report = _prewrite(root, ("model.c4",))
    assert report["verdict"] == "unknown", report
    assert "projection_ownership_unknown" in report["required_gaps"][0], report
    assert "projection.toml" in report["next_action"], report


def test_exact_patch_repairs_uncommitted_invalid_projection_declaration(tmp_path: Path) -> None:
    """Unknown current syntax permits a validated repair, not unrestricted authoring."""
    fixture = start_adopted_work_lane(tmp_path)
    root = fixture.worktree
    relative = ".config/checks/architecture/projection.toml"
    declaration = root / relative
    declaration.parent.mkdir(parents=True)
    good = 'schema = "ethos-architecture-projection-v1"\nprojection = []\n'
    declaration.write_text(good)
    commit_fixture(root, "declare empty projection set")
    bad = "schema = [\n"
    declaration.write_text(bad)
    patch = tmp_path / "repair.patch"
    patch.write_text(
        f"diff --git a/{relative} b/{relative}\n--- a/{relative}\n+++ b/{relative}\n"
        '@@ -1 +1,2 @@\n-schema = [\n+schema = "ethos-architecture-projection-v1"\n'
        "+projection = []\n"
    )
    blocked = _prewrite(root, (relative,))
    assert blocked["verdict"] == "unknown", blocked
    assert "--patch" in blocked["next_action"], blocked
    repaired = _prewrite(root, (relative,), patch)
    assert repaired["verdict"] == "pass", repaired
    assert declaration.read_text() == bad


def test_deleted_input_dynamic_path_is_public_unknown(tmp_path: Path) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    root = fixture.worktree
    path = root / "config.json"
    path.write_text("{}\n")
    (root / "package.json").write_text(
        json.dumps(
            {
                "private": True,
                "scripts": {"format": "prettier --config $CONFIG README.md"},
                "devDependencies": {"prettier": "3.6.2"},
            }
        )
        + "\n"
    )
    commit_fixture(root, "declare dynamic input")
    path.unlink()
    patch = tmp_path / "remove.patch"
    patch.write_text(git(root, "diff", "--no-ext-diff") + "\n")
    path.write_text("{}\n")
    report = _prewrite(root, ("config.json",), patch)
    assert report["verdict"] == "unknown", report
    assert "deleted_input_observation_unknown:package.json:format" in report["required_gaps"]
    assert "package.json" in report["next_action"], report


@pytest.mark.parametrize("work_copy", ["different", "outside-symlink"])
@pytest.mark.parametrize("staged_valid", [True, False])
def test_precommit_validates_index_projection_not_working_copy(
    tmp_path: Path,
    work_copy: str,
    *,
    staged_valid: bool,
) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    root = fixture.worktree
    declaration = root / ".config/checks/architecture/projection.toml"
    declaration.parent.mkdir(parents=True)
    declaration.write_text(
        'schema = "ethos-architecture-projection-v1"\n[[projection]]\n'
        'id = "view"\nsource = "model.c4"\noutput = "diagram.mmd"\n'
        'kind = "likec4-to-mermaid"\n',
    )
    model = root / "model.c4"
    output = root / "diagram.mmd"
    model.write_text('system Example "Before"\n')
    before = '%% Generated from model.c4. Do not edit by hand.\nflowchart LR\n  Example["Before"]\n'
    output.write_text(before)
    commit_fixture(root, "declare exact producer")
    model.write_text('system Example "After"\n')
    after = before.replace('"Before"', '"After"')
    output.write_text(after if staged_valid else "wrong staged output\n")
    git(root, "add", "model.c4", "diagram.mmd")
    output.write_text("wrong work copy\n" if staged_valid else after)
    if work_copy == "outside-symlink":
        target = tmp_path / "outside-output"
        target.write_text(output.read_text())
        output.unlink()
        output.symlink_to(target)
    index_before = git(root, "write-tree")
    completed = run_ethos_raw("hook", "run", "pre-commit", cwd=root)
    assert completed.returncode == (0 if staged_valid else 1), completed.stderr
    if not staged_valid:
        assert "generated_projection_drift:diagram.mmd" in completed.stderr
    assert git(root, "write-tree") == index_before
    assert output.read_text() == ("wrong work copy\n" if staged_valid else after)


@pytest.mark.parametrize("effect", ["disguise", "retire", "unlink-source", "symlink-output"])
def test_staged_retirement_preserves_exact_output_existence(tmp_path: Path, effect: str) -> None:
    root = init_git_repo(tmp_path / "repo")
    declaration = root / ".config/checks/architecture/projection.toml"
    declaration.parent.mkdir(parents=True)
    declaration.write_text(
        'schema = "ethos-architecture-projection-v1"\n[[projection]]\n'
        'source = "model.c4"\noutput = "diagram.mmd"\nkind = "likec4-to-mermaid"\n',
    )
    (root / "model.c4").write_text('system Example "Example"\n')
    output = root / "diagram.mmd"
    output.write_text(
        '%% Generated from model.c4. Do not edit by hand.\nflowchart LR\n  Example["Example"]\n'
    )
    commit_active_change(root)
    baseline = git(root, "rev-parse", "HEAD")
    if effect in {"disguise", "retire"}:
        declaration.unlink()
        if effect == "disguise":
            output.write_text("arbitrary retained content\n")
        else:
            output.unlink()
    elif effect == "unlink-source":
        (root / "model.c4").unlink()
    else:
        output.unlink()
        output.symlink_to("model.c4")
    git(root, "add", "--all")
    index = git(root, "write-tree")
    result = staged_artifact_admission(root, baseline)
    assert result["verdict"] == ("pass" if effect == "retire" else "block"), result
    if effect == "disguise":
        assert result["reason"] == "generated_projection_owner_removed:diagram.mmd"
    assert git(root, "write-tree") == index
    assert git(root, "rev-parse", "HEAD") == baseline


@pytest.mark.parametrize("changed_coordinate", ["head", "index"])
def test_index_admission_rejects_coordinate_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    changed_coordinate: str,
) -> None:
    root = init_git_repo(tmp_path / "repo")
    (root / "input.json").write_text("{}\n")
    commit_active_change(root)
    baseline = git(root, "rev-parse", "HEAD")
    (root / "input.json").write_text('{"new":true}\n')
    git(root, "add", "input.json")
    original = patch_owner.run_git
    writes = 0

    def inject(repository, *args, **kwargs):
        nonlocal writes
        if args == ("write-tree",):
            writes += 1
            if writes == 2:
                if changed_coordinate == "head":
                    git(root, "commit", "--allow-empty", "-m", "injected concurrent commit")
                else:
                    (root / "input.json").write_text('{"concurrent":true}\n')
                    git(root, "add", "input.json")
        return original(repository, *args, **kwargs)

    monkeypatch.setattr(patch_owner, "run_git", inject)
    result = staged_artifact_admission(root, baseline)
    assert result["verdict"] == "block", result
    gaps = result["required_gaps"]
    assert isinstance(gaps, list)
    assert any("changed_during_admission" in gap for gap in gaps), result
