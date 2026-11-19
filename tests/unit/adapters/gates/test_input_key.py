"""A gate's input key, the record and comparison of its results, and what its providers open."""

from __future__ import annotations

import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from functools import partial
from threading import Barrier
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import ethos.adapters.gates.input_key as input_key
import ethos.application.proof.host as host
from ethos.adapters.gates.verification import provider_reports
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.store.state.schema import local_state_root
from ethos.application.docs_registry import DOCS_REGISTRY_PROVIDER
from ethos.contracts.gate_providers import provider_catalog
from ethos.repository.release.identity import BuildIdentity
from tests.support.ethos_cli_runner import ROOT
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_tree

if TYPE_CHECKING:
    from pathlib import Path

_DOCS = ("provider", "provider.docs-registry")
_GATE = {"id": "docs-registry", "execution_identity": list(_DOCS), "sources": []}
_COMMAND = {"execution_identity": ["python", "check.py"]}
_NAMED = dict.fromkeys(("product", "python", "platform", "git", "attributes", "ignored"), "one")
_DOC, _CODE = ("docs/a.md", "100644 blob 1"), ("lib/a.py", "100644 blob 2")
_MOVED = (_DOC, ("lib/a.py", "100644 blob 9"))
_RUN = input_key.RunInputs((_DOC, _CODE), _NAMED, frozenset(), 0)
_OTHER = BuildIdentity("1", "1", "c" * 40, "d" * 40)


def _key(run: input_key.RunInputs = _RUN, **gate: object) -> object:
    return input_key.input_key(_GATE | gate, run)["key"]


def test_the_packaged_table_names_catalog_providers_and_none_twice() -> None:
    """Every stated or open provider is a catalog ID, and no provider is both."""
    inputs, unbounded = input_key.statements()

    assert set(inputs) | unbounded <= set(provider_catalog()[0])
    assert not unbounded & set(inputs)


@pytest.mark.parametrize(
    ("identity", "kind"),
    [
        (_DOCS, "declared"),
        (("provider", "ethos.application.docs_registry:docs_registry_report"), "declared"),
        (("provider", "tests.fixture:provider"), "tree"),
        (("python", "-m", "nox", "-s", "unit"), "tree"),
        (("provider", "provider.repository-audit"), "open"),
        ((*_DOCS, "provider.repository-audit"), "open"),
    ],
)
def test_a_gate_is_stated_keyed_by_the_whole_tree_or_open(identity, kind) -> None:
    """Only a gate whose every provider the table states is keyed by less than the tree."""
    assert input_key.gate_statement(identity)[0] == kind


@pytest.mark.parametrize(
    ("base", "gate", "run", "same"),
    [
        ({}, {}, {"entries": _MOVED}, True),
        ({}, {}, {"entries": (("docs/a.md", "100644 blob 9"), _CODE)}, False),
        ({}, {}, {"entries": (("docs/a.md", "100755 blob 1"), _CODE)}, False),
        ({}, {}, {"entries": (_CODE,)}, False),
        ({}, {}, {"entries": _MOVED, "product_paths": {"lib/a.py"}}, False),
        (_COMMAND, {}, {"entries": _MOVED}, False),
        ({}, {"timeout_seconds": 5}, {}, False),
        ({}, {"sources": [{"path": "lib/a.py", "sha256": "1"}]}, {}, False),
        *(({}, {}, {"named": _NAMED | {name: "other"}}, False) for name in _NAMED),
    ],
)
def test_the_key_follows_the_gate_its_selected_paths_and_each_named_input(
    base, gate, run, same
) -> None:
    """A path outside the statement leaves the key; a command gate selects every path."""
    assert (_key(_RUN._replace(**run), **base, **gate) == _key(**base)) is same


