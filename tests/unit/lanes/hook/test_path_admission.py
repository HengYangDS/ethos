from __future__ import annotations

from pathlib import Path

import pytest

import ethos.adapters.admission.prewrite as admission_prewrite
from ethos.adapters.admission.git_admission import hook_admission_report
from ethos.adapters.admission.prewrite import has_control_character
from ethos.adapters.admission.prewrite import has_path_whitespace
from ethos.contracts.admission import HookAdmissionRequest
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_active_commitment
from tests.support.lane_scenarios import leased_worktree


@pytest.fixture
def worktree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = init_git_repo(tmp_path / "repo")
    write_active_commitment(repo)
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "declare fixture change",
    )
    worktree = leased_worktree(repo, tmp_path / "repo-work-feature")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")
    return worktree


def test_path_token_control_character_detector_covers_ascii_controls() -> None:
    assert has_control_character("README.md") is False
    assert has_control_character("README.md\nAGENTS.md") is True
    assert has_control_character("README.md\x7fAGENTS.md") is True


def test_path_token_whitespace_detector_marks_ambiguous_subjects() -> None:
    assert has_path_whitespace("README.md") is False
    assert has_path_whitespace("README.md .gitignore") is True
    assert has_path_whitespace("README.md\t.gitignore") is True


@pytest.mark.parametrize(
    ("token", "kind"),
    [
        ("README.md\nAGENTS.md", "control_character"),
        ("README.md .gitignore", "whitespace"),
    ],
    ids=["control-character", "whitespace"],
)
def test_pre_tool_hook_rejects_invalid_path_tokens(
    worktree: Path,
    token: str,
    kind: str,
) -> None:
    report = hook_admission_report(
        HookAdmissionRequest(
            root=worktree,
            layer="pre-tool",
            paths=[Path(token)],
            editor_root=worktree,
            require_editor_root=True,
        )
    )

    assert report["verdict"] == "block"
    assert "ok" not in report
    assert report["decision"] == {
        "action": "block",
        "reason": f"prewrite_path_invalid_{kind}",
    }
    assert report["admission"]["paths"] == [
        {
            "path": token,
            "relative_path": "",
            "ignored": False,
            "tracked_candidate": False,
            "allowed": False,
            "reason": f"path_invalid_{kind}",
        }
    ]
    assert f"prewrite_path_invalid_{kind}" in report["required_gaps"]


def test_pre_tool_hook_blocks_ignored_external_method_pack_shadow_authority(
    worktree: Path,
) -> None:
    shadow_path = worktree / ".superpowers/sdd/tasks/progress.md"
    shadow_path.parent.mkdir(parents=True)
    (worktree / ".superpowers/sdd/.gitignore").write_text("*\n", encoding="utf-8")

    report = hook_admission_report(
        HookAdmissionRequest(
            root=worktree,
            layer="pre-tool",
            paths=[shadow_path],
            editor_root=worktree,
            require_editor_root=True,
        )
    )

    gap = "external_method_pack_shadow_authority:.superpowers/sdd/tasks/progress.md"
    assert report["verdict"] == "block"
    assert "ok" not in report
    assert report["decision"] == {"action": "block", "reason": gap}
    assert report["admission"]["error"] == gap
    assert report["admission"]["paths"][0]["ignored"] is True
    assert report["admission"]["paths"][0]["tracked_candidate"] is False
    assert report["admission"]["paths"][0]["reason"] == gap


def test_pre_tool_hook_admits_ignored_runtime_home(worktree: Path) -> None:
    runtime_path = worktree / "build/runtime/work/provider/session.json"
    runtime_path.parent.mkdir(parents=True)
    runtime_path.write_text("{}\n", encoding="utf-8")
    (worktree / ".gitignore").write_text("build/\n", encoding="utf-8")

    report = hook_admission_report(
        HookAdmissionRequest(
            root=worktree,
            layer="pre-tool",
            paths=[runtime_path],
            editor_root=worktree,
            require_editor_root=True,
        )
    )

    assert report["verdict"] == "pass"
    assert "ok" not in report
    assert report["admission"]["paths"][0]["ignored"] is True
    assert report["admission"]["paths"][0]["tracked_candidate"] is False
    assert report["admission"]["paths"][0]["allowed"] is True
    assert report["admission"]["paths"][0]["reason"] == "allowed"


