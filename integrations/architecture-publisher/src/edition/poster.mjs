import path from "node:path";
import { readSourceBundle } from "architecture-publisher/source";
import { writeSourceBundle } from "architecture-publisher/source";
import { fail, isDigest } from "architecture-publisher/source";
import { readEthosSource, sha256, stableStringify } from "../adapter/projection.mjs";
import { createMetricReader } from "architecture-publisher/renderers/svg";
import { auditScene, auditCanvasEnvelope } from "architecture-publisher/qualification";
import { auditNaturalSeparation } from "architecture-publisher/qualification";
import { auditEmittedEdges } from "architecture-publisher/qualification";
import { composeNaturalOverview } from "./static/natural-overview.mjs";
import { compileTraceScene, renderTraceSvg } from "./static/trace-scene.mjs";
import { auditNaturalSemantics } from "./static/natural-semantics.mjs";

function fields(value, keys) {
  if (
    !value ||
    typeof value !== "object" ||
    Array.isArray(value) ||
    Object.keys(value).length !== keys.length ||
    keys.some((k) => !Object.hasOwn(value, k))
  )
    fail("poster_fields_invalid");
}
function parse(bytes) {
  try {
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  } catch {
    fail("poster_json_invalid");
  }
}
const encoded = (value) => Buffer.from(JSON.stringify(value, null, 2) + "\n");

/** Reconstruct one selected authored edition. Never discover a source or font. */
export async function compileEthosPoster(plan) {
  fields(plan, [
    "sourceManifest",
    "sourceSha256",
    "projectionDigest",
    "editionManifest",
    "editionSha256",
    "output",
  ]);
  for (const key of ["sourceManifest", "editionManifest", "output"])
    if (typeof plan[key] !== "string" || !path.isAbsolute(plan[key])) fail("poster_path_required");
  const source = await readEthosSource(
    plan.sourceManifest,
    plan.sourceSha256,
    plan.projectionDigest,
  );
  const bundle = await readSourceBundle(plan.editionManifest, plan.editionSha256);
  if (
    bundle.members.length !== 2 ||
    !["edition.json", "metrics.json"].every((p) => bundle.members.some((m) => m.path === p))
  )
    fail("poster_members_invalid");
  const member = (p) => bundle.members.find((m) => m.path === p).content;
  const edition = parse(member("edition.json"));
  const candidate = edition.schema === "architecture.ethos-poster-candidate/v1";
  fields(edition, [
    "schema",
    "source",
    "metricsSha256",
    candidate ? "authoring" : "expected",
    "scope",
  ]);
  fields(edition.source, ["commit", "manifestSha256", "projectionDigest"]);
  if (!candidate) fields(edition.expected, ["svgSha256", "sceneSha256", "labels"]);
  if (
    candidate &&
    (!edition.authoring ||
      typeof edition.authoring !== "object" ||
      Array.isArray(edition.authoring) ||
      Object.keys(edition.authoring).some(
        (k) => !["labels", "laneCount", "refresh", "carriers"].includes(k),
      ))
  )
    fail("poster_authoring_invalid");
  if (
    (!candidate && edition.schema !== "architecture.ethos-poster-input/v1") ||
    typeof edition.scope !== "string" ||
    !edition.scope.trim() ||
    !isDigest(edition.metricsSha256) ||
    (!candidate &&
      (!isDigest(edition.expected.svgSha256) ||
        !isDigest(edition.expected.sceneSha256) ||
        !Number.isSafeInteger(edition.expected.labels) ||
        edition.expected.labels < 1 ||
        edition.expected.labels > 10000))
  )
    fail("poster_identity_invalid");
  if (
    stableStringify(edition.source) !==
    stableStringify({
      commit: source.projection.source.git.commit,
      manifestSha256: plan.sourceSha256,
      projectionDigest: plan.projectionDigest,
    })
  )
    fail("poster_source_mismatch");
  if (sha256(member("metrics.json")) !== edition.metricsSha256) fail("poster_metrics_mismatch");

  const reader = createMetricReader(parse(member("metrics.json"))),
    input = source.projection;
  const quality = parse(Buffer.from(input.documents.quality_contract));
  const composition = composeNaturalOverview(
    input,
    reader.measure,
    quality,
    candidate ? edition.authoring : {},
    source.sourceDocuments,
  );
  const scene = compileTraceScene(composition.document, reader.measure);
  const svg = Buffer.from(renderTraceSvg(scene));
  if (
    !candidate &&
    (scene.texts.length !== edition.expected.labels ||
      sha256(stableStringify(scene)) !== edition.expected.sceneSha256 ||
      sha256(svg) !== edition.expected.svgSha256)
  )
    fail("poster_reconstruction_mismatch");
  const g = quality.hard_gates.geometry_each_scale,
    t = quality.hard_gates.typography_and_accessibility;
  const scale = quality.scales.find((s) => s.name === "source");
  if (!scale) fail("poster_quality_invalid");
  const checks = {
    sourceBindings: auditNaturalSemantics(composition, input, source.sourceDocuments),
    separation: auditNaturalSeparation(scene, composition.separation, quality),
    geometry: auditScene(scene, {
      minimumFont: Math.max(
        t.effective_font_px_min_at_reference,
        t.source_font_px_min === undefined
          ? 0
          : (t.source_font_px_min * scene.referenceWidth) / scale.width,
      ),
      ownerClearance: g.inside_glyph_to_owner_inner_stroke_px_at_reference_min,
      textClearance: g.text_to_nonowner_geometry_clearance_px_at_reference_min,
      endpointTolerance: g.arrow_tip_error_px_max,
      minimumTerminal: g.arrow_terminal_straight_run_px_at_reference_min,
      widthGrowth: g.font_width_growth_fraction,
      heightGrowth: g.font_height_growth_fraction,
    }),
    emittedEdges: auditEmittedEdges(svg.toString(), scene, {
      minimumTerminal: g.arrow_terminal_straight_run_px_at_reference_min,
      endpointTolerance: g.arrow_tip_error_px_max,
    }),
    canvas: auditCanvasEnvelope(scene, quality),
  };
  if (Object.values(checks).some((x) => x.failures.length)) fail("poster_checks_failed");
  const result = {
    status: "rendered",
    mode: candidate ? "candidate" : "replay",
    source: edition.source,
    editionSha256: plan.editionSha256,
    labels: scene.texts.length,
    measurement: "recorded",
    metrics: {
      sha256: edition.metricsSha256,
      records: reader.recordCount,
      used: reader.usedCount,
    },
    svg: { sha256: sha256(svg), bytes: svg.length },
    sceneSha256: sha256(stableStringify(scene)),
    checks,
    browserAcceptance: "not-performed",
    semanticAcceptance: "not-performed",
    scope:
      "Recompiled source-bound composition and SVG with selected recorded metrics. Measurement provenance is separate; no raster output, actual browser paint or new visual approval.",
  };
  return { result, scene, svg, composition };
}

export async function renderEthosPoster(plan) {
  const { result, scene, svg } = await compileEthosPoster(plan);
  const output = await writeSourceBundle(
    plan.output,
    { id: "ethos:poster", revision: result.source.commit },
    [
      { path: "terminal.svg", content: svg },
      { path: "scene.json", content: encoded(scene) },
      { path: "checks.json", content: encoded(result) },
      {
        path: "text.txt",
        content: Buffer.from(scene.texts.map((x) => `${x.id}\t${x.text}`).join("\n") + "\n"),
      },
    ],
  );
  return { ...result, output };
}
