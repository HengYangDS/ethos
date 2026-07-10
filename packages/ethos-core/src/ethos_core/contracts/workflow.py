"""Workflow contract helpers for ETHOS derived runtime projections.

These helpers validate `system/workflows.toml` as a contract. They do not run a
workflow engine and do not store lifecycle truth.
"""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

from ethos_core.action_graph.core import ActionGraph
from ethos_core.action_graph.core import ActionNode
from ethos_core.contracts.system.contracts import load_system_contract
from ethos_core.graph.core import GraphKernel
from ethos_core.graph.core import GraphNode
from ethos_core.state.invalid import NODE_ORDER

_ALLOWED_NODE_KINDS = {"control", "producer", "action", "handoff", "guardrail"}
_ALLOWED_ENFORCEMENT = {"guarded", "handoff-guarded", "evidence-only", "advisory"}
_ALLOWED_METRICS = {"pass_at_k", "pass_power_k", "weighted_score", "instability_gap"}
_EXPECTED_TRANSITION_COMMANDS = (
    "ethos status",
    "ethos plan",
    "ethos prove",
    "ethos land",
    "ethos publish",
)
_LEARNING_PATH_REQUIRED = (
    "research",
    "hypothesis",
    "experiment",
    "evaluation",
    "canonization",
    "retirement",
)
_COMMITMENT_EFFECT_POLICY = (
    "practice_claim_declares_create_compose_refine_replace_remove_or_reject_commitment_effect"
)
_PRACTICE_CHANGE_POLICY = (
    "relation_to_incumbent_determines_introduce_compose_refine_supersede_retire_or_reject"
)


