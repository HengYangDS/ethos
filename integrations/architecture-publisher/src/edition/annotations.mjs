import fs from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
const hash = (b) => createHash("sha256").update(b).digest("hex");

/** Presentation only. Endpoint shapes and declared boundaries remain intact. */
export function validateNativeAnnotations(spec, nodes, emphasisNodes = []) {
  if (
    spec.diagram_type !== "architecture" ||
    !Array.isArray(nodes) ||
    !nodes.length ||
    new Set(nodes).size !== nodes.length
  )
    throw Error("Distinct native annotation identities required");
  const byId = new Map(spec.components.map((n) => [n.id, n]));
  for (const id of nodes) {
    if (typeof id !== "string" || !byId.has(id)) throw Error("Unknown annotation node");
    if (spec.connections.some((e) => e.from === id || e.to === id))
      throw Error("An endpoint cannot become an unframed annotation");
    if ((spec.boundaries ?? []).some((b) => b.wraps.includes(id)))
      throw Error("A boundary member cannot become an unframed annotation");
  }
  if (
    !Array.isArray(emphasisNodes) ||
    new Set(emphasisNodes).size !== emphasisNodes.length ||
    emphasisNodes.some((id) => typeof id !== "string" || !byId.has(id) || nodes.includes(id))
  )
    throw Error("Distinct non-annotation emphasis identities required");
  return [...nodes];
}

/** Runs before native validate/deliver. No HTML rewrite, SVG shell or viewer code. */
export async function applyNativeAnnotations(
  toolRoot,
  spec,
  nodes,
  expectedDigest,
  { emphasisNodes = [] } = {},
) {
  const admitted = validateNativeAnnotations(spec, nodes, emphasisNodes);
  const file = path.join(toolRoot, "renderers/architecture/render-architecture.mjs"),
    before = await fs.readFile(file, "utf8");
  if (!/^[a-f0-9]{64}$/.test(expectedDigest ?? "") || hash(before) !== expectedDigest)
    throw Error("Unsupported annotation renderer digest");
  let after = before;
  const replace = (old, next) => {
    if (after.split(old).length !== 2) throw Error("Annotation renderer seam mismatch");
    after = after.replace(old, next);
  };
  replace(
    "function renderComponent(c) {",
    `const annotationNodes = new Set(${JSON.stringify(admitted)});\nfunction renderComponent(c) {`,
  );
  replace(
    "<g ${focusNodeAttrs(c.id, c.label, passport, arch.meta.locale)}>",
    "<g ${focusNodeAttrs(c.id, c.label, passport, arch.meta.locale)}${annotationNodes.has(c.id) ? ' data-native-presentation=\"annotation\"' : ''}>",
  );
  replace(
    'rx="6" class="c-mask"/>',
    'rx="6" class="c-mask"${annotationNodes.has(c.id) ? \' style="fill:transparent"\' : \'\'}/>',
  );
  replace(
    'stroke-width="1.5"/>\n          ${renderSemanticSigil(c.type, { x: c.x + 6, y: c.y + 6 })}',
    "stroke-width=\"1.5\"${annotationNodes.has(c.id) ? ' style=\"fill:none;stroke:none\"' : ''}/>\n          ${annotationNodes.has(c.id) ? '<!-- Native explanatory note -->' : renderSemanticSigil(c.type, { x: c.x + 6, y: c.y + 6 })}",
  );
  if (emphasisNodes.length) {
    // Reading priority only: retain endpoint geometry, semantic classes, text,
    // stroke width and native viewer behavior. No status color or new glyph.
    replace(
      "function renderComponent(c) {",
      `const readingEmphasis = new Set(${JSON.stringify(emphasisNodes)});\nfunction renderComponent(c) {`,
    );
    replace(
      "${annotationNodes.has(c.id) ? ' data-native-presentation=\"annotation\"' : ''}>",
      "${annotationNodes.has(c.id) ? ' data-native-presentation=\"annotation\"' : ' data-reading-emphasis=\"' + (readingEmphasis.has(c.id) ? 'primary' : 'secondary') + '\"'}>",
    );
    replace(
      "stroke-width=\"1.5\"${annotationNodes.has(c.id) ? ' style=\"fill:none;stroke:none\"' : ''}/>",
      'stroke-width="1.5"${annotationNodes.has(c.id) ? \' style="fill:none;stroke:none"\' : readingEmphasis.has(c.id) ? \' style="fill:var(--text);stroke:var(--text)"\' : \' style="fill:none;stroke:var(--text-muted)"\'}/>',
    );
    replace(
      '<text data-node-label=""',
      "<text${readingEmphasis.has(c.id) ? ' style=\"fill:var(--bg)\"' : ''} data-node-label=\"\"",
    );
    replace(
      'class="t-muted" font-size="${fittedNodeFontSize(c.sublabel',
      'class="t-muted"${readingEmphasis.has(c.id) ? \' style="fill:var(--bg)"\' : \'\'} font-size="${fittedNodeFontSize(c.sublabel',
    );
    replace(
      'class="${accent}" font-size="${fittedNodeFontSize(c.tag',
      'class="${accent}"${readingEmphasis.has(c.id) ? \' style="fill:var(--bg)"\' : \'\'} font-size="${fittedNodeFontSize(c.tag',
    );
  }
  await fs.writeFile(file, after);
  return {
    schema: "ethos.native-annotations/v1",
    nodes: admitted,
    ...(emphasisNodes.length
      ? {
          emphasisNodes: [...emphasisNodes],
          readingEmphasis:
            "Fill and ink hierarchy only; no semantic, authority or maturity classification.",
        }
      : {}),
    before: hash(before),
    after: hash(after),
    scope:
      "Remove frame paint and generic sigil from isolated notes; keep labels, geometry, focus target, node identities and native viewer unchanged.",
    browserAcceptance: "UNVERIFIED",
    perceptualAcceptance: "UNVERIFIED",
  };
}
