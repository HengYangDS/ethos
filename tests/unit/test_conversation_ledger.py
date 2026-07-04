from __future__ import annotations

from pathlib import Path

from ethos.repository.repository_audit import REQUIRED_DOCS

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "docs" / "governance" / "conversation-ledger.md"


def test_conversation_ledger_is_governance_truth_with_metadata() -> None:
    text = LEDGER.read_text(encoding="utf-8")
    header = text.split("---", 2)[1]

    assert "subject: ethos:conversation-ledger" in header
    assert "role: governance-ledger" in header
    assert "state: active" in header
    assert "relations:" in header
    assert "canonical_for: conversation-derived product gaps" in header


def test_conversation_ledger_captures_all_known_requirement_ids() -> None:
    text = LEDGER.read_text(encoding="utf-8")

    for index in range(1, 26):
        assert f"CL-{index:03d}" in text


def test_conversation_ledger_preserves_critical_chat_requirements() -> None:
    text = LEDGER.read_text(encoding="utf-8")

    for phrase in (
        "governance junk drawer",
        "official-quality assistant skills",
        "Superpowers",
        "assistant host memory",
        "backlog-md",
        "tools/agent",
        "dmgr reference adopter",
        ".mailmap",
        "__init__.py",
        "delta-to-canonical",
    ):
        assert phrase in text


def test_conversation_ledger_is_discoverable_and_repository_audited() -> None:
    index = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")

    assert "docs/governance/conversation-ledger.md" in REQUIRED_DOCS
    assert "Conversation Ledger" in index
    assert "governance/conversation-ledger.md" in index
