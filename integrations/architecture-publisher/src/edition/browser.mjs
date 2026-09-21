import path from "node:path";
import { decodeBrowserReport } from "./browser-report.mjs";
import { readSourceBundle } from "architecture-publisher/source";
// ETHOS edition browser obligations. No browser launch, credentials or host discovery.
import { portablePath, isDigest } from "architecture-publisher/source";
import { readEthosAtlasOutput } from "./atlas-output.mjs";
import { readEthosSource, sha256 } from "../adapter/projection.mjs";
import {
  ATLAS_VIEWPORTS,
  ATLAS_EXPORTS,
  derivePageObligations,
  browserCoverageGaps,
} from "./browser-obligations.mjs";

/** Required observations derived from actual selected bytes, never from a report. */
export async function describeEthosBrowser(atlas) {
  const output = await readEthosAtlasOutput(atlas),
    source = await readEthosSource(
      atlas.sourceManifest,
      atlas.sourceSha256,
      atlas.projectionDigest,
    );
  const quality = JSON.parse(source.projection.documents.quality_contract);
  const members = new Map(output.members.map((m) => [m.path, m.content]));
  return {
    schema: "architecture.ethos-browser-obligations/v1",
    scope: "required-browser-observations",
    source: {
      commit: source.projection.source.git.commit,
      tree: source.projection.source.git.tree,
      digest: source.projection.digest,
      qualitySha256: sha256(source.projection.documents.quality_contract),
    },
    outputManifestSha256: output.manifestSha256,
    viewports: ATLAS_VIEWPORTS,
    exports: ATLAS_EXPORTS,
    typography: quality.hard_gates.typography_and_accessibility,
    pages: output.pages.map((p) => ({
      id: p.id,
      path: p.path,
      htmlSha256: p.sha256,
      obligations: derivePageObligations(members.get(p.path).toString("utf8")),
    })),
    browserExecuted: false,
    browserAcceptance: "not-performed",
  };
}

/** Consume observed values and exact evidence bytes; no execution authenticity claim.
 * @internal Focused verification seam; readEthosBrowserEvidence is the reader. */
export function validateEthosBrowserReport({ report, members }, target, viewport) {
  if (
    !report ||
    typeof report !== "object" ||
    Object.hasOwn(report, "fixtureOnly") ||
    Object.hasOwn(report, "synthetic")
  )
    throw Error("Synthetic or missing browser evidence");
  if (
    report.source?.digest !== target.source.digest ||
    report.source?.qualitySha256 !== target.source.qualitySha256 ||
    report.source?.commit !== target.source.commit ||
    report.source?.tree !== target.source.tree
  )
    throw Error("Browser evidence source mismatch");
  if (report.artifactManifestSha256 !== target.outputManifestSha256)
    throw Error("Browser artifact identity mismatch");
  if (
    !isDigest(target.checkerManifestSha256) ||
    report.checkerManifestSha256 !== target.checkerManifestSha256
  )
    throw Error("Browser checker identity mismatch");
  const gaps = browserCoverageGaps(report, target.pages, viewport, target.typography);
  if (gaps.length) throw Error("Browser coverage failure: " + gaps.join(", "));
  if (!Array.isArray(report.evidenceFiles) || !Array.isArray(members))
    throw Error("Browser evidence files missing");
  const supplied = new Map(),
    content = new Map(members.map((m) => [m.path, m]));
  if (content.size !== members.length) throw Error("Duplicate browser evidence member");
  for (const item of report.evidenceFiles) {
    portablePath(item.path);
    if (
      supplied.has(item.path) ||
      !Number.isSafeInteger(item.bytes) ||
      item.bytes < 1 ||
      !isDigest(item.sha256)
    )
      throw Error("Invalid browser evidence identity");
    const actual = content.get(item.path);
    if (
      !actual ||
      !Buffer.isBuffer(actual.content) ||
      actual.content.length !== item.bytes ||
      sha256(actual.content) !== item.sha256
    )
      throw Error("Browser evidence bytes mismatch");
    supplied.set(item.path, item);
  }
  const references = [];
  for (const observation of report.observations) {
    references.push("screenshots/" + observation.screenshot);
    if (observation.fullScreenshot) references.push("screenshots/" + observation.fullScreenshot);
  }
  for (const story of report.stories)
    for (const sample of story.samples)
      if (sample.screenshot) references.push("screenshots/" + sample.screenshot);
  for (const disclosure of report.disclosures)
    for (const item of disclosure.results) references.push("screenshots/" + item.screenshot);
  for (const group of report.exports)
    for (const item of group.results)
      if (item.status !== "NOT_APPLICABLE") {
        portablePath(item.file);
        references.push(item.file);
        const identity = supplied.get(item.file);
        if (identity?.sha256 !== item.sha256 || identity?.bytes !== item.bytes)
          throw Error("Browser export identity mismatch");
      }
  for (const ref of references) portablePath(ref);
  const sorted = (a) => JSON.stringify([...a].sort());
  if (
    new Set(references).size !== references.length ||
    sorted(references) !== sorted([...supplied.keys()]) ||
    sorted(references) !== sorted(members.map((m) => m.path))
  )
    throw Error("Browser evidence coverage or output reuse");
  return {
    viewport,
    files: references.length,
    scope: "bounded-reported-browser-observations",
  };
}

/** Explicit reported-evidence intake. Authentic execution must be observed by the operator. */
export async function readEthosBrowserEvidence({ atlas, reports, checker }) {
  const target = await describeEthosBrowser(atlas);
  if (!Array.isArray(reports) || reports.length !== target.viewports.length)
    throw Error("Browser viewport coverage incomplete");
  const supplied = reports.map((r) => JSON.stringify(r.viewport)).sort(),
    expected = target.viewports.map((v) => JSON.stringify(v)).sort();
  if (JSON.stringify(supplied) !== JSON.stringify(expected))
    throw Error("Browser viewport coverage mismatch");
  if (
    !checker ||
    typeof checker.manifestPath !== "string" ||
    !path.isAbsolute(checker.manifestPath)
  )
    throw Error("Explicit checker source required");
  const selectedChecker = await readSourceBundle(checker.manifestPath, checker.sha256);
  target.checkerManifestSha256 = selectedChecker.manifestSha256;
  const results = [];
  for (const item of reports) {
    if (
      typeof item.manifestPath !== "string" ||
      !path.isAbsolute(item.manifestPath) ||
      typeof item.report !== "string"
    )
      throw Error("Explicit browser evidence paths required");
    portablePath(item.report);
    const bundle = await readSourceBundle(item.manifestPath, item.sha256);
    const member = bundle.members.find((m) => m.path === item.report);
    if (!member) throw Error("Browser report missing");
    const report = decodeBrowserReport(item.report, member.content);
    const observed = validateEthosBrowserReport(
      {
        report,
        members: bundle.members.filter((m) => m.path !== item.report),
      },
      target,
      item.viewport,
    );
    results.push({
      ...observed,
      manifestSha256: bundle.manifestSha256,
      reportSha256: sha256(member.content),
    });
  }
  return {
    scope: "bounded-reported-browser-observations",
    source: target.source,
    outputManifestSha256: target.outputManifestSha256,
    reports: results,
    checkerManifestSha256: target.checkerManifestSha256,
    executionAuthenticity: "requires-observed-run",
    semanticAcceptance: "not-performed",
    publicationAcceptance: "not-performed",
  };
}
