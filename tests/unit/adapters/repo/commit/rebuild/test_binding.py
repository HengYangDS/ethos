"""A rebuild record binds to its repository, its key and its originals, or refuses by fixed gap."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.commit.rebuild.binding import bind_record
from ethos.adapters.repo.commit.rebuild.entries import Resolved
from ethos.adapters.repo.commit.rebuild.entries import admitted_hosts
from ethos.contracts.outcome import OutcomeError
from ethos.repository.paradigm.peer_identity import Sighting
from ethos.repository.paradigm.peer_identity import Span
from ethos.repository.paradigm.peer_identity import generation
from ethos.repository.paradigm.peer_identity import marker
from ethos.repository.paradigm.peer_identity import marker_image
from ethos.repository.paradigm.peer_identity import read_key
from ethos.repository.paradigm.peer_identity import rebuild_image
from ethos.repository.rebuild_record import Entry
from ethos.repository.rebuild_record import Witness
from tests.support.governed_repository import git
from tests.support.private_addresses import ipv4
from tests.support.rebuild import F1
from tests.support.rebuild import H1
from tests.support.rebuild import KEY
from tests.support.rebuild import RECORD
from tests.support.rebuild import digest as _digest
from tests.support.rebuild import entry as _entry
from tests.support.rebuild import land_record
from tests.support.rebuild import peer_history as _history
from tests.support.rebuild import record as _record

if TYPE_CHECKING:
    from pathlib import Path


def _bind(repo: Path, text: str, *, refs: tuple[str, ...] | None = None) -> object:
    return bind_record(repo, path=RECORD, old=land_record(repo, text), key=KEY, refs=refs)


def test_a_record_binds_to_its_change_key_and_originals(tmp_path: Path) -> None:
    """Every entry resolves through its witness, and its count is the occurrence model's."""
    repo, base = _history(tmp_path)

    record = _bind(repo, _record(base), refs=("refs/heads/dev",))

    assert getattr(record, "id", "") == "fixture-rebuild"


def _case(case: str, base: str, keyed: str) -> dict[str, str]:
    lone = marker_image("path", path="other/lone")
    public = marker_image("path", path="acme/tools")
    return {
        "count": {"spans": _entry(marker_image("prefix", H1, "", F1), base, count=2)},
        "witness": {"hosts": _entry(marker_image("host", H1), base, n=2)},
        "generation": {"generation": generation(read_key("cd" * 32))},
        "segment": {"paths": _entry(marker_image("path", path="tools"), base)},
        "untied": {"paths": _entry(lone, base)},
        "public": {"paths": _entry(public, base)},
        "outside": {"hosts": _entry(marker_image("host", "example.com"), base)},
        "image": {"reason": f"replace {H1}"},
        "retain-slash": {"retain": '"/"'},
        "retain-private": {"retain": f'"{ipv4(10, 0, 0, 1)}/x"'},
        "retain-declared": {"retain": f'"{F1}/sub"'},
        "retain-unused": {"retain": '"api/v4/projects"'},
        "unaffected": {
            "refs": (
                '\n[refs."refs/heads/clean"]\ndisposition = "rebuild"\n'
                f'old = {{ digest = "{keyed}" }}\npeers = {{ gitlab = "absent" }}\n'
            )
        },
    }[case]


@pytest.mark.parametrize(
    ("case", "gaps"),
    [
        ("count", ["rebuild_count_mismatch:spans:0"]),
        ("witness", ["rebuild_witness_misplaced:hosts:0"]),
        ("generation", ["rebuild_key_generation_mismatch"]),
        (
            "segment",
            [
                "rebuild_count_mismatch:paths:0",
                "rebuild_witness_misplaced:paths:0",
                "rebuild_path_segment:0",
                "rebuild_path_untied:0",
            ],
        ),
        ("untied", ["rebuild_path_untied:0"]),
        ("public", ["rebuild_path_untied:0", "rebuild_path_public:0"]),
        ("outside", ["rebuild_host_outside_pattern:hosts:0"]),
        ("image", ["rebuild_count_mismatch:hosts:0", "rebuild_record_changed_in_image"]),
        ("retain-slash", ["rebuild_retain_segment:0", "rebuild_retain_unused:0"]),
        ("retain-private", ["rebuild_retain_private:0", "rebuild_retain_unused:0"]),
        (
            "retain-declared",
            [
                "rebuild_count_mismatch:paths:0",
                "rebuild_retain_declared:0",
                "rebuild_retain_unused:0",
                "rebuild_record_changed_in_image",
            ],
        ),
        ("retain-unused", ["rebuild_retain_unused:0"]),
        ("unaffected", ["rebuild_ref_unaffected:refs/heads/clean"]),
    ],
)
def test_an_entry_that_does_not_bind_refuses_by_its_gap(
    tmp_path: Path, case: str, gaps: list[str]
) -> None:
    """A count, witness, key, path, host, retained prefix or ref that does not bind names itself."""
    repo, base = _history(tmp_path)
    first = git(repo, "rev-list", "--max-parents=0", "HEAD")
    git(repo, "branch", "clean", first)
    keyed = _digest(rebuild_image("oid", first))

    with pytest.raises(OutcomeError) as refused:
        _bind(repo, _record(base, **_case(case, base, keyed)))

    assert list(refused.value.outcome.gaps) == gaps


