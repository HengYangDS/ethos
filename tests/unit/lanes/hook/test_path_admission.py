"""Admit exact editor paths through native hooks and explicit patch baselines."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import cast

import pytest

import ethos.adapters.admission.paths as path_admission
import ethos.adapters.admission.prewrite as admission_prewrite
import ethos.adapters.openspec.cli as openspec_cli
import ethos.adapters.repo.git as git_adapter
import ethos.adapters.repo.git_attributes as git_attributes
from ethos.adapters.admission.git_admission import hook_admission_report
from ethos.contracts.admission import HookAdmissionRequest
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import commit_active_change
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_active_commitment
from tests.support.lane_scenarios import leased_worktree
from tests.support.runtime_scenarios import install_fixture_hook_runtime


@pytest.fixture(autouse=True)
def actor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    repo = init_git_repo(tmp_path / "repo")
    commit_active_change(repo)
    install_fixture_hook_runtime(repo)
    return leased_worktree(repo, tmp_path / "repo-work-feature")


def _hook(root: Path, path: Path) -> dict[str, object]:
    request = HookAdmissionRequest(
        root=str(root),
        layer="pre-tool",
        paths=(str(path),),
        editor_root=str(root),
        require_editor_root=True,
    )
    return hook_admission_report(request)


def test_prewrite_batches_fresh_native_ignore_reads(
    worktree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Current native reads preserve ignored, tracked and spaced path admission."""
    ignore = worktree / ".gitignore"
    before_ignore = ignore.read_text()
    ignore.write_text(before_ignore + "scratch/\n")
    scratch = worktree / "scratch"
    scratch.mkdir()
    paths = [scratch / name for name in ("output.txt", "with space.txt", "tracked.txt")]
    for path in paths:
        path.write_text("retained content\n", encoding="utf-8")
    git(worktree, "add", "-f", "scratch/tracked.txt")
    index = git(worktree, "write-tree")
    native = git_adapter.run_git
    reads = []

    def observe(root, *args, **kwargs):
        if args[0] == "check-ignore":
            reads.append(kwargs.get("stdin"))
        return native(root, *args, **kwargs)

    monkeypatch.setattr(git_adapter, "run_git", observe)
    first = admission_prewrite.prewrite_guard(root=worktree, paths=paths, editor_root=worktree)
    assert first["verdict"] == "pass", first
    assert [item["ignored"] for item in first["paths"]] == [True, True, False]
    assert [item["tracked_candidate"] for item in first["paths"]] == [False, False, True]
    assert reads == ["scratch/output.txt\0scratch/with space.txt\0scratch/tracked.txt\0"]

    ignore.write_text(before_ignore)
    second = admission_prewrite.prewrite_guard(root=worktree, paths=paths, editor_root=worktree)
    assert second["verdict"] == "pass", second
    assert [item["ignored"] for item in second["paths"]] == [False, False, False]
    assert len(reads) == 2
    assert git(worktree, "write-tree") == index
    assert all(path.read_text() == "retained content\n" for path in paths)


@pytest.mark.parametrize("with_patch", [False, True])
def test_prewrite_refuses_unavailable_native_ignore_observation(
    worktree: Path, monkeypatch: pytest.MonkeyPatch, *, with_patch: bool
) -> None:
    """Failed required native reads never authorize an ordinary source path."""
    before = git(worktree, "status", "--porcelain=v1", "--untracked-files=all")
    native = git_adapter.run_git

    def unavailable(root, *args, **kwargs):
        if args[0] == "check-ignore":
            return subprocess.CompletedProcess(args, 128, "", "fatal: ignore observation failed")
        return native(root, *args, **kwargs)

    monkeypatch.setattr(git_adapter, "run_git", unavailable)

    def unavailable_projections(*_args):
        message = "projection observation unavailable"
        raise ValueError(message)

    if with_patch:
        monkeypatch.setattr(path_admission, "projection_preimages", unavailable_projections)
    patch = _patch("src/source.py", "VALUE = 1", new=True) if with_patch else ""
    report = _guard(worktree, ("src/source.py",), patch)
    assert report["verdict"] == "unknown", report
    assert any(
        gap.startswith("prewrite_ignore_observation_unavailable") for gap in report["required_gaps"]
    )
    assert git(worktree, "status", "--porcelain=v1", "--untracked-files=all") == before


