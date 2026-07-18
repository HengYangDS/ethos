from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "docs/plans/post-publication-governance-plan.md"


def test_post_publication_plan_preserves_remote_local_lane_boundaries() -> None:
    text = PLAN.read_text(encoding="utf-8")

    assert "A default `ethos publish --json` does not probe or push a remote" in text
    assert "`--probe-remote` observes availability without" in text
    assert "do not mutate, retire, reset, stash, or clean another Work Lane" in text
    assert "local fallback evidence" in text
    assert "dev == candidate/dev" in text
    assert "`origin/dev` may be unknown until an explicit read-only probe" in text


def test_post_publication_plan_keeps_no_compat_and_isomorphic_kernel_as_next_phases() -> None:
    text = PLAN.read_text(encoding="utf-8")

    assert "No-compatibility-residue gate" in text
    assert "same kernel" in text
    assert "profiles and adapters" in text
    assert "not product cloning" in text