class _WorkflowModel(BaseModel):
    """Strict immutable base for workflow declaration contracts."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class LifecycleDeclaration(_WorkflowModel):
    """Declared lifecycle states for the workflow runtime projection."""

    states: tuple[str, ...]
    initial: str = "planned"


class WorkflowTransition(_WorkflowModel):
    """One declared lifecycle transition and its guard facts."""

    source: str = Field(alias="from")
    target: str = Field(alias="to")
    guard: str
    invalid_state: str = ""
    required_facts: tuple[str, ...] = ()
    invalid_states: tuple[str, ...] = ()

    def to_projection(self) -> dict[str, Any]:
        """Project this transition to existing public command JSON."""
        return {
            "from": self.source,
            "to": self.target,
            "guard": self.guard,
            "required_facts": list(self.required_facts),
            "invalid_states": list(self.invalid_states),
        }


class WorkflowRuntimeDeclaration(_WorkflowModel):
    """Runtime metadata for the derived workflow read model."""

    truth_boundary: str = ""
    run_state_locality: str = ""
    run_state_schema: str = ""
    event_stream_locality: str = ""
    handoff_package_schema: str = ""
    public_lifecycle_commands: tuple[str, ...] = ()
    evolution_bridge: bool = False


class WorkflowNode(_WorkflowModel):
    """One declared workflow node used to compile graph projections."""

    id: str = ""
    kind: str = ""
    command: str = ""
    enforcement: str = ""
    requires: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()

    def graph_node(self, producer_by_fact: dict[str, str]) -> GraphNode | None:
        """Compile this node into the shared graph kernel input."""
        if not self.id:
            return None
        return GraphNode(id=self.id, depends_on=self.dependencies(producer_by_fact))

    def dependencies(self, producer_by_fact: dict[str, str]) -> tuple[str, ...]:
        """Return declared node dependencies via produced facts."""
        return tuple(
            dict.fromkeys(
                producer
                for requirement in self.requires
                if (producer := producer_by_fact.get(requirement)) and producer != self.id
            )
        )

    def external_requirements(self, producer_by_fact: dict[str, str]) -> tuple[str, ...]:
        """Return facts required by this node that are produced outside the graph."""
        return tuple(
            dict.fromkeys(
                requirement for requirement in self.requires if requirement not in producer_by_fact
            )
        )

    def to_summary(self) -> dict[str, Any]:
        """Project this node to the stable workflow report summary."""
        return {
            "id": self.id,
            "kind": self.kind,
            "enforcement": self.enforcement,
            "requires": list(self.requires),
            "produces": list(self.produces),
        }

    def to_action_node(
        self,
        *,
        inputs: tuple[str, ...],
        producer_by_fact: dict[str, str],
    ) -> ActionNode:
        """Compile this workflow declaration into an ActionGraph node."""
        return ActionNode(
            id=self.id,
            kind=str(self.kind),
            command=tuple(shlex.split(self.command)),
            inputs=inputs,
            outputs=self.produces,
            policy="required",
            depends_on=self.dependencies(producer_by_fact),
            metadata={
                "enforcement": str(self.enforcement),
                "requires": list(self.requires),
                "produces": list(self.produces),
                "source": "system/workflows.toml",
            },
        )


class WorkflowEvent(_WorkflowModel):
    """One workflow event declaration."""

    id: str = ""
    kind: str = ""
    locality: str = ""
    chronicle_promotion: str = ""


class WorkflowEvalDeclaration(_WorkflowModel):
    """Evaluation metadata for workflow practice experiments."""

    metric_names: tuple[str, ...] = ()
    bounds: str = ""
    truth_boundary: str = ""


class WorkflowEvolutionDeclaration(_WorkflowModel):
    """Evolution bridge declaration for trustworthy-practice claims."""

    learning_path: tuple[str, ...] = ()
    selection_policy: str = ""
    commitment_effect_policy: str = ""
    practice_claim_policy: str = ""
    practice_change_policy: str = ""
    truth_boundary: str = ""


class WorkflowContract(_WorkflowModel):
    """Validated source declaration for the ETHOS workflow runtime projection."""

    schema_path: str = Field(default="", alias="schema")
    lifecycle: LifecycleDeclaration = Field(default_factory=lambda: LifecycleDeclaration(states=()))
    transition: tuple[WorkflowTransition, ...] = ()
    guards: tuple[str, ...] = ()
    runtime: WorkflowRuntimeDeclaration = Field(default_factory=WorkflowRuntimeDeclaration)
    node: tuple[WorkflowNode, ...] = ()
    event: tuple[WorkflowEvent, ...] = ()
    eval: WorkflowEvalDeclaration = Field(default_factory=WorkflowEvalDeclaration)
    evolution: WorkflowEvolutionDeclaration = Field(default_factory=WorkflowEvolutionDeclaration)

    @field_validator("guards", mode="before")
    @classmethod
    def compile_guard_keys(cls, value: object) -> tuple[str, ...]:
        """Compile the TOML guard table into immutable guard ids."""
        if isinstance(value, dict):
            return tuple(str(item) for item in value)
        if isinstance(value, list | tuple):
            return tuple(str(item) for item in value)
        return ()

    def producer_by_fact(self) -> dict[str, str]:
        """Map produced facts to their first declared producer node."""
        producers: dict[str, str] = {}
        for item in self.node:
            if not item.id:
                continue
            for fact in item.produces:
                producers.setdefault(fact, item.id)
        return producers

    def selected_nodes(self, node_ids: tuple[str, ...]) -> tuple[WorkflowNode, ...]:
        """Return requested nodes in declaration order."""
        requested = set(node_ids)
        return tuple(item for item in self.node if item.id in requested)

    def graph_plan(self, nodes: tuple[WorkflowNode, ...] | None = None) -> dict[str, Any]:
        """Compile declared workflow nodes through the shared GraphKernel."""
        selected = self.node if nodes is None else nodes
        producer_by_fact = self.producer_by_fact()
        graph_nodes = tuple(
            graph_node
            for item in selected
            if (graph_node := item.graph_node(producer_by_fact)) is not None
        )
        return GraphKernel(nodes=graph_nodes).plan().to_dict()

    def external_requirements(
        self,
        nodes: tuple[WorkflowNode, ...] | None = None,
    ) -> list[dict[str, Any]]:
        """Project requirements that must be supplied by repository facts."""
        selected = self.node if nodes is None else nodes
        producer_by_fact = self.producer_by_fact()
        return [
            {"node": item.id, "requires": list(external)}
            for item in selected
            if item.id and (external := item.external_requirements(producer_by_fact))
        ]

    def action_graph(
        self,
        *,
        changed_paths: tuple[str, ...] = (),
        node_ids: tuple[str, ...] = ("status", "plan", "prove"),
    ) -> ActionGraph:
        """Compile a workflow node subset into an ActionGraph."""
        inputs = tuple(sorted(changed_paths)) or ("pyproject.toml",)
        selected = self.selected_nodes(node_ids)
        selected_ids = {item.id for item in selected}
        missing = tuple(
            f"workflow_plan_node_missing:{node_id}"
            for node_id in node_ids
            if node_id not in selected_ids
        )
        producer_by_fact = self.producer_by_fact()
        graph_nodes = tuple(
            graph_node
            for item in selected
            if (graph_node := item.graph_node(producer_by_fact)) is not None
        )
        ordered_ids = GraphKernel(nodes=graph_nodes).ordered_ids()
        by_id = {item.id: item for item in selected if item.id}
        nodes = tuple(
            by_id[node_id].to_action_node(inputs=inputs, producer_by_fact=producer_by_fact)
            for node_id in ordered_ids
            if node_id in by_id
        )
        return ActionGraph(nodes=nodes, validation_issues=missing)

    def to_report(self) -> dict[str, Any]:
        """Validate and summarize the declared workflow runtime contract."""
        states = set(self.lifecycle.states)
        guards = set(self.guards)
        gaps: list[str] = []
        gaps.extend(_transition_gaps(states, guards, self.transition))
        gaps.extend(_node_gaps(self.node))
        gaps.extend(_runtime_gaps(self.runtime))
        gaps.extend(_event_gaps(self.event))
        gaps.extend(_eval_gaps(self.eval))
        gaps.extend(_evolution_gaps(self.evolution))
        return {
            "ok": not gaps,
            "states": sorted(states),
            "transition_count": len(self.transition),
            "node_count": len(self.node),
            "event_count": len(self.event),
            "guard_count": len(guards),
            "nodes": [item.to_summary() for item in self.node],
            "runtime": self.runtime.model_dump(mode="json"),
            "eval": self.eval.model_dump(mode="json"),
            "evolution": self.evolution.model_dump(mode="json"),
            "required_gaps": list(dict.fromkeys(gaps)),
        }

    def to_projection(self, *, changed_paths: tuple[str, ...] = ()) -> dict[str, Any]:
        """Return deterministic transition projection data for `ethos plan`."""
        return {
            "kind": "workflow_runtime_plan",
            "truth_boundary": "derived_repository_projection",
            "changed_path_count": len(changed_paths),
            "changed_paths": list(changed_paths),
            "graph": self.graph_plan(),
            "external_requirements": self.external_requirements(),
            "transitions": [item.to_projection() for item in self.transition],
            "nodes": [item.to_summary() for item in self.node],
        }


def action_graph_from_workflow_contract(
    contract: WorkflowContract | dict[str, Any],
    *,
    changed_paths: tuple[str, ...] = (),
    node_ids: tuple[str, ...] = ("status", "plan", "prove"),
) -> ActionGraph:
    """Compile a workflow ``[[node]]`` declaration subset into an ActionGraph."""
    return _workflow_contract(contract).action_graph(changed_paths=changed_paths, node_ids=node_ids)


def workflow_contract_report(
    contract: WorkflowContract | dict[str, Any],
) -> dict[str, Any]:
    """Validate and summarize the declared workflow runtime contract."""
    return _workflow_contract(contract).to_report()


def planned_transition_projection(
    contract: WorkflowContract | dict[str, Any],
    *,
    changed_paths: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Return deterministic transition projection data for `ethos plan`."""
    return _workflow_contract(contract).to_projection(changed_paths=changed_paths)


