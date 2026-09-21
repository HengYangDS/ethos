import fs from "node:fs/promises";
import path from "node:path";
import { fail, isDigest, portablePath } from "architecture-publisher/source";
import { readSourceBundle } from "architecture-publisher/source";
import { readEthosSource, sha256, stableStringify } from "../adapter/projection.mjs";
import { readArchifyLicense, renderNativeDiagram } from "architecture-publisher/renderers/archify";
import { loadBundledFonts } from "architecture-publisher/renderers/fonts";
import { applyNativeTypography, nativeTypography } from "./typography.mjs";
import { applyNativeAnnotations, validateNativeAnnotations } from "./annotations.mjs";
import { validateAtlasCatalog, applyNativePresentation, applyAtlasNavigation } from "./reader.mjs";
import { deriveNativeSemanticPassport, applyNativeSemanticPassport } from "./passport.mjs";
import { deriveResourceComparison, applyResourceComparison } from "./resource-comparison.mjs";
import { deriveVerificationDetails, applyVerificationDetails } from "./verification-details.mjs";
import { deriveWriteBoundary, applyWriteBoundary } from "./write-boundary.mjs";
import { applyNativeFonts } from "./fonts.mjs";
import { checkBindings } from "./bindings.mjs";

const object = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const same = (a, b) => stableStringify(a) === stableStringify(b);
function fields(value, required) {
  if (!object(value) || !same(Object.keys(value).sort(), [...required].sort()))
    fail("atlas_fields_invalid");
}
function parse(bytes) {
  try {
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  } catch {
    fail("atlas_json_invalid");
  }
}

