"""OpenSpec conventions of the repository paradigm and their deterministic repairs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.openspec import CONFIGURATION
from ethos.repository.paradigm.openspec import common_rules_repair
from ethos.repository.paradigm.openspec import openspec_gaps
from ethos.repository.paradigm.repair import paradigm_repair_plan

if TYPE_CHECKING:
    from pathlib import Path

PARADIGM = load_repository_paradigm()
COMMON = PARADIGM.openspec.rules.model_dump(mode="json")
ARTIFACTS = tuple(COMMON)
OWN_TASK = "Name the verifier that proves each task."
SPEC = "openspec/specs/sample/spec.md"


def _gaps(root: Path, text: str | None, *, path: str = CONFIGURATION) -> list:
    """Evaluate a repository that tracks one OpenSpec spec and, unless absent, the carrier."""
    if text is not None:
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")
    tracked = frozenset({SPEC, *([path] if text is not None else [])})
    return list(openspec_gaps(PARADIGM, root, tracked))


def _repair(root: Path, text: str | None) -> tuple[str | None, list]:
    """Apply the deterministic plan once and return the result and its report-only gaps."""
    plan = paradigm_repair_plan(root, _gaps(root, text))
    after = next((edit.after for edit in plan.edits if edit.path == CONFIGURATION), None)
    return after, [gap.carrier for gap in plan.report_only]


def _conforming(**own: list[str]) -> str:
    rules = {artifact: [*common, *own.get(artifact, [])] for artifact, common in COMMON.items()}
    return yaml.safe_dump({"schema": "spec-driven", "rules": rules}, sort_keys=False)


def test_packaged_common_rules_cover_every_spec_driven_artifact() -> None:
    """The contract selects spec-driven and holds non-empty rules for each of its artifacts."""
    assert PARADIGM.openspec.artifact_schema == "spec-driven"
    assert ARTIFACTS == ("proposal", "specs", "design", "tasks")
    assert all(rules and all(rules) for rules in COMMON.values())


def test_a_repository_without_openspec_artifacts_has_no_openspec_obligation(
    tmp_path: Path,
) -> None:
    """The obligation applies where OpenSpec is tracked; it never creates empty structure."""
    assert list(openspec_gaps(PARADIGM, tmp_path, frozenset({"README.md"}))) == []


def test_a_configuration_beginning_with_the_common_rules_conforms(tmp_path: Path) -> None:
    """Repository rules after the common ones and other keys leave nothing to report."""
    text = _conforming(tasks=[OWN_TASK]).replace("rules:", "context: |\n  Sample.\nrules:", 1)
    assert _gaps(tmp_path, text) == []


def test_another_schema_and_a_missing_common_rule_are_reported(tmp_path: Path) -> None:
    """Each missing common prefix names its artifact; another schema names the shared one."""
    text = f"schema: custom\nrules:\n  tasks:\n    - {OWN_TASK}\n"
    gaps = _gaps(tmp_path, text)
    assert [(gap.obligation, gap.carrier) for gap in gaps] == [
        ("openspec-schema", f"{CONFIGURATION}:schema"),
        *(("openspec-rules", f"{CONFIGURATION}:rules.{artifact}") for artifact in ARTIFACTS),
    ]
    assert gaps[0].repair == "set schema to spec-driven"
    assert gaps[-1].required_gap == (
        f"repository_paradigm_openspec_rules:{CONFIGURATION}:rules.tasks"
    )
    assert gaps[-1].repair.startswith("begin rules.tasks with the paradigm's common tasks rules")


def test_repair_puts_common_rules_first_and_keeps_own_lines(tmp_path: Path) -> None:
    """Own items keep their exact lines and comments; copies of a common rule are dropped."""
    common_specs = COMMON["specs"][0]
    text = (
        "# Repository configuration.\n"
        "schema: spec-driven\n"
        "context: |\n"
        "  Sample product.\n"
        "rules:\n"
        "  # Repository rules.\n"
        "  proposal: [state intent and scope]\n"
        "  specs:\n"
        "  # Keep this list short.\n"
        f"  - {common_specs}\n"
        "  # The repository's own rule.\n"
        "  - Name the\n"
        "    capability owner.\n"
        "  tasks:\n"
        f"    - {OWN_TASK}\n"
        "operations:\n"
        "  apply:\n"
        "    guidance:\n"
        "      - Resolve status first.\n"
    )
    after, report_only = _repair(tmp_path, text)
    assert report_only == []
    assert after is not None
    declared = yaml.safe_load(after)
    assert declared["rules"] == {
        "proposal": [*COMMON["proposal"], "state intent and scope"],
        "specs": [*COMMON["specs"], "Name the capability owner."],
        "tasks": [*COMMON["tasks"], OWN_TASK],
        "design": COMMON["design"],
    }
    original = yaml.safe_load(text)
    assert {key: value for key, value in declared.items() if key != "rules"} == {
        key: value for key, value in original.items() if key != "rules"
    }
    for kept in (
        "# Repository configuration.\n",
        "  # Repository rules.\n",
        "  # Keep this list short.\n",
        "  # The repository's own rule.\n  - Name the\n    capability owner.\n",
        f"    - {OWN_TASK}\n",
    ):
        assert kept in after
    assert max(len(line) for line in after.splitlines()) <= 100
    (tmp_path / CONFIGURATION).write_text(after, encoding="utf-8")
    assert _gaps(tmp_path, after) == []
    assert _repair(tmp_path, after) == (None, [])


@pytest.mark.parametrize(
    "text",
    [None, "schema: spec-driven\nrules:\n", "schema: spec-driven\nrules:\n  tasks:\n"],
    ids=["absent", "empty-rules", "empty-artifact"],
)
def test_repair_completes_an_absent_or_empty_configuration(
    tmp_path: Path, text: str | None
) -> None:
    """A missing configuration, rules key or rule list gets the schema and every common rule."""
    after, report_only = _repair(tmp_path, text)
    assert report_only == []
    assert after is not None
    assert yaml.safe_load(after) == {"schema": "spec-driven", "rules": COMMON}
    assert _gaps(tmp_path, after) == []


def test_repair_adds_a_missing_schema_ahead_of_the_first_key(tmp_path: Path) -> None:
    """The schema line goes before the first key, after any leading comment."""
    text = _conforming().replace("schema: spec-driven\n", "# Sample.\n", 1)
    after, report_only = _repair(tmp_path, text)
    assert report_only == []
    assert after == text.replace("# Sample.\n", "# Sample.\nschema: spec-driven\n", 1)


def test_repair_quotes_an_own_rule_that_plain_style_cannot_carry(tmp_path: Path) -> None:
    """A flow item rendered as a block item keeps its value, quoted where plain style fails."""
    after, report_only = _repair(
        tmp_path, "schema: spec-driven\nrules:\n  tasks: ['Keep: short']\n"
    )
    assert report_only == []
    assert after is not None
    assert "    - 'Keep: short'\n" in after
    assert yaml.safe_load(after)["rules"]["tasks"] == [*COMMON["tasks"], "Keep: short"]


def test_rules_stay_report_only_without_a_yaml_print_width(tmp_path: Path) -> None:
    """The rules repair renders within the YAML formatter's width, so it needs that binding."""
    unbound = PARADIGM.model_copy(
        update={
            "formatter": tuple(item for item in PARADIGM.formatter if ".yaml" not in item.suffixes)
        }
    )
    gap = _gaps(tmp_path, "schema: spec-driven\n")[-1]
    assert common_rules_repair(unbound, gap, "schema: spec-driven\n") is None


