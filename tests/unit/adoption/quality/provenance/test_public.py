"""Exercise source integrity and both code-quality axes through the public command."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import tarfile
import tomllib
from pathlib import Path

import pytest
import tomli_w

import tests
import tools.ci.sessions as ci_sessions
from ethos.adapters.gates.code_quality import behavior_report
from ethos.adapters.gates.code_quality import static_report
from ethos.adapters.gates.formatting import render_source_content
from ethos.adapters.gates.provenance.observation import integrity_report
from ethos.adapters.repo.gate_policy import observe_quality_subjects
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo
from tests.support.proof import declare_quality_profile
from tests.support.proof import run_quality_proof


def _locked_upstream_member(
    repo: Path, original: bytes, member: str = "package/source.py"
) -> tuple[str, str]:
    """Publish one exact native tar member and its npm lock identity in the fixture."""
    archive = repo / "upstream.tgz"
    with tarfile.open(archive, "w:gz") as stream:
        entry = tarfile.TarInfo(member)
        entry.size = len(original)
        stream.addfile(entry, io.BytesIO(original))
    integrity = "sha512-" + base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode()
    (repo / "package-lock.json").write_text(
        json.dumps(
            {
                "lockfileVersion": 3,
                "packages": {
                    "node_modules/example": {
                        "resolved": "file:upstream.tgz",
                        "integrity": integrity,
                    }
                },
            }
        )
    )
    return "package-lock.json#packages/node_modules/example", member


@pytest.mark.parametrize(
    "defect", ["none", "artifact-drift", "upstream-drift", "authored", "unbound", "unlabelled"]
)
def test_public_quality_gate_requires_native_artifact_integrity(
    tmp_path: Path, defect: str
) -> None:
    """Artifacts retain real behavior duties while their native owners prove exact bytes."""
    repo = init_git_repo(tmp_path / "adopter")
    declare_quality_profile(repo)
    fixture = Path(tests.__file__).resolve().parent / "fixtures" / "quality-sample"
    for name in ("pyproject.toml", "uv.lock"):
        (repo / name).write_bytes((fixture / name).read_bytes())
    (repo / ".gitignore").write_text(".venv/\n__pycache__/\n")
    source = repo / "src/sample"
    source.mkdir(parents=True)
    authored = "def answer() -> int:\n    return 42\n"
    (source / "__init__.py").write_text(
        "import math\n" + authored if defect == "authored" else authored
    )
    original = b"import math\nVALUE = 42\n"
    (repo / "template.txt").write_bytes(original)
    generated_path = "src/sample/generated.py"
    (repo / generated_path).write_bytes(
        original + b"# drift\n" if defect == "artifact-drift" else original
    )
    upstream_path = "src/sample/upstream.py"
    (repo / upstream_path).write_bytes(
        original + b"# drift\n" if defect == "upstream-drift" else original
    )
    reference, member = _locked_upstream_member(repo, original)
    (repo / "tests").mkdir()
    (repo / "tests/test_sample.py").write_text(
        "from sample import answer\n"
        "from sample.generated import VALUE as GENERATED\n"
        "from sample.upstream import VALUE as UPSTREAM\n\n\n"
        "def test_answer() -> None:\n    assert answer() == GENERATED == UPSTREAM == 42\n"
    )
    declaration = ".config/checks/ci-projection/policy.toml"
    owner = repo / declaration
    owner.parent.mkdir(parents=True)
    owner.write_bytes(
        render_source_content(
            repo,
            declaration,
            "taplo",
            tomli_w.dumps(
                {
                    "schema": "ethos-ci-template-consistency-v1",
                    "projection": [{"template": "template.txt", "projection": generated_path}],
                }
            ).encode(),
        )[0]
    )
    (repo / ".gitattributes").write_text(f"{generated_path} ethos-role=generated\n")
    profile = repo / ".ethos/profile.toml"
    payload = tomllib.loads(profile.read_text())
    payload["proof"]["code_correctness_gates"].append("integrity")
    payload["proof"]["gates"].append(
        {
            "id": "integrity",
            "kind": "integrity",
            "providers": ["ethos.adapters.gates.provenance.observation:integrity_report"],
            "trust_bearing": True,
        }
    )
    for gate in payload["proof"]["gates"][:2]:
        gate["depends_on"] = ["integrity"]
    if defect != "unlabelled":
        payload["proof"]["source_contracts"] = [
            {
                "kind": "generated",
                "input_refs": [declaration],
                "members": {generated_path: [declaration, generated_path]},
                "integrity_gate": "static" if defect == "unbound" else "integrity",
            },
            {
                "kind": "upstream",
                "input_refs": [reference],
                "members": {upstream_path: [reference, member]},
                "integrity_gate": "integrity",
            },
        ]
    profile.write_bytes(
        render_source_content(
            repo, profile.relative_to(repo).as_posix(), "taplo", tomli_w.dumps(payload).encode()
        )[0]
    )
    head = commit_fixture(repo, "declare complete mixed native quality obligations")
    result = run_quality_proof(repo, head)
    report = json.loads(result.stdout)
    if defect == "none":
        assert (result.returncode, report["verdict"], report["required_gaps"]) == (0, "pass", []), (
            report
        )
        policy = resolve_gate_policy(repo, tree_ref=head, full=True)
        owner = policy.projection["owner"]
        assert isinstance(owner, dict)
        subjects = owner["quality_subjects"]
        assert isinstance(subjects, dict)
        assert generated_path in subjects["static-analysis"]
        assert upstream_path in subjects["static-analysis"]
        assert set(subjects["behavior"]) == {
            "src/sample/__init__.py",
            generated_path,
            upstream_path,
        }
    else:
        assert result.returncode != 0, report
        assert report["verdict"] == "block", report
        assert report["required_gaps"]
    assert report["summary"]["proof_attestation_issued"] is False


class _JavaScriptLintSession:
    """Capture the existing session's real native reports and propagate refusals."""

    def __init__(self) -> None:
        self.reports: list[dict[str, object]] = []

    def log(self, message: str) -> None:
        self.reports.append(json.loads(message))

    def error(self, message: str) -> None:
        raise ValueError(message)


