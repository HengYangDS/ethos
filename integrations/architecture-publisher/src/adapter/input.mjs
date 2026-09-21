import path from "node:path";
import { noSymlinkAncestors, regularBytes } from "architecture-publisher/source";

function fail(code) {
  throw Object.assign(new Error(code), { code });
}

async function selectedJson(file, code) {
  const selected = path.resolve(file);
  await noSymlinkAncestors(selected);
  const bytes = await regularBytes(selected, 1024 * 1024);
  try {
    return {
      base: path.dirname(selected),
      value: JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)),
    };
  } catch {
    fail(code);
  }
}

/** Verify one explicitly selected ETHOS projection without returning source bytes. */
export async function verifyEthosSourceInput(manifestPath, expectedSha256, projectionDigest) {
  const { readEthosSource } = await import("./projection.mjs");
  const value = await readEthosSource(manifestPath, expectedSha256, projectionDigest);
  return {
    status: "verified",
    source: value.projection.source,
    projectionDigest: value.projection.digest,
    manifestSha256: value.manifestSha256,
    scope: value.scope,
    officialReplay: value.officialReplay,
    semanticAcceptance: value.semanticAcceptance,
  };
}

/** Resolve one explicit import request relative to its own descriptor. */
export async function importEthosSourceInput(file) {
  const { base, value: plan } = await selectedJson(file, "import_plan_invalid");
  for (const key of ["repository", "output", "git", "python"]) {
    if (typeof plan?.[key] !== "string" || !plan[key]) fail("import_plan_invalid");
    plan[key] = path.resolve(base, plan[key]);
  }
  const { importEthosSource } = await import("./import.mjs");
  return { status: "imported", ...(await importEthosSource(plan)) };
}