def test_local_git_state_is_a_named_input_and_no_environment_value_is(
    tmp_path: Path, monkeypatch
) -> None:
    """A local attribute line and a new ignored directory each move the key; a variable does not."""
    repo = init_git_repo(tmp_path / "repo")
    runs = [input_key.run_inputs(repo, current_tree(repo), _OTHER)]
    monkeypatch.setenv("GATE_REUSE_MARKER", "marker-value")
    for local in (
        {},
        {".git/info/attributes": "# local\n\n*.md linguist-generated\n"},
        {".git/info/exclude": "cache/\n", "cache/entry": ""},
    ):
        write_tree(repo, local)
        runs.append(input_key.run_inputs(repo, current_tree(repo), _OTHER))
    keys = [_key(run) for run in runs]

    assert keys[0] == keys[1]
    assert len(set(keys)) == 3
    assert [run.attribute_lines for run in runs] == [0, 0, 1, 1]


def test_the_product_tree_states_its_source_and_carried_files_in_place_of_a_build() -> None:
    """Where the running product is built from the proved tree, its files are paths of the key."""
    tree = current_tree(ROOT)
    own = input_key.run_inputs(ROOT, tree, _OTHER._replace(source_tree=tree))
    other = input_key.run_inputs(ROOT, tree, _OTHER)
    moved = tuple(
        (path, "0" if path == "src/ethos/result.py" else meta) for path, meta in own.entries
    )

    assert {"src/ethos/result.py", "system/gates.toml", "pyproject.toml"} <= own.product_paths
    assert (own.named["product"], other.product_paths) == ("tree", frozenset())
    assert _key(own) != _key(own._replace(entries=moved))
    assert _key(other) == _key(other._replace(entries=moved))


def test_a_run_is_one_content_addressed_record_and_only_a_parsed_one_is_read(
    tmp_path: Path,
) -> None:
    """The record's name is its digest; an unparsable file or another schema holds no result."""
    row = {"gate": "g", "key": "k", "verdict": "pass"}
    document = {"schema": 1, "head": "h", "tree": "t", "results": [row]}

    path = input_key.record_results(tmp_path, document)
    for name, content in (("broken", "{"), ("list", "[]"), ("later", '{"schema": 2}')):
        (path.parent / f"{name}.json").write_text(content, encoding="utf-8")

    assert path == input_key.record_results(tmp_path, document)
    assert path.stem == hashlib.sha256(path.read_bytes()).hexdigest()
    assert input_key.earlier_results(tmp_path) == {("g", "k"): [row | {"tree": "t"}]}


@pytest.mark.parametrize(
    ("earlier", "verdict", "statement", "expected"),
    [
        ([("pass", "u"), ("pass", "t")], "pass", "tree", ("agree", 2, 1, [])),
        ([("block", "u")], "pass", "declared", ("mismatch", 1, 1, ["u"])),
        ([("pass", "t")], "block", "declared", ("mismatch", 1, 0, ["t"])),
        ([("block", "u")], "pass", "open", ("open", 1, 1, ["u"])),
        ([("unknown", "t")], "pass", "declared", ("none",)),
        ([([], "t")], "pass", "declared", ("none",)),
        ([("pass", "t")], "unknown", "declared", ("none",)),
    ],
)
def test_a_decided_verdict_is_compared_with_the_decided_results_of_its_key(
    earlier, verdict, statement, expected
) -> None:
    """The state, the decided earlier results, those of another tree, and a differing tree.

    A verdict of another form in a parsed record, here a list, is not a decided result.
    """
    rows = [{"verdict": result, "tree": tree} for result, tree in earlier]

    assert tuple(input_key.comparison(rows, verdict, "t", statement).values()) == expected


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """A governed repository with two modules outside and one page inside the statement."""
    repo = init_git_repo(tmp_path / "repo")
    write_tree(repo, {"lib/one.py": "", "lib/two.py": "", "docs/page.md": ""})
    commit_fixture(repo, "docs: add a page and two modules")
    return repo


