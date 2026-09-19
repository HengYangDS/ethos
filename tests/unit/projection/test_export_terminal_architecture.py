"""Exercise immutable terminal projection inputs and semantic obligations."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tests.support.architecture import projection_quality_fixture
from tests.support.governed_repository import git
from tools.ci import architecture_projection
from tools.projection.export_terminal_architecture import export_projection_input

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
EXPORTER_PATH = REPOSITORY_ROOT / "tools/projection/export_terminal_architecture.py"
SCHEMA_PATH = REPOSITORY_ROOT / "system/schemas/projection-input.schema.json"


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(value))


def _fixture_repository(tmp_path: Path, *, effect_authority: bool = False) -> tuple[Path, str]:
    root = tmp_path / "repository"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "projection@example.invalid")
    git(root, "config", "user.name", "Projection Fixture")

    source_path = root / "docs/source.md"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("bounded source assertion\n", encoding="utf-8")
    source_digest = _sha256(source_path.read_bytes())

    semantic_graph = {
        "schema": "ethos.terminal-semantic-graph/v1",
        "sources": {
            "source": {
                "path": "docs/source.md",
                "authority": "fixture semantic authority",
                "sha256": source_digest,
            }
        },
        "nodes": {
            name: {"kind": kind, "label": name.title(), "evidence": ["source"]}
            for name, kind in (("intent", "semantic_root"), ("effect", "effect"))
        },
        "edges": [
            {
                "id": "intent-to-effect",
                "from": "intent",
                "to": "effect",
                "kind": "constrains",
                "source_ids": ["source"],
            }
        ],
    }
    view_profile = {
        "node_projection": {
            "intent": {"view_id": "intent", "mode": "direct"},
        },
        "omitted_nodes": {
            "effect": {"reason": "The fixture renderer intentionally omits effects."},
        },
        "edge_projection": {},
        "omitted_edges": {
            "intent-to-effect": {"reason": "The omitted endpoint makes the edge absent."},
        },
    }
    documents = {
        "semantic_graph": ("semantic-graph", semantic_graph),
        "copy": ("copy", {"schema": "fixture.copy/v1", "title": "Fixture Terminal"}),
        "view_profile": ("view-profile", view_profile),
        "quality_contract": ("quality-contract", projection_quality_fixture(("source",))),
    }
    projection_root = root / "system/projections/terminal-architecture"
    declaration = {
        "schema": "ethos.projection-declaration/v1",
        "id": "fixture-terminal",
        "title": "Fixture Terminal",
        "authority": {
            "semantic_owner": "docs/source.md",
            "scope": "lossless visual assertion selection",
            "effect_authority": effect_authority,
        },
        "sources": [
            {
                "id": "source",
                "path": "docs/source.md",
                "authority": "fixture semantic authority",
            }
        ],
        "documents": {
            role: (projection_root / f"{name}.json").relative_to(root).as_posix()
            for role, (name, _body) in documents.items()
        },
    }
    _write_json(projection_root / "declaration.json", declaration)
    for name, body in documents.values():
        _write_json(projection_root / f"{name}.json", body)
    owner = "src/ethos/repository/policy/projections.py"
    (root / owner).parent.mkdir(parents=True)
    (root / owner).write_bytes((REPOSITORY_ROOT / owner).read_bytes())

    git(root, "add", ".")
    git(root, "commit", "-qm", "fixture")
    return root, git(root, "rev-parse", "HEAD")


def test_export_is_exact_tree_bound_deterministic_and_host_path_free(tmp_path: Path) -> None:
    """One export journey verifies identity, schema, isolation and canonical transport."""
    root, commit = _fixture_repository(tmp_path)
    tree = git(root, "rev-parse", f"{commit}^{{tree}}")
    committed_source = (root / "docs/source.md").read_bytes()
    (root / "docs/source.md").write_text("uncommitted drift\n", encoding="utf-8")
    (root / "src/ethos/repository/policy/projections.py").write_text(
        "raise RuntimeError('uncommitted owner must not run')\n", encoding="utf-8"
    )
    first = export_projection_input(root=root, revision=commit)
    assert first == export_projection_input(root=root, revision=commit)
    isolated = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-S",
            "-c",
            EXPORTER_PATH.read_text(),
            "--root",
            str(root),
            "--revision",
            commit,
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        timeout=30,
    )
    assert json.loads(isolated.stdout) == first
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(first)
    assert first["documents"]["copy"]["title"] == "Fixture Terminal"
    assert json.loads(first["documents"]["quality_contract"]) == projection_quality_fixture(
        ("source",)
    )
    assert "assertion" not in first["semantics"]["nodes"]["intent"]
    assert "assertion" not in first["semantics"]["relations"][0]
    assert first["source"]["revision"] == commit
    assert first["source"]["git"] == {"commit": commit, "tree": tree}
    assert first["source"]["bindings"][0]["sha256"] == _sha256(committed_source)
    assert str(tmp_path) not in json.dumps(first)
    digest = first.pop("digest")
    assert digest == _sha256(_canonical_bytes(first))


@pytest.mark.parametrize(
    "source_state", ["valid", "stale", "missing", "uncommitted", "native_drift"]
)
def test_architecture_gate_checks_the_same_exact_export(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    source_state: str,
) -> None:
    """Source alignment must fail in the cheap gate, not first in heavy tests."""
    root, commit = _fixture_repository(tmp_path)
    source = root / "docs/source.md"
    if source_state == "missing":
        source.unlink()
    elif source_state in {"stale", "uncommitted"}:
        source.write_text("changed source meaning\n", encoding="utf-8")
    if source_state == "native_drift":
        config = root / ".config/checks/architecture/projection.toml"
        config.parent.mkdir(parents=True)
        config.write_text(
            'schema = "ethos-architecture-projection-v1"\n[[projection]]\n'
            'source = "docs/model.c4"\noutput = "docs/model.mmd"\n',
            encoding="utf-8",
        )
        (root / "docs/model.c4").write_text("model {}\n", encoding="utf-8")
        (root / "docs/model.mmd").write_text("invalid rendering\n", encoding="utf-8")
    if source_state in {"stale", "missing"}:
        git(root, "add", ".")
        git(root, "commit", "-qm", "source changed after archive")
        commit = git(root, "rev-parse", "HEAD")
    monkeypatch.setattr(architecture_projection, "ROOT", root)
    monkeypatch.setattr(
        architecture_projection, "CONFIG_PATH", root / ".config/checks/architecture/projection.toml"
    )

    result = architecture_projection.main()
    report = json.loads(capsys.readouterr().out)

    if source_state in {"stale", "missing", "native_drift"}:
        assert result == 1
        assert report["verdict"] == "block"
        reason = report["failures"][0]["reason"]
        expected = {
            "stale": "source digest mismatch: source",
            "missing": "docs/source.md does not exist in the selected Git tree",
            "native_drift": "projection drift: docs/model.mmd",
        }
        assert expected[source_state] in reason
    else:
        assert result == 0
        exported = export_projection_input(root=root, revision=commit)
        terminal = next(p for p in report["projections"] if p["id"] == "terminal-architecture")
        assert report["head"] == commit
        assert terminal["source"] == exported["source"]["git"]
        assert terminal["digest"] == exported["digest"]
        assert terminal["matches"] is True


def test_export_fails_closed_on_stale_or_missing_exact_tree_sources(tmp_path: Path) -> None:
    root, commit = _fixture_repository(tmp_path)
    graph_path = root / "system/projections/terminal-architecture/semantic-graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["sources"]["source"]["sha256"] = "0" * 64
    _write_json(graph_path, graph)
    git(root, "add", ".")
    git(root, "commit", "-qm", "stale binding")

    with pytest.raises(ValueError, match="source digest mismatch"):
        export_projection_input(root=root, revision="HEAD")

    with pytest.raises(ValueError, match="does not exist in the selected Git tree"):
        export_projection_input(root=root, revision=commit, declaration_path="missing.json")


def test_export_rejects_an_altered_source_authority(tmp_path: Path) -> None:
    """An unchanged digest cannot validate a contradictory authority label."""
    root, _commit = _fixture_repository(tmp_path)
    graph_path = root / "system/projections/terminal-architecture/semantic-graph.json"
    graph = json.loads(graph_path.read_text())
    graph["sources"]["source"]["authority"] = "projection is now product authority"
    _write_json(graph_path, graph)
    git(root, "add", ".")
    git(root, "commit", "-qm", "alter authority without changing source")

    with pytest.raises(ValueError, match="source authority mismatch"):
        export_projection_input(root=root)


def test_projection_declaration_cannot_own_repository_effect_authority(tmp_path: Path) -> None:
    root, _commit = _fixture_repository(tmp_path, effect_authority=True)

    with pytest.raises(ValueError, match="effect authority"):
        export_projection_input(root=root, revision="HEAD")


def _revise_projection(root: Path, name: str, revise) -> None:
    path = root / "system/projections/terminal-architecture" / name
    value = json.loads(path.read_text())
    revise(value)
    _write_json(path, value)
    if name == "semantic-graph.json":
        for invariant in value.get("invariants", []):
            invariant.setdefault("source_ids", ["source"])
        _write_json(path, value)
        _write_json(
            path.with_name("quality-contract.json"),
            projection_quality_fixture(
                ("source",), tuple(row["id"] for row in value.get("invariants", []))
            ),
        )
    git(root, "add", ".")
    git(root, "commit", "--allow-empty", "-qm", "revise projection")


def test_export_retains_source_attributes_and_graph_contracts(tmp_path: Path) -> None:
    root, _ = _fixture_repository(tmp_path)

    def revise(graph):
        graph["nodes"]["intent"].update(
            semantics="Accepted intent compiles transiently",
            maturity="terminal",
            required_visible=False,
        )
        graph["edges"][0].update(guard="fresh authorization", effect_capable=False)
        graph["invariants"] = [{"id": "I1", "statement": "Views never authorize effects"}]
        graph["meta"] = {"view": "target, not delivered capability"}

    _revise_projection(root, "semantic-graph.json", revise)
    result = export_projection_input(root=root)
    assert result["schema"] == "projection.input/v2"
    assert result["semantics"]["nodes"]["intent"]["attributes"] == {
        "semantics": "Accepted intent compiles transiently",
        "maturity": "terminal",
        "required_visible": False,
    }
    assert result["semantics"]["relations"][0]["attributes"]["guard"] == "fresh authorization"
    assert result["semantics"]["contracts"]["invariants"][0]["id"] == "I1"
    Draft202012Validator(json.loads(SCHEMA_PATH.read_text())).validate(result)


@pytest.mark.parametrize("kind", ["node", "relation", "invariant"])
@pytest.mark.parametrize("failure", ["omitted", "hidden", "missing-copy"])
def test_required_assertion_rejects_nonvisible_disposition(
    tmp_path: Path,
    kind: str,
    failure: str,
) -> None:
    root, _ = _fixture_repository(tmp_path)
    identity = {"node": "effect", "relation": "intent-to-effect", "invariant": "I1"}[kind]

    def graph_change(graph):
        if kind == "invariant":
            graph["invariants"] = [
                {"id": identity, "statement": "Keep meaning", "required_visible": True}
            ]
        else:
            item = graph["nodes"][identity] if kind == "node" else graph["edges"][0]
            item["required_visible"] = True

    def view_change(view):
        if kind == "invariant":
            view["invariant_projection"] = {}
            projected = view["invariant_projection"]
        else:
            prefix = "node" if kind == "node" else "edge"
            projected = view[f"{prefix}_projection"]
            if failure != "omitted":
                del view[f"omitted_{prefix}s"][identity]
        if failure != "omitted":
            projected[identity] = {"view_id": "effect", "witness": "meaning"}

    _revise_projection(root, "semantic-graph.json", graph_change)
    _revise_projection(root, "view-profile.json", view_change)
    _revise_projection(
        root,
        "copy.json",
        lambda copy: copy.update(
            assertions={
                "meaning": {
                    "text": "Preserve meaning",
                    "surface": "hover" if failure == "hidden" else "main-static",
                }
            }
            if failure != "missing-copy"
            else {}
        ),
    )
    with pytest.raises(ValueError, match=r"required.*witness"):
        export_projection_input(root=root)


def test_required_assertions_accept_readable_shared_aggregation(tmp_path: Path) -> None:
    root, _ = _fixture_repository(tmp_path)
    _revise_projection(
        root,
        "semantic-graph.json",
        lambda graph: graph["nodes"]["intent"].update(required_visible=True),
    )
    _revise_projection(
        root,
        "view-profile.json",
        lambda view: view["node_projection"]["intent"].update(witness="meaning"),
    )
    _revise_projection(
        root,
        "copy.json",
        lambda copy: copy.update(
            assertions={
                "meaning": {"text": "Accepted intent bounds effects", "surface": "main-static"}
            }
        ),
    )
    result = export_projection_input(root=root)
    assert result["view"]["nodes"]["intent"]["project"]["witness"] == "meaning"


def test_required_view_notice_cannot_disappear(tmp_path: Path) -> None:
    root, _ = _fixture_repository(tmp_path)
    _revise_projection(
        root,
        "view-profile.json",
        lambda view: view.update(meta={"required_visible_copy": ["maturity"]}),
    )
    with pytest.raises(ValueError, match=r"required.*maturity.*witness"):
        export_projection_input(root=root)


def test_duplicate_relation_identity_is_not_collapsed(tmp_path: Path) -> None:
    root, _ = _fixture_repository(tmp_path)
    _revise_projection(
        root, "semantic-graph.json", lambda graph: graph["edges"].append(graph["edges"][0])
    )
    with pytest.raises(ValueError, match="duplicate relation"):
        export_projection_input(root=root)


def test_actual_view_accounts_for_each_contract_invariant() -> None:
    """Mapping completeness is a structural floor, not proof of understanding."""
    directory = REPOSITORY_ROOT / "system/projections/terminal-architecture"
    view = json.loads((directory / "view-profile.json").read_text())
    copy = json.loads((directory / "copy.json").read_text())
    mapped = {
        number
        for projection in view["invariant_projection"].values()
        for number in projection.get("contract_invariants", [])
    }
    assert mapped == set(range(1, 16))
    for projection in view["invariant_projection"].values():
        if projection.get("contract_invariants"):
            witness = copy["assertions"][projection["witness"]]
            assert witness["surface"] == "main-static"
            assert witness["text"].strip()


def test_actual_publication_graph_does_not_require_acceptance_for_review() -> None:
    """The publication projection cannot restore the proved-candidate review cycle."""
    directory = REPOSITORY_ROOT / "system/projections/terminal-architecture"
    graph = json.loads((directory / "semantic-graph.json").read_text())
    gate = graph["gates"]["publication_admission_gate"]
    assert "git_substrate" in gate["required_inputs"]
    assert not {"accepted_next", "attestation_n"}.intersection(gate["required_inputs"])
    assert "review" in gate["required_claim_selector"].lower()
    copy = json.loads((directory / "copy.json").read_text())
    visible = copy["assertions"]["publication"]
    assert visible["surface"] == "main-static"
    assert "review" in visible["text"].lower()
    assert "accepted" in visible["text"].lower()
    view = json.loads((directory / "view-profile.json").read_text())
    relation = next(
        edge for edge in graph["edges"] if edge["id"] == "git-projects-publication-object"
    )
    assert (relation["from"], relation["to"]) == ("git_substrate", "publication_remote")
    assert view["edge_projection"][relation["id"]]["source_view"] == "norms"


@pytest.mark.parametrize(
    ("identity", "obligations"),
    [
        ("coordination", ("migration", "rollback", "locked toolchain")),
        ("accepted", ("proposal", "dev", "main", "release")),
        ("intent", ("superseded", "pending verification", "rejected")),
        ("norms", ("one semantic owner", "consumer", "lifecycle")),
        ("capabilities", ("mature", "pure", "effects")),
        ("evidence", ("derived", "no persistent", "ledger")),
        ("verification", ("disabled", "optional", "required", "committed", "identity changes")),
    ],
)
def test_reviewed_invariant_distinctions_remain_in_static_copy(
    identity: str, obligations: tuple[str, ...]
) -> None:
    """Guard reviewed phrases against deletion, without claiming semantic proof."""
    copy = json.loads(
        (REPOSITORY_ROOT / "system/projections/terminal-architecture/copy.json").read_text()
    )
    text = copy["assertions"][identity]["text"].lower()
    assert all(obligation in text for obligation in obligations)
