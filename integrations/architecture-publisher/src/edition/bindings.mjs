import { exactBindingErrors } from "./predicates.mjs";
import { deriveResourceComparison } from "./resource-comparison.mjs";
import { verifyMeaningCarriers } from "./evolution.mjs";
export function checkBindings(spec, bindings, input, sourceDocuments = []) {
  const type = spec.diagram_type;
  if (!["architecture", "sequence"].includes(type) || spec.meta?.quality_profile !== "showcase")
    throw Error("Supported native showcase spec required: architecture or sequence");
  const nodes = type === "sequence" ? spec.participants : spec.components;
  const edges = type === "sequence" ? spec.messages : spec.connections;
  if (bindings.meaning !== undefined) {
    const carriers = {};
    for (const [i, card] of (spec.cards ?? []).entries())
      for (const [j, value] of (card.items ?? []).entries())
        carriers[`cards/${i}/items/${j}`] = value;
    for (const node of nodes ?? [])
      for (const key of ["label", "sublabel", "tag"])
        if (typeof node[key] === "string") carriers[`nodes/${node.id}/${key}`] = node[key];
    verifyMeaningCarriers(input, bindings.meaning, carriers, sourceDocuments);
  }
  if (!Array.isArray(nodes) || !nodes.length || !Array.isArray(edges))
    throw Error("Native typed entities and relations required");
  if (
    bindings.sourceDigest !== input.digest ||
    bindings.sourceRevision !== input.source.git.commit ||
    bindings.effectAuthority !== false
  )
    throw Error("Native bindings source or authority mismatch");
  const ids = new Set(nodes.map((n) => n.id));
  if (ids.size !== nodes.length || nodes.some((n) => typeof n.id !== "string" || !n.id))
    throw Error("Duplicate or absent native node identity");
  const edgeIds = new Set();
  for (const n of nodes) {
    if (!bindings.nodes[n.id]?.length) throw Error("Unbound native node " + n.id);
    for (const id of bindings.nodes[n.id])
      if (!Object.hasOwn(input.semantics.nodes, id)) throw Error("Unknown semantic node " + id);
  }
  for (const edge of edges) {
    if (
      typeof edge.id !== "string" ||
      !edge.id ||
      edgeIds.has(edge.id) ||
      !ids.has(edge.from) ||
      !ids.has(edge.to)
    )
      throw Error("Invalid native connection " + edge.id);
    edgeIds.add(edge.id);
    if (!bindings.connections[edge.id]?.length) throw Error("Unbound native connection " + edge.id);
    for (const id of bindings.connections[edge.id])
      if (!Object.hasOwn(input.documents.copy.assertions, id))
        throw Error("Unknown assertion " + id);
  }
  for (const id of Object.keys(bindings.nodes))
    if (!ids.has(id)) throw Error("Unused native node binding " + id);
  for (const id of Object.keys(bindings.connections))
    if (!edgeIds.has(id)) throw Error("Unused native edge binding " + id);
  for (const predicate of bindings.predicates ?? []) {
    const errors = exactBindingErrors(predicate, spec, bindings, input);
    if (errors.length)
      throw Error("Invalid exact binding " + predicate.id + ": " + errors.join(", "));
  }
  const visibleNodeIds = new Set(Object.values(bindings.nodes).flat());
  const claimedRelations = new Set([
    ...Object.values(bindings.relations ?? {}).flatMap((r) => r.sourceRelations ?? []),
    ...(bindings.selfConformance?.sourceRelations ?? []),
  ]);
  for (const relation of input.semantics.relations.filter(
    (r) =>
      r.kind === "conforms" &&
      claimedRelations.has(r.id) &&
      input.semantics.nodes[r.from]?.kind === "repository" &&
      input.semantics.nodes[r.to]?.kind === "conformance" &&
      visibleNodeIds.has(r.from),
  )) {
    if (
      !visibleNodeIds.has(relation.to) &&
      !bindings.repositoryJudgments?.some(
        (r) => r.repository === relation.from && r.conformance === relation.to,
      )
    )
      throw Error("Missing separate repository judgment carrier");
  }
  if (bindings.repositoryJudgments !== undefined) {
    if (!Array.isArray(bindings.repositoryJudgments) || !bindings.repositoryJudgments.length)
      throw Error("Explicit repository judgment carriers required");
    const compared = deriveResourceComparison(input),
      seen = new Set();
    for (const row of bindings.repositoryJudgments) {
      const local = compared.find(
        (r) => r.resource === row.repository && r.conformance?.id === row.conformance,
      );
      if (
        !local ||
        row.carrier !== "resource-comparison" ||
        row.effectAuthority !== false ||
        seen.has(row.conformance) ||
        local.conformance.sourceRelation !== row.sourceRelation ||
        !bindings.nodes[row.node]?.includes(row.repository) ||
        Object.values(bindings.nodes).some((ids) => ids.includes(row.conformance))
      )
        throw Error("Invalid separate repository judgment carrier");
      seen.add(row.conformance);
    }
    for (const ids of Object.values(bindings.nodes))
      for (const id of ids) {
        const local = compared.find((r) => r.resource === id && r.conformance);
        if (local && !seen.has(local.conformance.id))
          throw Error("Missing separate repository judgment carrier");
      }
  }
  const boundaries = spec.boundaries ?? [],
    scopes = bindings.scopes ?? [];
  if (scopes.length !== boundaries.length)
    throw Error("Native boundary scope set is not fully bound");
  const semanticRelations = new Set(input.semantics.relations.map((e) => e.id));
  for (const [index, boundary] of boundaries.entries()) {
    const matches = scopes.filter((s) => s.boundaryIndex === index);
    if (matches.length !== 1) throw Error("Native boundary scope identity mismatch");
    const scope = matches[0];
    if (
      scope.label !== boundary.label ||
      scope.effectAuthority !== false ||
      JSON.stringify([...scope.appliesTo].sort()) !== JSON.stringify([...boundary.wraps].sort())
    )
      throw Error("Native boundary scope meaning or membership mismatch");
    if (
      !scope.explanation?.trim() ||
      !scope.semanticNodes?.length ||
      !scope.sourceRelations?.length
    )
      throw Error("Native boundary scope lacks source witnesses");
    for (const id of scope.semanticNodes)
      if (!Object.hasOwn(input.semantics.nodes, id))
        throw Error("Unknown scope semantic node " + id);
    for (const id of scope.sourceRelations)
      if (!semanticRelations.has(id)) throw Error("Unknown scope source relation " + id);
  }
  return type;
}
