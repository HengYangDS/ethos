import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";

/** An explicit authoring budget, not a claim about a browser's actual scale. */
export function nativeTypography(contract, { viewBox, diagramArea, fit = "contain" }) {
  if (!["contain", "document-width"].includes(fit)) throw Error("Unsupported native reading fit");
  for (const pair of [viewBox, diagramArea]) {
    if (
      !Array.isArray(pair) ||
      pair.length !== 2 ||
      pair.some((n) => !Number.isFinite(n) || n <= 0)
    ) {
      throw Error("Positive viewBox and diagramArea dimensions are required");
    }
  }
  if (
    diagramArea[0] > contract.reference_viewport.width ||
    diagramArea[1] > contract.reference_viewport.height
  ) {
    throw Error("Diagram budget exceeds source reference viewport");
  }
  const minimumScale =
    fit === "document-width"
      ? diagramArea[0] / viewBox[0]
      : Math.min(diagramArea[0] / viewBox[0], diagramArea[1] / viewBox[1]);
  const context = Math.ceil(
    contract.hard_gates.typography_and_accessibility.effective_font_px_min_at_reference /
      minimumScale,
  );
  const innerPadding = Math.ceil(
    contract.hard_gates.geometry_each_scale.inside_glyph_to_owner_inner_stroke_px_at_reference_min /
      minimumScale,
  );
  return {
    status: "AUTHORING_BUDGET_NOT_BROWSER_MEASUREMENT",
    viewBox,
    diagramArea,
    minimumScale,
    fit,
    declaredDocumentHeight: viewBox[1] * minimumScale,
    context,
    primary: Math.ceil(context * 1.2),
    edge: context,
    innerPadding,
    edgeMaskTop: context,
    edgeMaskHeight: Math.ceil(context * 1.5),
  };
}

/** Patches only the pinned ephemeral native renderer; native routes and viewer
 * remain upstream-owned. Footprints and text change together BEFORE validate. */
