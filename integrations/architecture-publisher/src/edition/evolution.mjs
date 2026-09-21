import { sha256, stableStringify, validateProjectionEnvelope } from "../adapter/projection.mjs";
import { ethosClaimModel } from "../adapter/semantics.mjs";
import { claimModelDigest, exact, record, text } from "architecture-publisher/semantics";
import { compileEditionEvolution } from "architecture-publisher/edition";
import { isDigest } from "architecture-publisher/source";

const map = (rows) => Object.fromEntries(rows.map((row) => [row.id, row]));
const sorted = (values) => [...new Set(values)].sort();
const projectDelta = (change) => ({
  nodes: change.entities,
  relations: change.relations,
  assertions: change.claims,
  documents: [
    ...change.sources.filter((id) => id !== "document:copy"),
    ...change.context.filter((id) => id.startsWith("documents:")).map((id) => id.slice(10)),
  ].sort(),
  contracts: change.context.filter((id) => id.startsWith("contracts:")).map((id) => id.slice(10)),
  presentation: change.context
    .filter((id) => id.startsWith("presentation:"))
    .map((id) => id.slice(13)),
});

function completeDependencies(value, model, name) {
  const nodes = new Set(value.nodes),
    relations = new Set(value.relations),
    claims = new Set(value.claims);
  for (const id of relations) {
    const relation = model.relations[id];
    if (!relation) throw Error("Unknown ETHOS scene relation: " + id);
    nodes.add(relation.subject);
    nodes.add(relation.object);
  }
  for (const id of claims) {
    const claim = model.claims[id];
    if (!claim) throw Error("Unknown ETHOS scene claim: " + id);
    nodes.add(claim.subject);
    if (claim.object !== null) nodes.add(claim.object);
    for (const reference of claim.dependsOn)
      if (reference.section === "relations") {
        relations.add(reference.id);
        nodes.add(model.relations[reference.id].subject);
        nodes.add(model.relations[reference.id].object);
      }
  }
  for (const id of nodes)
    if (!Object.hasOwn(model.entities, id)) throw Error("Unknown ETHOS scene entity: " + id);
  return {
    label: value.label,
    nodes: sorted(nodes),
    relations: sorted(relations),
    claims: sorted(claims),
    ...(value.authoredInputSha256 ? { authoredInputSha256: value.authoredInputSha256 } : {}),
  };
}

function pageDependencies(page, model) {
  const nodes = new Set(Object.values(page.bindings.nodes ?? {}).flat()),
    relations = new Set(),
    claims = new Set(Object.values(page.bindings.connections ?? {}).flat()),
    collect = (value) => {
      if (Array.isArray(value)) {
        for (const item of value) collect(item);
        return;
      }
      if (!record(value)) return;
      for (const [key, nested] of Object.entries(value)) {
        if (
          ["sourceRelations", "sourceAssertions", "assertions", "semanticNodes"].includes(key) &&
          Array.isArray(nested)
        ) {
          const target =
            key === "sourceRelations" ? relations : key === "semanticNodes" ? nodes : claims;
          for (const id of nested) if (typeof id === "string") target.add(id);
        } else collect(nested);
      }
    };
  collect(page.bindings);
  for (const meaning of page.bindings.meaning ?? []) {
    if (meaning.kind === "node") nodes.add(meaning.id);
    else if (meaning.kind === "relation") relations.add(meaning.id);
    else if (meaning.kind === "assertion") claims.add(meaning.id);
  }
  return completeDependencies(
    { label: page.label, nodes: [...nodes], relations: [...relations], claims: [...claims] },
    model,
    page.id,
  );
}