export async function readEthosAtlasSelection(plan) {
  fields(plan, [
    "sourceManifest",
    "sourceSha256",
    "projectionDigest",
    "editionManifest",
    "editionSha256",
  ]);
  for (const key of ["sourceManifest", "editionManifest"])
    if (typeof plan[key] !== "string" || !path.isAbsolute(plan[key])) fail("atlas_path_required");
  const source = await readEthosSource(
    plan.sourceManifest,
    plan.sourceSha256,
    plan.projectionDigest,
  );
  const bundle = await readSourceBundle(plan.editionManifest, plan.editionSha256);
  const members = new Map(bundle.members.map((m) => [m.path, m.content]));
  const needed = new Set(["edition.json", "catalog.json", "original-font-selection.json"]);
  const member = (name) => {
    portablePath(name);
    const bytes = members.get(name);
    if (!bytes) fail("atlas_member_missing");
    return bytes;
  };
  const edition = parse(member("edition.json")),
    catalog = parse(member("catalog.json"));
  const candidate = edition.schema === "architecture.ethos-atlas-candidate/v1";
  fields(edition, [
    "schema",
    "source",
    ...(candidate ? [] : ["acceptedAtlasManifestSha256"]),
    "fontSelectionSha256",
    "pages",
    "scope",
  ]);
  fields(edition.source, ["commit", "projectionDigest", "manifestSha256"]);
  if (
    (!candidate && edition.schema !== "architecture.ethos-edition-input/v1") ||
    !same(edition.source, {
      commit: source.projection.source.git.commit,
      projectionDigest: plan.projectionDigest,
      manifestSha256: plan.sourceSha256,
    })
  )
    fail("atlas_source_mismatch");
  for (const key of [...(candidate ? [] : ["acceptedAtlasManifestSha256"]), "fontSelectionSha256"])
    if (!isDigest(edition[key])) fail("atlas_identity_invalid");
  fields(catalog, ["schema", "sourceDigest", "pages"]);
  validateAtlasCatalog(catalog);
  for (const page of catalog.pages) fields(page, ["id", "label", "path"]);
  if (
    catalog.sourceDigest !== plan.projectionDigest ||
    !Array.isArray(edition.pages) ||
    edition.pages.length !== catalog.pages.length
  )
    fail("atlas_catalog_mismatch");
  const input = source.projection,
    quality = parse(Buffer.from(input.documents.quality_contract));
  const sourceRelations = new Set(input.semantics.relations.map((r) => r.id));
  const assertions = input.documents.copy.assertions;
  const pages = [];
  for (const [index, page] of edition.pages.entries()) {
    fields(page, [
      "id",
      "label",
      "path",
      "spec",
      "bindings",
      "specSha256",
      "bindingsSha256",
      ...(candidate ? [] : ["acceptedHtmlSha256"]),
      "typography",
      "resourceComparison",
      "verificationDetails",
      "writeBoundary",
    ]);
    if (!same({ id: page.id, label: page.label, path: page.path }, catalog.pages[index]))
      fail("atlas_catalog_mismatch");
    for (const key of ["resourceComparison", "verificationDetails", "writeBoundary"])
      if (typeof page[key] !== "boolean") fail("atlas_fields_invalid");
    for (const key of [
      "specSha256",
      "bindingsSha256",
      ...(candidate ? [] : ["acceptedHtmlSha256"]),
    ])
      if (!isDigest(page[key])) fail("atlas_identity_invalid");
    for (const key of ["spec", "bindings"]) {
      if (needed.has(page[key])) fail("atlas_member_duplicate");
      needed.add(portablePath(page[key]));
    }
    const specBytes = member(page.spec),
      bindingBytes = member(page.bindings);
    if (sha256(specBytes) !== page.specSha256 || sha256(bindingBytes) !== page.bindingsSha256)
      fail("atlas_member_digest_mismatch");
    const spec = parse(specBytes),
      bindings = parse(bindingBytes);
    if (checkBindings(spec, bindings, input, source.sourceDocuments) !== "architecture")
      fail("atlas_type_unsupported");
    if (
      !object(bindings.relations) ||
      !same(Object.keys(bindings.relations).sort(), spec.connections.map((c) => c.id).sort())
    )
      fail("atlas_relation_bindings_invalid");
    for (const relation of Object.values(bindings.relations)) {
      if (
        !object(relation) ||
        !Array.isArray(relation.sourceRelations) ||
        relation.sourceRelations.some((id) => !sourceRelations.has(id)) ||
        typeof relation.explanation !== "string" ||
        !relation.explanation.trim() ||
        relation.effectAuthority === true
      )
        fail("atlas_relation_bindings_invalid");
      for (const id of [...(relation.assertions ?? []), ...(relation.sourceAssertions ?? [])])
        if (!Object.hasOwn(assertions, id)) fail("atlas_relation_bindings_invalid");
    }
    fields(page.typography, ["diagramArea", "fit"]);
    nativeTypography(quality, {
      ...page.typography,
      viewBox: spec.meta.viewBox,
    });
    if (bindings.presentation !== undefined) {
      if (
        !object(bindings.presentation) ||
        Object.keys(bindings.presentation).some(
          (k) => !["annotationNodes", "emphasisNodes"].includes(k),
        )
      )
        fail("atlas_presentation_invalid");
      validateNativeAnnotations(
        spec,
        bindings.presentation.annotationNodes,
        bindings.presentation.emphasisNodes,
      );
    }
    if (bindings.repositoryJudgments?.length && !page.resourceComparison)
      fail("atlas_detail_required");
    if (bindings.verificationDetailsRequired === true && !page.verificationDetails)
      fail("atlas_detail_required");
    if (page.resourceComparison) deriveResourceComparison(input);
    if (page.verificationDetails) deriveVerificationDetails(input);
    let writeBoundary;
    const required = bindings.writeBoundaryRequired;
    if (Boolean(required) !== page.writeBoundary) fail("atlas_detail_required");
    if (required) {
      const doc = source.sourceDocuments.find((d) => d.id === "runner_mutation");
      const lanes = Object.entries(bindings.nodes)
        .filter(([, ids]) => ids.includes("work_lane"))
        .map(([id]) => id)
        .sort();
      if (
        !doc ||
        required.effectAuthority !== false ||
        required.sourceId !== doc.id ||
        required.sourceSha256 !== doc.sha256 ||
        !Array.isArray(required.appliesTo) ||
        !lanes.length ||
        !same([...required.appliesTo].sort(), lanes)
      )
        fail("atlas_write_boundary_invalid");
      writeBoundary = deriveWriteBoundary(input, doc.content);
    }
    pages.push({
      ...page,
      specBytes,
      spec,
      bindings,
      writeBoundary,
      passport: deriveNativeSemanticPassport(spec, bindings, input),
    });
  }
  if (!same([...needed].sort(), [...members.keys()].sort())) fail("atlas_members_mismatch");
  const lockBytes = member("original-font-selection.json");
  if (sha256(lockBytes) !== edition.fontSelectionSha256) fail("atlas_font_selection_mismatch");
  const lock = parse(lockBytes),
    packaged = await loadBundledFonts();
  if (
    lock.schema !== "ethos.font-supply/v1" ||
    lock.family !== "ETHOS JetBrains Mono" ||
    lock.sourceFamily !== "JetBrains Mono" ||
    !same(
      lock.fonts?.map((f) => [f.weight, f.sha256, f.bytes]),
      packaged.fonts.map((f) => [f.weight, f.sha256, f.bytes.length]),
    ) ||
    lock.license?.sha256 !== packaged.license.sha256
  )
    fail("atlas_font_selection_mismatch");
  const fonts = {
    ...packaged,
    lockSha256: edition.fontSelectionSha256,
    lock,
    family: lock.family,
  };
  return {
    source,
    edition,
    catalog,
    quality,
    pages,
    fonts,
    mode: candidate ? "candidate" : "replay",
  };
}