def test_repair_appends_rules_after_a_commented_template(tmp_path: Path) -> None:
    """A configuration with only the schema and comments keeps them ahead of the new rules."""
    text = "schema: spec-driven\n\n# Per-artifact rules (optional)\n#   rules:\n"
    after, _ = _repair(tmp_path, text)
    assert after is not None
    assert after.startswith(text.rstrip("\n") + "\n\nrules:\n  proposal:\n")
    assert yaml.safe_load(after) == {"schema": "spec-driven", "rules": COMMON}


@pytest.mark.parametrize(
    ("path", "text", "repair"),
    [
        (
            "openspec/config.yml",
            "schema: spec-driven\n",
            f"rename openspec/config.yml to {CONFIGURATION}",
        ),
        (CONFIGURATION, "- not\n- a mapping\n", f"make {CONFIGURATION} a readable YAML mapping"),
        (CONFIGURATION, "schema: [\n", f"make {CONFIGURATION} a readable YAML mapping"),
    ],
    ids=["alternate-name", "not-a-mapping", "invalid-yaml"],
)
def test_an_unreadable_or_alternate_configuration_stays_report_only(
    tmp_path: Path, path: str, text: str, repair: str
) -> None:
    """Only the configuration gap is reported, and no repair is derived for it."""
    gaps = _gaps(tmp_path, text, path=path)
    assert [(gap.obligation, gap.carrier, gap.repair) for gap in gaps] == [
        ("openspec-configuration", path, repair)
    ]
    plan = paradigm_repair_plan(tmp_path, gaps)
    assert plan.edits == ()
    assert plan.report_only == tuple(gaps)