/** Derive Edition dependencies from validated ETHOS publication inputs. */
export function selectEthosEditionDependencies(projection, pages, staticAuthoring = {}) {
  validateProjectionEnvelope(projection, projection?.digest);
  if (
    !Array.isArray(pages) ||
    !pages.length ||
    new Set(pages.map((page) => page?.id)).size !== pages.length ||
    pages.some(
      (page) =>
        !record(page) ||
        !text(page.id) ||
        !text(page.label) ||
        !record(page.spec) ||
        !record(page.bindings),
    )
  )
    throw Error("Complete ETHOS Edition pages required");
  let quality;
  try {
    quality = JSON.parse(projection.documents.quality_contract);
  } catch {
    throw Error("ETHOS quality contract JSON required");
  }
  const requiredClaims =
    quality?.hard_gates?.semantic?.required_static_assertion_ids ??
    Object.keys(projection.documents.copy.assertions);
  if (
    !Array.isArray(requiredClaims) ||
    !requiredClaims.length ||
    new Set(requiredClaims).size !== requiredClaims.length
  )
    throw Error("ETHOS static claim selection required");
  const model = ethosClaimModel(projection),
    projected = completeDependencies(
      {
        label: "Complete ETHOS overview",
        nodes: Object.entries(projection.view.nodes)
          .filter(([, value]) => record(value?.project))
          .map(([id]) => id),
        relations: Object.entries(projection.view.relations)
          .filter(([, value]) => record(value?.project))
          .map(([id]) => id),
        claims: [],
      },
      model,
      "static",
    ),
    overview = pages.find((page) => page.id === "overview");
  if (!overview) throw Error("ETHOS overview page required");
  const selectedPages = pages.map((page) => {
    const selected = pageDependencies(page, model);
    return {
      id: page.id,
      label: page.label,
      authoredInputSha256: sha256(stableStringify(page.spec)),
      ...(page.id === "overview"
        ? {
            nodes: projected.nodes,
            relations: projected.relations,
            claims: [...requiredClaims],
          }
        : selected),
    };
  });
  return {
    static: {
      label: "Complete ETHOS overview",
      nodes: projected.nodes,
      relations: projected.relations,
      claims: [...requiredClaims],
      authoredInputSha256: sha256(stableStringify(staticAuthoring)),
    },
    pages: selectedPages,
    narrative: pages.map((page) => page.id),
  };
}

function dependencies(value, model, name) {
  const allowed = ["id", "label", "nodes", "relations", "claims", "authoredInputSha256"];
  if (
    !record(value) ||
    !["label", "nodes", "relations", "claims"].every((key) => Object.hasOwn(value, key)) ||
    Object.keys(value).some((key) => !allowed.includes(key)) ||
    !text(value.label) ||
    !Array.isArray(value.nodes) ||
    !Array.isArray(value.relations) ||
    !Array.isArray(value.claims) ||
    (Object.hasOwn(value, "authoredInputSha256") && !isDigest(value.authoredInputSha256))
  )
    throw Error("Explicit ETHOS scene dependencies required: " + name);
  return completeDependencies(value, model, name);
}

function sceneGroups(value, model) {
  const byType = new Map();
  for (const id of value.nodes) {
    const type = model.entities[id].type;
    if (!byType.has(type)) byType.set(type, []);
    byType.get(type).push(id);
  }
  const groups = [];
  for (const [type, ids] of [...byType].sort(([left], [right]) =>
    left < right ? -1 : left > right ? 1 : 0,
  )) {
    const count = Math.ceil(ids.length / 8),
      label = type.replaceAll("_", " ").replaceAll("-", " ");
    for (let offset = 0; offset < ids.length; offset += 8) {
      const part = offset / 8 + 1;
      groups.push({
        id: `semantic-scope-${groups.length + 1}`,
        label: count === 1 ? label : `${label} ${part}/${count}`,
        entities: ids.slice(offset, offset + 8),
      });
    }
  }
  return groups;
}

const scene = (value, model) => ({
  label: value.label,
  questions: [value.id],
  claims: [...value.claims],
  ...(value.authoredInputSha256 ? { authoredInputSha256: value.authoredInputSha256 } : {}),
  composition: {
    groups: sceneGroups(value, model),
    relations: value.relations.map((id) => ({
      id,
      fromSide: "right",
      toSide: "left",
      route: "straight",
    })),
  },
});