def _guard(lane: Path, paths: tuple[str, ...], patch: str = "") -> dict[str, object]:
    return admission_prewrite.prewrite_guard(
        root=lane,
        paths=[lane / path for path in paths],
        editor_root=lane,
        require_editor_root=True,
        patch=patch,
    )


@pytest.mark.parametrize(
    ("token", "kind"),
    [("README.md\nAGENTS.md", "control_character"), ("README.md\tAGENTS.md", "control_character")],
)
def test_invalid_path_matrix(worktree: Path, token: str, kind: str) -> None:
    report = _hook(worktree, Path(token))
    reason = f"prewrite_path_invalid_{kind}"
    assert report["verdict"] == "block"
    assert "ok" not in report
    assert report["decision"] == {"action": "block", "reason": reason}
    assert cast("dict[str, object]", report["admission"])["paths"] == [
        {
            "path": token,
            "relative_path": "",
            "ignored": False,
            "tracked_candidate": False,
            "allowed": False,
            "reason": f"path_invalid_{kind}",
            "effect": "unspecified",
        }
    ]
    assert reason in cast("list[str]", report["required_gaps"])


@pytest.mark.parametrize(
    ("relative", "verdict"),
    [
        ("docs/guide [draft].md", "block"),
        ("docs/README.md .gitignore", "block"),
        ("docs/guide.md", "pass"),
    ],
)
def test_literal_path_transport_preserves_naming_admission(
    worktree: Path, relative: str, verdict: str
) -> None:
    """Literal names keep creation admission; existing documents keep native formatting."""
    requested = worktree / relative
    before = (worktree / "README.md").read_bytes() if (worktree / "README.md").is_file() else None
    index = git(worktree, "ls-files", "--stage")
    runner = run_ethos_blocked if verdict == "block" else run_ethos
    result = runner(
        "lane",
        "prewrite",
        relative,
        "--root",
        str(worktree),
        "--editor-root",
        str(worktree),
        "--require-editor-root",
        "--json",
    )
    assert result["verdict"] == verdict
    assert [item["relative_path"] for item in result["data"]["paths"]] == [relative]
    hooked = _hook(worktree, Path(relative))
    assert hooked["verdict"] == verdict
    admission = cast("dict[str, object]", hooked["admission"])
    admitted = cast("list[dict[str, object]]", admission["paths"])
    assert [item["relative_path"] for item in admitted] == [relative]
    gaps = [f"repository_paradigm_authored_name:{relative}"] if verdict == "block" else []
    assert result["required_gaps"] == hooked["required_gaps"] == gaps
    assert not requested.exists()
    assert git(worktree, "ls-files", "--stage") == index
    if before is not None:
        assert (worktree / "README.md").read_bytes() == before
    if relative.endswith(".md"):
        requested.parent.mkdir(parents=True, exist_ok=True)
        original = b"# Native source  \n\n\n"
        requested.write_bytes(original)
        git(worktree, "add", "--", relative)
        index = git(worktree, "ls-files", "--stage")
        head = git(worktree, "rev-parse", "HEAD")
        lane_format = ("lane", "format", relative, "--root", str(worktree), "--json")
        result = run_ethos(*lane_format, "--apply", "--authorize", "--expect-head", head)
        assert result["data"]["files"] == [relative]
        assert result["state"] == "formatted"
        assert result["required_gaps"] == []
        assert git(worktree, "ls-files", "--stage") == index
        formatted = requested.read_bytes()
        fixed = run_ethos(*lane_format, "--check")
        assert fixed["data"]["changed_paths"] == []
        assert requested.read_bytes() == formatted == b"# Native source\n"