def load_workflow_contract_declaration(
    root: Path | str | None = None,
) -> WorkflowContract:
    """Load and validate the tracked workflow runtime declaration."""
    return WorkflowContract.model_validate(load_system_contract(Path(root or "."), "workflows"))


def _workflow_contract(contract: WorkflowContract | dict[str, Any]) -> WorkflowContract:
    if isinstance(contract, WorkflowContract):
        return contract
    return WorkflowContract.model_validate(contract)


def _transition_gaps(
    states: set[str],
    guards: set[str],
    transitions: tuple[WorkflowTransition, ...],
) -> list[str]:
    taxonomy = set(NODE_ORDER)
    gaps: list[str] = []
    if not transitions:
        gaps.append("workflow_transition_missing")
    for index, item in enumerate(transitions):
        if item.source not in states:
            gaps.append(f"workflow_transition_state_unknown:{index}:from:{item.source}")
        if item.target not in states:
            gaps.append(f"workflow_transition_state_unknown:{index}:to:{item.target}")
        if item.guard not in guards:
            gaps.append(f"workflow_transition_guard_unknown:{index}:{item.guard}")
        invalid_states = set(item.invalid_states)
        if item.invalid_state not in taxonomy:
            gaps.append(f"workflow_transition_invalid_state_unknown:{index}:{item.invalid_state}")
        if item.invalid_state and item.invalid_state not in invalid_states:
            gaps.append(
                f"workflow_transition_invalid_state_not_listed:{index}:{item.invalid_state}"
            )
        gaps.extend(
            f"workflow_transition_invalid_state_unknown:{index}:{unknown}"
            for unknown in sorted(invalid_states - taxonomy)
        )
    return gaps


