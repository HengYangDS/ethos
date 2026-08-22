"""Close observed product references against positive native ownership."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Literal

from ethos.contracts.system.contracts import system_contracts_report
from ethos.contracts.verdict import close_verdict
from ethos.repository.policy.references.carriers import REFERENCE_KINDS
from ethos.repository.policy.references.carriers import reference_carrier
from ethos.repository.policy.references.declarations import command_owner_sources_from_files
from ethos.repository.policy.references.declarations import native_owned_references_from_files
from ethos.repository.policy.references.observation import observe_repository_references
from ethos.repository.policy.references.observation import reference_consumer_sources_from_files
from ethos.repository.policy.references.python_syntax import complete_python_tree
from ethos.repository.registry.docs.registry import build_docs_registry

if TYPE_CHECKING:
    from pathlib import Path

SemanticCategory = Literal[
    "missing",
    "duplicate",
    "orphan",
    "superseded",
    "conflict",
    "unknown",
]


@dataclass(frozen=True, slots=True)
class SemanticClosureFinding:
    """One exact relation that prevents repository semantic closure."""

    category: SemanticCategory
    relation: str
    kind: str
    identity: str
    sources: tuple[str, ...]

    def gap(self) -> str:
        """Return the stable machine gap for this relation."""
        source_text = ",".join(self.sources)
        return f"semantic_{self.relation}_{self.category}:{self.kind}:{self.identity}:{source_text}"

    def to_dict(self) -> dict[str, object]:
        """Project one uniform finding shape for every category."""
        return {
            "relation": self.relation,
            "kind": self.kind,
            "identity": self.identity,
            "sources": list(self.sources),
        }


def product_reference_gaps(
    allowed: dict[str, frozenset[str]],
    observed: dict[str, set[str]],
) -> list[str]:
    """Reject machine references outside one declared product closure."""
    gaps = []
    for kind in REFERENCE_KINDS:
        permitted = allowed.get(kind, frozenset())
        for value in sorted(observed.get(kind, set()) - set(permitted)):
            if kind == "import" and value in {"ethos", "tests", "tools"}:
                continue
            gaps.append(f"product_reference_not_admitted_at_baseline:{kind}:{value}")
    return gaps


def repository_semantic_closure(
    root: Path,
    *,
    system_contracts: dict[str, object] | None = None,
) -> dict[str, object]:
    """Prove current native reference ownership and relation closure."""
    observation = observe_repository_references(root)
    files = observation.files
    parsed_files = {
        path: complete_python_tree(text)
        for path, text in files.items()
        if reference_carrier(path).name == "python"
    }
    command_owners = command_owner_sources_from_files(files, parsed_files=parsed_files)
    owners = native_owned_references_from_files(files, command_owners=command_owners)
    consumption = reference_consumer_sources_from_files(
        files,
        declared_commands=owners["command"],
        parsed_files=parsed_files,
    )
    contract_report = system_contracts or system_contracts_report(root)
    findings = [
        *_duplicate_command_owners(command_owners),
        *_missing_command_parents(command_owners),
        *_orphan_consumers(owners, consumption.sources),
        *_superseded_current_carriers(root, files),
        *_declaration_findings(contract_report),
        *_unknown_carriers((*observation.unreadable_paths, *consumption.unknown_paths)),
    ]
    findings.sort(
        key=lambda item: (
            item.category,
            item.relation,
            item.kind,
            item.identity,
            item.sources,
        )
    )
    categories: tuple[SemanticCategory, ...] = (
        "missing",
        "duplicate",
        "orphan",
        "superseded",
        "conflict",
        "unknown",
    )
    required_gaps = [finding.gap() for finding in findings]
    verdict = (
        "unknown" if findings and all(item.category == "unknown" for item in findings) else "pass"
    )
    return {
        "verdict": close_verdict(verdict, required_gaps=tuple(required_gaps)),
        "coverage": "unknown"
        if any(item.category == "unknown" for item in findings)
        else "evaluated",
        "summary": {
            category: sum(finding.category == category for finding in findings)
            for category in categories
        },
        **{
            category: [finding.to_dict() for finding in findings if finding.category == category]
            for category in categories
        },
        "required_gaps": required_gaps,
    }


def _duplicate_command_owners(
    owners: dict[str, frozenset[str]],
) -> list[SemanticClosureFinding]:
    return [
        SemanticClosureFinding(
            category="duplicate",
            relation="owner",
            kind="command",
            identity=identity,
            sources=tuple(sorted(sources)),
        )
        for identity, sources in owners.items()
        if len(sources) > 1
    ]


def _missing_command_parents(
    owners: dict[str, frozenset[str]],
) -> list[SemanticClosureFinding]:
    identities = set(owners)
    prefixes = {
        identity.rpartition(" ")[0]
        for identity in identities
        if " " in identity and identity.rpartition(" ")[0]
    }
    return [
        SemanticClosureFinding(
            category="missing",
            relation="selector",
            kind="command",
            identity=parent,
            sources=tuple(
                sorted(
                    source
                    for identity, sources in owners.items()
                    if identity.startswith(f"{parent} ")
                    for source in sources
                )
            ),
        )
        for parent in sorted(prefixes - identities)
    ]


def _orphan_consumers(
    owners: dict[str, frozenset[str]],
    consumers: dict[str, dict[str, frozenset[str]]],
) -> list[SemanticClosureFinding]:
    findings = []
    for kind in REFERENCE_KINDS:
        for identity, sources in consumers[kind].items():
            if identity in owners.get(kind, ()):
                continue
            if kind == "import" and identity in {"ethos", "tests", "tools"}:
                continue
            findings.append(
                SemanticClosureFinding(
                    category="orphan",
                    relation="consumer",
                    kind=kind,
                    identity=identity,
                    sources=tuple(sorted(sources)),
                )
            )
    return findings


def _superseded_current_carriers(
    root: Path,
    files: dict[str, str],
) -> list[SemanticClosureFinding]:
    if not (root / "docs").is_dir():
        return []
    return [
        SemanticClosureFinding(
            category="superseded",
            relation="carrier",
            kind="document",
            identity=entry["subject"] or entry["path"],
            sources=(entry["path"],),
        )
        for entry in build_docs_registry(root)
        if entry["state"] in {"archived", "superseded"} and entry["path"] in files
    ]


def _declaration_findings(report: dict[str, object]) -> list[SemanticClosureFinding]:
    issues = report.get("declaration_issues")
    rows = issues if isinstance(issues, list) else []
    return [
        SemanticClosureFinding(
            category=item["category"],
            relation=str(item["relation"]),
            kind=str(item["kind"]),
            identity=str(item["identity"]),
            sources=tuple(str(source) for source in item["sources"]),
        )
        for item in rows
        if isinstance(item, dict)
        and item.get("category")
        in {"missing", "duplicate", "orphan", "superseded", "conflict", "unknown"}
        and isinstance(item.get("sources"), list)
    ]


def _unknown_carriers(paths: tuple[str, ...]) -> list[SemanticClosureFinding]:
    return [
        SemanticClosureFinding(
            category="unknown",
            relation="carrier",
            kind="reference",
            identity=path,
            sources=(path,),
        )
        for path in sorted(set(paths))
    ]