def test_an_open_belongs_to_the_stated_provider_whose_context_made_it(
    repository: Path, monkeypatch
) -> None:
    """Two providers on two threads each name their own file; a run not kept drops its names."""
    run = input_key.run_inputs(repository, current_tree(repository), _OTHER)
    barrier = Barrier(2)
    added: list[object] = []
    add = sys.addaudithook
    monkeypatch.setattr(sys, "addaudithook", lambda hook: (added.append(hook), add(hook)))

    def provider(gate):
        with input_key.watching(repository, gate, _DOCS):
            barrier.wait(timeout=30)
            sys.audit("open", 7, "r", 0)
            for name in (f"lib/{gate}.py", "docs/page.md", ".git/HEAD"):
                (repository / name).read_bytes()

    with ThreadPoolExecutor(2) as pool:
        for done in [pool.submit(copy_context().run, provider, gate) for gate in ("one", "two")]:
            done.result()
    with input_key.watching(repository, "command", _COMMAND["execution_identity"]):
        (repository / "lib/one.py").read_bytes()
    (repository / "lib/two.py").read_bytes()
    taken = [
        input_key.opened_outside(repository, _GATE | {"id": gate}, run)
        for gate in ("one", "two", "command", "one")
    ]
    with input_key.watching(repository, "one", _DOCS):
        (repository / "lib/one.py").read_bytes()
    input_key.gate_inputs(repository, head="", tree="", policy={}, checks=(), kept=False)

    assert taken == [["lib/one.py"], ["lib/two.py"], [], []]
    assert input_key.opened_outside(repository, _GATE | {"id": "one"}, run) == []
    assert len(added) <= 1


def test_an_observation_records_what_its_stated_provider_opened(
    repository: Path, monkeypatch
) -> None:
    """Through the runner, the record names the unstated file and the verdict stands."""

    def provider(root):
        for name in ("lib/one.py", "docs/page.md"):
            (root / name).read_bytes()
        return {"verdict": "pass", "state": "clean", "required_gaps": []}

    monkeypatch.setattr(DOCS_REGISTRY_PROVIDER.replace(":", "."), provider)
    head = current_tracked_head(repository)

    observed = host.observe_gate_execution(
        repository, gate_ids=("docs-registry",), expect_head=head
    )

    recorded = input_key.earlier_results(local_state_root(repository)).values()

    assert observed["verdict"] == "pass"
    assert [[row["opened"] for row in rows] for rows in recorded] == [[["lib/one.py"]]]


def test_a_held_gate_has_no_row_and_the_record_holds_no_environment_name_or_value(
    repository: Path, monkeypatch
) -> None:
    """Only an executed gate of a kept run is recorded, with its inputs and no variable.

    Statements that cannot be read fail no gate: the scope still opens, and the record is
    named unavailable.
    """
    monkeypatch.setenv("GATE_REUSE_MARKER", "marker-value")
    checks = [
        {"action_id": "docs-registry", "verdict": verdict, "duration_seconds": seconds}
        for verdict, seconds in (("pass", 0.5), ("block", None))
    ]
    tree = current_tree(repository)
    run = partial(
        input_key.gate_inputs, repository, head="h", policy={"gates": [_GATE]}, checks=checks
    )
    found = run(tree=tree, kept=True).data["gate_inputs"]
    document = (local_state_root(repository) / "gate-results" / found["record"]).read_text()
    record = json.loads(document)

    assert (found["attribute_lines"], found["compared"]) == (0, {"none": 1})
    assert [row["verdict"] for row in record["results"]] == ["pass"]
    assert set(record["inputs"]) == set(_NAMED)
    assert "marker" not in document.lower()
    assert run(tree=tree, kept=False) == run(tree="", kept=True) == input_key.GateInputs({})
    monkeypatch.setattr(input_key, "statements", Mock(side_effect=OSError))
    with input_key.watching(repository, "docs-registry", _DOCS):
        unread = run(tree=tree, kept=True).data["gate_inputs"]
    assert unread == {"record": "", "unavailable": "OSError"}


@pytest.mark.parametrize("provider", sorted(input_key.statements()[0]))
def test_no_stated_provider_opens_a_committed_file_outside_its_statement(provider) -> None:
    """The product's table covers what each of its providers opens on the product's own tree."""
    tree = current_tree(ROOT)
    gate = {"id": provider, "execution_identity": ["provider", provider]}
    with input_key.watching(ROOT, provider, gate["execution_identity"]):
        provider_reports(provider, (provider,), ROOT, candidate=True)
    run = input_key.run_inputs(ROOT, tree, _OTHER._replace(source_tree=tree))

    assert input_key.opened_outside(ROOT, gate, run) == []
