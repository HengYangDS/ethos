from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_readme_isomorphic_governance_is_operational_not_slogan() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    raw_section = readme.split("## Isomorphic Governance", 1)[1].split("## First Hour", 1)[0]
    section = " ".join(raw_section.split())

    required_phrases = {
        "ETHOS product repository and adopted repositories",
        "same kernel: authority, subject, commitment, change, evidence, claim, and chronicle",
        "profiles and adapters",
        "not product cloning",
        "one evidence-bound transition loop",
        "same commands answer the same transition questions",
        "Repository truth stays in source, tests, schemas, docs, evidence, and promoted decisions",
    }

    missing = sorted(phrase for phrase in required_phrases if phrase not in section)
    assert missing == []
