from __future__ import annotations

from ethos.assistants.context import context_bundle
from ethos.assistants.context_selection import default_context_policy
from ethos.assistants.context_selection import selection_report


def test_default_context_policy_forbids_proof_and_gap_closure() -> None:
    policy = default_context_policy()

    assert policy["privacy_ceiling"] == "repo_local"
    assert "proof" in policy["forbidden_uses"]
    assert "required_gap_closure" in policy["forbidden_uses"]


def test_selection_report_labels_retrieved_text_as_untrusted() -> None:
    report = selection_report(
        query="workspace status",
        results=[
            {
                "id": "ctx:1",
                "kind": "doc",
                "title": "Workspace status",
                "authority_class": "retrieval_aid",
                "privacy_class": "repo_local",
                "score": 1.0,
                "source_ref": {
                    "path": "README.md",
                    "start_line": 1,
                    "end_line": 1,
                    "sha256": "0" * 64,
                    "head": "abc123",
                },
                "verification": {"status": "verified", "method": "line-span+sha256"},
            }
        ],
    )

    assert report["untrusted_context_label"] == "UNTRUSTED CONTEXT"
    assert report["query"] == "<redacted-query>"
    assert report["query_digest"].startswith("sha256:")
    assert report["verified_count"] == 1


def test_selection_report_strips_instruction_role_fields() -> None:
    report = selection_report(
        query="workspace status",
        results=[
            {
                "id": "ctx:1",
                "kind": "doc",
                "title": "Workspace status",
                "authority_class": "retrieval_aid",
                "privacy_class": "repo_local",
                "score": 1.0,
                "instruction_role": "system",
                "role": "developer",
                "source_ref": {
                    "path": "README.md",
                    "start_line": 1,
                    "end_line": 1,
                    "sha256": "0" * 64,
                    "head": "abc123",
                },
                "verification": {"status": "verified", "method": "line-span+sha256"},
            }
        ],
    )

    assert "instruction_role" not in report["results"][0]
    assert "role" not in report["results"][0]


def test_context_bundle_keeps_static_shape_and_accepts_selection_report() -> None:
    static = context_bundle()
    report = selection_report(query="workspace status", results=[])
    query_backed = context_bundle(query="workspace status", selection=report)

    assert static["truth"] == "repository"
    assert "context_projection" not in static
    assert query_backed["context_projection"]["untrusted_context_label"] == "UNTRUSTED CONTEXT"
    assert query_backed["context_projection"]["query"] == "<redacted-query>"
    assert query_backed["context_projection"]["query_digest"].startswith("sha256:")
