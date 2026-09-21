// Compose existing qualification owners; file installation is a separate effect.
import fs from "node:fs/promises";
import path from "node:path";
import { readSourceBundle } from "architecture-publisher/source";
import { readPublisherRuntime } from "architecture-publisher/runtime";
import { readEthosExtensionRuntime } from "../runtime.mjs";
import { readEthosAtlasOutput } from "./atlas-output.mjs";
import { readEthosReview } from "./review.mjs";
import { readStaticArtifact } from "./static-artifact.mjs";
import { readEthosBrowserEvidence } from "./browser.mjs";
import { sha256 } from "../adapter/projection.mjs";
import {
  planPairFiles,
  installPairFiles,
  recoverPairFiles,
  noLinks,
} from "architecture-publisher/publication";
import { exactFields, requireExplicitAcceptance } from "architecture-publisher/publication";
const encode = (value) => JSON.stringify(value, null, 2) + "\n";
const equal = (a, b, why) => {
  if (a !== b) throw Error(why);
};
const fields = (value, names) => exactFields(value, names, "Invalid publication plan fields");
function entry(medium) {
  const target =
    medium === "native" ? "terminal/native/terminal.html" : "atlas/index.html?theme=light";
  return `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=${target}"><title>ETHOS · 问道</title><p><a href="${target}">Open ETHOS architecture</a></p></html>\n`;
}