def test_both_configuration_names_keep_the_canonical_one(tmp_path: Path) -> None:
    """With both names tracked, the alternate is the one to remove."""
    (tmp_path / "openspec").mkdir()
    (tmp_path / CONFIGURATION).write_text(_conforming(), encoding="utf-8")
    (tmp_path / "openspec/config.yml").write_text(_conforming(), encoding="utf-8")
    tracked = frozenset({CONFIGURATION, "openspec/config.yml"})
    [gap] = openspec_gaps(PARADIGM, tmp_path, tracked)
    assert (
        gap.repair == f"remove openspec/config.yml; {CONFIGURATION} is the OpenSpec configuration"
    )


@pytest.mark.parametrize(
    ("text", "report_only"),
    [
        ("schema: custom\n", ["schema"]),
        ("schema: a\nschema: b\n", ["schema"]),
        ("schema: spec-driven\nrules:\n  - a\n", list(ARTIFACTS)),
        ("schema: spec-driven\nrules: {tasks: [a]}\n", list(ARTIFACTS)),
        ('schema: spec-driven\n"rules":\n  tasks:\n    - a\n', list(ARTIFACTS)),
        ("schema: spec-driven\nrules:\n  tasks: one rule\n", ["tasks"]),
        ("schema: spec-driven\nrules:\n  tasks: |\n    one rule\n", ["tasks"]),
        ("schema: spec-driven\nrules:\n  tasks: [a,\n    b]\n", ["tasks"]),
        ("schema: spec-driven\nrules:\n  tasks:\n    - {a: b}\n", ["tasks"]),
        ('schema: spec-driven\nrules:\n  "tasks":\n    - a\n', list(ARTIFACTS)),
        ("schema: spec-driven\nrules:\n  tasks:\n    - a\n  tasks:\n    - b\n", ["tasks"]),
        ("schema: spec-driven\nrules:\n  tasks:\n    [a, b]\n", ["tasks"]),
        ("schema: spec-driven\nrules:\n  tasks:\n    - &rule A.\n    - *rule\n", ["tasks"]),
        ("schema: spec-driven\nrules:\n  tasks: [a]  # keep\n", ["tasks"]),
    ],
    ids=[
        "other-schema",
        "repeated-schema",
        "rules-list",
        "rules-flow-mapping",
        "quoted-key",
        "scalar-rules",
        "block-scalar-rules",
        "multi-line-flow",
        "mapping-item",
        "quoted-artifact-key",
        "repeated-artifact",
        "flow-on-next-line",
        "aliased-item",
        "flow-with-comment",
    ],
)
def test_shapes_the_repair_cannot_isolate_stay_report_only(
    tmp_path: Path, text: str, report_only: list[str]
) -> None:
    """A rewrite that would need judgment or guessing leaves its gap with the report."""
    _after, remaining = _repair(tmp_path, text)
    assert remaining == [
        f"{CONFIGURATION}:{name if name == 'schema' else f'rules.{name}'}" for name in report_only
    ]
