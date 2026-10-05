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
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo
from tests.support.proof import declare_quality_profile
from tests.support.proof import run_quality_proof


def _locked_upstream_member(repo: Path, original: bytes) -> tuple[str, str]:
    """Publish one exact native tar member and its npm lock identity in the fixture."""
    archive = repo / "upstream.tgz"
    member = "package/source.py"
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
    declaration = ".config/checks/ci/templates.toml"
    owner = repo / declaration
    owner.parent.mkdir(parents=True)
    owner.write_text(
        tomli_w.dumps(
            {
                "schema": "ethos-ci-template-consistency-v1",
                "projection": [{"template": "template.txt", "projection": generated_path}],
            }
        )
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
    profile.write_text(tomli_w.dumps(payload))
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