SHADOW = "external_method_pack_shadow_authority:.superpowers/sdd/tasks/progress.md"
IGNORED_CASES = [
    (".superpowers/sdd/tasks/progress.md", ".superpowers/sdd/.gitignore", "*\n", "block", SHADOW),
    ("build/runtime/work/provider/session.json", ".gitignore", "build/\n", "pass", "allowed"),
]


@pytest.mark.parametrize("case", IGNORED_CASES)
def test_ignored_path_matrix(worktree: Path, case: tuple[str, str, str, str, str]) -> None:
    relative, ignore, content, verdict, reason = case
    path = worktree / relative
    path.parent.mkdir(parents=True)
    path.write_text("{}\n")
    (worktree / ignore).write_text(content)
    report = _hook(worktree, path)
    admission = cast("dict[str, object]", report["admission"])
    admitted = cast("list[dict[str, object]]", admission["paths"])[0]
    assert report["verdict"] == verdict
    assert "ok" not in report
    assert admitted["ignored"] is True
    assert admitted["tracked_candidate"] is False
    assert admitted["allowed"] is (verdict == "pass")
    assert admitted["reason"] == reason
    if verdict == "block":
        assert report["decision"] == {"action": "block", "reason": reason}
        assert admission["error"] == reason


@pytest.mark.parametrize("mismatch", ["runner", "schema"])
def test_editor_binding_matrix(
    worktree: Path, monkeypatch: pytest.MonkeyPatch, mismatch: str
) -> None:
    binding = admission_prewrite.runtime_binding(worktree)
    binding["state"] = "external_current_runner"
    for component in ("runner", "schema"):
        matches = component != mismatch
        binding[f"{component}_matches_audit_root"] = matches
        binding[f"{component}_source_root"] = (
            binding["audit_root"] if matches else f"/foreign/{component}"
        )
    monkeypatch.setattr(
        admission_prewrite,
        "runtime_binding",
        lambda _root, **_kwargs: binding,
    )
    report = _guard(worktree, ("README.md",))
    assert report["verdict"] == "block"
    assert "ok" not in report
    assert report["error"] == "root_binding_mismatch"
    assert cast("dict[str, object]", report["runtime_binding"])["audit_root"] == worktree.as_posix()
    assert cast("dict[str, object]", report["editor_root"])["reason"] == "matched"