/** Adapt explicit ETHOS publication dependencies into the public Edition contract. */
function createEthosEvolutionEdition(projection, sourceManifestSha256, selection) {
  validateProjectionEnvelope(projection, projection?.digest);
  if (
    !isDigest(sourceManifestSha256) ||
    !record(selection) ||
    !exact(selection, ["static", "pages", "narrative"]) ||
    !Array.isArray(selection.pages) ||
    !selection.pages.length ||
    !Array.isArray(selection.narrative) ||
    selection.narrative.length !== selection.pages.length ||
    new Set(selection.narrative).size !== selection.narrative.length
  )
    throw Error("Explicit ETHOS Edition selection required");
  const model = ethosClaimModel(projection),
    ids = new Set(),
    pages = new Map();
  for (const value of selection.pages) {
    const fields = ["id", "label", "nodes", "relations", "claims", "authoredInputSha256"];
    if (
      !record(value) ||
      !["id", "label", "nodes", "relations", "claims"].every((field) =>
        Object.hasOwn(value, field),
      ) ||
      Object.keys(value).some((field) => !fields.includes(field)) ||
      !text(value.id) ||
      ids.has(value.id)
    )
      throw Error("Distinct ETHOS Edition page identities required");
    ids.add(value.id);
    pages.set(value.id, dependencies(value, model, value.id));
  }
  if (selection.narrative.some((id) => !pages.has(id)) || selection.narrative[0] !== "overview")
    throw Error("Complete ETHOS Edition narrative required");
  const staticSelection = dependencies(selection.static, model, "static"),
    requiredClaims = [...staticSelection.claims],
    overview = pages.get("overview");
  const edition = {
    schema: "architecture.edition/v1",
    id: "ethos-architecture",
    owner: model.owner,
    class: "flagship",
    product: {
      name: "Architecture Publisher",
      schema: "architecture.publisher/v1",
      version: "0.2.0-alpha.0",
    },
    source: { manifestSha256: sourceManifestSha256 },
    claimModel: {
      schema: "architecture.claim-model/v2",
      digest: claimModelDigest(model),
    },
    title: projection.title,
    audiences: { steward: { label: "Repository stewards" } },
    questions: Object.fromEntries(
      selection.narrative.map((id) => {
        const page = pages.get(id),
          claims = page.claims;
        if (!claims.length) throw Error("ETHOS Edition page requires semantic claims: " + id);
        return [
          id,
          {
            audience: "steward",
            prompt:
              id === "overview"
                ? "How does the complete selected ETHOS architecture work?"
                : `How does ${page.label} work in the selected ETHOS architecture?`,
            claims: [...claims],
            detail: id === "overview" ? "overview" : "mechanism",
            risk: "Omission would hide selected ETHOS meaning.",
          },
        ];
      }),
    ),
    requiredClaims,
    omissions: {},
    narrative: [...selection.narrative],
    visualGrammar: {
      entityTypes: Object.fromEntries(model.vocabulary.entities.map((type) => [type, "external"])),
      relationTypes: Object.fromEntries(
        model.vocabulary.relations.map((type) => [
          type,
          { label: type.replaceAll("_", " "), variant: "default" },
        ]),
      ),
      principles: [
        "Source meaning before presentation",
        "Independent media retain bounded composition",
      ],
    },
    scenes: {
      static: {
        ...scene({ id: "overview", ...staticSelection }, model),
        questions: ["overview"],
      },
      interactive: Object.fromEntries(
        selection.narrative.map((id) => [
          id,
          {
            ...scene({ id, ...pages.get(id) }, model),
            purpose: id === "overview" ? "overview" : "mechanism",
          },
        ]),
      ),
    },
    qualification: {
      semantic: ["claim-model-valid"],
      coverage: ["required-claims-visible"],
      static: ["painted-geometry"],
      interactive: ["browser-behavior"],
      accessibility: ["keyboard-and-reduced-motion"],
      installed: ["offline-reproduction"],
      recovery: ["publication-recovery"],
      human: ["faithful", "intelligible", "restrained"].flatMap((predicate) => [
        {
          predicate,
          scope: {
            kind: "physical",
            medium: "static",
            artifact: "flagship-png",
            width: 6000,
            height: 3375,
          },
        },
        {
          predicate,
          scope: {
            kind: "viewport",
            medium: "interactive",
            artifact: "standalone-atlas",
            width: 1920,
            height: 1080,
          },
        },
      ]),
    },
    scope:
      "Selected ETHOS publication dependencies; not source, effect, proof or acceptance authority.",
  };
  return edition;
}

