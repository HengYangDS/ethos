import { createHash } from "node:crypto";
import { readSourceBundle } from "architecture-publisher/source";
import { fail, isDigest, portablePath } from "architecture-publisher/source";

export const SOURCE_PATHS = Object.freeze({
  license: "LICENSE",
  declaration: "system/projections/terminal-architecture/declaration.json",
  exporter: "tools/projection/export_terminal_architecture.py",
  owner: "src/ethos/repository/policy/projections.py",
});
export const sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");
export function stableStringify(value) {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return "[" + value.map(stableStringify).join(",") + "]";
  return (
    "{" +
    Object.keys(value)
      .sort()
      .map((k) => JSON.stringify(k) + ":" + stableStringify(value[k]))
      .join(",") +
    "}"
  );
}
const object = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const text = (value) => typeof value === "string" && Boolean(value.trim());
const same = (a, b) => stableStringify(a) === stableStringify(b);
const oid = (value) => typeof value === "string" && /^(?:[a-f0-9]{40}|[a-f0-9]{64})$/.test(value);
function parse(bytes) {
  try {
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  } catch {
    fail("projection_json_invalid");
  }
}

/** Protocol integrity only. Values and all qualifiers remain owned by the source. */
export function validateProjectionEnvelope(value, expectedDigest) {
  if (!isDigest(expectedDigest)) fail("projection_digest_required");
  if (!object(value) || value.schema !== "projection.input/v2")
    fail("projection_schema_unsupported");
  const { digest, ...body } = value;
  if (digest !== expectedDigest || sha256(stableStringify(body) + "\n") !== digest)
    fail("projection_digest_mismatch");
  if (
    !object(value.authority) ||
    value.authority.effect_authority !== false ||
    !text(value.authority.semantic_owner) ||
    !text(value.authority.scope)
  )
    fail("projection_authority_invalid");
  const source = value.source;
  if (
    !object(source) ||
    !text(source.id) ||
    !object(source.git) ||
    !oid(source.git.commit) ||
    !oid(source.git.tree) ||
    source.revision !== source.git.commit
  )
    fail("projection_source_invalid");
  for (const collection of ["bindings", "documents"]) {
    const rows = source[collection];
    if (!Array.isArray(rows) || !rows.length) fail("projection_bindings_invalid");
    const ids = new Set(),
      paths = new Set();
    for (const row of rows) {
      if (!object(row) || !text(row.id) || !isDigest(row.sha256))
        fail("projection_bindings_invalid");
      portablePath(row.path);
      if (ids.has(row.id) || paths.has(row.path)) fail("projection_binding_duplicate");
      ids.add(row.id);
      paths.add(row.path);
    }
  }
  const required = ["copy", "quality_contract", "semantic_graph", "view_profile"];
  if (!same(source.documents.map((d) => d.id).sort(), required))
    fail("projection_documents_invalid");
  if (
    !object(value.documents) ||
    !object(value.semantics) ||
    !object(value.view) ||
    !object(value.semantics.nodes) ||
    !Array.isArray(value.semantics.relations) ||
    !object(value.semantics.contracts)
  )
    fail("projection_structure_invalid");
  const known = new Set(source.bindings.map((b) => b.id));
  const provenance = (values) => {
    if (!Array.isArray(values) || !values.length || values.some((x) => !known.has(x)))
      fail("projection_provenance_invalid");
  };
  for (const node of Object.values(value.semantics.nodes)) {
    if (!object(node) || !text(node.label) || !text(node.kind) || !object(node.attributes))
      fail("projection_node_invalid");
    provenance(node.provenance);
  }
  const relations = new Set();
  for (const relation of value.semantics.relations) {
    if (
      !object(relation) ||
      !text(relation.id) ||
      relations.has(relation.id) ||
      !text(relation.kind) ||
      !object(relation.attributes) ||
      !Object.hasOwn(value.semantics.nodes, relation.from) ||
      !Object.hasOwn(value.semantics.nodes, relation.to)
    )
      fail("projection_relation_invalid");
    relations.add(relation.id);
    provenance(relation.provenance);
  }
  for (const [kind, ids] of [
    ["nodes", Object.keys(value.semantics.nodes)],
    ["relations", [...relations]],
  ]) {
    const views = value.view[kind];
    if (!object(views) || !same(Object.keys(views).sort(), ids.sort()))
      fail("projection_view_invalid");
    for (const view of Object.values(views)) {
      if (
        !object(view) ||
        Number(Object.hasOwn(view, "project")) + Number(view.omit === true) !== 1 ||
        (view.omit === true && !text(view.reason)) ||
        (Object.hasOwn(view, "project") && !object(view.project))
      )
        fail("projection_view_invalid");
      if (Object.hasOwn(view, "project"))
        for (const field of [
          "id",
          "label",
          "kind",
          "from",
          "to",
          "provenance",
          "attributes",
          "authority",
          "contracts",
        ])
          if (Object.hasOwn(view.project, field)) fail("projection_view_semantic_override");
    }
  }
  return value;
}

