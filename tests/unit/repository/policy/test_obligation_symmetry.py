"""A repository's obligations are one function of its authored carriers and declared values."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import ethos
from ethos.adapters.repo.gate_policy import resolve_proof_policies
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

_FLOOR_FIELDS = (
    "quality_floor_version",
    "code_correctness_map",
    "quality_subjects",
    "quality_carrier_roles",
)
_VERIFIERS = "".join(
    f'[[gates]]\nid = "native-{axis}"\nkind = "{kind}"\n'
    f'providers = ["ethos.adapters.gates.code_quality:{axis}_report"]\n'
    'profile = "repository"\ntoolchain = "ethos"\nexecution_mode = "provider"\n'
    f'dimensions = ["{dimension}"]\nevidence_class = "proof"\ntrust_bearing = true\n\n'
    for axis, kind, dimension in (
        ("static", "lint", "static-analysis"),
        ("behavior", "test", "behavior"),
    )
)
_REGISTRY = (
    'schema_version = 1\nid = "symmetry"\n\n[proof_sets]\n'
    'default = ["native-static", "native-behavior"]\n'
    'full = ["native-static", "native-behavior"]\n\n' + _VERIFIERS
)
# A tree that builds the product ships its shared registry at the packaged path.
_SHARED = (
    'schema_version = 1\nid = "gate-registry"\n\n'
    '[proof_sets]\ndefault = ["prose"]\nfull = ["prose"]\n\n'
    '[[gates]]\nid = "prose"\nkind = "docs"\nrequired_for_paths = ["*.md"]\n'
    'providers = ["ethos.adapters.gates.tool:prose_report"]\nprofile = "repository"\n'
    'tool_adapter = "ethos"\ndimensions = ["fixture-supplied"]\n'
)
_PROVIDER = '"""A tree-supplied copy of the shared provider module."""\n'


def _fixture(
    root: Path,
    *,
    profile_id: str = "symmetry",
    registry: str = "system/gates.toml",
    project: str = "sample",
) -> tuple[Path, str]:
    repo = init_git_repo(root)
    profile = f'profile_id = "{profile_id}"\n\n[proof]\ngate_registry = "{registry}"\n'
    manifest = f'[project]\nname = "{project}"\nversion = "0"\nrequires-python = ">=3.12"\n'
    files = {
        ".ethos/profile.toml": profile,
        registry: _REGISTRY,
        "pyproject.toml": manifest,
        "src/app.py": "answer = 42\n",
    }
    for relative, content in files.items():
        (repo / relative).parent.mkdir(parents=True, exist_ok=True)
        (repo / relative).write_text(content, encoding="utf-8")
    return repo, commit_fixture(repo, "declare the obligation fixture")


def _obligations(repo: Path, ref: str) -> dict[str, tuple[object, dict[str, object]]]:
    obligations: dict[str, tuple[object, dict[str, object]]] = {}
    for floor, policy in resolve_proof_policies(repo, tree_ref=ref):
        owner = policy.projection["owner"]
        assert isinstance(owner, dict)
        fields = {field: owner.get(field) for field in _FLOOR_FIELDS}
        obligations[floor] = (policy.projection["gates"], fields)
    return obligations


def test_names_paths_locations_and_histories_leave_the_obligations_unchanged(
    tmp_path: Path,
) -> None:
    """Profile id, registry path, location and ancestry are not inputs of any obligation."""
    repo, head = _fixture(tmp_path / "base")
    expected = _obligations(repo, head)
    git(repo, "checkout", "-q", "--orphan", "unrelated")
    unrelated = commit_fixture(repo, "record the same tree in an unrelated history")
    variants = [
        _fixture(tmp_path / "renamed", profile_id="renamed"),
        _fixture(tmp_path / "moved", registry="system/repository-gates.toml"),
        _fixture(tmp_path / "elsewhere" / "nested"),
        (repo, unrelated),
    ]
    assert expected["full"][1]["quality_floor_version"] == 2
    assert all(_obligations(*variant) == expected for variant in variants)


@pytest.mark.parametrize("project", ["ethos", "ETHOS", "sample"])
def test_a_tree_that_builds_the_running_product_supplies_its_shared_data(
    tmp_path: Path, project: str
) -> None:
    """The running distribution's own source is judged by the shared data it builds."""
    repo, _ = _fixture(tmp_path / "repo", registry="system/repository-gates.toml", project=project)
    for relative, content in (
        ("system/gates.toml", _SHARED),
        ("src/ethos/adapters/gates/tool.py", _PROVIDER),
    ):
        (repo / relative).parent.mkdir(parents=True, exist_ok=True)
        (repo / relative).write_text(content, encoding="utf-8")
    head = commit_fixture(repo, "ship a shared registry and provider")

    policy = dict(resolve_proof_policies(repo, tree_ref=head))["full"]

    own = project.lower() == ethos.__name__
    provider = (
        _PROVIDER.encode()
        if own
        else (Path(ethos.__file__).parent / "adapters/gates/tool.py").read_bytes()
    )
    assert dict(dict(policy.sources)["prose"]) == {
        "@ethos/adapters/gates/tool.py": hashlib.sha256(provider).hexdigest()
    }
    prose = next(gate for gate in policy.gates if gate.id == "prose")
    assert (prose.dimensions == ("fixture-supplied",)) is own
