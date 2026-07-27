from __future__ import annotations

import pytest

from ethos.adapters.openspec.protocol.proposal_protocol import proposal_protocol_report


def _report(tmp_path, metadata: str, *, capability: str = "contracts", accepted=True):
    if accepted:
        spec_dir = tmp_path / "openspec" / "specs" / capability
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Accepted\n", encoding="utf-8")
    change_dir = tmp_path / "openspec" / "changes" / "sample-change"
    change_dir.mkdir(parents=True)
    (change_dir / "proposal.md").write_text(
        "# Change\n\n## Capabilities\n\n"
        f"- `{capability}`: {metadata}\n\n"
        "## Out of Scope\n\n- Everything else.\n",
        encoding="utf-8",
    )
    return proposal_protocol_report(tmp_path, "sample-change")


def test_known_capability_uses_spec_identity_without_profile(tmp_path) -> None:
    report = _report(tmp_path, "subject=terminal-contracts; reuse=extend; change=modify")

    assert report["ok"] is True
    assert report["required_gaps"] == []


@pytest.mark.parametrize("missing_field", ["subject", "reuse", "change"])
def test_each_required_proposal_field_blocks(tmp_path, missing_field: str) -> None:
    metadata = {
        "subject": "terminal-contracts",
        "reuse": "extend",
        "change": "modify",
    }
    del metadata[missing_field]

    report = _report(tmp_path, "; ".join(f"{key}={value}" for key, value in metadata.items()))

    assert report["required_gaps"] == [
        f"openspec_proposal_metadata_missing:sample-change:contracts:{missing_field}"
    ]


@pytest.mark.parametrize(
    "unknown_key", ["facet:lifecycle", "facet:surface", "facet:authority", "owner"]
)
def test_unknown_proposal_metadata_is_rejected(tmp_path, unknown_key: str) -> None:
    report = _report(
        tmp_path,
        f"subject=terminal-contracts; reuse=extend; change=modify; {unknown_key}=legacy",
    )

    assert report["required_gaps"] == [
        f"openspec_proposal_metadata_unknown:sample-change:contracts:{unknown_key}"
    ]


def test_unknown_capability_blocks_when_spec_is_absent(tmp_path) -> None:
    report = _report(
        tmp_path,
        "subject=unknown-subject; reuse=new; change=add",
        capability="unknown-capability",
        accepted=False,
    )

    assert report["required_gaps"] == [
        "openspec_proposal_capability_unknown:sample-change:unknown-capability"
    ]


@pytest.mark.parametrize("fragment", ["malformed", "owner=one=two"])
def test_malformed_proposal_metadata_segment_is_rejected(tmp_path, fragment: str) -> None:
    report = _report(
        tmp_path,
        f"subject=terminal-contracts; reuse=extend; change=modify; {fragment}",
    )

    assert report["required_gaps"] == [
        "openspec_proposal_metadata_segment_malformed:sample-change:contracts:4"
    ]


def test_duplicate_proposal_metadata_is_rejected_without_overwrite(tmp_path) -> None:
    report = _report(
        tmp_path,
        "subject=terminal-contracts; reuse=extend; subject=overwritten; change=modify",
    )

    assert report["required_gaps"] == [
        "openspec_proposal_metadata_duplicate:sample-change:contracts:subject"
    ]
    assert report["capabilities"][0]["metadata"]["subject"] == "terminal-contracts"
