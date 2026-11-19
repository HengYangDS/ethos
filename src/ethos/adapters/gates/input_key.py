"""A gate's input key, the record of a run's results and the comparison of a repeated result.

The key names what a gate's verdict is taken to depend on: the gate as its policy binds it, the
committed paths its statement selects and the run's named inputs. Nothing here skips a gate: every
gate has already run when its key is made, its verdict is compared with the earlier results of
that key, and the run is recorded. No value of an environment variable is read.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib
from collections import Counter
from contextlib import contextmanager
from contextlib import suppress
from contextvars import ContextVar
from functools import lru_cache
from importlib import resources
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple

import ethos.contracts
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.runtime.authority import invoking_build_identity
from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.adapters.store.state.schema import local_state_root
from ethos.contracts.gate_providers import provider_id
from ethos.contracts.semantic import canonical_json_digest
from ethos.repository.policy.rules.config import path_matches

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Generator
    from collections.abc import Mapping
    from collections.abc import Sequence

    from ethos.repository.release.identity import BuildIdentity

RECORD_DIRECTORY = "gate-results"
# Every gate reads the repository's profile and its gate declarations.
_COMMON = (".ethos/**", "system/gates.toml", "system/repository-gates.toml")
_DECIDED = frozenset({"pass", "block"})
_MISMATCH = (
    "gate_input_mismatch:{gate}; key {key}; an earlier result of tree {differing[0]} differs"
)
# The record is a cache: nothing that fails while it is made or read may reach the proof.
_FAILURES = (OSError, ValueError, LookupError, TypeError, RuntimeError, subprocess.SubprocessError)
_WATCH: ContextVar[list[object] | None] = ContextVar("gate_opened_files", default=None)
# By root, then by gate: a run that is not kept drops its root's names.
_OPENED: dict[str, dict[str, list[object]]] = {}
_HOOKED: list[bool] = []
_LOCK = Lock()


class RunInputs(NamedTuple):
    """What one run reads once: the committed listing, the named inputs and the local state."""

    entries: tuple[tuple[str, str], ...]
    named: Mapping[str, str]
    product_paths: frozenset[str]
    attribute_lines: int


class GateInputs(NamedTuple):
    """The result data of one run's keys, empty for no record, and the notes of its mismatches."""

    data: dict[str, object]
    notes: tuple[dict[str, object], ...] = ()


@lru_cache(maxsize=1)
def statements() -> tuple[Mapping[str, Sequence[str]], frozenset[str]]:
    """Load what each stated provider reads and the providers that read outside the tree.

    The table is found from the imported package itself, never by a lookup of its name.
    """
    source = resources.files(ethos.contracts).joinpath("gate-inputs.toml")
    table = tomllib.loads(source.read_text(encoding="utf-8"))
    return table["inputs"], frozenset(table["open"])


def gate_statement(identity: Sequence[str]) -> tuple[str, tuple[str, ...]]:
    """Return a gate's statement kind and the patterns of the committed paths it selects.

    Only a gate whose every provider the table states is `declared`. A command gate and a
    provider outside the table are keyed by the whole `tree`; a provider that reads outside the
    committed tree makes its gate `open`.
    """
    inputs, unbounded = statements()
    names = [provider_id(name) or name for name in identity[1:] if identity[0] == "provider"]
    if not names or any(name not in inputs for name in names):
        return ("open" if unbounded.intersection(names) else "tree"), ()
    return "declared", (*_COMMON, *(pattern for name in names for pattern in inputs[name]))


def run_inputs(root: Path, tree: str, product: BuildIdentity) -> RunInputs:
    """Read the committed listing and the named inputs of one run.

    Where the running product was built from the proved tree itself, its build identity would
    change with every commit, so the committed files its wheel is built from are paths of every
    statement instead.
    """
    listed = _git(root, "ls-tree", "-r", "-z", tree)
    rows = (record.partition("\t") for record in listed.split("\0") if record)
    entries = tuple((path, meta) for meta, _tab, path in rows)
    paths = "".join(f"{path}\0" for path, _meta in entries)
    own = product.source_tree == tree
    ignored = ("ls-files", "--others", "--ignored", "--exclude-standard", "--directory", "-z")
    classified = run_git(root, "check-attr", "-z", "--stdin", "-a", stdin=paths, observation=True)
    named = {
        "product": "tree" if own else canonical_json_digest(product.projection()),
        "python": sys.version,
        "platform": sys.platform,
        "git": _git(root, "--version"),
        "attributes": _sha(classified.stdout),
        "ignored": _sha(_git(root, *ignored)),
    }
    local = Path(root, _git(root, "rev-parse", "--git-path", "info/attributes").strip())
    text = local.read_text(encoding="utf-8", errors="replace") if local.is_file() else ""
    carried = _product_paths(root, tree, entries) if own else frozenset()
    return RunInputs(entries, named, carried, len(re.findall(r"(?m)^[ \t]*[^#\s]", text)))


