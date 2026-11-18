"""Each committed audit record names an artifact of the committed lock and ends on its day."""

from __future__ import annotations

import hashlib
import json
import tomllib
from datetime import timedelta
from pathlib import Path
from typing import Any

from ethos.repository.policy.quality.dependency_acceptance import AUDIT_POLICY_PATH
from ethos.repository.policy.quality.dependency_acceptance import AuditDisposition
from ethos.repository.policy.quality.dependency_acceptance import AuditPolicy
from ethos.repository.policy.quality.dependency_acceptance import evaluate_dependency_acceptance
from tests.unit.ci.dependency_audit.support import clean_report

ROOT = Path(__file__).resolve().parents[4]
FINDINGS = "vulnerabilities_or_adverse_statuses"


def _committed() -> tuple[AuditPolicy, bytes]:
    declared = tomllib.loads((ROOT / AUDIT_POLICY_PATH).read_text(encoding="utf-8"))
    return AuditPolicy.model_validate(declared), (ROOT / "package-lock.json").read_bytes()


def _nodes(record: AuditDisposition, packages: dict[str, Any]) -> list[str]:
    """Return the nodes a record names, or every locked node of its package and version."""
    if record.nodes:
        return sorted(record.nodes)
    return sorted(
        node
        for node, locked in packages.items()
        if node.rpartition("node_modules/")[2] == record.package
        and locked.get("version") == record.version
    )


def _observation(policy: AuditPolicy, lock: bytes) -> dict[str, Any]:
    """Build the native report npm would give for exactly the findings the records name."""
    packages = json.loads(lock)["packages"]
    aggregates: dict[str, dict[str, Any]] = {}
    for record in policy.dispositions:
        finding = aggregates.setdefault(
            record.package, {"name": record.package, "via": [], "nodes": []}
        )
        advisory = {"url": record.advisory_url, "dependency": record.package}
        if advisory not in finding["via"]:
            finding["via"].append(advisory)
        finding["nodes"] = sorted({*finding["nodes"], *_nodes(record, packages)})
    raw = clean_report("npm") | {"vulnerabilities": aggregates}
    raw["metadata"]["vulnerabilities"] |= {"high": len(aggregates), "total": len(aggregates)}
    return {
        "state": "finished",
        "verdict": "block",
        "required_gaps": [f"npm:{FINDINGS}"],
        "inputs": {"package-lock.json": hashlib.sha256(lock).hexdigest()},
        "checks": [
            {
                "ecosystem": "python",
                "exit_code": 0,
                "stdout": json.dumps(clean_report("python")),
                "verdict": "pass",
                "reason": "clean",
            },
            {
                "ecosystem": "npm",
                "exit_code": 1,
                "stdout": json.dumps(raw),
                "verdict": "block",
                "reason": FINDINGS,
            },
        ],
        # A newer npm than the locked one exists, so no finding counts as unfixed upstream.
        "upstream": {"npm": {"npm": "999.0.0"}},
    }


def test_each_committed_record_names_an_artifact_of_the_committed_lock() -> None:
    """A record whose node or version left the lock would accept nothing, and say nothing."""
    policy, lock = _committed()
    packages = json.loads(lock)["packages"]
    committed = hashlib.sha256(lock).hexdigest()
    for record in policy.dispositions:
        # A record bound to another lock accepts nothing, and only the online audit would say so.
        assert record.lock_sha256 in {None, committed}, record.approval_ref
        if record.scope == "production-release":
            assert record.lock_sha256 == committed, record.approval_ref
        nodes = _nodes(record, packages)
        assert nodes, record.approval_ref
        for node in nodes:
            assert node in packages, node
            assert node.rpartition("node_modules/")[2] == record.package, node
            assert packages[node]["version"] == record.version, node


def test_the_committed_records_cover_their_findings_until_their_last_day() -> None:
    """The product's own decision admits every record before its end and none from it."""
    policy, lock = _committed()
    ends = [record.expires_at for record in policy.dispositions if record.expires_at is not None]
    if not ends:
        return
    payload = _observation(policy, lock)
    context = {"lock_source": lock, "scope": "production-release", "host": "any-host", "ci": True}

    before = evaluate_dependency_acceptance(
        policy, payload, now=min(ends) - timedelta(seconds=1), **context
    )
    assert (before["verdict"], before["reason"]) == ("pass", "authorized_findings"), before
    # Every record matched a finding whose version and integrity the lock itself supplied.
    assert len(before["approvals"]) == len(policy.dispositions)

    after = evaluate_dependency_acceptance(policy, payload, now=max(ends), **context)
    assert (after["verdict"], after["reason"]) == ("block", "unapproved_or_expired_findings")
    assert sorted(after["expired_approvals"]) == sorted(
        record.approval_ref for record in policy.dispositions if record.expires_at is not None
    )
