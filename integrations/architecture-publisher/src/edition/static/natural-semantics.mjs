import { verifyMeaningCarriers } from "../evolution.mjs";

/** A bounded endpoint/type check, not semantic approval. Structural junctions
 * are contracted before comparing the source and target semantic identities. */
export function auditNaturalSemantics(v, input, sourceDocuments = []) {
  const failures = [],
    source = new Map(input.semantics.relations.map((r) => [r.id, r]));
  const edges = v.document.relations,
    marks = new Map(v.document.marks.map((m) => [m.id, m]));
  const paths = [],
    routing = [],
    conditions = [];
  const authoredMeaning = new Set(
    (v.authoredCarriers?.meaning ?? []).map(({ kind, id }) => `${kind}:${id}`),
  );
  if (v.authoredCarriers) {
    try {
      const carriers = Object.fromEntries(v.document.labels.map((l) => [l.id, l.text]));
      verifyMeaningCarriers(input, v.authoredCarriers.meaning, carriers, sourceDocuments);
      if (v.authoredCarriers.edits.some((e) => carriers[e.id] !== e.after))
        throw Error("Changed authored carrier");
    } catch {
      failures.push("authored-meaning-visible");
    }
  }
  if (v.refresh) {
    try {
      const carriers = Object.fromEntries(v.document.labels.map((l) => [l.id, l.text]));
      verifyMeaningCarriers(
        input,
        [
          {
            kind: "node",
            id: v.refresh.node,
            sha256: v.refresh.sha256,
            carriers: v.refresh.labels,
          },
        ],
        carriers,
      );
      if (
        carriers["refresh-options"] !== [v.refresh.replay, v.refresh.merge].join(" · ") ||
        carriers["refresh-pending"] !== v.refresh.pending
      )
        throw Error("Changed refresh carrier");
      if (carriers["refresh-pending-key"] !== "Pending")
        throw Error("Missing pending-merge field name");
    } catch {
      failures.push("refresh-meaning-visible");
    }
  }
  const edgeIds = new Set(edges.map((e) => e.id));
  if (edgeIds.size !== edges.length) failures.push("duplicate-relation-identity");
  if (marks.size !== v.document.marks.length) failures.push("duplicate-mark-identity");
  if (
    input.semantics.nodes.runtime_generation_retirement.attributes.required_consumer_observations.includes(
      "linked_interpreter_bindings",
    )
  ) {
    const admission = v.candidateAdmission,
      g = input.semantics.contracts.gates.candidate_integration_gate;
    const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
    const capability = v.capabilityContract;
    const visible = (prefix) =>
      v.document.labels
        .filter((l) => l.id.startsWith(prefix))
        .map((l) => l.text)
        .join(" ");
    const scopedRequirements = [
      [
        "intent-scope",
        ["Problem research", "examples", "scope", "exceptions", "assumptions", "guarantees"],
        "problem-research-visible",
      ],
      [
        "action-conjunction",
        ["Subject delegates to Actor", "policy/intent/Facts/Plan"],
        "subject-delegation-visible",
      ],
      [
        "thesis",
        [
          "Plan selects",
          authoredMeaning.has("node:skills") ? "versioned Skills/tools" : "official/mature",
          "Skills/tools",
          "people/Agents in session",
        ],
        "actor-capability-use-visible",
      ],
      [
        "responsibility-owners-label",
        ["ETHOS repo: source + durable evidence"],
        "repository-ownership-visible",
      ],
      [
        "responsibility-owners-value",
        ["One owner/current consumer", "executable rules", "bounded lifecycle"],
        "native-lifecycle-visible",
      ],
      [
        "runtime-family",
        [
          "Activation report",
          "hooks path/runtime",
          "all worktrees checked/repaired",
          "generations retained/removed",
        ],
        "family-report-visible",
      ],
      [
        "capability-purity",
        [
          "Code/tests/specs/config/docs/rules/Skills",
          "temporary resources",
          "Pure semantics; bounded effects",
        ],
        "semantic-effect-boundary-visible",
      ],
    ];
    for (const [prefix, terms, code] of scopedRequirements)
      if (!terms.every((term) => visible(prefix).includes(term))) failures.push(code);
    if (visible("verification-trust") !== "Hosted: observe; no permission")
      failures.push("hosted-claim-authority-scope");
    const verificationCopy = visible("verification-");
    for (const term of [
      "Optional:",
      "local/independent claim IDs",
      "explicit rule",
      "Responsible verifier",
      "new composite claim",
      "No scope gain",
    ])
      if (!verificationCopy.includes(term)) failures.push("composite-production-visible");
    if (!visible("intent-status").includes("pending verification"))
      failures.push("intent-status-scope");
    if (visible("resource-greenfield_effect-obligation") !== "Minimal native Skills scaffold")
      failures.push("formation-scope");
    if (!visible("attestation-scope").includes("Binds Commitment/pre/effect/post"))
      failures.push("attestation-binding-visible");
    if (
      v.document.labels.find((l) => l.id === "responsibility-views-label")?.text !==
      "Rebuildable CLI/JSON · SDK · CI/Forge"
    )
      failures.push("projection-rebuildability-scope");
    const projectionCopy = v.document.labels.find(
      (l) => l.id === "responsibility-views-value",
    )?.text;
    const projectionTerms = authoredMeaning.has("assertion:projection")
      ? ["context", "MCP", "A2A"]
      : ["From native source/evidence"];
    if (!projectionTerms.every((term) => projectionCopy?.includes(term)))
      failures.push("projection-native-source-visible");
    if (
      !v.document.labels
        .find((l) => l.id === "verification-applicability")
        ?.text.includes("separate trust")
    )
      failures.push("independent-trust-visible");
    if (
      !capability ||
      capability.source !== "capability_contract" ||
      capability.effectAuthority !== false
    )
      failures.push("capability-contract-scope");
    if (
      !equal(capability?.sourceRelations, [
        "contracts-constrain-skills",
        "contracts-constrain-verification",
      ]) ||
      capability?.sourceRelations.some(
        (id) =>
          source.get(id)?.from !== "capability_contract" || source.get(id)?.kind !== "narrows",
      )
    )
      failures.push("capability-contract-relations");
    if (
      capability?.verifier !== "verification-independent" ||
      !equal(v.witnesses.marks[capability?.verifier ?? ""], ["independent_verifier"])
    )
      failures.push("capability-contract-verifier");
    const capabilityCopy = (capability?.labels ?? [])
      .map((id) => v.document.labels.find((l) => l.id === id)?.text ?? "")
      .join(" ");
    if (!visible("responsibility-methods-label").includes("tools"))
      failures.push("capability-contract-visible:tools");
    for (const term of [
      "Skills",
      "tools",
      "generators",
      "verifiers",
      "observers",
      "Small contracts:",
      "I/O",
      "identity/version",
      "permission",
      "cancel/failure",
      "no authority/lifecycle",
      "Plan selects",
      authoredMeaning.has("node:skills") ? "versioned Skills/tools" : "official/mature",
      "people/Agents in session",
      "Independent verifier",
    ])
      if (!capabilityCopy.includes(term)) failures.push("capability-contract-visible:" + term);
    if (
      !capabilityCopy.includes("roles") ||
      !capabilityCopy.includes("versioned interpretation") ||
      !capabilityCopy.includes("no authority/lifecycle ownership")
    )
      failures.push("capability-name-version-scope");
    if (
      !admission ||
      admission.gate !== "candidate_integration_gate" ||
      admission.mode !== "all" ||
      g.mode !== "all" ||
      admission.effectAuthority !== false
    )
      failures.push("candidate-admission-mode");
    if (
      admission?.evaluation !== "candidate-evaluation" ||
      admission?.pass !== "candidate-admission" ||
      !equal(v.witnesses.marks["candidate-evaluation"], ["candidate_integration_evaluation"]) ||
      !equal(v.witnesses.marks["candidate-admission"], ["candidate_integration_pass"])
    )
      failures.push("candidate-admission-identity");
    if (
      !equal(
        admission?.inputs.map((i) => i.source),
        g.required_inputs,
      )
    )
      failures.push("candidate-admission-inputs");
    const terms = {
      authority_reference: ["Policy"],
      commitment_n: ["Commitment"],
      fresh_facts: ["Facts"],
      transition_plan: ["Plan"],
      candidate_bundle: ["Proven object"],
      candidate_state: ["state"],
      lane_proof_claim: ["one selected Lane proof"],
    };
    for (const binding of admission?.inputs ?? []) {
      const relation = source.get(binding.relation),
        label = v.document.labels.find((l) => l.id === binding.label);
      const copy = v.document.labels
        .filter((l) => l.id === binding.label || l.id.startsWith(binding.label + "-"))
        .map((l) => l.text)
        .join(" ");
      const kind = binding.source === "lane_proof_claim" ? "returns" : "binds";
      if (
        relation?.from !== binding.source ||
        relation?.to !== "candidate_integration_evaluation" ||
        relation?.kind !== kind ||
        relation?.attributes.guard !== admission?.gate
      )
        failures.push("candidate-admission-input-relation:" + binding.source);
      if (!label || !terms[binding.source]?.every((term) => copy.includes(term)))
        failures.push("candidate-admission-input-visible:" + binding.source);
    }
    const candidateRow = v.resourceRows?.find((r) => r.contract === "candidate_integration_effect");
    const rowLabels = new Set(candidateRow?.labels ?? []),
      rowCopy = (candidateRow?.labels ?? [])
        .map((id) => v.document.labels.find((l) => l.id === id)?.text ?? "")
        .join(" ");
    if (admission?.inputs.some((b) => !rowLabels.has(b.label)))
      failures.push("candidate-conjunction-locality");
    for (const term of [
      "All: Proven object",
      "state",
      "Commitment",
      "Policy/Facts/Plan",
      "one selected Lane proof",
    ])
      if (!rowCopy.includes(term)) failures.push("candidate-conjunction-visible");
    if (
      admission?.claimSelector !== g.required_claim_selector ||
      !equal(admission?.failureOutputs, g.failure_outputs)
    )
      failures.push("candidate-admission-claim");
    const title = v.document.labels.find((l) => l.id === "candidate-evaluation-label"),
      passLabel = v.document.labels.find((l) => l.id === "candidate-pass-label");
    if (
      title?.text !== "All inputs" ||
      title.about !== "candidate-evaluation" ||
      passLabel?.text !== "PASS" ||
      passLabel.about !== "candidate-admission" ||
      !equal(admission?.labels, ["candidate-evaluation-label", "candidate-pass-label"])
    )
      failures.push("candidate-admission-visible");
    for (const [id, from, to, relation] of [
      [
        "candidate-request",
        "combination",
        "candidate-evaluation",
        "candidate-bundle-binds-integration",
      ],
      [
        "candidate-pass",
        "candidate-evaluation",
        "candidate-admission",
        "candidate-integration-pass-branch",
      ],
      ["candidate-permission", "candidate-admission", "candidate-cas", "candidate-pass-to-recheck"],
    ]) {
      const edge = edges.find((e) => e.id === id);
      if (
        edge?.source !== from ||
        edge?.target !== to ||
        !equal(v.witnesses.relations[id], [relation])
      )
        failures.push("candidate-admission-path");
    }
    if (
      edges
        .filter((e) => e.target === "candidate-admission")
        .some((e) => e.source !== "candidate-evaluation")
    )
      failures.push("candidate-admission-path");
    const loss = v.lossRecovery;
    if (
      !loss ||
      loss.event !== "protocol-loss" ||
      loss.anchor !== "protocol-reobserve" ||
      loss.interrupts !== "session_host" ||
      loss.effectAuthority !== false ||
      JSON.stringify(loss.sourceRelations) !==
        JSON.stringify(["loss-interrupts-session", "loss-to-recovery-anchor"])
    )
      failures.push("loss-recovery-scope");
    const trigger = v.document.labels.find((l) => l.id === "protocol-loss-label");
    if (
      trigger?.text !== "Actor/session/host loss" ||
      trigger.about !== "protocol-loss" ||
      JSON.stringify(v.witnesses.marks["protocol-loss"]) !== JSON.stringify(["executor_loss"])
    )
      failures.push("loss-recovery-visible");
    const lossEdge = edges.find((e) => e.id === "loss-reobserve"),
      merge = edges.find((e) => e.id === "recovery-join-observe");
    if (
      lossEdge?.source !== "protocol-loss" ||
      lossEdge?.target !== "protocol-recovery-join" ||
      merge?.source !== "protocol-recovery-join" ||
      merge?.target !== "protocol-reobserve" ||
      !v.routingEdges["recovery-join-observe"]
    )
      failures.push("loss-recovery-path");
    const reaches = (target, omit = []) => {
      const seen = new Set(omit),
        queue = ["protocol-loss"];
      for (let i = 0; i < queue.length; i++) {
        const at = queue[i];
        if (seen.has(at)) continue;
        if (at === target) return true;
        seen.add(at);
        for (const e of edges) if (e.source === at) queue.push(e.target);
      }
      return false;
    };
    if (
      !reaches("protocol-run") ||
      ["protocol-reobserve", "protocol-recompile", "protocol-admit", "protocol-recheck"].some(
        (id) => reaches("protocol-run", [id]),
      )
    )
      failures.push("loss-recovery-bypass");
    const p = v.feedbackPredicates;
    if (
      !p ||
      p.effectAuthority !== false ||
      JSON.stringify(p.from) !== JSON.stringify(["use", "retained"]) ||
      p.via !== "learning" ||
      p.target !== "inquiry"
    )
      failures.push("feedback-predicate-scope");
    if (
      JSON.stringify(p?.sourceRelations) !==
      JSON.stringify([
        "evidence-informs-learning",
        "feedback-revisits-problem",
        "feedback-proposes-intent",
      ])
    )
      failures.push("feedback-predicate-relations");
    const text = (p?.visibleLabels ?? [])
      .map((id) => v.document.labels.find((l) => l.id === id)?.text ?? "")
      .join(" ");
    for (const term of [
      "Reopen inquiry",
      "Use/findings challenge",
      "goals/intent/code/assumptions",
      "No silent authority/history edits",
      "Can invalidate applicability",
    ])
      if (!text.includes(term)) failures.push("feedback-predicate-visible");
    const retention = visible("retention-");
    for (const term of [
      "Explore: knowledge only.",
      "Negative/inconclusive too.",
      "All-drop: keep useful findings.",
    ])
      if (!retention.includes(term)) failures.push("selection-retention-visible");
    if (!visible("benefit-").includes("time window")) failures.push("outcome-time-window-visible");
    if (visible("lane-admission-2-value") !== "Own PASS only; BLOCK / UNKNOWN stop")
      failures.push("action-verdict-visible");
    if (visible("candidate-qualifier") !== "CAS stales bases: refresh/prove/re-admit")
      failures.push("candidate-drift-visible");
    if (
      !["people/Agents", "Interchangeable", "Small contracts:"].every((term) =>
        capabilityCopy.includes(term),
      )
    )
      failures.push("capability-ecosystem-visible");
    const expectedExit = authoredMeaning.has("node:adoption_exit")
      ? "Remove Discharged native install/runtime projections"
      : "Remove Discharged runtime/install projections";
    if (visible("exit-discharge") !== expectedExit) failures.push("exit-discharge-visible");
    // A condition belongs to its operation row, not any nearby runtime text.
    // This also excludes the UNKNOWN subrow from per-removal requirements.
    const runtimeRow = (prefix) =>
      v.document.labels
        .filter((l) => l.id === prefix + "-key" || new RegExp("^" + prefix + "-\\d+$").test(l.id))
        .map((l) => l.text)
        .join(" ")
        .toLowerCase();
    const activation = runtimeRow("runtime-upgrade");
    for (const term of [
      "activation",
      "failure: exact rollback",
      "locked immutable runtime",
      "migrate state",
      "rebind hooks",
      "verify every worktree",
    ])
      if (!activation.includes(term)) failures.push("runtime-activation-visible:" + term);
    for (const [prefix, terms] of [
      [
        "runtime-reclamation",
        [
          "After activation",
          "Each removal",
          "fresh operational dependencies",
          "exact owned directory",
        ],
      ],
      [
        "runtime-reclamation-unknown",
        [
          "UNKNOWN defers deletion",
          "preserves activation/partial results",
          "Historical observations are not executable leases",
        ],
      ],
    ])
      for (const term of terms)
        if (!runtimeRow(prefix).includes(term.toLowerCase()))
          failures.push("runtime-reclamation-visible:" + term);
  }
  if (
    v.resourceRows?.some((r) => r.protocol) ||
    v.document.labels.some(
      (l) => l.id === "protocol-title" && l.text === "Per-resource effect protocol",
    )
  ) {
    const rows = v.resourceRows ?? [],
      contracts = input.semantics.contracts.effect_contracts;
    const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
    if (!equal(rows.map((r) => r.contract).sort(), Object.keys(contracts).sort()))
      failures.push("resource-protocol-set");
    for (const row of rows) {
      const c = contracts[row.contract],
        p = row.protocol,
        g = c && input.semantics.contracts.gates[c.admission_gate];
      if (!p || !c || !g) {
        failures.push("resource-protocol-missing:" + row.contract);
        continue;
      }
      if (
        p.mode !== "resource-local-schematic" ||
        p.effectAuthority !== false ||
        row.sharedPermission !== false ||
        row.resource !== c.repository_boundary
      )
        failures.push("resource-protocol-authority:" + row.contract);
      const admission =
        row.contract === "candidate_integration_effect"
          ? "candidate_integration_evaluation"
          : "effect_evaluation";
      const stages = {
        "protocol-admit": [admission, c.pass_verdict],
        "protocol-state": [c.expected_pre_state],
        "protocol-recheck": [c.fresh_recheck],
        "protocol-run": [c.admitted_runner],
        "protocol-cas": [c.linearization_point],
        "protocol-observe": [c.post_observation],
        "protocol-receipt": [c.effect_attestation],
        "protocol-refusal": g.failure_outputs,
      };
      if (!equal(Object.keys(p.stages).sort(), Object.keys(stages).sort()))
        failures.push("resource-protocol-stages:" + row.contract);
      for (const [view, ids] of Object.entries(stages))
        if (!marks.has(view) || !equal(p.stages[view], ids))
          failures.push("resource-protocol-stage:" + row.contract + ":" + view);
      if (
        p.gate !== c.admission_gate ||
        !equal(p.requiredInputs, g.required_inputs) ||
        p.claimSelector !== g.required_claim_selector
      )
        failures.push("resource-protocol-gate:" + row.contract);
      const expected = [
        [
          "protocol-admit-recheck",
          "protocol-admit",
          "protocol-recheck",
          c.pass_verdict,
          c.fresh_recheck,
          "admits",
        ],
        [
          "protocol-state-recheck",
          "protocol-state",
          "protocol-recheck",
          c.expected_pre_state,
          c.fresh_recheck,
          "binds",
        ],
        [
          "protocol-recheck-run",
          "protocol-recheck",
          "protocol-run",
          c.fresh_recheck,
          c.admitted_runner,
          "admits",
        ],
        [
          "protocol-run-cas",
          "protocol-run",
          "protocol-cas",
          c.admitted_runner,
          c.linearization_point,
          "applies",
        ],
        [
          "protocol-cas-observe",
          "protocol-cas",
          "protocol-observe",
          c.linearization_point,
          c.post_observation,
          "post_observes",
        ],
        [
          "protocol-observe-receipt",
          "protocol-observe",
          "protocol-receipt",
          c.post_observation,
          c.effect_attestation,
          "attests",
        ],
      ];
      if (
        !equal(
          p.relations.map((r) => r.view).sort(),
          [...expected.map((r) => r[0]), "protocol-refusal"].sort(),
        )
      )
        failures.push("resource-protocol-relations:" + row.contract);
      for (const [view, from, to, sourceFrom, sourceTo, kind] of expected) {
        const matches = [...source.values()].filter(
          (r) => r.from === sourceFrom && r.to === sourceTo && r.kind === kind,
        );
        const mapping = p.relations.filter((r) => r.view === view),
          edge = edges.find((e) => e.id === view);
        if (
          matches.length !== 1 ||
          mapping.length !== 1 ||
          !equal(
            mapping[0]?.source,
            matches.map((r) => r.id),
          ) ||
          edge?.source !== from ||
          edge?.target !== to ||
          (view === "protocol-run-cas" && edge?.kind !== "effect")
        )
          failures.push("resource-protocol-relation:" + row.contract + ":" + view);
      }
      const refused = g.failure_outputs.flatMap((to) =>
        [...source.values()]
          .filter((r) => r.from === admission && r.to === to && r.kind === "branches")
          .map((r) => r.id),
      );
      const refusal = p.relations.filter((r) => r.view === "protocol-refusal");
      if (
        refusal.length !== 1 ||
        refused.length !== g.failure_outputs.length ||
        !equal(refusal[0]?.source, refused)
      )
        failures.push("resource-protocol-refusal:" + row.contract);
      const conditions = {
        beforeRun: {
          view: "protocol-refusal",
          sourceVerdicts: g.failure_outputs,
          effectAllowed: false,
        },
        stale: {
          view: "protocol-recheck",
          guard: "effect_time_freshness",
          runnerAllowed: false,
        },
        mismatch: {
          view: "protocol-cas",
          scope: "this-resource-cas-update",
          globalRollback: false,
        },
        uncertain: {
          view: "protocol-observe",
          source: "outcome_unknown",
          replayAllowed: false,
        },
      };
      if (!equal(p.conditions, conditions))
        failures.push("resource-protocol-conditions:" + row.contract);
      const text = p.labels
        .map((id) => v.document.labels.find((l) => l.id === id)?.text ?? "")
        .join(" ");
      for (const term of [
        "Per-resource effect protocol",
        "Each row: own gate/state/runner/CAS/result",
        "no global rollback",
        "All inputs; own PASS",
        "Recheck authority",
        "Single-use runner",
        "CAS",
        "Observe",
        "Attest",
        "BLOCK",
        "UNKNOWN",
        "Stale: no runner",
        "CAS rejects mismatch",
        "Uncertain attempt",
        "Observe before retry",
      ])
        if (!text.includes(term))
          failures.push("resource-protocol-visible:" + row.contract + ":" + term);
      const stateLabel = v.document.labels.find((l) => l.id === "protocol-state-label")?.text;
      if (
        !p.labels.includes("protocol-state-label") ||
        !["Expected state", "Expected prior state"].includes(stateLabel ?? "")
      )
        failures.push("resource-protocol-visible:" + row.contract + ":expected-state");
    }
  }
  if (
    v.repositoryLocalInputs ||
    v.document.labels.some((l) => l.id.startsWith("resource-local-claims-"))
  ) {
    const local = v.repositoryLocalInputs;
    if (!local) failures.push("repository-local-missing");
    else {
      const expected = Object.values(input.semantics.contracts.repository_worlds)
        .map((w) => w.effect_contract_id)
        .sort();
      if (local.sharedAuthority !== false) failures.push("repository-local-authority");
      if (JSON.stringify(local.rows.map((r) => r.contract).sort()) !== JSON.stringify(expected))
        failures.push("repository-local-contract-set");
      for (const row of local.rows) {
        const c = input.semantics.contracts.effect_contracts[row.contract],
          gate = c && input.semantics.contracts.gates[c.admission_gate];
        if (
          !c ||
          row.repository !== c.repository_boundary ||
          row.inputOwner !== c.repository_boundary ||
          row.prestate !== c.expected_pre_state ||
          row.linearization !== c.linearization_point
        )
          failures.push("repository-local-binding:" + row.contract);
        if (
          !gate ||
          row.gate !== c.admission_gate ||
          JSON.stringify(row.requiredInputs) !== JSON.stringify(gate.required_inputs) ||
          row.claimSelector !== gate.required_claim_selector
        )
          failures.push("repository-local-inputs:" + row.contract);
        if (
          input.semantics.nodes.runtime_generation_retirement.attributes.required_consumer_observations.includes(
            "linked_interpreter_bindings",
          )
        ) {
          const j = row.conformance,
            conforms = [...source.values()].filter(
              (r) => r.from === row.repository && r.kind === "conforms",
            );
          const subject = conforms.length === 1 ? conforms[0].to : null;
          const grammar = [...source.values()].filter(
            (r) => r.from === "protocol_grammar" && r.to === subject && r.kind === "narrows",
          );
          if (
            !j ||
            subject !== j.subject ||
            j.grammar !== "protocol_grammar" ||
            grammar.length !== 1 ||
            JSON.stringify([...j.sourceRelations].sort()) !==
              JSON.stringify([...conforms, ...grammar].map((r) => r.id).sort())
          )
            failures.push("conformance-binding:" + row.contract);
          if (j?.effectAuthority !== false) failures.push("conformance-authority:" + row.contract);
        }
      }
      if (local.rows.some((r) => r.conformance)) {
        const visible = v.document.labels
          .filter((l) => l.id.startsWith("resource-conformance-"))
          .map((l) => l.text)
          .join(" ");
        if (
          visible !==
          "Repositories judge imported grammar + fresh local facts; conformance is not permission."
        )
          failures.push("conformance-visible");
      }
      const copy = local.labels
        .map((id) => v.document.labels.find((l) => l.id === id)?.text ?? "")
        .join(" ");
      for (const term of [
        "Root, Greenfield, Brownfield, Peers",
        "own subject",
        "current policy",
        "Commitment",
        "fresh Facts",
        "Plan",
        "candidate",
        "local proof",
        "Local PASS only",
        "All applicable declared proof-plane claims",
        "subject/predicate/scope/bindings/validity/verifier",
      ])
        if (!copy.includes(term)) failures.push("repository-local-visible");
    }
  }
  for (const [id, ids] of Object.entries(v.witnesses.marks)) {
    if (!marks.has(id)) failures.push("missing-mark-witness:" + id);
    if (ids.some((s) => !input.semantics.nodes[s])) failures.push("unknown-mark-source:" + id);
    const boundaries = new Set(
      Object.values(input.semantics.contracts.effect_contracts)
        .filter((c) => ids.includes(c.linearization_point))
        .map((c) => c.repository_boundary),
    );
    if (boundaries.size > 1) failures.push("mixed-effect-boundary:" + id);
  }
  for (const id of Object.keys(v.witnesses.relations))
    if (!edgeIds.has(id)) failures.push("missing-relation-witness:" + id);
  for (const id of marks.keys())
    if (!Object.hasOwn(v.witnesses.marks, id)) failures.push("unbound-mark:" + id);
  for (const c of v.conditionalConsequences)
    if (!edgeIds.has(c.edge)) failures.push("missing-condition-edge:" + c.edge);
  for (const [id, role] of Object.entries(v.routingMarks)) {
    if (!marks.has(id) || role.role !== "routing-only" || v.witnesses.marks[id]?.length)
      failures.push("routing-identity:" + id);
  }
  for (const [id, role] of Object.entries(v.routingEdges)) {
    const edge = edges.find((e) => e.id === id);
    if (!edge || role.role !== "routing-only") failures.push("routing-edge:" + id);
    if (edge?.kind === "effect") failures.push("routing-authority:" + id);
    if (v.witnesses.relations[id]?.length) failures.push("routing-source:" + id);
    if (edge && !v.routingMarks[edge.source] && !v.routingMarks[edge.target])
      failures.push("routing-without-junction:" + id);
  }
  // A declared lane contribution is conjunctive: its own proof and prewrite
  // must both reach its checkpoint. Semantic type equality cannot establish
  // instance identity across lanes, and ordinary reachability behaves like OR.
  const exactRoutingSources = (start) => {
    const queue = [start],
      seen = new Set(),
      result = new Set();
    for (let i = 0; i < queue.length; i++) {
      const id = queue[i];
      if (seen.has(id)) continue;
      seen.add(id);
      if (!v.routingMarks[id]) {
        result.add(id);
        continue;
      }
      for (const edge of edges)
        if (edge.target === id && v.routingEdges[edge.id]) queue.push(edge.source);
    }
    return result;
  };
  const scopedClaims = (v.lanes ?? []).filter(
    (l) => JSON.stringify(v.witnesses.marks[l.proof]) === JSON.stringify(["lane_proof_claim"]),
  );
  if (scopedClaims.length || v.selectedProvenance) {
    const p = v.selectedProvenance;
    if (!p) failures.push("selected-provenance-missing");
    else {
      if (
        p.target !== "combination" ||
        p.appliesOnlyToSelected !== true ||
        p.effectAuthority !== false ||
        JSON.stringify(v.witnesses.marks[p.target]) !== JSON.stringify(["candidate_bundle"])
      )
        failures.push("selected-provenance-scope");
      const selected = v.document.labels
        .filter((l) => p.visibleLabels.includes(l.id))
        .map((l) => l.text)
        .join(" ");
      if (
        !["Selected only", "Base/prewrite", "one selected Lane proof"].every((s) =>
          selected.includes(s),
        )
      )
        failures.push("selected-provenance-visible");
      if (
        JSON.stringify(p.sourceRelations) !==
        JSON.stringify([
          "exact-base-to-candidate",
          "lane-to-candidate-bundle",
          "lane-proof-admits-candidate",
        ])
      )
        failures.push("selected-provenance-relations");
      if (p.lanes.length !== (v.lanes ?? []).length) failures.push("selected-provenance-count");
      for (const lane of v.lanes ?? []) {
        const row = p.lanes.filter((r) => r.work === lane.work);
        if (
          row.length !== 1 ||
          row[0].base !== lane.base ||
          row[0].prewrite !== lane.prewrite ||
          row[0].proof !== lane.proof
        )
          failures.push("selected-provenance-lane:" + lane.work);
        if (JSON.stringify(v.witnesses.marks[lane.proof]) !== JSON.stringify(["lane_proof_claim"]))
          failures.push("contribution-proof-identity:" + lane.proof);
        const proof = edges.filter(
          (e) =>
            e.target === lane.proof &&
            JSON.stringify(v.witnesses.relations[e.id]) ===
              JSON.stringify(["lane-witnesses-proof"]),
        );
        const sources = proof.length === 1 ? exactRoutingSources(proof[0].source) : new Set();
        if (proof.length !== 1 || sources.size !== 1 || !sources.has(lane.work))
          failures.push("contribution-proof:" + lane.proof);
      }
      if (
        p.gate !== "candidate_integration_gate" ||
        p.claimSelector !==
          input.semantics.contracts.gates.candidate_integration_gate.required_claim_selector
      )
        failures.push("selected-proof-selector");
      const detail = v.document.labels
        .filter((l) => l.id.startsWith("resource-candidate_integration_effect-"))
        .map((l) => l.text)
        .join(" ");
      const required = v.capabilityContract
        ? ["one selected Lane proof", "Exact Commitment/base/current Lease/HEAD/proof"]
        : ["one selected Lane proof", "Exact Commitment/base/Lease/HEAD"];
      if (!required.every((term) => (v.capabilityContract ? selected : detail).includes(term)))
        failures.push("selected-proof-visible");
      if (
        !edges.some(
          (e) =>
            e.source === "selection" &&
            e.target === p.target &&
            v.witnesses.relations[e.id]?.includes("selection-binds-combination"),
        )
      )
        failures.push("selected-combination-missing");
    }
  }
  for (const lane of v.lanes ?? [])
    for (const [field, relation] of [
      ["base", "base-binds-lane"],
      ["lease", "lease-coordinates-lane"],
    ]) {
      if (lane[field] === undefined) {
        if (
          Object.values(v.witnesses.marks).some(
            (ids) => ids.length === 1 && ids[0] === (field === "base" ? "exact_base" : "lease"),
          )
        )
          failures.push("lane-" + field + "-identity:" + lane.work);
        continue; // Historical aggregate artifacts retain their explicitly bound identities.
      }
      if (
        JSON.stringify(v.witnesses.marks[lane[field]]) !==
        JSON.stringify([field === "base" ? "exact_base" : "lease"])
      )
        failures.push("lane-" + field + "-identity:" + lane.work);
      const incoming = edges.filter(
        (e) =>
          v.witnesses.relations[e.id]?.includes(relation) &&
          (e.target === lane.work ||
            edges.some(
              (out) =>
                out.source === e.target && out.target === lane.work && v.routingEdges[out.id],
            )),
      );
      if (incoming.length !== 1 || incoming[0].source !== lane[field])
        failures.push("lane-" + field + "-binding:" + lane.work);
    }
  if (v.lanes?.some((l) => l.lease !== undefined)) {
    const r = v.leasePrewrite,
      expected = v.lanes.map((l) => ({
        lease: l.lease,
        prewrite: l.prewrite,
      }));
    if (
      !r ||
      JSON.stringify(r.appliesTo) !== JSON.stringify(expected) ||
      r.sourceRelation !== "lease-binds-prewrite" ||
      r.effectAuthority !== false
    )
      failures.push("lease-prewrite-scope");
    const text = (r?.visibleLabels ?? [])
      .map((id) => v.document.labels.find((l) => l.id === id)?.text ?? "")
      .join(" ");
    if (
      !/Every prewrite/.test(text) ||
      !text.includes("own four-field Lease") ||
      !(v.capabilityContract
        ? text.includes("Base (ref/HEAD/tree) · Lease")
        : text.includes("Base · Lease"))
    )
      failures.push("lease-prewrite-visible");
  }
  const verificationRoles = {
    "verification-subject": ["candidate_state"],
    "verification-independent": ["independent_verifier"],
    "verification-local": ["local_claim"],
    "verification-claim": ["independent_claim"],
  };
  if (Object.keys(verificationRoles).some((id) => marks.has(id))) {
    for (const [id, ids] of Object.entries(verificationRoles))
      if (!marks.has(id) || JSON.stringify(v.witnesses.marks[id]) !== JSON.stringify(ids))
        failures.push("verification-role:" + id);
    for (const [id, from, to, relation] of [
      [
        "verification-execute",
        "verification-subject",
        "verification-independent",
        "candidate-state-to-independent",
      ],
      [
        "verification-return",
        "verification-independent",
        "verification-claim",
        "independent-to-claim",
      ],
      [
        "verification-local-proof",
        "verification-subject",
        "verification-local",
        "candidate-state-witnesses-local",
      ],
    ]) {
      const edge = edges.find((e) => e.id === id);
      if (
        !edge ||
        edge.source !== from ||
        edge.target !== to ||
        JSON.stringify(v.witnesses.relations[id]) !== JSON.stringify([relation])
      )
        failures.push("verification-wire:" + id);
    }
    const copy = v.document.labels
      .filter((l) => l.id.startsWith("verification-"))
      .map((l) => l.text)
      .join(" ");
    const verificationTerms = [
      ...(v.capabilityContract
        ? ["Independent verifier", "Hosted: observe; no permission", "separate trust"]
        : ["Separate trust identity", "never PASS"]),
      ...(authoredMeaning.has("assertion:verification")
        ? ["Action policy:", "disabled", "optional", "required"]
        : [
            v.capabilityContract
              ? "optional unless risk/policy requires"
              : "independent optional unless risk/policy requires",
          ]),
      v.capabilityContract ? "Responsible verifier" : "responsible verifier",
      "claim IDs",
      "No scope gain",
    ];
    for (const term of verificationTerms)
      if (!copy.includes(term)) failures.push("verification-boundary:" + term);
  }
  for (const [id, identities] of Object.entries(v.witnesses.marks)) {
    if (!["work_lane", "lane_proof_claim", "candidate_bundle"].every((s) => identities.includes(s)))
      continue;
    const lanes = (v.lanes ?? []).filter((l) => l.proof === id);
    if (lanes.length !== 1) {
      failures.push("contribution-lane:" + id);
      continue;
    }
    const lane = lanes[0],
      output = edges.filter((e) => e.target === id);
    if (output.length !== 1 || !v.routingEdges[output[0].id] || !v.routingMarks[output[0].source]) {
      failures.push("contribution-conjunction:" + id);
      continue;
    }
    const inputs = edges.filter((e) => e.target === output[0].source);
    const prewrite = inputs.filter((e) =>
      v.witnesses.relations[e.id]?.includes("lane-to-candidate-bundle"),
    );
    if (
      prewrite.length !== 1 ||
      prewrite[0].source !== lane.prewrite ||
      prewrite[0].kind === "effect"
    )
      failures.push("contribution-prewrite:" + id);
    const proof = inputs.filter((e) =>
      ["lane-witnesses-proof", "lane-proof-admits-candidate"].every((s) =>
        v.witnesses.relations[e.id]?.includes(s),
      ),
    );
    const sources = proof.length === 1 ? exactRoutingSources(proof[0].source) : new Set();
    if (
      proof.length !== 1 ||
      sources.size !== 1 ||
      !sources.has(lane.work) ||
      proof[0].kind === "effect"
    )
      failures.push("contribution-proof:" + id);
    if (inputs.length !== 2) failures.push("contribution-conjunction:" + id);
  }
  const endpoint = (start, side) => {
    const result = new Set(),
      queue = [start],
      seen = new Set();
    for (let i = 0; i < queue.length; i++) {
      const id = queue[i];
      if (seen.has(id)) continue;
      seen.add(id);
      if (!v.routingMarks[id]) {
        for (const s of v.witnesses.marks[id] ?? []) result.add(s);
        continue;
      }
      for (const e of edges)
        if (v.routingEdges[e.id]) {
          if (side === "source" && e.target === id) queue.push(e.source);
          if (side === "target" && e.source === id) queue.push(e.target);
        }
    }
    return [...result];
  };
  for (const edge of edges) {
    if (!marks.has(edge.source) || !marks.has(edge.target))
      failures.push("missing-semantic-endpoint:" + edge.id);
    if (
      edge.kind === "object-binding" &&
      !v.document.apertures?.some((a) => a.mark === edge.target && a.objectInput === edge.source)
    )
      failures.push("object-input-not-required:" + edge.id);
    if (v.routingEdges[edge.id]) {
      routing.push({ id: edge.id, role: "routing-only" });
      continue;
    }
    const condition = v.conditionalConsequences.find((c) => c.edge === edge.id);
    if (condition) {
      if (!input.semantics.contracts.effect_contracts[condition.sourceContract])
        failures.push("condition-contract:" + edge.id);
      if (
        !condition.condition.trim() ||
        condition.effectAuthority !== false ||
        v.witnesses.relations[edge.id]?.length
      )
        failures.push("condition-source:" + edge.id);
      conditions.push(condition);
      continue;
    }
    const ids = v.witnesses.relations[edge.id] ?? [],
      relations = ids.map((id) => source.get(id));
    if (!ids.length || relations.some((r) => !r)) {
      failures.push("source-relation:" + edge.id);
      continue;
    }
    if (new Set(ids).size !== ids.length) failures.push("duplicate-source-relation:" + edge.id);
    const effect = relations.some((r) => r.attributes.effect_capable);
    if (effect && edge.kind !== "effect") failures.push("hidden-effect-kind:" + edge.id);
    if (!effect && edge.kind === "effect") failures.push("unsupported-effect-kind:" + edge.id);
    const from = endpoint(edge.source, "source"),
      to = endpoint(edge.target, "target");
    // Both directions are needed: a reachable dead end and an unrelated
    // incoming dependency do not explain this drawn source-to-target arrow.
    const reach = (seeds, reverse = false) => {
      const queue = [...seeds],
        seen = new Set();
      for (let i = 0; i < queue.length; i++) {
        const at = queue[i];
        if (seen.has(at)) continue;
        seen.add(at);
        for (const r of relations)
          if ((reverse ? r.to : r.from) === at) queue.push(reverse ? r.from : r.to);
      }
      return seen;
    };
    const forward = reach(from),
      backward = reach(to, true);
    const connected = relations.some((r) => forward.has(r.from) && to.includes(r.to));
    const onPathSourceRelations = relations
      .filter((r) => forward.has(r.from) && backward.has(r.to))
      .map((r) => r.id);
    const offPathSourceRelations = relations
      .filter((r) => !forward.has(r.from) || !backward.has(r.to))
      .map((r) => r.id);
    for (const id of offPathSourceRelations)
      failures.push("off-path-source-relation:" + edge.id + ":" + id);
    if (!connected) failures.push("semantic-endpoint:" + edge.id);
    paths.push({
      id: edge.id,
      from,
      to,
      sourceRelations: ids,
      onPathSourceRelations,
      offPathSourceRelations,
      guards: [...new Set(relations.map((r) => r.attributes.guard))],
      endpointConnected: connected,
    });
  }
  return {
    scope:
      "Bidirectional source/witness identity, local effect-boundary separation and effect-kind checks plus per-relation membership in the directed endpoint corridor after routing contraction; not full semantic, guard sufficiency, painted visibility or aesthetic acceptance.",
    paths,
    routing,
    conditions,
    failures,
  };
}
