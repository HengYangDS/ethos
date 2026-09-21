/** Field-level source binding shared by delivery and review. Reference integrity
 * does not prove that a reader understands the relation or its full guard. */
export function exactBindingErrors(predicate, spec, bindings, input) {
  if (predicate.mode !== "exact-binding") return [];
  const errors = [],
    nodes = new Map((spec.components ?? []).map((n) => [n.id, n]));
  const field = predicate.visibleField ?? predicate.field,
    target = nodes.get(predicate.node);
  if (
    !["label", "sublabel", "tag"].includes(field) ||
    typeof predicate.expression !== "string" ||
    target?.[field] !== predicate.expression
  )
    errors.push("exact-binding-field");
  if (!nodes.has(predicate.subject) || predicate.effectAuthority !== false)
    errors.push("exact-binding-subject");
  if (!Array.isArray(predicate.sourceRelations) || !predicate.sourceRelations.length)
    errors.push("exact-binding-source");
  else
    for (const id of predicate.sourceRelations) {
      const relation = input.semantics.relations.find((r) => r.id === id);
      if (
        !relation ||
        !bindings.nodes[predicate.subject]?.includes(relation.from) ||
        !bindings.nodes[predicate.node]?.includes(relation.to) ||
        relation.attributes.effect_capable
      )
        errors.push("exact-binding-endpoints");
    }
  return [...new Set(errors)];
}