def _javascript_supply_repository(tmp_path: Path, *, kind: str, role: str, entered: bool) -> Path:
    """Bind identical JavaScript bytes to real producer, lock, or authored identities."""
    repo = init_git_repo(tmp_path / "javascript")
    declare_quality_profile(repo)
    original = b"const unused = 0;\nexport const supplied = 42;\n"
    (repo / "supply.js").write_bytes(original)
    (repo / ".gitattributes").write_text(f"supply.js ethos-role={role}\n")
    (repo / "package.json").write_text(
        json.dumps(
            {
                "type": "module",
                "scripts": {
                    "test": "node --test answer.test.js",
                    "test:coverage": "c8 --config .config/coverage.json npm test",
                },
            }
        )
    )
    config = repo / ".config/coverage.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        json.dumps(
            {
                "all": True,
                "include": ["answer.js"],
                "lines": 100,
                "branches": 100,
                "functions": 100,
                "statements": 100,
            }
        )
    )
    (repo / "answer.js").write_text(
        'import { supplied } from "./supply.js";\n\n'
        "export function answer() {\n  return supplied;\n}\n"
        if entered
        else "export function answer() {\n  return 42;\n}\n"
    )
    (repo / "answer.test.js").write_text(
        'import test from "node:test";\n'
        'import assert from "node:assert/strict";\n'
        'import { answer } from "./answer.js";\n\n'
        'test("answer", () => {\n  assert.equal(answer(), 42);\n});\n'
    )
    profile = repo / ".ethos/profile.toml"
    payload = tomllib.loads(profile.read_text())
    if kind != "authored":
        if kind == "generated":
            reference = ".config/checks/ci-projection/policy.toml"
            member = "supply.js"
            (repo / "template.txt").write_bytes(original)
            owner = repo / reference
            owner.parent.mkdir(parents=True)
            owner.write_text(
                tomli_w.dumps(
                    {
                        "schema": "ethos-ci-template-consistency-v1",
                        "projection": [{"template": "template.txt", "projection": member}],
                    }
                )
            )
        else:
            reference, member = _locked_upstream_member(repo, original, "package/source.js")
        payload["proof"]["code_correctness_gates"].append("integrity")
        payload["proof"]["gates"].append(
            {
                "id": "integrity",
                "kind": "integrity",
                "providers": ["ethos.adapters.gates.provenance.observation:integrity_report"],
                "trust_bearing": True,
            }
        )
        for gate in payload["proof"]["gates"][:2]:
            gate["depends_on"] = ["integrity"]
        payload["proof"]["source_contracts"] = [
            {
                "kind": kind,
                "input_refs": [reference],
                "members": {"supply.js": [reference, member]},
                "integrity_gate": "integrity",
            }
        ]
        profile.write_text(tomli_w.dumps(payload))
    commit_fixture(repo, "bind exact JavaScript source obligations")
    return repo


