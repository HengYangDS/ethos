import path from "node:path";
import { noSymlinkAncestors, regularBytes } from "architecture-publisher/source";

function fail(code) {
  throw Object.assign(new Error(code), { code });
}

async function selectedJson(file, code, maximum = 4 * 1024 * 1024) {
  const selected = path.resolve(file);
  await noSymlinkAncestors(selected);
  const bytes = await regularBytes(selected, maximum);
  try {
    return {
      base: path.dirname(selected),
      value: JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes)),
    };
  } catch {
    fail(code);
  }
}

function resolveField(object, key, base, code) {
  if (typeof object?.[key] !== "string" || !object[key]) fail(code);
  object[key] = path.resolve(base, object[key]);
}

export async function renderEthosAtlasInput(file) {
  const { base, value: plan } = await selectedJson(file, "atlas_plan_invalid");
  for (const key of ["sourceManifest", "editionManifest", "output"])
    resolveField(plan, key, base, "atlas_plan_invalid");
  const { renderEthosAtlas } = await import("./atlas.mjs");
  return renderEthosAtlas(plan);
}

export async function readEthosAtlasOutputInput(file) {
  const { base, value: plan } = await selectedJson(file, "atlas_plan_invalid");
  for (const key of ["sourceManifest", "editionManifest", "outputManifest"])
    resolveField(plan, key, base, "atlas_plan_invalid");
  const { readEthosAtlasOutput } = await import("./atlas-output.mjs");
  const result = await readEthosAtlasOutput(plan);
  return {
    status: "verified",
    ...result,
    members: result.members.map(({ content, ...member }) => member),
  };
}

export async function prepareEthosCandidateInput(file) {
  const { base, value: plan } = await selectedJson(file, "candidate_plan_invalid");
  resolveField(plan, "output", base, "candidate_plan_invalid");
  resolveField(plan, "authoring", base, "candidate_plan_invalid");
  for (const selection of [plan.source, plan.previous])
    resolveField(selection, "sourceManifest", base, "candidate_plan_invalid");
  resolveField(plan.previous, "editionManifest", base, "candidate_plan_invalid");
  const { prepareEthosCandidate } = await import("./candidate.mjs");
  return prepareEthosCandidate(plan);
}

export async function renderStandaloneAtlasInput(file) {
  const { base, value: plan } = await selectedJson(file, "atlas_plan_invalid");
  resolveField(plan, "output", base, "atlas_plan_invalid");
  for (const key of ["sourceManifest", "editionManifest", "outputManifest"])
    resolveField(plan.atlas, key, base, "atlas_plan_invalid");
  const { renderStandaloneAtlas } = await import("./standalone.mjs");
  return renderStandaloneAtlas(plan);
}

export async function describeEthosBrowserInput(file) {
  const { base, value: plan } = await selectedJson(file, "atlas_plan_invalid");
  for (const key of ["sourceManifest", "editionManifest", "outputManifest"])
    resolveField(plan, key, base, "atlas_plan_invalid");
  const { describeEthosBrowser } = await import("./browser.mjs");
  return describeEthosBrowser(plan);
}

export async function readEthosReviewInput(file) {
  const { base, value: plan } = await selectedJson(file, "review_inputs_invalid");
  for (const key of ["sourceManifest", "editionManifest", "outputManifest"])
    resolveField(plan.atlas, key, base, "review_path_required");
  if (!Array.isArray(plan.evidenceBundles)) fail("review_inputs_invalid");
  for (const bundle of plan.evidenceBundles)
    resolveField(bundle, "manifestPath", base, "review_path_required");
  const { readEthosReview } = await import("./review.mjs");
  return readEthosReview(plan);
}

export async function renderEthosPosterInput(file) {
  const { base, value: plan } = await selectedJson(file, "poster_plan_invalid");
  for (const key of ["sourceManifest", "editionManifest", "output"])
    resolveField(plan, key, base, "poster_plan_invalid");
  const { renderEthosPoster } = await import("./poster.mjs");
  return renderEthosPoster(plan);
}

export async function outlineEthosPosterInput(file) {
  const { base, value: plan } = await selectedJson(file, "outline_plan_invalid");
  resolveField(plan, "output", base, "outline_plan_invalid");
  for (const key of ["sourceManifest", "editionManifest"])
    resolveField(plan.poster, key, base, "outline_plan_invalid");
  for (const key of ["renderer", "fontList"])
    resolveField(plan[key], "path", base, "outline_plan_invalid");
  if (!Array.isArray(plan.fonts)) fail("outline_plan_invalid");
  for (const font of plan.fonts) resolveField(font, "path", base, "outline_plan_invalid");
  const { outlineEthosPoster } = await import("./outline.mjs");
  return outlineEthosPoster(plan);
}

export async function planEthosPublicationInput(file) {
  const { base, value: plan } = await selectedJson(file, "publication_input_invalid");
  for (const key of ["sourceManifest", "editionManifest", "outputManifest"])
    resolveField(plan.review?.atlas, key, base, "publication_path_required");
  if (!Array.isArray(plan.review?.evidenceBundles) || !Array.isArray(plan.browser?.reports))
    fail("publication_input_invalid");
  for (const bundle of plan.review.evidenceBundles)
    resolveField(bundle, "manifestPath", base, "publication_path_required");
  resolveField(plan.staticArtifact, "manifestPath", base, "publication_path_required");
  if (plan.staticArtifact.poster)
    for (const key of ["sourceManifest", "editionManifest"])
      resolveField(plan.staticArtifact.poster, key, base, "publication_path_required");
  if (plan.browser.checker)
    resolveField(plan.browser.checker, "manifestPath", base, "publication_path_required");
  for (const report of plan.browser.reports)
    resolveField(report, "manifestPath", base, "publication_path_required");
  for (const key of ["native", "atlas"])
    resolveField(plan.deployment?.destinations, key, base, "publication_path_required");
  resolveField(plan.deployment, "recoveryRoot", base, "publication_path_required");
  const { planEthosPublication } = await import("./publication.mjs");
  return planEthosPublication(plan);
}

async function publicationEffectInput(operation, planFile, acceptanceFile) {
  const plan = (await selectedJson(planFile, "publication_input_invalid")).value;
  const acceptance = (await selectedJson(acceptanceFile, "publication_input_invalid")).value;
  const { publishEthosPublication, recoverEthosPublication } = await import("./publication.mjs");
  return operation === "apply"
    ? publishEthosPublication(plan, acceptance)
    : recoverEthosPublication(plan, acceptance);
}

export const publishEthosPublicationInput = (planFile, acceptanceFile) =>
  publicationEffectInput("apply", planFile, acceptanceFile);

export const recoverEthosPublicationInput = (planFile, acceptanceFile) =>
  publicationEffectInput("recover", planFile, acceptanceFile);
