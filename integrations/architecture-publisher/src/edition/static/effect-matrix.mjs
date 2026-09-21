// Presentation names and order only. Required contracts and their meaning come
// from the source. An unrecognized contract fails rather than disappearing.
const display = {
  candidate_integration_effect: {
    title: "Candidate integration",
    context: "One selected, proved work lane",
  },
  ethos_effect: {
    title: "Accepted-root closeout",
    context: "ETHOS self-governance",
  },
  greenfield_effect: {
    title: "Greenfield formation",
    context: "Founding state and scaffold",
  },
  brownfield_effect: {
    title: "Brownfield adoption",
    context: "Inherited history and owners",
  },
  adopter_peer_effect: {
    title: "Autonomous peer",
    context: "Independent repository judgment",
  },
  publication_effect: {
    title: "Publication target",
    context: "Selected remote ref; not an adopter",
  },
};
const boundaryFields = [
  "expected_pre_state",
  "fresh_recheck",
  "admitted_runner",
  "linearization_point",
  "post_observation",
  "effect_attestation",
];

/** A bounded structural reader, not a substitute for exact exporter verification
 * or source-to-view semantic acceptance. Never derives authority from evidence. */
export function deriveEffectRows(input) {
  if (input?.schema !== "projection.input/v2") throw Error("official v2 projection required");
  const { nodes, relations, contracts } = input.semantics ?? {};
  if (!nodes || !Array.isArray(relations) || !contracts?.effect_contracts)
    throw Error("missing effect contracts");
  const ids = Object.keys(contracts.effect_contracts);
  if (ids.some((id) => !display[id])) throw Error("unmapped effect contract");
  if (Object.keys(display).some((id) => !ids.includes(id))) throw Error("missing effect contract");
  const relationIds = new Set();
  for (const r of relations) {
    if (relationIds.has(r.id)) throw Error("duplicate protocol relation");
    relationIds.add(r.id);
  }
  const rows = [];
  for (const id of Object.keys(display)) {
    const c = contracts.effect_contracts[id];
    for (const field of boundaryFields) {
      const n = nodes[c[field]];
      if (!n || n.attributes?.reality_boundary !== c.repository_boundary)
        throw Error(`boundary mismatch: ${id}.${field}`);
    }
    if (
      nodes[c.admitted_runner].kind !== "execution" ||
      nodes[c.linearization_point].kind !== "effect_aperture" ||
      nodes[c.effect_attestation].kind !== "durable_root"
    )
      throw Error("boundary role mismatch");
    const gate = contracts.gates?.[c.admission_gate];
    if (!gate || gate.mode !== "all") throw Error("conjunctive gate required");
    if (gate.output !== c.pass_verdict || nodes[c.pass_verdict]?.attributes?.verdict !== "pass")
      throw Error("gate PASS binding mismatch");
    if (
      !Array.isArray(gate.required_inputs) ||
      !gate.required_inputs.length ||
      gate.required_inputs.some((n) => !nodes[n])
    )
      throw Error("unknown required input");
    if (!gate.required_claim_selector?.trim()) throw Error("missing scoped claim selector");
    const verdicts = gate.failure_outputs?.map((n) => nodes[n]?.attributes?.verdict);
    if (!verdicts?.includes("block") || !verdicts.includes("unknown"))
      throw Error("missing gate failure outputs");
    const ingresses = relations.filter(
      (r) => r.to === c.linearization_point && r.attributes?.effect_capable === true,
    );
    if (
      ingresses.length !== 1 ||
      ingresses[0].from !== c.admitted_runner ||
      ingresses[0].attributes.effect_contract_id !== id
    )
      throw Error("closed effect ingress violated");
    const ingress = ingresses[0];
    if (ingress.kind !== "applies" || ingress.attributes.guard !== "effect_pass_and_fresh_recheck")
      throw Error("effect guard mismatch");
    const pairs = [
      [c.pass_verdict, c.fresh_recheck, "admits"],
      [c.expected_pre_state, c.fresh_recheck, "binds"],
      [c.fresh_recheck, c.admitted_runner, "admits"],
      [c.linearization_point, c.post_observation, "post_observes"],
      [c.post_observation, c.effect_attestation, "attests"],
    ];
    const protocolRelations = pairs.map(([from, to, kind]) => {
      const found = relations.filter((r) => r.from === from && r.to === to && r.kind === kind);
      if (found.length !== 1)
        throw Error(`missing or ambiguous protocol relation: ${from} -> ${to}`);
      if (from === c.fresh_recheck && found[0].attributes.guard !== "effect_time_freshness")
        throw Error("recheck guard mismatch");
      return found[0];
    });
    const worlds = Object.values(contracts.repository_worlds ?? {}).filter(
      (w) => w.effect_contract_id === id,
    );
    if (worlds.length > 1) throw Error("ambiguous repository boundary classification");
    const world = worlds[0] ?? null;
    if (
      world &&
      (world.repository_node !== c.repository_boundary ||
        world.authority_local !== true ||
        world.conforms_to_kernel !== true)
    )
      throw Error("repository boundary classification mismatch");
    const target =
      contracts.publication_target?.effect_contract_id === id ? contracts.publication_target : null;
    if (
      target &&
      (world ||
        target.target_node !== c.repository_boundary ||
        target.authority_local !== false ||
        target.conforms_to_kernel !== false)
    )
      throw Error("publication boundary is not an adopter");
    if (id === "publication_effect" && !target)
      throw Error("missing publication boundary classification");
    if (id !== "publication_effect" && id !== "candidate_integration_effect" && !world)
      throw Error("missing repository boundary classification");
    rows.push(
      structuredClone({
        id,
        contract: c,
        gate,
        ingress,
        repositoryWorld: world,
        targetClassification: target,
        protocolRelations,
      }),
    );
  }
  return rows;
}