@pytest.mark.parametrize(
    ("kind", "role", "entered", "verdict"),
    [
        ("authored", "code", True, "block"),
        ("generated", "snapshot", True, "pass"),
        ("generated", "snapshot", False, "block"),
        ("upstream", "snapshot", False, "pass"),
        ("upstream", "code", True, "pass"),
        ("upstream", "code", False, "block"),
    ],
)
def test_javascript_provenance_preserves_native_lexical_and_behavior_obligations(
    tmp_path: Path, kind: str, role: str, *, entered: bool, verdict: str
) -> None:
    """Native provenance changes analysis, never raw execution or byte authenticity."""
    repo = _javascript_supply_repository(tmp_path, kind=kind, role=role, entered=entered)
    _, subjects = observe_quality_subjects(repo)
    supply = next(subject for subject in subjects if subject.path == "supply.js")
    assert supply.source_kind == kind
    assert supply.role == role
    assert integrity_report(repo)["verdict"] == "pass"
    lexical = static_report(repo)
    assert lexical["verdict"] == ("block" if kind == "authored" else "pass"), lexical
    behavior = behavior_report(repo, timeout_seconds=60)
    assert behavior["verdict"] == verdict, behavior
    native_reports = behavior["native"]
    assert isinstance(native_reports, list)
    assert len(native_reports) == 1
    native = native_reports[0]
    assert isinstance(native, dict)
    assert native["native_selection"]["selected_paths"] == ["answer.js"]
    assert native["raw_identity_preserved"] is True
    assert native["executed_generated_paths"] == (
        ["supply.js"] if kind != "authored" and entered else []
    )
    assert not any(
        str(argument).startswith(("--include=", "--exclude="))
        for argument in native["coverage_execution"]["argv"]
    )


@pytest.mark.parametrize(
    ("kind", "role"),
    [
        ("authored", "code"),
        ("authored", "snapshot"),
        ("generated", "snapshot"),
        ("upstream", "snapshot"),
    ],
)
def test_javascript_lint_session_uses_native_authored_partition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str, role: str
) -> None:
    """The Nox consumer cannot apply authored ESLint or formatting to frozen supply."""
    repo = _javascript_supply_repository(tmp_path, kind=kind, role=role, entered=False)
    originals = {path: path.read_bytes() for path in repo.glob("*.js")}
    monkeypatch.setattr(ci_sessions, "ROOT", repo)
    session = _JavaScriptLintSession()
    if kind == "authored":
        reason = "source_contract_missing:supply.js" if role == "snapshot" else "no-unused-vars"
        with pytest.raises(ValueError, match=reason):
            ci_sessions.javascript_lint(session)
        assert session.reports == []
    else:
        ci_sessions.javascript_lint(session)
        assert session.reports == [
            {
                "id": "source-format",
                "verdict": "pass",
                "state": "passed",
                "files": ["answer.js", "answer.test.js"],
                "file_count": 2,
                "changed_paths": [],
                "ignored_paths": [],
                "required_gaps": [],
            }
        ]
    assert all(path.read_bytes() == original for path, original in originals.items())