def _node_gaps(nodes: tuple[WorkflowNode, ...]) -> list[str]:
    gaps: list[str] = []
    ids: set[str] = set()
    for index, item in enumerate(nodes):
        node_key = item.id or str(index)
        if not item.id:
            gaps.append(f"workflow_node_id_missing:{index}")
        elif item.id in ids:
            gaps.append(f"workflow_node_id_duplicate:{item.id}")
        ids.add(item.id)
        if item.kind not in _ALLOWED_NODE_KINDS:
            gaps.append(f"workflow_node_kind_unknown:{node_key}:{item.kind}")
        if item.enforcement not in _ALLOWED_ENFORCEMENT:
            gaps.append(f"workflow_node_enforcement_unknown:{node_key}:{item.enforcement}")
        if item.enforcement == "handoff-guarded" and item.kind != "handoff":
            gaps.append(f"workflow_node_handoff_enforcement_kind_mismatch:{item.id}")
        if item.kind == "guardrail" and item.enforcement == "advisory":
            gaps.append(f"workflow_guardrail_advisory:{item.id}")
    return gaps


def _runtime_gaps(runtime: WorkflowRuntimeDeclaration) -> list[str]:
    gaps: list[str] = []
    if runtime.truth_boundary != "derived_repository_projection":
        gaps.append("workflow_runtime_truth_boundary_invalid")
    if runtime.public_lifecycle_commands != _EXPECTED_TRANSITION_COMMANDS:
        gaps.append("workflow_runtime_public_commands_invalid")
    gaps.extend(
        f"workflow_runtime_{key}_missing"
        for key, value in (
            ("run_state_schema", runtime.run_state_schema),
            ("handoff_package_schema", runtime.handoff_package_schema),
        )
        if not value
    )
    return gaps


def _event_gaps(events: tuple[WorkflowEvent, ...]) -> list[str]:
    gaps: list[str] = []
    for index, item in enumerate(events):
        event_id = item.id or str(index)
        if item.locality != "generated_until_chronicle_promotion":
            gaps.append(f"workflow_event_locality_invalid:{event_id}")
        if not item.chronicle_promotion:
            gaps.append(f"workflow_event_chronicle_promotion_missing:{event_id}")
    return gaps


def _eval_gaps(eval_contract: WorkflowEvalDeclaration) -> list[str]:
    gaps: list[str] = []
    metrics = set(eval_contract.metric_names)
    if not metrics:
        gaps.append("workflow_eval_metrics_missing")
    gaps.extend(
        f"workflow_eval_metric_unknown:{metric}" for metric in sorted(metrics - _ALLOWED_METRICS)
    )
    if eval_contract.truth_boundary != "skill_metadata_only":
        gaps.append("workflow_eval_truth_boundary_invalid")
    return gaps


def _evolution_gaps(evolution: WorkflowEvolutionDeclaration) -> list[str]:
    gaps: list[str] = []
    if not evolution.model_dump(exclude_defaults=True):
        gaps.append("workflow_evolution_bridge_missing")
        return gaps
    if evolution.selection_policy != "evidence_weighted_candidate_comparison":
        gaps.append("workflow_evolution_selection_policy_invalid")
    if evolution.commitment_effect_policy != _COMMITMENT_EFFECT_POLICY:
        gaps.append("workflow_evolution_commitment_effect_policy_invalid")
    if (
        evolution.practice_claim_policy
        != "practice_claim_is_evolution_carrier_for_governed_commitment_effect"
    ):
        gaps.append("workflow_evolution_practice_claim_policy_invalid")
    if evolution.practice_change_policy != _PRACTICE_CHANGE_POLICY:
        gaps.append("workflow_evolution_practice_change_policy_invalid")
    if evolution.truth_boundary != "evolution_ledger_claim_evidence_chronicle":
        gaps.append("workflow_evolution_truth_boundary_invalid")
    missing = [item for item in _LEARNING_PATH_REQUIRED if item not in evolution.learning_path]
    gaps.extend(f"workflow_evolution_learning_stage_missing:{item}" for item in missing)
    return gaps