@pytest.mark.parametrize(
    "mismatch",
    ["runner", "schema"],
)
def test_prewrite_blocks_checkout_binding_mismatch(
    worktree: Path,
    monkeypatch: pytest.MonkeyPatch,
    mismatch: str,
) -> None:
    profile = worktree / ".ethos" / "profile.toml"
    profile.write_text(
        profile.read_text(encoding="utf-8") + '\n[proof]\ngate_registry = "system/gates.toml"\n',
        encoding="utf-8",
    )
    original = admission_prewrite.runtime_binding
    runner_matches = mismatch != "runner"
    schema_matches = mismatch != "schema"

    def mismatched(root: Path) -> dict[str, object]:
        binding = original(root)
        binding.update(
            runner_matches_audit_root=runner_matches,
            schema_matches_audit_root=schema_matches,
            runner_source_root=(binding["audit_root"] if runner_matches else "/foreign/runner"),
            schema_source_root=(binding["audit_root"] if schema_matches else "/foreign/schema"),
        )
        return binding

    monkeypatch.setattr(admission_prewrite, "runtime_binding", mismatched)
    report = admission_prewrite.prewrite_guard(
        root=worktree,
        paths=[worktree / "README.md"],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert report["verdict"] == "block"
    assert "ok" not in report
    assert report["error"] == "root_binding_mismatch"
    assert report["runtime_binding"]["audit_root"] == worktree.as_posix()
    assert report["editor_root"]["reason"] == "matched"


def test_prewrite_preserves_unknown_component_without_synthetic_gap(
    worktree: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        admission_prewrite,
        "_runtime_binding_check",
        lambda _status: {"verdict": "unknown", "reason": ""},
    )

    report = admission_prewrite.prewrite_guard(
        root=worktree,
        paths=[worktree / "README.md"],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert report["verdict"] == "unknown"
    assert report["required_gaps"] == []
    assert "ok" not in report


def test_hook_admit_cli_preserves_control_character_path_token(
    worktree: Path,
) -> None:
    payload = run_ethos_blocked(
        "hook",
        "admit",
        "pre-tool",
        "README.md\nAGENTS.md",
        "--root",
        worktree.as_posix(),
        "--editor-root",
        worktree.as_posix(),
        "--require-editor-root",
        "--json",
        cwd=worktree,
    )

    assert payload["data"]["decision"] == {
        "action": "block",
        "reason": "prewrite_path_invalid_control_character",
    }
    assert payload["data"]["target_paths"] == ["README.md\nAGENTS.md"]
    assert payload["data"]["admission"]["paths"][0]["path"] == "README.md\nAGENTS.md"


def _product_baseline(
    repo: Path,
    *,
    scope: tuple[str, ...] = ("module.py",),
    import_roots: tuple[str, ...] = (),
    executables: tuple[str, ...] = (),
) -> None:
    (repo / "system").mkdir()
    dependencies = [root.replace("_", "-") for root in import_roots]
    (repo / "pyproject.toml").write_text(
        f'[project]\nname = "test-product"\nversion = "1"\ndependencies = {dependencies!r}\n'.replace(
            "'", '"'
        ),
        encoding="utf-8",
    )
    (repo / "system" / "tools.toml").write_text(
        f"""schema = "system/schemas/contracts/tools.schema.json"

[[tool]]
concern = "test_execution"
tool = "test tools"
config = "system/tools.toml"
profile = "product"
executables = {list(executables)!r}
""".replace("'", '"'),
        encoding="utf-8",
    )
    (repo / ".ethos").mkdir(exist_ok=True)
    write_active_commitment(repo, scope=scope)
    (repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "declare product baseline",
    )


def _patch(path: str, before: str, added: str, *, new: bool = False) -> str:
    if new:
        return (
            f"diff --git a/{path} b/{path}\nnew file mode 100644\n"
            f"--- /dev/null\n+++ b/{path}\n@@ -0,0 +1 @@\n+{added}\n"
        )
    return (
        f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n"
        f"@@ -1 +1,2 @@\n {before}\n+{added}\n"
    )


def test_patch_prewrite_rejects_reference_not_declared_at_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _product_baseline(repo)
    lane = leased_worktree(repo, tmp_path / "repo-work-feature")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")

    report = admission_prewrite.prewrite_guard(
        root=lane,
        paths=[lane / "module.py"],
        editor_root=lane,
        require_editor_root=True,
        patch=_patch("module.py", "VALUE = 1", "import external_sdk"),
    )

    assert report["verdict"] == "block"
    assert "ok" not in report
    assert report["error"] == ("product_reference_not_admitted_at_baseline:import:external_sdk")


@pytest.mark.parametrize(
    ("added", "kind", "reference"),
    [
        ('COMMAND = ["external-runner"]', "executable", "external-runner"),
        ('@app.command(name="external-operation")', "command", "external-operation"),
    ],
)
def test_patch_prewrite_rejects_each_undeclared_machine_reference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    added: str,
    kind: str,
    reference: str,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _product_baseline(repo)
    lane = leased_worktree(repo, tmp_path / "repo-work-feature")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")

    report = admission_prewrite.prewrite_guard(
        root=lane,
        paths=[lane / "module.py"],
        editor_root=lane,
        require_editor_root=True,
        patch=_patch("module.py", "VALUE = 1", added),
    )

    assert report["error"] == (f"product_reference_not_admitted_at_baseline:{kind}:{reference}")


def test_patch_prewrite_admits_reference_declared_at_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _product_baseline(repo, import_roots=("external_sdk",))
    lane = leased_worktree(repo, tmp_path / "repo-work-feature")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")

    report = admission_prewrite.prewrite_guard(
        root=lane,
        paths=[lane / "module.py"],
        editor_root=lane,
        require_editor_root=True,
        patch=_patch("module.py", "VALUE = 1", "import external_sdk"),
    )

    assert report["verdict"] == "pass"
    assert "ok" not in report
    assert report["patch_admission"]["baseline_head"] == git(lane, "rev-parse", "HEAD")


def test_patch_prewrite_requires_exact_baseline_scope_for_new_entity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _product_baseline(repo, scope=("src/**",))
    lane = leased_worktree(repo, tmp_path / "repo-work-feature")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")

    report = admission_prewrite.prewrite_guard(
        root=lane,
        paths=[lane / "src" / "external_adapter.py"],
        editor_root=lane,
        require_editor_root=True,
        patch=_patch("src/external_adapter.py", "", "VALUE = 1", new=True),
    )

    assert report["verdict"] == "block"
    assert "ok" not in report
    assert report["error"] == ("product_path_not_admitted_at_baseline:src/external_adapter.py")


def test_patch_prewrite_admits_exactly_declared_new_entity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _product_baseline(repo, scope=("src/external_adapter.py",))
    lane = leased_worktree(repo, tmp_path / "repo-work-feature")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")

    report = admission_prewrite.prewrite_guard(
        root=lane,
        paths=[lane / "src" / "external_adapter.py"],
        editor_root=lane,
        require_editor_root=True,
        patch=_patch("src/external_adapter.py", "", "VALUE = 1", new=True),
    )

    assert report["verdict"] == "pass"
    assert "ok" not in report


def test_patch_cannot_declare_and_consume_reference_in_same_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _product_baseline(repo)
    lane = leased_worktree(repo, tmp_path / "repo-work-feature")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")
    declaration_patch = (
        "diff --git a/system/tools.toml b/system/tools.toml\n"
        "--- a/system/tools.toml\n+++ b/system/tools.toml\n"
        '@@ -5,4 +5,4 @@ concern = "test_execution"\n'
        ' tool = "test tools"\n config = "system/tools.toml"\n profile = "product"\n'
        '-executables = []\n+executables = ["external-runner"]\n'
    )
    consumption_patch = _patch("module.py", "VALUE = 1", 'COMMAND = ["external-runner"]')

    report = admission_prewrite.prewrite_guard(
        root=lane,
        paths=[lane / "system" / "tools.toml", lane / "module.py"],
        editor_root=lane,
        require_editor_root=True,
        patch=declaration_patch + consumption_patch,
    )

    assert report["verdict"] == "block"
    assert "ok" not in report
    assert report["error"] == (
        "product_reference_not_admitted_at_baseline:executable:external-runner"
    )


def test_patch_prewrite_allows_declaration_only_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _product_baseline(repo, scope=("system/tools.toml",))
    lane = leased_worktree(repo, tmp_path / "repo-work-feature")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")
    patch = (
        "diff --git a/system/tools.toml b/system/tools.toml\n"
        "--- a/system/tools.toml\n+++ b/system/tools.toml\n"
        '@@ -5,4 +5,4 @@ concern = "test_execution"\n'
        ' tool = "test tools"\n config = "system/tools.toml"\n profile = "product"\n'
        '-executables = []\n+executables = ["external-runner"]\n'
    )

    report = admission_prewrite.prewrite_guard(
        root=lane,
        paths=[lane / "system" / "tools.toml"],
        editor_root=lane,
        require_editor_root=True,
        patch=patch,
    )

    assert report["verdict"] == "pass"
    assert "ok" not in report
