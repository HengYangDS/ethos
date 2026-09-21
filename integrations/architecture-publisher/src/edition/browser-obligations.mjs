// Exact generated-document obligations, not a general HTML conformance parser.
// Reading this module never launches a browser or grants visual acceptance.
import { viewportFindings, storyFindings } from "./browser-viewport.mjs";

export const ATLAS_VIEWPORTS = Object.freeze(
  [
    [1440, 900],
    [1600, 900],
    [1920, 1080],
    [2048, 1320],
  ].map(Object.freeze),
);
export const ATLAS_EXPORTS = Object.freeze([
  "svg",
  "png",
  "jpeg",
  "webp",
  "share-card",
  "webm",
  "route",
  "reach",
]);
/** @internal Development observer vocabulary; not an installed-runtime API. */
export const ATLAS_DISCLOSURES =
  ".container > [data-resource-comparison] details,.container > [data-write-boundary] details,.container > [data-verification-details] details";
const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const array = (x) => (Array.isArray(x) ? x : []);
const clean = (x) => Array.isArray(x) && x.length === 0;
const identifier = (x) => typeof x === "string" && /^[A-Za-z0-9_-]+$/.test(x);
const digest = (x) => typeof x === "string" && /^[a-f0-9]{64}$/.test(x);
const uniqueSet = (a, b) => a.length === new Set(a).size && equal([...a].sort(), [...b].sort());