export async function applyNativeTypography(toolRoot, contract, budget) {
  const typography = nativeTypography(contract, budget);
  const file = path.join(toolRoot, "renderers/architecture/render-architecture.mjs");
  const fitFile = path.join(toolRoot, "renderers/shared/text-fit.mjs");
  const markerFile = path.join(toolRoot, "renderers/shared/utils.mjs");
  const before = await readFile(file, "utf8"),
    beforeFit = await readFile(fitFile, "utf8");
  const hash = (text) => createHash("sha256").update(text).digest("hex");
  if (hash(before) !== "f57077cb9fa64a8412ab0af705cb31e2e7a920114b31852882c04a76840365dc") {
    throw Error("Unsupported native renderer digest; review the upstream change before adapting");
  }
  if (hash(beforeFit) !== "35b6ef2c64d88c1ea4e5aab2af7c4e8a2c2e1be62db71263787d39a9797e7dea") {
    throw Error("Unsupported native text-fit digest; review the upstream change before adapting");
  }
  const beforeMarkers = await readFile(markerFile, "utf8");
  if (hash(beforeMarkers) !== "20124265300eb286db184a053561005cc32b6128dc1bc1b3f9520ffa8d43a241") {
    throw Error("Unsupported native marker owner digest");
  }
  // Polygon tip and route anchor coincide for every stroke width and variant.
  const markers = replaceCount(
    beforeMarkers,
    'refX="9"',
    'refX="10"',
    "exact marker tip anchor",
    4,
  );
  let source = before;
  for (const [key, value] of [
    ["boundaryLabelFontPreferred", 9],
    ["boundaryLabelFontMinimum", 6],
  ]) {
    source = replaceExactly(source, `${key}: ${value},`, `${key}: ${typography.context},`, key);
  }
  const boundaryPadding =
    typography.innerPadding +
    Math.ceil(
      typography.context * contract.hard_gates.geometry_each_scale.font_height_growth_fraction,
    ) +
    1;
  source = replaceExactly(
    source,
    "boundaryLabelClearance: 4,",
    `boundaryLabelClearance: ${boundaryPadding},`,
    "boundary inner text clearance",
  );
  // Boundary titles are start-anchored. Their growth reserve must precede the
  // first glyph, not merely increase the mask width to its right. Expand the
  // measured title rail before native validation; never cover a frame later.
  const frameLabelX =
    typography.innerPadding +
    Math.ceil(
      typography.context * contract.hard_gates.geometry_each_scale.font_width_growth_fraction,
    ) +
    1;
  source = replaceExactly(
    source,
    "boundaryLabelFrameInset: 4,",
    `boundaryLabelFrameInset: ${frameLabelX},`,
    "boundary title frame clearance",
  );
  source = replaceExactly(
    source,
    "function boundaryLabelWidth(label, fontSize) {\n  return Math.max(30, textUnits(label) * fontSize * 0.6 + 10);\n}",
    `function boundaryTitleReserve(label, fontSize) {\n  return Math.ceil(textUnits(label) * fontSize * 0.6 * ${contract.hard_gates.geometry_each_scale.font_width_growth_fraction} / 2);\n}\nfunction boundaryLabelWidth(label, fontSize) {\n  return Math.max(30, textUnits(label) * fontSize * 0.6 + 10 + 2 * boundaryTitleReserve(label, fontSize));\n}`,
    "boundary glyph growth reserve",
  );
  source = replaceExactly(
    source,
    "(availableWidth - 10) / (units * 0.6)",
    `(availableWidth - 10) / (units * 0.6 * ${1 + contract.hard_gates.geometry_each_scale.font_width_growth_fraction})`,
    "boundary fitting growth",
  );
  source = replaceExactly(
    source,
    "baselineOffset: fontSize + 4,",
    "baselineOffset: fontSize + 4,\n    glyphReserve: boundaryTitleReserve(boundary.label, fontSize),",
    "boundary title reserve field",
  );
  source = replaceExactly(
    source,
    "${b.title.x + 4}",
    "${b.title.x + 4 + b.title.glyphReserve}",
    "boundary title glyph origin",
  );
  source = replaceExactly(
    source,
    "const componentTextFit = {",
    `const nativeType = ${JSON.stringify(typography)};\nconst componentTextFit = {`,
    "native type declaration",
  );
  for (const [key, value] of [
    ["sublabelPreferred", 9],
    ["sublabelMinimum", 6],
    ["tagPreferred", 7],
    ["tagMinimum", 6],
  ]) {
    source = replaceExactly(source, `${key}: ${value},`, `${key}: nativeType.context,`, key);
  }
  source = replaceExactly(
    source,
    "textUnits(c.label) * 6.6",
    "textUnits(c.label) * nativeType.primary * 0.6",
    "primary measured width",
  );
  source = replaceExactly(
    source,
    "estLabelW > c.width + 8",
    "estLabelW > availableNodeTextWidth(c.width)",
    "primary inner clearance",
  );
  source = replaceCount(
    source,
    "textUnits(conn.label) * 4.8 + 10",
    "textUnits(conn.label) * nativeType.edge * 0.6 + 2 * nativeType.innerPadding",
    "edge footprint",
    3,
  );
  source = replaceExactly(
    source,
    "textUnits(connection.label) * 4.8 + 10",
    "textUnits(connection.label) * nativeType.edge * 0.6 + 2 * nativeType.innerPadding",
    "legend edge footprint",
  );
  source = replaceExactly(
    source,
    "y: ly - 10, width: w, height: 14, lx, ly",
    "y: ly - nativeType.edgeMaskTop, width: w, height: nativeType.edgeMaskHeight, lx, ly",
    "validation label height",
  );
  source = replaceExactly(
    source,
    "y: Math.round(ly - 10),\n      width: Math.round(w),\n      height: 14,",
    "y: Math.round(ly - nativeType.edgeMaskTop),\n      width: Math.round(w),\n      height: nativeType.edgeMaskHeight,",
    "layout report label height",
  );
  source = replaceExactly(
    source,
    'y="${ly - 10}" width="${w}" height="14"',
    'y="${ly - nativeType.edgeMaskTop}" width="${w}" height="${nativeType.edgeMaskHeight}"',
    "rendered label height",
  );
  source = replaceExactly(
    source,
    "y: y - 10, width, height: 14",
    "y: y - nativeType.edgeMaskTop, width, height: nativeType.edgeMaskHeight",
    "legend label height",
  );
  source = replaceExactly(
    source,
    'font-size="8" text-anchor="middle">${esc(conn.label)}</text>',
    'font-size="${nativeType.edge}" text-anchor="middle">${esc(conn.label)}</text>',
    "rendered edge font",
  );
  source = replaceExactly(
    source,
    "fittedNodeFontSize(c.label, brandLabelFitWidth(c, c.width), 11, 8)",
    "fittedNodeFontSize(c.label, brandLabelFitWidth(c, c.width), nativeType.primary, nativeType.primary)",
    "rendered primary font",
  );
  source = replaceExactly(
    source,
    "const labelY = hasSub ? c.y + c.height / 2 - 2 : c.y + c.height / 2 + 4;",
    "const labelY = hasSub ? c.y + c.height / 2 - nativeType.context * (c.tag ? 0.9 : 0.25) : c.y + c.height / 2 + nativeType.primary * 0.3;",
    "primary baseline",
  );
  source = replaceExactly(
    source,
    "${c.y + c.height / 2 + 14}",
    "${c.y + c.height / 2 + nativeType.context * (c.tag ? 0.55 : 1.2)}",
    "context baseline",
  );
  source = replaceExactly(
    source,
    "${c.y + c.height - 8}",
    "${c.y + c.height / 2 + nativeType.context * 2}",
    "tag baseline",
  );
  if (typography.fit === "document-width") {
    source = replaceExactly(
      source,
      '<text data-detail="fine"',
      '<text data-detail="context"',
      "load-bearing publication tag visibility",
    );
  }
  const fit = replaceExactly(
    beforeFit,
    "horizontalPadding: 8,",
    `horizontalPadding: ${2 * typography.innerPadding},`,
    "node inner padding",
  );
  // No file is written unless every exact replacement above has succeeded.
  await writeFile(file, source);
  await writeFile(fitFile, fit);
  await writeFile(markerFile, markers);
  return {
    schema: "ethos.native-typography/v1",
    typography,
    scope: "Native architecture font/label footprint adaptation; no semantic or browser acceptance",
    patchedFiles: [
      {
        path: path.relative(toolRoot, file),
        before: hash(before),
        after: hash(source),
      },
      {
        path: path.relative(toolRoot, fitFile),
        before: hash(beforeFit),
        after: hash(fit),
      },
      {
        path: path.relative(toolRoot, markerFile),
        before: hash(beforeMarkers),
        after: hash(markers),
      },
    ],
  };
}
function replaceExactly(source, before, after, label) {
  const occurrences = source.split(before).length - 1;
  if (occurrences !== 1)
    throw new Error(`Renderer adapter expected one ${label}, observed ${occurrences}.`);
  return source.replace(before, after);
}

function replaceCount(source, before, after, label, expected) {
  const occurrences = source.split(before).length - 1;
  if (occurrences !== expected)
    throw new Error(`Renderer adapter expected ${expected} ${label}, observed ${occurrences}.`);
  return source.replaceAll(before, after);
}