def input_key(gate: Mapping[str, Any], run: RunInputs) -> dict[str, object]:
    """Return one gate's key, its statement kind and the count of committed paths it selects."""
    statement, selects = _selection(gate, run)
    selected = [f"{meta}\t{path}" for path, meta in run.entries if selects(path)]
    material = {"schema": 1, "gate": gate, "inputs": _sha("\0".join(selected)), **run.named}
    key = canonical_json_digest(material)
    return {"key": key, "statement": statement, "input_count": len(selected)}


def earlier_results(store: Path) -> dict[tuple[str, str], list[dict[str, object]]]:
    """Return the recorded results by gate and key; a record that cannot be parsed holds none."""
    found: dict[tuple[str, str], list[dict[str, object]]] = {}
    directory = store / RECORD_DIRECTORY
    for path in sorted(directory.glob("*.json")) if directory.is_dir() else ():
        try:
            record = json.loads(path.read_bytes())
            rows = record["results"] if record["schema"] == 1 else ()
            keyed = [((str(row["gate"]), str(row["key"])), row, record["tree"]) for row in rows]
        except (OSError, ValueError, LookupError, TypeError):
            continue
        for key, row, tree in keyed:
            found.setdefault(key, []).append({**row, "tree": tree})
    return found


def comparison(
    earlier: Sequence[Mapping[str, Any]], verdict: str, tree: str, statement: str
) -> dict[str, object]:
    """Compare a decided verdict with the decided earlier results of its key.

    Pass and block are compared in both directions. The results of another tree are counted
    apart, the tree of the first differing result is named, and an open gate's comparison is
    named open instead of agreeing or differing.
    """
    decided = [row for row in earlier if str(row.get("verdict")) in _DECIDED]
    if verdict not in _DECIDED or not decided:
        return {"state": "none"}
    differing = [row["tree"] for row in decided if row["verdict"] != verdict]
    return {
        "state": "open" if statement == "open" else "mismatch" if differing else "agree",
        "earlier": len(decided),
        "other_trees": sum(row["tree"] != tree for row in decided),
        "differing": differing[:1],
    }


def record_results(store: Path, document: Mapping[str, object]) -> Path:
    """Write one run's results as a file that the digest of its bytes names."""
    payload = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    name = f"{hashlib.sha256(payload).hexdigest()}.json"
    return write_content_addressed(
        store / RECORD_DIRECTORY / name, payload, collision="gate_result_collision"
    )