export function validateEthosMembers(bundle, expectedDigest) {
  const map = new Map(bundle.members.map((m) => [m.path, m.content]));
  const needed = new Set([
    "projection-input.json",
    ...Object.values(SOURCE_PATHS).map((p) => "source/" + p),
  ]);
  const bytes = (name) => {
    const b = map.get(name);
    if (!b) fail("projection_member_missing");
    return b;
  };
  const projection = validateProjectionEnvelope(
    parse(bytes("projection-input.json")),
    expectedDigest,
  );
  if (
    bundle.source.id !== projection.source.id ||
    bundle.source.revision !== projection.source.revision
  )
    fail("projection_source_invalid");
  const sourceDocuments = [];
  for (const row of [...projection.source.bindings, ...projection.source.documents]) {
    const member = "source/" + row.path;
    needed.add(member);
    const content = bytes(member);
    if (sha256(content) !== row.sha256) fail("projection_binding_mismatch");
    sourceDocuments.push({ ...row, content });
  }
  const declaration = parse(bytes("source/" + SOURCE_PATHS.declaration));
  const paths = Object.fromEntries(projection.source.documents.map((d) => [d.id, d.path]));
  if (
    declaration.schema !== "ethos.projection-declaration/v1" ||
    declaration.id !== projection.source.id ||
    declaration.title !== projection.title ||
    !same(declaration.documents, paths)
  )
    fail("projection_declaration_mismatch");
  if (
    !object(declaration.authority) ||
    declaration.authority.semantic_owner !== projection.authority.semantic_owner ||
    declaration.authority.scope !== projection.authority.scope ||
    declaration.authority.effect_authority !== false
  )
    fail("projection_declaration_mismatch");
  if (!Array.isArray(declaration.sources)) fail("projection_declaration_mismatch");
  const selected = declaration.sources
    .map(({ id, path, authority }) => ({ id, path, authority }))
    .sort((a, b) => a.id.localeCompare(b.id));
  const bound = projection.source.bindings
    .map(({ id, path, authority }) => ({ id, path, authority }))
    .sort((a, b) => a.id.localeCompare(b.id));
  if (!same(selected, bound)) fail("projection_declaration_mismatch");
  for (const id of ["copy", "view_profile"])
    if (!same(parse(bytes("source/" + paths[id])), projection.documents[id]))
      fail("projection_document_mismatch");
  if (
    bytes("source/" + paths.quality_contract).toString("utf8") !==
    projection.documents.quality_contract
  )
    fail("projection_document_mismatch");
  for (const required of needed) bytes(required);
  if (!same([...map.keys()].sort(), [...needed].sort())) fail("projection_members_mismatch");
  return {
    projection,
    sourceDocuments,
    manifestSha256: bundle.manifestSha256,
    scope: "source-binding-integrity",
    officialReplay: "not-performed",
    semanticAcceptance: "not-performed",
  };
}

export async function readEthosSource(manifestPath, manifestSha256, projectionDigest) {
  if (!isDigest(projectionDigest)) fail("projection_digest_required");
  return validateEthosMembers(
    await readSourceBundle(manifestPath, manifestSha256),
    projectionDigest,
  );
}