export async function planEthosPublication(input, replayPrestates) {
  fields(input, [
    "review",
    "staticArtifact",
    "browser",
    "deployment",
    ...(Object.hasOwn(input, "replacement") ? ["replacement"] : []),
  ]);
  fields(input.deployment, ["destinations", "recoveryRoot"]);
  fields(input.browser, ["reports", "checker"]);
  const review = await readEthosReview(input.review);
  const staticArtifact = await readStaticArtifact(input.staticArtifact, input.review.atlas, review);
  let browser;
  try {
    browser = await readEthosBrowserEvidence({
      atlas: input.review.atlas,
      ...input.browser,
    });
  } catch (error) {
    throw Object.assign(new Error(error.message), {
      code: "publication_browser_unqualified",
      cause: error,
    });
  }
  const atlas = await readEthosAtlasOutput(input.review.atlas);
  const dependencies = new Map(),
    payload = [],
    sourceRoots = new Set();
  function bind(file, digest) {
    const old = dependencies.get(file);
    if (old && old !== digest) throw Error("Conflicting selected dependency");
    dependencies.set(file, digest);
  }
  async function add(medium, source, target, digest) {
    await noLinks(source);
    const bytes = await fs.readFile(source);
    if (digest) equal(sha256(bytes), digest, "Publication payload drift");
    bind(source, sha256(bytes));
    payload.push({
      medium,
      source,
      path: target,
      bytes: bytes.length,
      sha256: sha256(bytes),
    });
  }
  async function bundle(manifestPath, digest) {
    const selected = await readSourceBundle(manifestPath, digest),
      root = path.dirname(manifestPath);
    sourceRoots.add(root);
    bind(manifestPath, digest);
    for (const m of selected.members) bind(path.join(root, m.path), m.sha256);
    return selected;
  }
  const atlasRoot = path.dirname(input.review.atlas.outputManifest);
  sourceRoots.add(atlasRoot);
  bind(input.review.atlas.outputManifest, atlas.manifestSha256);
  for (const member of atlas.members)
    await add("atlas", path.join(atlasRoot, member.path), "atlas/" + member.path, member.sha256);
  await add(
    "atlas",
    input.review.atlas.outputManifest,
    "atlas/manifest.json",
    atlas.manifestSha256,
  );
  const staticRoot = path.dirname(input.staticArtifact.manifestPath);
  await bundle(input.staticArtifact.manifestPath, input.staticArtifact.sha256);
  const staticReaderFiles = new Set([
    "native/terminal.html",
    "native/terminal.svg",
    ...[1600, 2400, 6000].map((width) => `native/terminal-${width}.png`),
  ]);
  for (const member of staticArtifact.members) {
    if (!staticReaderFiles.has(member.path)) continue;
    const target = "terminal/" + member.path;
    await add("native", path.join(staticRoot, member.path), target, member.sha256);
  }
  await bundle(input.review.atlas.sourceManifest, input.review.atlas.sourceSha256);
  await bundle(input.review.atlas.editionManifest, input.review.atlas.editionSha256);
  if (input.staticArtifact.poster)
    await bundle(
      input.staticArtifact.poster.editionManifest,
      input.staticArtifact.poster.editionSha256,
    );
  // Qualification remains bound at effect time, but is not reader content.
  for (const item of input.review.evidenceBundles) await bundle(item.manifestPath, item.sha256);
  await bundle(input.browser.checker.manifestPath, input.browser.checker.sha256);
  for (const item of input.browser.reports) await bundle(item.manifestPath, item.sha256);
  // Bind public runtime closures without knowing either package's layout.
  for (const member of [...(await readPublisherRuntime()), ...(await readEthosExtensionRuntime())])
    bind(member.file, member.sha256);
  const entries = Object.fromEntries(
    ["native", "atlas"].map((medium) => [
      medium,
      {
        "index.html": entry(medium),
        "README.md": `# ETHOS · 问道\n\nOpen index.html. ${medium === "native" ? "Static architecture" : "Interactive architecture atlas"}.\n\nSource commit: ${review.source.commit}\nProjection: ${review.source.digest}\n\nTarget architecture, not a claim of current implementation. Earlier content is preserved. Source history belongs in the project repositories, not this delivery directory.\n`,
      },
    ]),
  );
  const filePlan = await planPairFiles(
    {
      options: { sourceRoots: [...sourceRoots].sort(), ...input.deployment },
      source: review.source,
      payload,
      entries,
      ...(input.replacement ? { replacement: input.replacement } : {}),
      dependencies: [...dependencies]
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([file, sha256]) => ({ file, sha256 })),
    },
    replayPrestates,
  );
  const body = {
    schema: "architecture.ethos-pair-publication/v1",
    mode: "dry-run",
    input: structuredClone(input),
    filePlan,
    qualification: {
      review: {
        scope: review.scope,
        reviewSha256: review.reviewSha256,
        reviewBindingSha256: review.reviewBindingSha256,
        pages: review.pages,
        limits: review.notEstablished,
      },
      static: {
        scope: staticArtifact.scope,
        manifestSha256: staticArtifact.manifestSha256,
      },
      browser,
    },
    requires: { ownerAcceptance: true, observedBrowserRun: true },
    globalAtomicity: false,
  };
  return { ...body, sha256: sha256(encode(body)) };
}
function admitted(plan, acceptance) {
  const { sha256: digest, ...body } = plan;
  equal(sha256(encode(body)), digest, "Publication plan digest mismatch");
  if (plan.schema !== "architecture.ethos-pair-publication/v1")
    throw Error("Exact owner publication acceptance required");
  requireExplicitAcceptance(
    acceptance,
    digest,
    "ACCEPTED",
    "Exact owner publication acceptance required",
  );
  if (
    acceptance.authority?.kind !== "human_product_owner" ||
    acceptance.authority?.source !== "explicit_user_instruction" ||
    !acceptance.authority.statement
  )
    throw Error("Exact owner publication acceptance required");
  // This is an operator assertion with explicit identities, not cryptographic
  // browser authenticity. Never generate it from successful report parsing.
  const observed = acceptance.browserObservation;
  if (
    observed?.decision !== "OBSERVED" ||
    observed.outputManifestSha256 !== plan.qualification.browser.outputManifestSha256 ||
    observed.checkerManifestSha256 !== plan.qualification.browser.checkerManifestSha256 ||
    !Array.isArray(observed.reportSha256) ||
    JSON.stringify([...observed.reportSha256].sort()) !==
      JSON.stringify(plan.qualification.browser.reports.map((r) => r.reportSha256).sort()) ||
    typeof observed.evidenceRef !== "string" ||
    !observed.evidenceRef
  )
    throw Error("Exact observed browser execution reference required");
  return {
    decision: "AUTHORIZED",
    planSha256: plan.filePlan.sha256,
    publication: { planSha256: digest, acceptance },
  };
}
export async function publishEthosPublication(plan, acceptance) {
  const authorization = admitted(plan, acceptance),
    current = await planEthosPublication(plan.input, plan.filePlan.prestates);
  equal(current.sha256, plan.sha256, "Publication qualification changed");
  const result = await installPairFiles(current.filePlan, authorization);
  return {
    ...result,
    scope: "qualified-pair-publication",
    publicationPlanSha256: current.sha256,
  };
}
export async function recoverEthosPublication(plan, acceptance) {
  return recoverPairFiles(plan.filePlan, admitted(plan, acceptance));
}
