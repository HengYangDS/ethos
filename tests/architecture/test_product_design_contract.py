from __future__ import annotations

import re
import shutil
import subprocess
import tomllib
from fnmatch import fnmatchcase
from itertools import pairwise
from pathlib import Path

import pytest

from ethos.repository.design.integrity import design_integrity_report
from ethos.surface.cli.application import app
from ethos.surface.cli.application import load_command_groups

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_OWNER = "docs/governance/product-design-contract.md"
PLAN = "docs/plans/terminal-governance-product-design.md"
AXIOMS = "system/axioms.md"
TERMINAL_TASKS = "openspec/changes/terminal-convergence/tasks.md"
TERMINAL_PROPOSAL = "openspec/changes/terminal-convergence/proposal.md"
TERMINAL_DESIGN = "openspec/changes/terminal-convergence/design.md"
TERMINAL_SPECS = "openspec/changes/terminal-convergence/specs"
PROJECTIONS = {
    "README.md",
    "docs/concepts/kernel-model.md",
    "docs/reference/glossary.md",
    "docs/reference/command-plane.md",
}
PUBLIC_ROOTS = {"status", "plan", "prove", "land", "publish", "adopt"}
HIDDEN_ROOTS = {"lane", "hook"}
TASK_PATTERN = re.compile(
    r"^- \[([ x])\] ((?:F|\d+)\.\d+(?:\.\d+)?)\s+(.+?)"
    r"(?=\n- \[[ x]\] |\n## |\n\*\*Exit|\Z)",
    re.MULTILINE | re.DOTALL,
)


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def headings(text: str) -> set[str]:
    return {
        re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", match.group(2).lower())).strip("-")
        for match in re.finditer(r"^(#{1,6})\s+(.+?)\s*$", text, re.MULTILINE)
    }


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}$", text, re.MULTILINE)
    assert match, heading
    following = re.search(r"^## [^#].+$", text[match.end() :], re.MULTILINE)
    end = match.end() + following.start() if following else len(text)
    return text[match.start() : end]


def task_rows(text: str) -> dict[str, tuple[str, str]]:
    rows: dict[str, tuple[str, str]] = {}
    for checked, identifier, body in TASK_PATTERN.findall(text):
        assert identifier not in rows
        rows[identifier] = (checked, " ".join(body.split()))
    return rows