function composeEffectMatrix(rows, binding, notice) {
  if (
    rows.length !== Object.keys(display).length ||
    new Set(rows.map((r) => r.id)).size !== rows.length ||
    rows.some((r) => !display[r.id])
  )
    throw Error("complete distinct row set required");
  const document = {
    title: "Independent effect boundaries",
    subtitle: "Component study: shared protocol, separate state and authority.",
    brand: "ETHOS · 问道",
    binding,
    labels: [],
    marks: [],
    relations: [],
    rules: [],
    required: [],
  };
  const witnesses = [];
  const text = (id, value, x, y, size = 14, weight = "400") =>
    document.labels.push({
      id,
      text: value,
      x,
      y,
      size,
      weight,
      tone: weight === "400" ? "muted" : "ink",
      semantics: [],
    });
  text("brand", "ETHOS · 问道", 48, 35, 18, "600");
  text("title", "Independent effect boundaries", 48, 92, 38, "serif");
  text("maturity", notice, 1110, 35, 12.5);
  text("scope", "Component study — not the complete product architecture.", 48, 124, 15);
  text(
    "rule",
    "One grammar. Six separate bindings. A shared column never means shared permission.",
    48,
    172,
    17,
    "600",
  );
  text(
    "gate-rule",
    "Admission is conjunctive over each row’s declared inputs and exact claim selector.",
    48,
    201,
    14,
  );
  text(
    "state-rule",
    "Expected state enters fresh recheck; only the admitted runner can apply that row’s CAS.",
    48,
    224,
    14,
  );
  const columns = [
    ["evaluate", "Admit", 390],
    ["pass", "PASS", 525],
    ["recheck", "Recheck", 700],
    ["runner", "Run once", 875],
    ["cas", "Local CAS", 1050],
    ["post", "Observe", 1225],
    ["receipt", "Attestation", 1410],
  ];
  for (const [id, label, x] of columns) text("column-" + id, label, x - 32, 255, 14, "600");
  rows.forEach((row, index) => {
    const y = 315 + index * 73,
      prefix = row.id + "--",
      c = row.contract;
    const names = display[row.id];
    text(prefix + "name", names.title, 48, y + 2, 17, "600");
    text(prefix + "context", names.context, 48, y + 24, 12.5);
    const mapping = {
      evaluate: c.admission_gate,
      pass: c.pass_verdict,
      recheck: c.fresh_recheck,
      runner: c.admitted_runner,
      cas: c.linearization_point,
      post: c.post_observation,
      receipt: c.effect_attestation,
      pre: c.expected_pre_state,
    };
    for (const [id, , x] of columns) {
      const kind =
        id === "evaluate" || id === "cas" ? "gate" : id === "receipt" ? "evidence" : "state";
      const r = id === "evaluate" || id === "cas" ? 8 : id === "receipt" ? 9 : 4;
      document.marks.push({
        id: prefix + id,
        kind,
        x,
        y,
        r,
        tone: id === "receipt" ? "proof" : "line",
      });
      witnesses.push({
        contractId: row.id,
        viewId: prefix + id,
        sourceId: mapping[id],
      });
    }
    document.marks.push({
      id: prefix + "pre",
      kind: "state",
      x: 700,
      y: y - 34,
      r: 4,
      tone: "line",
    });
    witnesses.push({
      contractId: row.id,
      viewId: prefix + "pre",
      sourceId: c.expected_pre_state,
    });
    text(prefix + "expected", "Expected state", 728, y - 29, 12.5);
    const mark = (id) => document.marks.find((m) => m.id === prefix + id);
    const connect = (from, to, kind) => {
      const a = mark(from),
        b = mark(to),
        vertical = a.x === b.x;
      document.relations.push({
        id: prefix + from + "-" + to,
        source: a.id,
        target: b.id,
        kind,
        arrow: true,
        points: vertical
          ? [
              { x: a.x, y: a.y + a.r },
              { x: b.x, y: b.y - b.r },
            ]
          : [
              { x: a.x + a.r, y: a.y },
              { x: b.x - b.r, y: b.y },
            ],
      });
    };
    connect("evaluate", "pass", "admission");
    connect("pass", "recheck", "admission");
    connect("pre", "recheck", "state-binding");
    connect("recheck", "runner", "admission");
    connect("runner", "cas", "effect");
    connect("cas", "post", "observation");
    connect("post", "receipt", "retain");
  });
  text(
    "blocked",
    "BLOCK / UNKNOWN admit no new effect. An uncertain past attempt must be re-observed, never blindly replayed.",
    48,
    745,
    14,
  );
  text(
    "scope-limit",
    "Each row retains its own pre-state, scope, verifier and receipt. No global CAS; evidence is not permission.",
    48,
    774,
    14,
  );
  text(
    "publication",
    "Publication target: a selected full remote ref, not an adopter. No autonomous repository authority is implied.",
    48,
    803,
    14,
  );
  text(
    "selector",
    "Candidate: exact Lane claim. Root: declared proof-plane claims. Publication: full ref, request digest, common-dir and signature trust.",
    48,
    832,
    13,
  );
  text(
    "claim-limit",
    "Source-bound structural diagram; not implemented-capability evidence, full semantic verification, or visual acceptance.",
    48,
    871,
    12.5,
  );
  return {
    status: "COMPONENT_STUDY",
    semanticAcceptance: "UNVERIFIED",
    document,
    witnesses,
  };
}
