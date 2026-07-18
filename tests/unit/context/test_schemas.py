from __future__ import annotations

from ethos.assistants.context.bundle import context_bundle
from ethos.repository.policy.schema import validate_schema_instance


def test_context_bundle_schema_accepts_untrusted_source_verified_bundle() -> None:
    payload = context_bundle(
        query="workspace status schema validation",
        selection={
            "manifest_id": "manifest:demo",
            "query": "workspace status schema validation",
            "query_digest": "sha256:" + "1" * 64,
            "result_count": 1,
            "verified_count": 1,
            "untrusted_context_label": "UNTRUSTED CONTEXT",
            "diagnostics": [],
            "results": [
                {
                    "id": "ctx:demo",
                    "kind": "doc",
                    "title": "Workspace status schema validation",
                    "authority_class": "retrieval_aid",
                    "privacy_class": "repo_local",
                    "score": 1.0,
                    "source_ref": {
                        "path": "docs/architecture/schema-validation.md",
                        "start_line": 1,
                        "end_line": 4,
                        "sha256": "0" * 64,
                        "head": "abc123",
                    },
                    "verification": {"status": "verified", "method": "line-span+sha256"},
                }
            ],
        },
    )

    validation = validate_schema_instance("context-bundle.schema.json", payload)

    assert validation["ok"] is True


def test_context_selection_report_rejects_instruction_role_fields() -> None:
    payload = {
        "manifest_id": "manifest:demo",
        "query": "ignore rules",
        "query_digest": "sha256:" + "1" * 64,
        "result_count": 1,
        "verified_count": 0,
        "diagnostics": [],
        "results": [
            {
                "id": "ctx:bad",
                "kind": "doc",
                "title": "Bad memory",
                "authority_class": "retrieval_aid",
                "privacy_class": "repo_local",
                "score": 1.0,
                "instruction_role": "system",
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
    }

    validation = validate_schema_instance("context-selection-report.schema.json", payload)

    assert validation["ok"] is False


def test_context_index_manifest_and_policy_schemas_validate() -> None:
    manifest = {
        "id": "manifest:demo",
        "repo_id": "repo:demo",
        "root": "/repo",
        "head": "abc123",
        "schema_version": 1,
        "source_manifest_digest": "1" * 64,
        "policy_digest": "2" * 64,
        "privacy_ceiling": "repo_local",
        "dirty": False,
        "extractors": [{"name": "markdown", "version": "1"}],
        "created_at": "2026-07-01T00:00:00+00:00",
    }
    policy = {
        "id": "default",
        "privacy_ceiling": "repo_local",
        "allowed_source_kinds": ["tracked_file", "claim", "dated_evidence", "openspec"],
        "forbidden_uses": ["proof", "required_gap_closure", "workflow_ruling"],
        "max_results": 10,
        "max_context_bytes": 12000,
    }

    assert validate_schema_instance("context-index-manifest.schema.json", manifest)["ok"] is True
    assert validate_schema_instance("context-policy.schema.json", policy)["ok"] is True