def committed_tasks(commit: str) -> dict[str, tuple[str, str]]:
    text = subprocess.run(
        ("git", "show", f"{commit}:{TERMINAL_TASKS}"),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return task_rows(text)


@pytest.fixture
def design_tree(tmp_path: Path) -> Path:
    for relative in {CANONICAL_OWNER, PLAN, AXIOMS, *PROJECTIONS}:
        source = ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return tmp_path


def test_design_integrity_uses_owner_relations_not_prose_equivalence() -> None:
    report = design_integrity_report(ROOT)

    assert report["ok"] is True, report["required_gaps"]
    assert report["semantic_equivalence"] == "not_evaluated"
    assert PLAN in report["references"]


@pytest.mark.parametrize(
    ("heading", "required_tokens"),
    [
        ("Semantic Kernel", {"Commitment", "Attestation", "TransitionPlan", "Facts"}),
        ("Invalid-State Taxonomy", {"open", "unknown_required_fact", "model_promotion_required"}),
        ("Git-Native Repository Substrate", {"Git-native", "compare-and-swap", "work_lane"}),
        (
            "Isomorphic Adopter Governance",
            {"same kernel", "Profiles and adapters", "not product\ncloning"},
        ),
        (
            "Feedback Intent Preservation",
            {"semantic owner", "acceptance", "proof", "absence reason"},
        ),
        ("Projection Homomorphism", {"identity", "provenance", "validity", "absence reason"}),
    ],
)
def test_canonical_contract_covers_terminal_semantics(
    heading: str, required_tokens: set[str]
) -> None:
    body = section(read(CANONICAL_OWNER), heading)
    assert all(token in body for token in required_tokens), (heading, required_tokens)


def test_canonical_contract_uses_a_closed_machine_grammar_for_model_promotion() -> None:
    contract = read(CANONICAL_OWNER)
    body = re.search(r"^### Model Promotion$(.*?)(?=^## |\Z)", contract, re.MULTILINE | re.DOTALL)

    assert body
    text = body.group(1)
    assert {"contradiction", "model_gap", "model_promotion_required"} <= set(
        re.findall(r"\b[a-z_]+\b", text)
    )
    assert all(token in text for token in ("block effects", "retirement", "Preserve", "recompile"))
    assert not {"alias", "fallback", "shim"}.isdisjoint(set(re.findall(r"\b[a-z]+\b", text)))


def test_axioms_are_a_derived_constraint_not_a_second_truth() -> None:
    axioms = read(AXIOMS)

    assert axioms.startswith("---\n")
    assert "derives: ../docs/governance/product-design-contract.md#root-constraint" in axioms
    assert "second semantic owner" in axioms
    assert "道隐无名" not in axioms
    assert {"Commitment", "Attestation", "proposition"} <= set(
        re.findall(r"\b[A-Za-z][A-Za-z-]*\b", axioms)
    )


def test_design_integrity_rejects_missing_owner_anchor(design_tree: Path) -> None:
    contract = design_tree / CANONICAL_OWNER
    contract.write_text(
        contract.read_text(encoding="utf-8").replace("## Projection Homomorphism", "## Projection"),
        encoding="utf-8",
    )

    report = design_integrity_report(design_tree)

    assert (
        "design_canonical_owner_anchor_missing:projection-homomorphism" in report["required_gaps"]
    )


def test_design_integrity_rejects_unlinked_projection(design_tree: Path) -> None:
    projection = design_tree / "docs/concepts/kernel-model.md"
    projection.write_text(
        projection.read_text(encoding="utf-8").replace(
            "../governance/product-design-contract.md#semantic-kernel",
            "../governance/product-design-contract.md",
        ),
        encoding="utf-8",
    )

    report = design_integrity_report(design_tree)

    assert (
        "design_projection_owner_link_missing:docs/concepts/kernel-model.md"
        in report["required_gaps"]
    )


def test_design_integrity_rejects_non_derived_axioms(design_tree: Path) -> None:
    axioms = design_tree / AXIOMS
    axioms.write_text(
        axioms.read_text(encoding="utf-8").replace(
            "derives: ../docs/governance/product-design-contract.md#root-constraint",
            "projects: ../docs/governance/product-design-contract.md#semantic-kernel",
        ),
        encoding="utf-8",
    )

    report = design_integrity_report(design_tree)

    assert "design_axioms_derivation_metadata_invalid" in report["required_gaps"]


def test_design_integrity_rejects_duplicated_root_text(design_tree: Path) -> None:
    axioms = design_tree / AXIOMS
    root_line = next(
        line.removeprefix("> ")
        for line in (design_tree / CANONICAL_OWNER).read_text(encoding="utf-8").splitlines()
        if line.startswith("> ")
    )
    axioms.write_text(
        f"{axioms.read_text(encoding='utf-8')}\n{root_line}\n",
        encoding="utf-8",
    )

    report = design_integrity_report(design_tree)

    assert "design_axioms_duplicates_root_verse" in report["required_gaps"]


def test_terminal_plan_projects_canonical_semantics_without_repeating_its_model() -> None:
    plan = read(PLAN)

    assert "product-design-contract.md#semantic-kernel" in plan
    assert "product-design-contract.md#model-promotion" in plan
    assert headings(plan) >= {
        "semantic-authority-and-projection-homomorphism",
        "model-promotion",
        "git-native-transaction-boundary",
        "adopter-isomorphism-and-first-hour-ux",
        "feedback-intent-preservation",
    }
    assert "The only durable semantic roots" not in plan


def test_first_hour_projection_is_consistent_for_people_and_adopters() -> None:
    contract = read(CANONICAL_OWNER)
    readme = read("README.md")
    glossary = read("docs/reference/glossary.md")

    for text in (contract, readme, glossary):
        assert "same kernel" in text
        assert "profiles and adapters" in text.lower()
    assert "status -> plan -> prove -> land -> publish" in contract
    assert "status -> plan -> prove -> land -> publish" in readme


def test_live_cyclopts_tree_has_exact_public_and_hidden_roots() -> None:
    load_command_groups([])
    commands = {
        name: command
        for name, command in app.resolved_commands().items()
        if not name.startswith("-")
    }

    assert {name for name, command in commands.items() if command.show} == PUBLIC_ROOTS
    assert {name for name, command in commands.items() if not command.show} == HIDDEN_ROOTS


def test_terminal_tasks_preserve_stable_identity_and_completed_foundations() -> None:
    tasks = read(TERMINAL_TASKS)
    rows = re.findall(r"^- \[([ x])\] ((?:F|\d+)\.\d+(?:\.\d+)?)\b", tasks, re.MULTILINE)
    identifiers = [identifier for _state, identifier in rows]
    completed = {identifier for state, identifier in rows if state == "x"}

    assert len(identifiers) == len(set(identifiers))
    assert {f"F.{index}" for index in range(1, 12)} | {"0.1"} <= completed
    assert "first unchecked item in section 0 is the critical path" in tasks.replace("\n", " ")
    assert len(re.findall(r"^\*\*Exit \d:\*\*", tasks, re.MULTILINE)) == 8
    phase_zero = tasks.split("## 0. Restore Campaign Control And Intent Closure", 1)[1].split(
        "**Exit 0:**", 1
    )[0]
    assert re.findall(r"^- \[[ x]\] (0\.\d+(?:\.\d+)?)\b", phase_zero, re.MULTILINE) == [
        f"0.{index}" for index in range(1, 8)
    ]
    compact = " ".join(tasks.split())
    assert "0.2 Add failing tests for two-root persistence" in compact
    assert "0.3 Map every active carrier and legacy surface" in compact
    assert "0.4 Close every independent accepted feedback obligation" in compact


def test_terminal_thresholds_and_branch_roles_have_one_exact_projection() -> None:
    proposal = read(TERMINAL_PROPOSAL)
    tasks = read(TERMINAL_TASKS)
    routing = tomllib.loads(read("system/routing.toml"))["branch_roles"]
    coverage = tomllib.loads(read(".config/checks/coverage/policy.toml"))
    source_budget = tomllib.loads(read(".config/checks/format/selection.toml"))["source_budget"][
        "terminal"
    ]
    release = read("docs/governance/release-governance.md")

    assert routing == {
        "release_branch": "main",
        "accepted_branch": "dev",
        "candidate_branch": "candidate/dev",
        "work_branch_prefix": "work/",
        "proposal_branch_prefix": "proposal/",
    }
    assert coverage["current_hard_floor"] == 95
    assert coverage["branch_coverage_required"] is True
    assert source_budget == {"python_total": 54_000, "global_total": 68_000}
    for text in (proposal, tasks):
        assert all(token in text for token in ("54,000", "68,000", "95"))
    assert "`candidate/dev` and every `work/*` branch are local-only" in release
    assert "`dev`, `main`, and `proposal/*`" in release
    assert "submit/*" not in release


def test_terminal_execution_contract_is_self_profile_only_and_progress_is_irreversible() -> None:
    tasks = read(TERMINAL_TASKS)
    design = read(TERMINAL_DESIGN)
    compact_tasks = " ".join(tasks.split())
    compact_design = " ".join(design.split())

    assert "For the ETHOS self-profile only" in tasks
    assert "single campaign execution" in compact_tasks
    assert "obligation identity" in compact_tasks
    assert "never to reset progress" in compact_tasks
    assert "first incomplete task is the campaign critical path" in compact_design
    assert "elapsed activity without a terminal-state delta is not progress" in compact_design
    assert "old decisions" not in tasks.lower()

    assert "phase-local ordered coordinates" in compact_tasks
    assert "block task-ID reuse, completion reset" in compact_tasks


def test_terminal_intent_closure_and_post_cutover_task_history_are_complete() -> None:
    tasks = read(TERMINAL_TASKS)
    design = read(TERMINAL_DESIGN)
    governance = read(f"{TERMINAL_SPECS}/repository-governance/spec.md")
    audit = read("src/ethos/repository/audit.py")

    assert not (ROOT / "docs/governance/conversation-ledger.md").exists()
    assert "conversation-ledger.md" not in audit
    assert "## Carrier Disposition" in design
    assert "### Independent Fact-Boundary Closure" in design
    assert "## Accepted Feedback Closure" in design
    assert "## Pre-cutover Task Closure" in design
    assert "historical task identity is audited" in governance
    assert "history_is_current = false" in read("system/authority.toml")
    assert 'name = "history"\nmay_be_authoritative = false' in read("system/authority.toml")
    assert "the earlier ruling remains history and cannot silently return as current" in design
    assert "Official OpenSpec 1.7 Cutover" in design
    assert "post-archive HEAD" in tasks

    assert_feedback_and_carrier_closure(design)
    assert_task_history_closure(tasks, design)


def assert_feedback_and_carrier_closure(design: str) -> None:
    feedback = set(re.findall(r"^\| (CL-\d{3}) \|", design, re.MULTILINE))
    assert feedback == {f"CL-{number:03d}" for number in range(1, 26)}
    fact_boundaries = design.split("### Independent Fact-Boundary Closure", 1)[1].split(
        "## Accepted Feedback Closure", 1
    )[0]
    for required in (
        "one `src/ethos` distribution",
        "Domain contracts remain profile data",
        "OpenSpec remains a selectable self-profile carrier",
        "does not migrate into `tools/`",
        "`.mailmap` and package-root re-exports remain absent",
        "Retired Subject/Contract/Transition/Inscription/Chronicle/Evolve vocabulary",
    ):
        assert required in fact_boundaries
    disposition = design.split("## Carrier Disposition", 1)[1].split(
        "### Independent Fact-Boundary Closure", 1
    )[0]
    selector_cells = re.findall(
        r"^\| (.+?) \| .+? \| (?:absorbed|historical|deleted-after-proof) \|",
        disposition,
        re.MULTILINE,
    )
    assert selector_cells
    selector_rows = [
        re.findall(r"`([^`]+)`", cell)
        for cell in selector_cells
        if "linked `work/*` resources" not in cell
    ]
    tracked = subprocess.run(
        ("git", "ls-files"), cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.splitlines()
    for path in tracked:
        _assert_selector_winner(path, selector_rows)


def _assert_selector_winner(path: str, selector_rows: list[list[str]]) -> None:
    matching_rows = [
        index
        for index, selectors in enumerate(selector_rows)
        if any(fnmatchcase(path, selector) for selector in selectors)
    ]
    assert matching_rows, f"carrier_selector_missing:{path}"
    priorities = _matching_selector_priorities(path, selector_rows, matching_rows)
    assert priorities == sorted(priorities), f"carrier_selector_priority:{path}:{matching_rows}"
    assert priorities.count(min(priorities)) == 1, (
        f"carrier_selector_ambiguous:{path}:{matching_rows}"
    )


def _matching_selector_priorities(
    path: str, selector_rows: list[list[str]], matching_rows: list[int]
) -> list[tuple[int, int, int]]:
    return [
        min(
            _selector_priority(pattern)
            for pattern in selector_rows[index]
            if fnmatchcase(path, pattern)
        )
        for index in matching_rows
    ]


def _selector_priority(pattern: str) -> tuple[int, int, int]:
    parts = pattern.split("/")
    literal_parts = sum(not any(token in part for token in "*?[") for part in parts)
    literal_characters = sum(len(part.translate(str.maketrans("", "", "*?[]"))) for part in parts)
    wildcards = sum(pattern.count(token) for token in "*?[")
    return -literal_parts, -literal_characters, wildcards


def test_carrier_selector_rejects_equal_priority_winners() -> None:
    with pytest.raises(AssertionError, match="carrier_selector_ambiguous"):
        _assert_selector_winner("a/b/c", [["a/*/c"], ["a/b/*"]])


def assert_task_history_closure(tasks: str, design: str) -> None:
    pre_cutover_section = design.split("## Pre-cutover Task Closure", 1)[1].split(
        "## Alternatives Considered", 1
    )[0]
    historical = set(re.findall(r"^\| (.+?) \|", pre_cutover_section, re.MULTILINE))
    for identifier in ("0.2", "0.3", "1.6.1", "3.1.1", "3.3.4", "3.3.5", "4.7"):
        assert any(identifier in group for group in historical)

    closure_rows = re.findall(
        r"^\| (.+?) \| (?:absorbed|superseded|historical|deleted-after-proof|rejected|deferred) "
        r"\| (.+?) \| .+? \|$",
        pre_cutover_section,
        re.MULTILINE,
    )
    transitions = {
        source: tuple(re.findall(r"(?<![\w.])(?:F|\d+)\.\d+(?:\.\d+)?(?![\w.])", targets))
        for sources, targets in closure_rows
        for source in re.findall(r"(?<![\w.])(?:F|\d+)\.\d+(?:\.\d+)?(?![\w.])", sources)
    }
    baseline = committed_tasks("b23dc97cd92675bd3a6f58c13a1ec73c7f4ba2c6")
    current = task_rows(tasks)
    for identifier, (was_checked, body) in baseline.items():
        if identifier not in current:
            successors = transitions.get(identifier, ())
            assert successors, f"task_identity_unmapped:{identifier}"
            assert all(successor in current for successor in successors)
            if was_checked == "x":
                assert any(current[successor][0] == "x" for successor in successors)
            continue
        checked, current_body = current[identifier]
        assert current_body == body, f"task_identity_reused:{identifier}"
        assert not (was_checked == "x" and checked != "x"), f"task_completion_reset:{identifier}"

    history = subprocess.run(
        (
            "git",
            "rev-list",
            "--reverse",
            "5777d2d705^..b23dc97cd92675bd3a6f58c13a1ec73c7f4ba2c6",
            "--",
            TERMINAL_TASKS,
        ),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    pre_cutover = {identifier for commit in history for identifier in committed_tasks(commit)}
    mapped = {
        identifier
        for group in historical
        for identifier in re.findall(r"(?<![\w.])(?:F|\d+)\.\d+(?:\.\d+)?(?![\w.])", group)
    }
    assert pre_cutover <= set(current) | mapped
    assert_task_coordinate_normalization(history, baseline, current, transitions)
    assert_post_cutover_task_history(current, transitions)


def assert_post_cutover_task_history(
    current: dict[str, tuple[str, str]], transitions: dict[str, tuple[str, ...]]
) -> None:
    commits = subprocess.run(
        (
            "git",
            "rev-list",
            "--reverse",
            "b23dc97cd92675bd3a6f58c13a1ec73c7f4ba2c6^..HEAD",
            "--",
            TERMINAL_TASKS,
        ),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    snapshots = [committed_tasks(commit) for commit in commits] + [current]
    previous: dict[str, tuple[str, str]] = {}
    retired: set[str] = set()
    for rows in snapshots:
        assert not (retired & set(rows)), f"task_identity_resurrected:{retired & set(rows)}"
        for identifier, (checked, body) in rows.items():
            if identifier in previous:
                was_checked, previous_body = previous[identifier]
                assert body == previous_body, f"task_identity_reused:{identifier}"
                assert not (was_checked == "x" and checked != "x"), (
                    f"task_completion_reset:{identifier}"
                )
        removed = set(previous) - set(rows)
        assert all(identifier in transitions for identifier in removed), (
            f"task_identity_unmapped:{removed}"
        )
        retired.update(removed)
        previous = rows


def assert_task_coordinate_normalization(
    history: list[str],
    baseline: dict[str, tuple[str, str]],
    current: dict[str, tuple[str, str]],
    transitions: dict[str, tuple[str, ...]],
) -> None:
    historical_versions: dict[str, list[tuple[str, str]]] = {}
    for commit in history:
        for identifier, version in committed_tasks(commit).items():
            versions = historical_versions.setdefault(identifier, [])
            if not versions or versions[-1] != version:
                versions.append(version)
    reverse_transitions = {
        target: {source for source, targets in transitions.items() if target in targets}
        for target in current
    }
    for identifier in current:
        if identifier in baseline:
            continue
        predecessors = reverse_transitions.get(identifier, set()) & set(baseline)
        if identifier.startswith("F."):
            assert identifier in {
                successor for targets in transitions.values() for successor in targets
            }, f"task_coordinate_predecessor_missing:{identifier}"
            continue
        assert predecessors, f"task_coordinate_predecessor_missing:{identifier}"
        assert all(source in transitions for source in predecessors)
    assert_changed_coordinates_closed(historical_versions, baseline, current, transitions)


def assert_changed_coordinates_closed(
    historical_versions: dict[str, list[tuple[str, str]]],
    baseline: dict[str, tuple[str, str]],
    current: dict[str, tuple[str, str]],
    transitions: dict[str, tuple[str, ...]],
) -> None:
    known = set(baseline) | set(current)
    for identifier, versions in historical_versions.items():
        bodies = [body for _checked, body in versions]
        if len(bodies) < 2 or all(
            _task_body_extension(first, second) for first, second in pairwise(bodies)
        ):
            continue
        successors = transitions.get(identifier, ())
        assert successors, f"task_coordinate_prior_obligation_unclosed:{identifier}"
        assert all(successor in known for successor in successors)
        if any(checked == "x" for checked, _body in versions):
            assert any(
                successor.startswith("F.") and successor in current and current[successor][0] == "x"
                for successor in successors
            ), f"task_coordinate_completed_obligation_unclosed:{identifier}"


def _task_body_extension(first: str, second: str) -> bool:
    return first.startswith(second) or second.startswith(first)


def test_entrypoints_do_not_resurrect_global_authority_or_retired_kernel_names() -> None:
    agents = read("AGENTS.md")
    readme = read("README.md")

    assert "## Authority Order" not in agents
    assert all(token in agents for token in ("subject", "predicate", "scope", "plane", "validity"))
    assert all(token not in readme for token in ("ChangeContract", "RepositoryFacts", "PlanIR"))
    assert "(Commitment, Facts, prior Attestations) -> TransitionPlan" in readme
    assert "Only Commitment and Attestation persist" in readme


def test_terminal_archive_precedes_the_only_publication_sequence() -> None:
    tasks = read(TERMINAL_TASKS)

    assert tasks.index("6.10 Archive this Change") < tasks.index("## 7. Close The Campaign Once")
    assert "7.5 Archive this Change" not in tasks
    assert tasks.count("proposal/terminal-convergence") == 1
    assert "archive_tasks_incomplete" in tasks
    assert "with validation still enabled" in tasks
    assert "accepted capability specs and current Facts" in tasks
    assert "never remains a current execution owner" in tasks
    assert "no second proposal, release sequence" in tasks


def test_terminal_proposal_preserves_exact_public_roles_and_thresholds() -> None:
    proposal = read("openspec/changes/terminal-convergence/proposal.md")
    command_spec = read(f"{TERMINAL_SPECS}/command-plane/spec.md")
    quality_spec = read(f"{TERMINAL_SPECS}/quality/spec.md")

    assert all(token in proposal for token in ("54,000", "68,000", "95 percent"))
    assert all(token in quality_spec for token in ("54,000", "68,000", "95"))
    assert "`candidate/dev` and `work/*` remain local-only" in proposal
    assert "`dev` and default `main` are\nprotected" in proposal
    assert "`proposal/*` is the sole remote review branch role" in proposal
    assert "exactly the six public commands" in command_spec
    assert "without registering an `ethos openspec` public root" in command_spec


def test_terminal_runtime_owner_is_checkout_bound_through_with_python_runtime() -> None:
    runner = read("tools/ci/scripts/run-ethos-lane.sh")
    runtime = read("tools/ci/scripts/with-python-runtime.sh")

    assert 'exec "${script_dir}/with-python-runtime.sh" --' in runner
    assert 'uv run --group dev ethos "$@"' in runner
    assert "git rev-parse --show-toplevel" in runtime
    assert 'export ETHOS_RUNTIME_ROOT="${repo_root}"' in runtime
    assert not re.search(r"(?:^|[;&|])\s*(?:command\s+)?ethos(?:\s|$)", runner, re.MULTILINE)
    assert 'PATH="${repo_root}' not in runner


def test_terminal_specs_bind_the_critical_cross_surface_semantics() -> None:
    required = {
        "repository-governance/spec.md": (
            "takeover",
            "records",
            "candidate cas",
            "local convergence completion",
        ),
        "proof-hosts/spec.md": (
            "one terminal HEAD",
            "GitLab",
            "GitHub",
            "artifact",
            "bounded formal transition model",
        ),
        "contracts/spec.md": (
            "Python SDK",
            "subprocess JSON",
            "portable contract",
        ),
        "distribution/spec.md": (
            "one portable release contract",
            "artifact",
            "offline",
        ),
        "adapters/spec.md": (
            "exact permissions",
            "exact receipt",
            "mutation",
        ),
        "quality/spec.md": (
            "54,000",
            "68,000",
            "95",
            "repository-wide",
        ),
    }
    for relative, tokens in required.items():
        body = read(f"{TERMINAL_SPECS}/{relative}")
        assert all(token.lower() in body.lower() for token in tokens), (relative, tokens)