export function derivePageObligations(html) {
  if (typeof html !== "string" || html.length > 16 * 1024 * 1024)
    throw Error("Invalid selected HTML");
  const scripts = [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi)];
  const selected = scripts.filter((m) =>
    /\bid\s*=\s*["']archify-guided-views-data["']/i.test(m[1]),
  );
  if (selected.length !== 1) throw Error("One unique guided-view document required");
  const views = JSON.parse(selected[0][2]);
  if (!Array.isArray(views) || !views.length || views.length > 100)
    throw Error("Invalid guided-view chapters");
  const markup = html
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1\s*>/gi, "");
  const nodeIds = [...markup.matchAll(/\bdata-node-id\s*=\s*["']([^"']+)["']/g)].map((m) => m[1]);
  if (!nodeIds.length || new Set(nodeIds).size !== nodeIds.length)
    throw Error("Unique diagram node bindings required");
  const nodes = new Set(nodeIds),
    chapters = new Set(),
    beats = [];
  for (const view of views) {
    if (
      !identifier(view?.id) ||
      chapters.has(view.id) ||
      !Array.isArray(view.focus) ||
      !view.focus.length ||
      view.focus.length > 1000
    )
      throw Error("Invalid or duplicate story chapter");
    chapters.add(view.id);
    view.focus.forEach((nodeId, index) => {
      if (!nodes.has(nodeId)) throw Error("Story focus node binding missing");
      beats.push({ chapter: view.id, nodeId, index });
    });
  }
  const svgs = [...markup.matchAll(/<svg\b([^>]*)>/g)].filter((m) =>
    /\brole=["']img["']/.test(m[1]),
  );
  if (svgs.length !== 1) throw Error("One diagram SVG required");
  const sections = [];
  let disclosureCount = 0;
  for (const tag of markup.matchAll(/<\/?(?:section|details)\b[^>]*>/g)) {
    if (/^<section\b/.test(tag[0]))
      sections.push(
        Boolean(sections.at(-1)) ||
          /\bdata-(?:resource-comparison|write-boundary|verification-details)(?:\s|=|>)/.test(
            tag[0],
          ),
      );
    else if (/^<\/section\b/.test(tag[0])) {
      if (!sections.length) throw Error("Unbalanced authored sections");
      sections.pop();
    } else if (/^<details\b/.test(tag[0]) && sections.at(-1)) disclosureCount++;
  }
  if (sections.length) throw Error("Unbalanced authored sections");
  return {
    beats,
    disclosureCount,
    trace: /\bdata-animation=["']trace["']/.test(svgs[0][1]),
    nodeIds,
  };
}

export function browserCoverageGaps(report, pages, viewport, typography) {
  const gaps = [],
    add = (x) => gaps.push(x),
    key = (v) => `${v?.width}x${v?.height}`,
    expectedKey = viewport.join("x");
  if (!report || typeof report !== "object") return ["browser_report_missing"];
  if (Object.hasOwn(report, "fixtureOnly") || Object.hasOwn(report, "synthetic"))
    add("browser_synthetic_evidence");
  if (
    report.status !== "PASS_BOUNDED" ||
    report.scenario !== "story" ||
    report.browserClosed !== true ||
    typeof report.browserVersion !== "string" ||
    !report.browserVersion ||
    !clean(report.errors)
  )
    add("browser_execution_incomplete");
  if (!equal(report.viewports, [viewport])) add("browser_viewport_mismatch");
  if (
    !uniqueSet(
      array(report.pages).map((p) => p.id),
      pages.map((p) => p.id),
    )
  )
    add("browser_page_coverage");
  for (const p of pages) {
    const actual = array(report.pages).find((x) => x.id === p.id);
    if (actual?.path !== p.path || actual?.htmlSha256 !== p.htmlSha256)
      add("browser_page_identity:" + p.id);
  }
  const pairs = pages.flatMap((p) => ["document", "present"].map((state) => p.id + "/" + state));
  if (
    !uniqueSet(
      array(report.observations).map((r) => r.page + "/" + r.state),
      pairs,
    )
  )
    add("browser_observation_coverage");
  if (
    !uniqueSet(
      array(report.stories).map((r) => r.page + "/" + r.state),
      pairs,
    )
  )
    add("browser_story_coverage");
  function measured(value, kind, label) {
    try {
      if ((kind === "story" ? storyFindings : viewportFindings)(value, typography).length)
        add(label);
    } catch {
      add(label + ":missing_measurement");
    }
  }
  for (const observation of array(report.observations)) {
    const p = pages.find((x) => x.id === observation.page);
    if (
      !p ||
      observation.htmlSha256 !== p.htmlSha256 ||
      key(observation.viewport) !== expectedKey ||
      key(observation.measured?.viewport) !== expectedKey ||
      !clean(observation.findings)
    )
      add("browser_observation_identity");
    measured(observation.measured, "viewport", "browser_observation_layout");
    if (!observation.screenshot) add("browser_observation_screenshot");
  }
  for (const story of array(report.stories)) {
    const p = pages.find((x) => x.id === story.page),
      expected = p?.obligations.beats;
    if (
      !expected ||
      key(story.viewport) !== expectedKey ||
      !clean(story.findings) ||
      !equal(story.expected, expected) ||
      !equal(story.seen, expected)
    )
      add("browser_story_beat_order");
    const samples = array(story.samples);
    if (
      !equal(
        samples.map((s) => ({
          chapter: s.chapter,
          nodeId: s.beat?.nodeId,
          index: s.beat?.index,
        })),
        expected,
      )
    )
      add("browser_story_sample_coverage");
    for (const s of samples) {
      if (
        !clean(s.findings) ||
        s.measured?.story?.nodeId !== s.beat?.nodeId ||
        key(s.measured?.viewport) !== expectedKey
      )
        add("browser_story_sample_identity");
      measured(s.measured, "story", "browser_story_layout");
    }
    if (
      !(story.durationMs > 0) ||
      story.replay?.chapter !== expected?.[0]?.chapter ||
      story.replay?.beat?.index !== 0 ||
      story.replay?.playing !== true ||
      story.paused?.playing !== false ||
      story.retained?.playing !== false ||
      !equal(story.paused?.beat, story.retained?.beat) ||
      story.resumed !== true
    )
      add("browser_story_controls");
    measured(story.reset, "viewport", "browser_story_reset");
  }
  for (const name of ["exports", "disclosures"])
    if (
      !uniqueSet(
        array(report[name]).map((r) => r.page),
        pages.map((p) => p.id),
      )
    )
      add("browser_" + name + "_coverage");
  for (const group of array(report.exports)) {
    const p = pages.find((x) => x.id === group.page);
    if (
      !p ||
      key(group.viewport) !== expectedKey ||
      !uniqueSet(
        array(group.results).map((x) => x.format),
        ATLAS_EXPORTS,
      )
    )
      add("browser_export_formats");
    for (const item of array(group.results)) {
      if (item.status === "NOT_APPLICABLE") {
        if (
          item.format !== "webm" ||
          p?.obligations.trace ||
          item.capability?.animation === "trace" ||
          !item.reason
        )
          add("browser_export_invalid_exemption");
        continue;
      }
      if (
        !digest(item.sha256) ||
        !Number.isSafeInteger(item.bytes) ||
        item.bytes < 1 ||
        typeof item.file !== "string"
      )
        add("browser_export_bytes");
      const variant = ["route", "reach"].includes(item.format),
        r = item.receipt;
      if (
        !r ||
        r["data-last-export-error"] ||
        Number(r["data-last-export-bytes"]) !== item.bytes ||
        r["data-last-export-canonical"] !== (variant ? "false" : "true") ||
        (variant && r["data-last-export-" + item.format + "-state-clean"] !== "true")
      )
        add("browser_export_receipt");
      if (item.format === "svg") {
        if (
          !array(item.content?.original).length ||
          !equal(item.content?.original, item.content?.exported)
        )
          add("browser_export_svg_content");
      } else if (
        item.format !== "webm" &&
        (!(item.content?.width > 0) ||
          !(item.content?.height > 0) ||
          !(item.content?.luminanceRange >= 10))
      )
        add("browser_export_raster_content");
    }
  }
  for (const group of array(report.disclosures)) {
    const p = pages.find((x) => x.id === group.page);
    if (
      !p ||
      key(group.viewport) !== expectedKey ||
      !uniqueSet(
        array(group.results).map((x) => x.index),
        Array.from({ length: p?.obligations.disclosureCount ?? 0 }, (_, i) => i),
      )
    )
      add("browser_disclosure_coverage");
    for (const item of array(group.results)) {
      if (!clean(item.findings) || !item.screenshot) add("browser_disclosure_observation");
      measured(item.measured, "viewport", "browser_disclosure_layout");
    }
  }
  return [...new Set(gaps)];
}

/** @internal Development observer identity; not an installed-runtime API. */
export function observationName({ page, htmlSha256, viewport, state, part }) {
  if (
    !identifier(page) ||
    !digest(htmlSha256) ||
    !Array.isArray(viewport) ||
    viewport.length !== 2 ||
    viewport.some((x) => !Number.isSafeInteger(x) || x < 1) ||
    !identifier(state) ||
    !identifier(part)
  )
    throw Error("Invalid observation identity");
  return `${page}-${htmlSha256.slice(0, 16)}-${viewport.join("x")}-${state}-${part}`;
}
