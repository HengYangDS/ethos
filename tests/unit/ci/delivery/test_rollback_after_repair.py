"""The journey's rollback after the declaration repair records what the product decided."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

import tools.ci.delivery.acceptance.journey as journey
import tools.ci.delivery.acceptance.rollback_after_repair as leg

_REFUSED = "runtime_rollback_declaration_repaired"
_LEFT = {"receipted_rollback": "not_qualified", "pin_across_landings": "not_qualified"}


class _Adopter:
    """A retained adopter whose runtime selection the doubles keep as plain values."""

    def __init__(self, root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.common, self.lanes = root / "common", [("work/sample", root / "lane")]
        self.selector = self.common / "ethos/runtime/CURRENT"
        self.selector.parent.mkdir(parents=True)
        self.selector.write_text("successor", encoding="utf-8")
        self.held: Path | None = root / "held"
        self.answers: dict[str, list[str]] = {}
        self.retained, self.requests = ["state"], []
        self.moves_on_refusal = self.changes_retained = False
        for name, double in (
            ("git_common_dir", lambda _root: str(self.common)),
            ("run_git", lambda *_args: Mock(stdout="hooks\n")),
            ("parse_worktree_list", self._worktrees),
            ("current_runtime", self._current),
            ("named_runtime", lambda _common, _name: self.held),
            ("invoke", self._invoke),
            ("runtime_file_inventory", lambda _hooks: ("pre-commit",)),
        ):
            monkeypatch.setattr(leg, name, double)
        monkeypatch.setattr(
            leg.brownfield_acceptance, "retained_repository", lambda _root: tuple(self.retained)
        )

    def _worktrees(self, _listed: str) -> list[dict[str, str]]:
        return [
            {"worktree": str(path), "branch": f"refs/heads/{branch}"}
            for branch, path in [("dev", self.common.parent), *self.lanes]
        ]

    def _current(self, _common: Path) -> Mock:
        name = self.selector.read_text(encoding="utf-8")
        return Mock(python=Path("successor/python"), root=self.common.parent / name)

    def _invoke(
        self, _lane: Path, command: tuple[str, ...], *, environment: dict[str, str]
    ) -> tuple[int, dict[str, object], str]:
        assert environment == {"HOME": "isolated"}
        runtime = Path(command[command.index("--runtime") + 1]).name
        self.requests.append(runtime)
        gaps = self.answers.get(runtime, [])
        if self.changes_retained:
            self.retained.append("a changed byte")
        if not gaps or self.moves_on_refusal:
            self.selector.write_text(runtime, encoding="utf-8")
        return (1 if gaps else 0), {"required_gaps": gaps}, "the product's own answer"


def _prove(tmp_path: Path) -> dict[str, object]:
    return leg.prove_rollback_after_repair(tmp_path, environment={"HOME": "isolated"})


def test_an_admitted_rollback_selects_the_held_runtime_and_returns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The held runtime is selected from the lane, and the successor is selected again."""
    adopter = _Adopter(tmp_path, monkeypatch)
    assert _prove(tmp_path) == {"rollback_after_declaration_repair": "admitted", **_LEFT}
    assert adopter.requests == ["held", "successor"]
    assert adopter.selector.read_text(encoding="utf-8") == "successor"


def test_a_refused_rollback_is_recorded_when_nothing_changed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A predecessor that refuses the repaired declaration is one request and no change."""
    adopter = _Adopter(tmp_path, monkeypatch)
    adopter.answers = {"held": [_REFUSED]}
    assert _prove(tmp_path) == {"rollback_after_declaration_repair": "refused", **_LEFT}
    assert adopter.requests == ["held"]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        pytest.param({"lanes": []}, "lane_missing", id="no-work-lane"),
        pytest.param({"held": None}, "supply_missing", id="no-held-runtime"),
        pytest.param(
            {"answers": {"held": [_REFUSED]}, "moves_on_refusal": True},
            "refusal_changed_state",
            id="a-refusal-that-moved-the-selector",
        ),
        pytest.param(
            {"answers": {"held": ["runtime_rollback_probe_failed"]}},
            "failed:the product's own answer",
            id="any-other-answer",
        ),
        pytest.param(
            {"changes_retained": True},
            "retained_state_changed",
            id="an-admitted-rollback-that-changed-retained-state",
        ),
        pytest.param(
            {"answers": {"successor": ["runtime_install_failed"]}},
            "upgrade_failed:the product's own answer",
            id="no-way-back-to-the-successor",
        ),
    ],
)
def test_any_other_outcome_fails_the_leg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: dict[str, object], message: str
) -> None:
    """Only the two decisions pass; the failure carries the product's own answer."""
    adopter = _Adopter(tmp_path, monkeypatch)
    for name, value in change.items():
        setattr(adopter, name, value)
    with pytest.raises(RuntimeError, match="package_rollback_after_repair_") as raised:
        _prove(tmp_path)
    assert str(raised.value) == f"package_rollback_after_repair_{message}"


def test_the_journey_replaces_the_upgrade_constant_with_the_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The upgrade's `not_qualified` gives way to what the leg after the repair computed."""
    upgraded = {"state": "passed", "rollback_after_declaration_repair": "not_qualified"}
    monkeypatch.setattr(journey.adopter_fixture, "materialize_adopter", lambda *_a, **_k: None)
    monkeypatch.setattr(
        journey.runtime_acceptance, "prove_retained_upgrade", lambda *_a, **_k: dict(upgraded)
    )
    decided = {"rollback_after_declaration_repair": "admitted", **_LEFT}
    monkeypatch.setattr(journey, "prove_rollback_after_repair", lambda _root, **_k: decided)
    result = journey.prove_upgrade(Mock(), Mock(), tmp_path, environment={})
    assert result == {"state": "passed", **decided}
