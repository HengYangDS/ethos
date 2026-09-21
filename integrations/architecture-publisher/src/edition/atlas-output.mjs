import fs from "node:fs/promises";
import path from "node:path";
import { fail, isDigest } from "architecture-publisher/source";
import { readFileEnvelope } from "architecture-publisher/source";
import { readArchifyLicense } from "architecture-publisher/renderers/archify";
import { sha256, stableStringify } from "../adapter/projection.mjs";
import { readEthosAtlasSelection } from "./atlas.mjs";
const same = (a, b) => stableStringify(a) === stableStringify(b);
function fields(value, required) {
  if (
    !value ||
    typeof value !== "object" ||
    Array.isArray(value) ||
    !same(Object.keys(value).sort(), [...required].sort())
  )
    fail("atlas_output_fields_invalid");
}
function decode(value) {
  fields(value, [
    "schema",
    "source",
    "editionSha256",
    "files",
    "browserAcceptance",
    "semanticAcceptance",
  ]);
  if (value.schema !== "architecture.atlas-output/v1") fail("atlas_output_schema_invalid");
  fields(value.source, ["commit", "projectionDigest", "manifestSha256"]);
  if (!isDigest(value.editionSha256)) fail("atlas_output_edition_mismatch");
  if (value.browserAcceptance !== "not-performed" || value.semanticAcceptance !== "not-performed")
    fail("atlas_output_acceptance_invalid");
  return value;
}

/** Read current producer output directly. Identity is not approval or an effect. */
export async function readEthosAtlasOutput(plan) {
  fields(plan, [
    "sourceManifest",
    "sourceSha256",
    "projectionDigest",
    "editionManifest",
    "editionSha256",
    "outputManifest",
    "outputSha256",
  ]);
  if (typeof plan.outputManifest !== "string" || !path.isAbsolute(plan.outputManifest))
    fail("atlas_path_required");
  const { outputManifest, outputSha256, ...selection } = plan;
  const selected = await readEthosAtlasSelection(selection);
  const result = await readFileEnvelope(outputManifest, outputSha256, decode);
  if (!same(result.manifest.source, selected.edition.source)) fail("atlas_output_source_mismatch");
  if (result.manifest.editionSha256 !== plan.editionSha256) fail("atlas_output_edition_mismatch");
  const needed = [...selected.pages.map((p) => p.path), "ARCHIFY-LICENSE.txt", "FONT-LICENSE.txt"];
  if (!same(result.members.map((f) => f.path).sort(), needed.sort()))
    fail("atlas_output_members_mismatch");
  const members = new Map(result.members.map((m) => [m.path, m]));
  for (const page of selected.pages)
    if (selected.mode === "replay" && members.get(page.path).sha256 !== page.acceptedHtmlSha256)
      fail("atlas_output_page_mismatch");
  const archifyNotice = await readArchifyLicense();
  if (
    members.get("ARCHIFY-LICENSE.txt").sha256 !== sha256(archifyNotice) ||
    members.get("FONT-LICENSE.txt").sha256 !== selected.fonts.license.sha256
  )
    fail("atlas_output_license_mismatch");
  return {
    scope: "artifact-file-integrity",
    source: result.manifest.source,
    editionSha256: plan.editionSha256,
    manifestSha256: result.manifestSha256,
    pages: selected.pages.map((p) => ({
      id: p.id,
      path: p.path,
      sha256: members.get(p.path).sha256,
    })),
    members: result.members,
    semanticAcceptance: "not-performed",
    browserAcceptance: "not-performed",
    publicationAcceptance: "not-performed",
  };
}
