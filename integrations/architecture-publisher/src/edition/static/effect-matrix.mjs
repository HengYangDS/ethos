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