def gate_inputs(
    root: Path,
    *,
    head: str,
    tree: str,
    policy: object,
    checks: Sequence[Mapping[str, Any]],
    kept: bool,
) -> GateInputs:
    """Key each executed gate, compare its verdict with the earlier results and record the run.

    Nothing is keyed or recorded unless `kept` says that the gates executed and the source still
    equals the commit, and `tree` names that commit's tree. The policy is a resolved policy or
    its projection, the form a plan binds, and is read only then. A gate that an unmet
    prerequisite held did not execute, decided nothing of its own inputs and has no row. The
    result's data hold the record's name and the count of comparisons by state; the rows stay in
    the record, so the result's size does not grow with the gates. A Git read or a store that
    fails changes nothing of the proof: the result names the record as unavailable.
    """
    if not (kept and tree):
        _OPENED.pop(str(root), None)
        return GateInputs({})
    try:
        bound: Any = getattr(policy, "projection", policy)
        gates = {gate["id"]: gate for gate in bound["gates"]}
        run = run_inputs(root, tree, invoking_build_identity())
        store = local_state_root(root)
        earlier = earlier_results(store)
        rows: list[dict[str, Any]] = [
            {
                "gate": gate["id"],
                **input_key(gate, run),
                "verdict": check["verdict"],
                "duration": seconds,
                "opened": opened_outside(root, gate, run),
            }
            for check in checks
            if (seconds := check.get("duration_seconds")) is not None
            for gate in (gates[check["action_id"]],)
        ]
        for row in rows:
            known = earlier.get((row["gate"], row["key"]), ())
            row["comparison"] = comparison(known, row["verdict"], tree, row["statement"])
        local = {
            "attribute_lines": run.attribute_lines,
            "compared": dict(Counter(row["comparison"]["state"] for row in rows)),
        }
        document = {
            "schema": 1,
            "head": head,
            "tree": tree,
            "environment": _sha("\0".join(sorted(os.environ))),
            "inputs": run.named,
            "results": rows,
            **local,
        }
        record = record_results(store, document).name
    except _FAILURES as error:
        return GateInputs({"gate_inputs": {"record": "", "unavailable": type(error).__name__}})
    notes = tuple(
        {
            "severity": "note",
            "code": "gate_input_mismatch",
            "message": _MISMATCH.format(**row, **row["comparison"]),
        }
        for row in rows
        if row["comparison"]["state"] == "mismatch"
    )
    return GateInputs({"gate_inputs": {"record": record, **local}}, notes)


def opened_outside(root: Path, gate: Mapping[str, Any], run: RunInputs) -> list[str]:
    """Return the committed files that a gate's watched run opened outside its statement.

    The names are taken once. A file outside the repository, a file that is not committed and a
    file that the statement selects is never named.
    """
    names = _OPENED.get(str(root), {}).pop(str(gate["id"]), ())
    selects = _selection(gate, run)[1]
    committed, base = dict(run.entries), root.resolve()
    named = {name for name in names if isinstance(name, str | bytes | os.PathLike)}
    opened = {Path(os.fsdecode(name)).resolve() for name in named}
    inside = {path.relative_to(base).as_posix() for path in opened if path.is_relative_to(base)}
    return sorted(path for path in inside if path in committed and not selects(path))


@contextmanager
def watching(root: Path, gate: str, identity: Sequence[str]) -> Generator[None]:
    """Collect what one gate's stated providers open, in the calling context alone.

    The audit hook is added once in a process and keeps nothing outside this scope. A gate
    without a statement is not watched, and neither is any gate when the statements cannot be
    read: the gate runs as it would without this record.
    """
    seen: list[object] | None = None
    with suppress(*_FAILURES):
        if gate_statement(identity)[0] == "declared":
            with _LOCK:
                if not _HOOKED:
                    sys.addaudithook(_on_audit)
                    _HOOKED.append(True)
            seen = []
    token = _WATCH.set(seen)
    try:
        yield
    finally:
        _WATCH.reset(token)
        if seen is not None:
            _OPENED.setdefault(str(root), {})[gate] = seen


def _on_audit(
    event: str,
    arguments: tuple[object, ...],
    watch: Callable[[], list[object] | None] = _WATCH.get,
) -> None:
    """Keep the name that an executing stated provider opens; this never raises.

    The scope is bound when the hook is defined, so a call during interpreter shutdown reads no
    module state.
    """
    if event == "open" and (seen := watch()) is not None:
        seen.extend(arguments[:1])


def _selection(gate: Mapping[str, Any], run: RunInputs) -> tuple[str, Callable[[str], bool]]:
    """Return a gate's statement kind and whether it selects a committed path."""
    statement, patterns = gate_statement(gate["execution_identity"])

    def selects(path: str) -> bool:
        return statement != "declared" or path in run.product_paths or path_matches(path, patterns)

    return statement, selects


def _product_paths(root: Path, tree: str, entries: Sequence[tuple[str, str]]) -> frozenset[str]:
    """Return the committed files that this tree's wheel is built from, by its build table."""
    project = tomllib.loads(_git(root, "show", f"{tree}:pyproject.toml"))
    wheel = project["tool"]["hatch"]["build"]["targets"]["wheel"]
    carried = tuple(f"{item}/" for item in (*wheel["packages"], *wheel["force-include"]))
    return frozenset(path for path, _meta in entries if f"{path}/".startswith(carried))


def _git(root: Path, *arguments: str) -> str:
    return run_git(root, *arguments, observation=True).stdout


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "surrogateescape")).hexdigest()
