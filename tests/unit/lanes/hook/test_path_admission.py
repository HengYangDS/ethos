from __future__ import annotations

from pathlib import Path

import pytest

import ethos.adapters.admission.prewrite as admission_prewrite
from ethos.adapters.admission.git_admission import hook_admission_report
from ethos.contracts.admission import HookAdmissionRequest
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import commit_active_change
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.lane_scenarios import leased_worktree


@pytest.fixture(autouse=True)
def actor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    repo = init_git_repo(tmp_path / "repo")
    commit_active_change(repo)
    return leased_worktree(repo, tmp_path / "repo-work-feature")


def _hook(root: Path, path: Path) -> dict[str, object]:
    request = HookAdmissionRequest(
        root=root, layer="pre-tool", paths=(path,), editor_root=root, require_editor_root=True
    )
    return hook_admission_report(request)


def _guard(lane: Path, paths: tuple[str, ...], patch: str | None = None) -> dict[str, object]:
    return admission_prewrite.prewrite_guard(
        root=lane,
        paths=[lane / path for path in paths],
        editor_root=lane,
        require_editor_root=True,
        patch=patch,
    )


@pytest.mark.parametrize(
    ("token", "kind"),
    [("README.md\nAGENTS.md", "control_character"), ("README.md .gitignore", "whitespace")],
)
def test_invalid_path_matrix(worktree: Path, token: str, kind: str) -> None:
    report = _hook(worktree, Path(token))
    reason = f"prewrite_path_invalid_{kind}"
    assert report["verdict"] == "block"
    assert "ok" not in report
    assert report["decision"] == {"action": "block", "reason": reason}
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
    assert reason in report["required_gaps"]


SHADOW = "external_method_pack_shadow_authority:.superpowers/sdd/tasks/progress.md"
IGNORED_CASES = [
    (".superpowers/sdd/tasks/progress.md", ".superpowers/sdd/.gitignore", "*\n", "block", SHADOW),
    ("build/runtime/work/provider/session.json", ".gitignore", "build/\n", "pass", "allowed"),
]


@pytest.mark.parametrize("case", IGNORED_CASES)
def test_ignored_path_matrix(worktree: Path, case: tuple[object, ...]) -> None:
    relative, ignore, content, verdict, reason = case
    path = worktree / relative
    path.parent.mkdir(parents=True)
    path.write_text("{}\n")
    (worktree / ignore).write_text(content)
    report = _hook(worktree, path)
    admitted = report["admission"]["paths"][0]
    assert report["verdict"] == verdict
    assert "ok" not in report
    assert admitted["ignored"] is True
    assert admitted["tracked_candidate"] is False
    assert admitted["allowed"] is (verdict == "pass")
    assert admitted["reason"] == reason
    if verdict == "block":
        assert report["decision"] == {"action": "block", "reason": reason}
        assert report["admission"]["error"] == reason


@pytest.mark.parametrize("mismatch", ["runner", "schema"])
def test_editor_binding_matrix(
    worktree: Path, monkeypatch: pytest.MonkeyPatch, mismatch: str
) -> None:
    profile = worktree / ".ethos/profile.toml"
    profile.write_text(profile.read_text() + '\n[proof]\ngate_registry = "system/gates.toml"\n')
    binding = admission_prewrite.runtime_binding(worktree)
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
    assert report["runtime_binding"]["audit_root"] == worktree.as_posix()
    assert report["editor_root"]["reason"] == "matched"


def test_unknown_editor_component(worktree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def unknown(_status):
        return {"verdict": "unknown", "reason": ""}

    monkeypatch.setattr(admission_prewrite, "runtime_binding_check", unknown)
    report = _guard(worktree, ("README.md",))
    assert report["verdict"] == "unknown"
    assert report["required_gaps"] == []
    assert "ok" not in report


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


def _lane(tmp: Path, _scope: tuple[str, ...], imports: tuple[str, ...]) -> Path:
    repo = init_git_repo(tmp / "repo")
    dependencies = [root.replace("_", "-") for root in imports]
    (repo / "system").mkdir()
    project = f'[project]\nname = "test-product"\nversion = "1"\ndependencies = {dependencies!r}\n'
    (repo / "pyproject.toml").write_text(project.replace("'", '"'))
    tools = 'schema = "system/schemas/contracts/tools.schema.json"\n\n[[tool]]\n'
    tools += 'concern = "test_execution"\ntool = "test tools"\nconfig = "system/tools.toml"\n'
    (repo / "system/tools.toml").write_text(tools + 'profile = "product"\nexecutables = []\n')
    (repo / "module.py").write_text("VALUE = 1\n")
    commit_active_change(repo)
    return leased_worktree(repo, tmp / "repo-work-feature")


def _patch(path: str, added: str, *, new: bool = False) -> str:
    header = f"diff --git a/{path} b/{path}\n"
    if new:
        return (
            header + f"new file mode 100644\n--- /dev/null\n+++ b/{path}\n@@ -0,0 +1 @@\n+{added}\n"
        )
    return header + f"--- a/{path}\n+++ b/{path}\n@@ -1 +1,2 @@\n VALUE = 1\n+{added}\n"


DECL = "diff --git a/system/tools.toml b/system/tools.toml\n--- a/system/tools.toml\n"
DECL += '+++ b/system/tools.toml\n@@ -5,4 +5,4 @@ concern = "test_execution"\n'
DECL += ' tool = "test tools"\n config = "system/tools.toml"\n profile = "product"\n'
DECL += '-executables = []\n+executables = ["external-runner"]\n'
M = ("module.py",)
A = ("src/external_adapter.py",)
T = ("system/tools.toml",)
E_IMPORT = "product_reference_not_admitted_at_baseline:import:external_sdk"
E_EXEC = "product_reference_not_admitted_at_baseline:executable:external-runner"
E_COMMAND = "product_reference_not_admitted_at_baseline:command:external-operation"
P_IMPORT = _patch(*M, "import external_sdk")
P_EXEC = _patch(*M, 'COMMAND = ["external-runner"]')
P_COMMAND = _patch(*M, '@app.command(name="external-operation")')
P_NEW = _patch(*A, "VALUE = 1", new=True)
PATCH_CASES = [
    ((), M, M, P_IMPORT, E_IMPORT),
    ((), M, M, P_EXEC, E_EXEC),
    ((), M, M, P_COMMAND, E_COMMAND),
    (("external_sdk",), M, M, P_IMPORT, "head"),
    ((), ("src/**",), A, P_NEW, "pass"),
    ((), A, A, P_NEW, "pass"),
    ((), M, T + M, DECL + P_EXEC, E_EXEC),
    ((), T, T, DECL, "pass"),
]


@pytest.mark.parametrize("case", PATCH_CASES)
def test_patch_baseline_reference_path_matrix(tmp_path: Path, case: tuple[object, ...]) -> None:
    imports, scope, paths, patch, expected = case
    lane = _lane(tmp_path, scope, imports)
    report = _guard(lane, paths, patch)
    assert "ok" not in report
    if expected.startswith("product_"):
        assert report["verdict"] == "block"
        assert report["error"] == expected
    else:
        assert report["verdict"] == "pass"
        if expected == "head":
            assert report["patch_admission"]["baseline_head"] == git(lane, "rev-parse", "HEAD")