def test_javascript_lint_session_refuses_authored_format_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Authored format drift remains a native refusal without rewriting any source."""
    repo = _javascript_supply_repository(tmp_path, kind="generated", role="snapshot", entered=False)
    (repo / "answer.js").write_text("export function answer(){return 42;}\n")
    commit_fixture(repo, "record authored formatting drift")
    originals = {path: path.read_bytes() for path in repo.glob("*.js")}
    monkeypatch.setattr(ci_sessions, "ROOT", repo)
    session = _JavaScriptLintSession()

    with pytest.raises(ValueError, match="native source formatting did not pass"):
        ci_sessions.javascript_lint(session)

    assert session.reports == [
        {
            "id": "source-format",
            "verdict": "block",
            "state": "failed",
            "files": ["answer.js", "answer.test.js"],
            "file_count": 2,
            "changed_paths": ["answer.js"],
            "ignored_paths": [],
            "required_gaps": ["source_format_drift:answer.js"],
        }
    ]
    assert all(path.read_bytes() == original for path, original in originals.items())


@pytest.mark.parametrize("role", ["snapshot", "generated"])
@pytest.mark.parametrize("floor", ["profile", "packaged"])
def test_public_quality_requires_source_binding_before_native_dispatch(
    tmp_path: Path, role: str, floor: str
) -> None:
    """A lint-clean artifact claim needs provenance, not an authored-style exemption."""
    repo = _javascript_supply_repository(tmp_path, kind="authored", role=role, entered=False)
    (repo / "supply.js").write_text("export const supplied = 42;\n")
    if floor == "packaged":
        source = Path(tests.__file__).resolve().parent.parent
        registry = repo / "system/gates.toml"
        registry.parent.mkdir()
        registry.write_bytes((source / "system/gates.toml").read_bytes())
        profile_path = repo / ".ethos/profile.toml"
        profile = tomllib.loads(profile_path.read_text())
        profile["proof"] = {"gate_registry": "system/gates.toml"}
        profile_path.write_text(tomli_w.dumps(profile))
    head = commit_fixture(repo, "record clean artifact bytes without a source relationship")
    gap = "source_contract_missing:supply.js"
    policy = resolve_gate_policy(repo, tree_ref=head, full=True)
    assert gap in policy.gaps
    owner = policy.projection["owner"]
    assert isinstance(owner, dict)
    assert owner.get("quality_floor_version") == 2, "a copied product registry keeps the floor"
    result = run_quality_proof(repo, head)
    report = json.loads(result.stdout)
    assert result.returncode != 0, report
    assert report["verdict"] == "block", report
    assert gap in report["required_gaps"], report
    assert report["summary"]["proof_attestation_issued"] is False
    with pytest.raises(ValueError, match=gap):
        observe_quality_subjects(repo)
    for axis, report in (
        ("static-analysis", static_report(repo)),
        ("behavior", behavior_report(repo, timeout_seconds=60)),
    ):
        assert report["verdict"] == "block", report
        assert report["required_gaps"] == [f"quality_{axis}_{gap}"]
        assert "native" not in report


@pytest.mark.parametrize("kind", ["generated", "upstream"])
def test_javascript_artifact_analysis_cannot_certify_changed_supply(
    tmp_path: Path, kind: str
) -> None:
    """Skipping authored rules cannot authenticate a changed producer or archive member."""
    repo = _javascript_supply_repository(tmp_path, kind=kind, role="snapshot", entered=False)
    assert integrity_report(repo)["verdict"] == "pass"
    original = (repo / "supply.js").read_bytes()
    (repo / "supply.js").write_bytes(original + b"// drift\n")
    assert (repo / "supply.js").read_bytes() != original
    commit_fixture(repo, "record altered artifact without changing its native input")
    integrity = integrity_report(repo)
    assert integrity["verdict"] == "unknown", integrity
    gaps = integrity["required_gaps"]
    assert isinstance(gaps, list)
    assert "source_integrity_unproven:supply.js" in gaps