/** Portable ETHOS edition. Byte reproduction is not new semantic or browser acceptance. */
export async function renderEthosAtlas(plan) {
  const { output, ...selection } = plan;
  if (typeof output !== "string" || !path.isAbsolute(output)) fail("atlas_path_required");
  const selected = await readEthosAtlasSelection(selection);
  const parent = path.dirname(plan.output),
    stat = await fs.lstat(parent);
  if (!stat.isDirectory() || stat.isSymbolicLink() || (await fs.realpath(parent)) !== parent)
    fail("atlas_output_parent_invalid");
  try {
    await fs.mkdir(plan.output);
  } catch (error) {
    if (error.code === "EEXIST") fail("atlas_output_exists");
    throw error;
  }
  const { source, edition, catalog, quality, pages, fonts } = selected;
  const results = [],
    files = [];
  for (const page of pages) {
    const output = path.join(plan.output, page.path);
    await fs.mkdir(path.dirname(output), { recursive: true });
    const result = await renderNativeDiagram(
      { type: "architecture", inputBytes: page.specBytes, output },
      async (runtime) => {
        const typography = await applyNativeTypography(runtime, quality, {
          ...page.typography,
          viewBox: page.spec.meta.viewBox,
        });
        let renderer = typography.patchedFiles.find(
          (f) => f.path === "renderers/architecture/render-architecture.mjs",
        ).after;
        if (page.bindings.presentation?.annotationNodes)
          renderer = (
            await applyNativeAnnotations(
              runtime,
              page.spec,
              page.bindings.presentation.annotationNodes,
              renderer,
              { emphasisNodes: page.bindings.presentation.emphasisNodes },
            )
          ).after;
        const presentation = await applyNativePresentation(runtime);
        const passport = await applyNativeSemanticPassport(runtime, page.passport, {
          "renderers/architecture/render-architecture.mjs": renderer,
          "renderers/shared/cli.mjs":
            "2a6b8fa11234451627a70bca71985d80362a4c52401a90a21840d6e2ae3012d9",
          "assets/template.html": presentation.after,
        });
        renderer = passport.patchedFiles.find(
          (f) => f.path === "renderers/architecture/render-architecture.mjs",
        ).after;
        let template = passport.patchedFiles.find((f) => f.path === "assets/template.html").after;
        template = (
          await applyAtlasNavigation(
            runtime,
            catalog,
            page.id,
            template,
            quality.hard_gates.typography_and_accessibility.effective_font_px_min_at_reference,
          )
        ).after;
        if (page.resourceComparison)
          template = (await applyResourceComparison(runtime, source.projection, template)).after;
        if (page.verificationDetails)
          template = (await applyVerificationDetails(runtime, source.projection, template)).after;
        if (page.writeBoundary)
          template = (await applyWriteBoundary(runtime, page.writeBoundary, template)).after;
        await applyNativeFonts(runtime, fonts, { template, renderer });
      },
    );
    if (selected.mode === "replay" && result.artifact.sha256 !== page.acceptedHtmlSha256)
      fail("atlas_expected_html_mismatch");
    files.push({
      path: page.path,
      bytes: result.artifact.bytes,
      sha256: result.artifact.sha256,
    });
    results.push({
      id: page.id,
      path: page.path,
      artifact: result.artifact,
      nativeValidation: result.nativeValidation,
    });
  }
  const notices = [
    ["ARCHIFY-LICENSE.txt", await readArchifyLicense()],
    ["FONT-LICENSE.txt", fonts.license.bytes],
  ];
  for (const [name, bytes] of notices) {
    await fs.writeFile(path.join(plan.output, name), bytes, { flag: "wx" });
    files.push({ path: name, bytes: bytes.length, sha256: sha256(bytes) });
  }
  const observed = new Set();
  async function walk(directory, prefix = "") {
    for (const entry of await fs.readdir(directory, {
      withFileTypes: true,
    })) {
      const name = prefix + entry.name;
      if (entry.isSymbolicLink()) fail("atlas_output_changed");
      if (entry.isDirectory()) await walk(path.join(directory, entry.name), name + "/");
      else if (entry.isFile()) observed.add(name);
      else fail("atlas_output_changed");
    }
  }
  await walk(plan.output);
  if (!same([...observed].sort(), files.map((f) => f.path).sort())) fail("atlas_output_changed");
  for (const file of files) {
    const bytes = await fs.readFile(path.join(plan.output, file.path));
    if (bytes.length !== file.bytes || sha256(bytes) !== file.sha256) fail("atlas_output_changed");
  }
  const manifest = {
    schema: "architecture.atlas-output/v1",
    source: edition.source,
    editionSha256: plan.editionSha256,
    files,
    browserAcceptance: "not-performed",
    semanticAcceptance: "not-performed",
  };
  const bytes = Buffer.from(JSON.stringify(manifest, null, 2) + "\n");
  await fs.writeFile(path.join(plan.output, "manifest.json"), bytes, {
    flag: "wx",
  });
  return {
    status: "rendered",
    output: plan.output,
    pages: results,
    manifestSha256: sha256(bytes),
    browserAcceptance: "not-performed",
    semanticAcceptance: "not-performed",
  };
}