/** Compile ETHOS through the same public Edition evolution owner. */
export function compileEthosEditionEvolution(input) {
  if (
    !record(input) ||
    !exact(input, ["before", "after", "correspondences"]) ||
    !record(input.before) ||
    !record(input.after) ||
    !exact(input.before, ["projection", "sourceManifestSha256", "selection"]) ||
    !exact(input.after, ["projection", "sourceManifestSha256", "selection"]) ||
    !Array.isArray(input.correspondences)
  )
    throw Error("Explicit ETHOS Edition evolution input required");
  const before = input.before.projection,
    after = input.after.projection;
  validateProjectionEnvelope(before, before?.digest);
  validateProjectionEnvelope(after, after?.digest);
  if (before.source.id !== after.source.id) throw Error("Semantic source owner changed");
  const beforeModel = ethosClaimModel(before),
    afterModel = ethosClaimModel(after),
    beforeEdition = createEthosEvolutionEdition(
      before,
      input.before.sourceManifestSha256,
      input.before.selection,
    ),
    afterEdition = createEthosEvolutionEdition(
      after,
      input.after.sourceManifestSha256,
      input.after.selection,
    );
  const evolution = compileEditionEvolution({
    before: { claimModel: beforeModel, editions: [beforeEdition] },
    after: { claimModel: afterModel, editions: [afterEdition] },
    correspondences: input.correspondences,
  });
  return {
    ...evolution,
    ethos: {
      before: before.digest,
      after: after.digest,
      added: projectDelta(evolution.delta.added),
      removed: projectDelta(evolution.delta.removed),
      changed: projectDelta(evolution.delta.changed),
    },
  };
}

/** Bind reviewed meaning to visible authored carriers; text truth needs review. */
export function verifyMeaningCarriers(input, bindings, carriers, sourceDocuments = []) {
  if (!Array.isArray(bindings) || !carriers || typeof carriers !== "object")
    throw Error("Explicit meaning carriers required");
  const sections = {
    node: input.semantics.nodes,
    relation: map(input.semantics.relations),
    assertion: input.documents.copy.assertions,
  };
  const seen = new Set();
  for (const binding of bindings) {
    const key = binding.kind + ":" + binding.id;
    const document = binding.kind === "document";
    const meaning = document
      ? input.source.bindings.find((d) => d.id === binding.id)
      : sections[binding.kind]?.[binding.id];
    if (document) {
      const selected = sourceDocuments.filter((d) => d.id === binding.id);
      if (
        !meaning ||
        selected.length !== 1 ||
        !Buffer.isBuffer(selected[0].content) ||
        selected[0].path !== meaning.path ||
        selected[0].sha256 !== meaning.sha256 ||
        sha256(selected[0].content) !== meaning.sha256
      )
        throw Error("Missing or stale source document: " + binding.id);
      if (
        typeof binding.excerpt !== "string" ||
        !binding.excerpt.trim() ||
        !selected[0].content.toString("utf8").includes(binding.excerpt)
      )
        throw Error("Missing exact document excerpt: " + binding.id);
    }
    if (
      !meaning ||
      seen.has(key) ||
      (document ? meaning.sha256 : sha256(stableStringify(meaning))) !== binding.sha256
    )
      throw Error("Stale, unknown or duplicate meaning binding: " + key);
    seen.add(key);
    if (
      !Array.isArray(binding.carriers) ||
      !binding.carriers.length ||
      new Set(binding.carriers).size !== binding.carriers.length ||
      binding.carriers.some((id) => typeof carriers[id] !== "string" || !carriers[id].trim())
    )
      throw Error("Missing visible semantic carrier: " + key);
  }
  return [...seen].sort();
}