@pytest.mark.parametrize("case", ["unsigned", "scope", "refs", "marker", "public"])
def test_the_binding_refuses_what_its_originals_and_scope_cannot_carry(
    tmp_path: Path, case: str
) -> None:
    """What the originals and the scope cannot carry refuses, naming no value.

    An unsigned original named in clear, a base outside the Change, another ref set, a marker
    already in an original and an unresolvable public peer each name their gap.
    """
    extra = f"already {marker(KEY, 'host', H1)}\n" if case == "marker" else ""
    repo, base = _history(tmp_path, signed=case != "unsigned", extra=extra)
    first = git(repo, "rev-list", "--max-parents=0", "HEAD")
    text = _record(first if case == "scope" else base)
    refs = ("refs/heads/other",) if case == "refs" else None
    if case == "public":
        git(repo, "remote", "set-url", "github", str(tmp_path / "github.git"))

    with pytest.raises(OutcomeError) as refused:
        _bind(repo, text, refs=refs)

    expected = {
        "unsigned": "rebuild_original_unsigned:base",
        "scope": "rebuild_base_outside_change",
        "refs": "rebuild_ref_set_mismatch",
        "marker": "rebuild_original_marker",
        "public": "rebuild_public_peer_unresolved",
    }[case]
    assert expected in refused.value.outcome.gaps


def test_a_former_go_module_host_is_admitted_only_where_an_import_path_ties_it() -> None:
    """A public host is admitted when a Go file or `go.mod` uses it as a module's first element."""
    entry = Entry(digest="a" * 64, count=1, witness=Witness(object="c" * 40, n=1))
    sightings = [
        Sighting("b1", "c1", "cmd/main.go", 'import "legacy.example.org/team/tool"\n'),
        Sighting("b2", "c1", "README.md", "see public.example.net/team/tool\n"),
    ]
    resolved = [
        Resolved("hosts", index, entry, sightings[index], Span(0, 0, "host", "host", host=host))
        for index, host in enumerate(("legacy.example.org", "public.example.net"))
    ]

    assert admitted_hosts(resolved, frozenset(), sightings) == {
        "legacy.example.org": True,
        "public.example.net": False,
    }
    assert admitted_hosts(resolved[1:], frozenset({"public.example.net"}), sightings) == {
        "public.example.net": True
    }


API, CI = "id.api-projects", "id.ci-project-id"


def _ids(base: str, contexts: tuple[str, ...], keyed: tuple[str, ...], count: int) -> str:
    """An ID entry over its contexts whose digests key the `keyed` contexts, in that order."""
    digests = [_digest(rebuild_image("id", name, "123456789")) for name in keyed]
    return (
        f"{{ contexts = {list(contexts)!r}, digests = {digests!r}, count = {count}, ".replace(
            "'", '"'
        )
        + f'witness = {{ object = "{base}", path = "docs/peer.md", n = 1 }} }}'
    )


@pytest.mark.parametrize(
    ("line", "contexts", "keyed", "gaps"),
    [
        ("CI_PROJECT_ID=123456789", (API, CI), (API, CI), []),
        ("nothing else", (API,), (API,), ["rebuild_id_untied:0"]),
        ("CI_PROJECT_ID=123456789", (API, CI), (CI, API), ["rebuild_id_digest_mismatch:0"]),
    ],
)
def test_an_id_binds_in_its_named_contexts_once_the_ci_project_id_ties_it(
    tmp_path: Path,
    line: str,
    contexts: tuple[str, ...],
    keyed: tuple[str, ...],
    gaps: list[str],
) -> None:
    """Its digests key its contexts in order, and one `CI_PROJECT_ID=<ID>` ties the digits."""
    repo, base = _history(tmp_path, extra=f"jobs api/v4/projects/123456789/x and {line}\n")
    entry = _ids(base, contexts, keyed, len(contexts))

    if not gaps:
        assert getattr(_bind(repo, _record(base, ids=entry)), "id", "") == "fixture-rebuild"
        return
    with pytest.raises(OutcomeError) as refused:
        _bind(repo, _record(base, ids=entry))
    assert list(refused.value.outcome.gaps) == gaps
