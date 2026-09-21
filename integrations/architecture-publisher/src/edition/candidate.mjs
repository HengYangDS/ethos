import fs from "node:fs/promises";
import path from "node:path";
import { readSourceBundle } from "architecture-publisher/source";
import { writeSourceBundle } from "architecture-publisher/source";
import { readEthosSource, sha256, stableStringify } from "../adapter/projection.mjs";
import { readEthosAtlasSelection } from "./atlas.mjs";
import { checkBindings } from "./bindings.mjs";
import {
  compileEthosEditionEvolution,
  selectEthosEditionDependencies,
  verifyMeaningCarriers,
} from "./evolution.mjs";

const encode = (v) => Buffer.from(JSON.stringify(v, null, 2) + "\n");
const exact = (v, keys) =>
  v &&
  typeof v === "object" &&
  !Array.isArray(v) &&
  Object.keys(v).sort().join(",") === [...keys].sort().join(",");

/** Rebind selected authoring, never rewrite source meaning or qualify new bytes. */
export async function prepareEthosCandidate(plan) {
  if (
    !exact(plan, ["previous", "source", "authoring", "authoringSha256", "output"]) ||
    !exact(plan.source, ["sourceManifest", "sourceSha256", "projectionDigest"])
  )
    throw Error("Explicit candidate preparation inputs required");
  if (!path.isAbsolute(plan.output ?? "") || !path.isAbsolute(plan.authoring ?? ""))
    throw Error("Explicit absolute candidate paths required");
  const previous = await readEthosAtlasSelection(plan.previous);
  const source = await readEthosSource(
    plan.source.sourceManifest,
    plan.source.sourceSha256,
    plan.source.projectionDigest,
  );
  const selected = await readSourceBundle(
    plan.previous.editionManifest,
    plan.previous.editionSha256,
  );
  const stat = await fs.lstat(plan.authoring);
  if (
    !stat.isFile() ||
    stat.isSymbolicLink() ||
    stat.size > 1024 * 1024 ||
    (await fs.realpath(plan.authoring)) !== plan.authoring
  )
    throw Error("Regular bounded authored input required");
  const bytes = await fs.readFile(plan.authoring);
  if (sha256(bytes) !== plan.authoringSha256) throw Error("Candidate authoring identity changed");
  const authoring = JSON.parse(bytes);
  if (
    !exact(authoring, ["schema", "static", "interactive", "scope"]) ||
    authoring.schema !== "architecture.ethos-authored-edits/v1" ||
    !authoring.static ||
    typeof authoring.static !== "object" ||
    Array.isArray(authoring.static) ||
    Object.keys(authoring.static).some(
      (key) => !["labels", "laneCount", "refresh", "carriers"].includes(key),
    ) ||
    !exact(authoring.interactive, ["order", "pages"]) ||
    !Array.isArray(authoring.interactive.order) ||
    !Array.isArray(authoring.interactive.pages) ||
    typeof authoring.scope !== "string" ||
    !authoring.scope.trim()
  )
    throw Error("Unsupported authored edits");
  const order = authoring.interactive.order;
  if (
    order.length !== previous.pages.length ||
    new Set(order).size !== order.length ||
    order.some((id) => !previous.pages.some((p) => p.id === id))
  )
    throw Error("Complete distinct page order required");
  const edits = new Map();
  const represented = new Set();
  for (const page of authoring.interactive.pages) {
    if (
      !exact(page, ["id", "edits", "meaning"]) ||
      !order.includes(page.id) ||
      edits.has(page.id) ||
      !Array.isArray(page.edits) ||
      !page.edits.length ||
      !Array.isArray(page.meaning) ||
      !page.meaning.length
    )
      throw Error("Explicit distinct authored page required");
    const spec = structuredClone(previous.pages.find((p) => p.id === page.id).spec);
    const carriers = {};
    for (const edit of page.edits) {
      if (
        !exact(edit, ["carrier", "before", "after"]) ||
        typeof edit.carrier !== "string" ||
        Object.hasOwn(carriers, edit.carrier) ||
        typeof edit.after !== "string" ||
        !edit.after.trim() ||
        edit.after.length > 10000 ||
        /[\r\n]/.test(edit.after)
      )
        throw Error("Invalid or duplicate authored carrier");
      const node = /^nodes\/([^/]+)\/(label|sublabel|tag)$/.exec(edit.carrier);
      const card = /^cards\/(0|[1-9][0-9]*)\/items\/(0|[1-9][0-9]*)$/.exec(edit.carrier);
      let owner, field;
      if (node) {
        owner = (spec.components ?? spec.participants)?.find((n) => n.id === node[1]);
        field = node[2];
      } else if (card) {
        owner = spec.cards?.[Number(card[1])]?.items;
        field = Number(card[2]);
        if (!Array.isArray(owner) || field > owner.length) owner = undefined;
      }
      if (!owner) throw Error("Unknown authored carrier " + edit.carrier);
      const before = owner[field] === undefined ? null : owner[field];
      if (before !== edit.before) throw Error("Stale authored carrier " + edit.carrier);
      if (before === null && !card) throw Error("Unknown authored carrier " + edit.carrier);
      owner[field] = edit.after;
      carriers[edit.carrier] = edit.after;
    }
    for (const key of verifyMeaningCarriers(
      source.projection,
      page.meaning,
      carriers,
      source.sourceDocuments,
    ))
      represented.add(key);
    const bound = new Set(page.meaning.flatMap((m) => m.carriers));
    if (Object.keys(carriers).some((id) => !bound.has(id))) throw Error("Unbound authored carrier");
    edits.set(page.id, { spec, meaning: page.meaning });
  }
  const nextPages = previous.pages.map((page) => {
      const authored = edits.get(page.id);
      if (!authored) return page;
      const bindings = structuredClone(page.bindings),
        selectedMeaning = authored.meaning;
      bindings.meaning = [
        ...(bindings.meaning ?? []).filter(
          (old) => !selectedMeaning.some((item) => old.kind === item.kind && old.id === item.id),
        ),
        ...structuredClone(selectedMeaning),
      ];
      return { ...page, spec: authored.spec, bindings };
    }),
    previousSelection = selectEthosEditionDependencies(
      previous.source.projection,
      previous.pages,
      {},
    );
  let nextSelection;
  try {
    nextSelection = selectEthosEditionDependencies(source.projection, nextPages, authoring.static);
  } catch (error) {
    throw new Error("Unsupported semantic delta requires authored mapping: " + error.message, {
      cause: error,
    });
  }
  nextSelection.narrative = [...order];
  const evolution = compileEthosEditionEvolution({
    before: {
      projection: previous.source.projection,
      sourceManifestSha256: plan.previous.sourceSha256,
      selection: previousSelection,
    },
    after: {
      projection: source.projection,
      sourceManifestSha256: plan.source.sourceSha256,
      selection: nextSelection,
    },
    correspondences: [],
  });
  const supported =
    evolution.ethos.added.nodes.length === 0 &&
    evolution.ethos.removed.nodes.length === 0 &&
    evolution.ethos.changed.nodes.every(
      (id) =>
        represented.has("node:" + id) &&
        previous.source.projection.semantics.nodes[id].kind ===
          source.projection.semantics.nodes[id].kind,
    ) &&
    evolution.ethos.changed.relations.every(
      (id) =>
        represented.has("relation:" + id) &&
        ["from", "to", "kind"].every(
          (key) =>
            previous.source.projection.semantics.relations.find((r) => r.id === id)[key] ===
            source.projection.semantics.relations.find((r) => r.id === id)[key],
        ),
    ) &&
    evolution.ethos.changed.assertions.every((id) => represented.has("assertion:" + id)) &&
    ["relations", "assertions"].every(
      (k) => !evolution.ethos.added[k].length && !evolution.ethos.removed[k].length,
    ) &&
    ["contracts", "presentation"].every(
      (k) =>
        !evolution.ethos.added[k].length &&
        !evolution.ethos.removed[k].length &&
        !evolution.ethos.changed[k].length,
    );
  if (!supported || evolution.editions.affected[0]?.unrepresented.length)
    throw Error("Unsupported semantic delta requires authored mapping");
  const members = new Map(selected.members.map((m) => [m.path, m.content]));
  const edition = structuredClone(previous.edition);
  edition.pages = order.map((id) => edition.pages.find((p) => p.id === id));
  edition.schema = "architecture.ethos-atlas-candidate/v1";
  delete edition.acceptedAtlasManifestSha256;
  edition.source = {
    commit: source.projection.source.git.commit,
    projectionDigest: plan.source.projectionDigest,
    manifestSha256: plan.source.sourceSha256,
  };
  const catalog = structuredClone(previous.catalog);
  catalog.pages = order.map((id) => catalog.pages.find((p) => p.id === id));
  catalog.sourceDigest = plan.source.projectionDigest;
  for (const page of edition.pages) {
    delete page.acceptedHtmlSha256;
    const original = previous.pages.find((p) => p.id === page.id),
      spec = edits.get(page.id)?.spec ?? structuredClone(original.spec),
      bindings = structuredClone(original.bindings);
    bindings.sourceRevision = edition.source.commit;
    bindings.sourceDigest = edition.source.projectionDigest;
    if (bindings.writeBoundaryRequired) {
      const sourceId = bindings.writeBoundaryRequired.sourceId;
      bindings.writeBoundaryRequired.sourceSha256 = source.projection.source.bindings.find(
        (b) => b.id === sourceId,
      )?.sha256;
    }
    if (edits.has(page.id)) {
      const selectedMeaning = edits.get(page.id).meaning;
      for (const old of bindings.meaning ?? []) {
        const replacement = selectedMeaning.find((m) => old.kind === m.kind && old.id === m.id);
        if (replacement && old.carriers.some((id) => !replacement.carriers.includes(id)))
          throw Error("Existing semantic carrier would be orphaned");
      }
      bindings.meaning = [
        ...(bindings.meaning ?? []).filter(
          (old) => !selectedMeaning.some((m) => old.kind === m.kind && old.id === m.id),
        ),
        ...structuredClone(selectedMeaning),
      ];
    }
    checkBindings(spec, bindings, source.projection, source.sourceDocuments);
    members.set(page.spec, encode(spec));
    members.set(page.bindings, encode(bindings));
    page.specSha256 = sha256(members.get(page.spec));
    page.bindingsSha256 = sha256(members.get(page.bindings));
  }
  members.set("edition.json", encode(edition));
  members.set("catalog.json", encode(catalog));
  const written = await writeSourceBundle(
    plan.output,
    { id: "ethos:atlas-authoring", revision: edition.source.commit },
    [...members].map(([path, content]) => ({ path, content })),
  );
  return {
    status: "prepared",
    pages: edition.pages.length,
    input: plan,
    atlas: {
      ...plan.source,
      editionManifest: written.manifestPath,
      editionSha256: written.manifestSha256,
    },
    evolution,
    posterAuthoring: structuredClone(authoring.static),
    authoringSha256: plan.authoringSha256,
    semanticAcceptance: "not-performed",
    browserAcceptance: "not-performed",
  };
}