def test_unknown_editor_component(worktree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def unknown(_status):
        return {"verdict": "unknown", "reason": ""}

    monkeypatch.setattr(admission_prewrite, "runtime_binding_check", unknown)
    report = _guard(worktree, ("README.md",))
    assert report["verdict"] == "unknown"
    assert report["required_gaps"] == []
    assert "ok" not in report


def test_owned_lane_bootstraps_only_official_change_artifacts(worktree: Path) -> None:
    previous = worktree / "openspec/changes/fixture-change"
    shutil.rmtree(previous)
    change_root = "openspec/changes/bootstrap-test"
    metadata = "openspec/changes/bootstrap-test/.openspec.yaml"

    root_intent = _guard(worktree, (change_root,))
    initial = _guard(worktree, (metadata,))

    assert root_intent["verdict"] == "block"
    assert root_intent["error"] == ("openspec_change_metadata_prewrite_required:bootstrap-test")
    assert root_intent["next_action"] == (
        f"ethos lane prewrite --paths {metadata} "
        f"--editor-root {worktree} --require-editor-root --root {worktree} --json"
    )
    assert initial["verdict"] == "pass"
    assert (
        cast("dict[str, object]", initial["material_scope"])["state"] == "official_change_bootstrap"
    )
    assert initial["next_action"] == "openspec new change bootstrap-test --json"

    command = openspec_cli.openspec_base_command()
    assert command is not None
    created = openspec_cli.run_json(
        worktree,
        command,
        ("new", "change", "bootstrap-test", "--json"),
    )
    assert created["exit_code"] == 0

    proposal = _guard(worktree, ("openspec/changes/bootstrap-test/proposal.md",))
    sidecar = _guard(worktree, ("openspec/changes/bootstrap-test/README.md",))
    product = _guard(worktree, ("src/product.py",))

    assert proposal["verdict"] == "pass"
    assert proposal["next_action"] == (
        "openspec instructions proposal --change bootstrap-test --json"
    )
    assert sidecar["verdict"] == "block"
    assert product["verdict"] == "block"


def test_owned_lane_bootstraps_third_change_without_cross_change_authority(
    worktree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Public prewrite keeps exact bootstrap reachable amid other active Changes."""
    write_active_commitment(worktree, change_id="second")
    metadata = "openspec/changes/third/.openspec.yaml"

    unselected = _guard(worktree, (metadata,))
    assert unselected["verdict"] == "pass"
    assert unselected["next_action"] == "openspec new change third --json"

    monkeypatch.setenv("ETHOS_CHANGE", "fixture-change")
    mismatched = _guard(worktree, (metadata,))
    assert mismatched["verdict"] == "block"
    assert mismatched["error"] == f"openspec_change_path_mismatch:fixture-change:{metadata}"

    monkeypatch.setenv("ETHOS_CHANGE", "third")
    selected = _guard(worktree, (metadata,))
    assert selected["verdict"] == "pass"
    assert selected["next_action"] == "openspec new change third --json"


def test_cli_path_token(worktree: Path) -> None:
    token = "README.md\nAGENTS.md"
    data = run_ethos_blocked(
        "hook",
        "admit",
        "pre-tool",
        token,
        "--root",
        str(worktree),
        "--editor-root",
        str(worktree),
        "--require-editor-root",
        "--json",
        cwd=worktree,
    )["data"]
    assert data["decision"] == {
        "action": "block",
        "reason": "prewrite_path_invalid_control_character",
    }
    assert data["target_paths"] == [token]
    assert data["admission"]["paths"][0]["path"] == token


@pytest.mark.parametrize(
    ("attribute", "received"),
    [("linguist-vendored", True), ("linguist-generated=true", True), ("-linguist-vendored", False)],
)
def test_new_path_its_attributes_mark_received_keeps_its_name(
    worktree: Path, monkeypatch: pytest.MonkeyPatch, attribute: str, *, received: bool
) -> None:
    """New received names use one fresh native attribute read per admission request."""
    fonts = ("assets/fonts/NotoSansCJKsc-Bold.otf", "assets/fonts/NotoSansCJKsc-Regular.otf")
    attributes = worktree / ".gitattributes"
    original = attributes.read_text(encoding="utf-8")
    index = git(worktree, "write-tree")
    native = git_attributes.run_git
    reads = []

    def observe(root, *args, **kwargs):
        if args[0] == "check-attr":
            reads.append(kwargs.get("stdin"))
        return native(root, *args, **kwargs)

    monkeypatch.setattr(git_attributes, "run_git", observe)
    attributes.write_text(f"assets/fonts/** {attribute}\n{original}", encoding="utf-8")
    for font, path in zip(fonts, _guard(worktree, fonts)["paths"], strict=True):
        gap = f"repository_paradigm_authored_name:{font}"
        assert (path["reason"] != gap) is received, path
    frame = b"".join(font.encode() + b"\0" for font in fonts)
    assert reads == [frame]

    attributes.write_text(original, encoding="utf-8")
    for font, path in zip(fonts, _guard(worktree, fonts)["paths"], strict=True):
        assert path["reason"] == f"repository_paradigm_authored_name:{font}"
    assert reads == [frame, frame]
    assert git(worktree, "write-tree") == index


def _lane(tmp: Path, imports: tuple[str, ...]) -> Path:
    repo = init_git_repo(tmp / "repo")
    dependencies = [root.replace("_", "-") for root in imports]
    (repo / "system").mkdir()
    project = f'[project]\nname = "test-product"\nversion = "1"\ndependencies = {dependencies!r}\n'
    project += '[project.scripts]\nethos = "sample:main"\n'
    (repo / "pyproject.toml").write_text(project.replace("'", '"'))
    (repo / "system/surfaces.toml").write_text(
        'schema = "system/schemas/contracts/surfaces.schema.json"\n\n'
        "[runtime]\nexecutables = []\ninputs = []\n\n"
        '[[surface]]\nname = "runtime"\ncarrier = "src"\n'
    )
    (repo / "module.py").write_text("VALUE = 1\n")
    commit_active_change(repo)
    install_fixture_hook_runtime(repo)
    return leased_worktree(repo, tmp / "repo-work-feature")


def _patch(path: str, added: str, *, new: bool = False) -> str:
    header = f"diff --git a/{path} b/{path}\n"
    if new:
        return (
            header
            + f"new file mode 100644\n--- /dev/null\n+++ b/{path}\n"
            + f"@@ -0,0 +1,{len(added.splitlines())} @@\n"
            + "".join(f"+{line}\n" for line in added.splitlines())
        )
    return (
        header
        + f"--- a/{path}\n+++ b/{path}\n@@ -1 +1,{len(added.splitlines()) + 1} @@\n VALUE = 1\n"
        + "".join(f"+{line}\n" for line in added.splitlines())
    )


DECL = "diff --git a/system/surfaces.toml b/system/surfaces.toml\n"
DECL += "--- a/system/surfaces.toml\n+++ b/system/surfaces.toml\n"
DECL += '@@ -1,7 +1,7 @@\n schema = "system/schemas/contracts/surfaces.schema.json"\n'
DECL += ' \n [runtime]\n-executables = []\n+executables = ["external-runner"]\n inputs = []\n'
DECL += " \n [[surface]]\n"
M = ("module.py",)
A = ("src/external_adapter.py",)
T = ("system/surfaces.toml",)
E_IMPORT = "product_reference_not_admitted_at_baseline:import:external_sdk"
E_EXEC = "product_reference_not_admitted_at_baseline:executable:external-runner"
E_COMMAND = "product_reference_not_admitted_at_baseline:command:ethos external-operation"
P_IMPORT = _patch(*M, "import external_sdk")
P_EXEC = _patch(*M, 'import subprocess\nCOMMAND = ["external-runner"]\nsubprocess.run(COMMAND)')
C = ("src/commands.py",)
P_COMMAND = _patch(
    *C,
    'from cyclopts import App\napp = App(name="ethos")\n'
    "@app.command\ndef external_operation():\n    return None",
    new=True,
)
P_CONSUMER = _patch("docs/guide.md", "`ethos external-operation`", new=True)
P_NEW = _patch(*A, "VALUE = 1", new=True)
PATCH_CASES = [
    ((), M, P_IMPORT, E_IMPORT),
    ((), M, P_EXEC, E_EXEC),
    (("cyclopts",), C, P_COMMAND, "pass"),
    (("cyclopts",), (*C, "docs/guide.md"), P_COMMAND + P_CONSUMER, E_COMMAND),
    (("external_sdk",), M, P_IMPORT, "head"),
    ((), A, P_NEW, "pass"),
    ((), T + M, DECL + P_EXEC, E_EXEC),
    ((), T, DECL, "pass"),
    ((), M, _patch(*M, 'COMMAND = ["external-runner"]'), E_EXEC),
]


@pytest.mark.parametrize("case", PATCH_CASES)
def test_patch_baseline_reference_path_matrix(
    tmp_path: Path, case: tuple[tuple[str, ...], tuple[str, ...], str, str]
) -> None:
    imports, paths, patch, expected = case
    lane = _lane(tmp_path, imports)
    report = _guard(lane, paths, patch)
    assert "ok" not in report
    if expected.startswith("product_"):
        assert report["verdict"] == "block"
        assert report["error"] == expected
    else:
        assert report["verdict"] == "pass"
        if expected == "head":
            assert cast("dict[str, object]", report["patch_admission"])["baseline_head"] == git(
                lane, "rev-parse", "HEAD"
            )
