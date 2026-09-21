import fs from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
import { validateProjectionEnvelope } from "../adapter/projection.mjs";
const hash = (b) => createHash("sha256").update(b).digest("hex");
const RENDERER = "renderers/architecture/render-architecture.mjs",
  CLI = "renderers/shared/cli.mjs",
  TEMPLATE = "assets/template.html";

/** Rebuildable inspection metadata. A renderer type never supplies product meaning. */
export function deriveNativeSemanticPassport(spec, bindings, raw) {
  const input = validateProjectionEnvelope(raw, raw?.digest);
  if (
    spec.diagram_type !== "architecture" ||
    !Array.isArray(spec.components) ||
    !spec.components.length
  )
    throw Error("Architecture components required");
  if (
    bindings.sourceDigest !== input.digest ||
    bindings.sourceRevision !== input.source.git.commit ||
    bindings.effectAuthority !== false
  )
    throw Error("Passport source or authority mismatch");
  const ids = spec.components.map((n) => n.id);
  if (
    new Set(ids).size !== ids.length ||
    Object.keys(bindings.nodes ?? {}).length !== ids.length ||
    Object.keys(bindings.nodes ?? {}).some((id) => !ids.includes(id))
  )
    throw Error("Exact component binding set required");
  const nodes = Object.fromEntries(
    spec.components.map((n) => {
      const refs = bindings.nodes[n.id];
      if (!Array.isArray(refs) || !refs.length || new Set(refs).size !== refs.length)
        throw Error("Distinct source entities required: " + n.id);
      const entities = refs.map((id) => {
        const entity = input.semantics.nodes[id];
        if (!entity) throw Error("Unknown source entity: " + id);
        const { label, kind, attributes } = entity;
        if (typeof label !== "string" || !label.trim() || !/^[-a-z0-9_]+$/.test(kind ?? ""))
          throw Error("Explicit source label and kind required");
        return { id, label, kind, maturity: attributes.maturity };
      });
      const kinds = [...new Set(entities.map((e) => e.kind))];
      return [
        n.id,
        {
          rendererKind: n.type,
          kind: kinds.length === 1 ? kinds[0] : "visual-aggregate",
          representation: entities.length === 1 ? "source-entity" : "visual-aggregate",
          entities,
        },
      ];
    }),
  );
  return {
    sourceRevision: input.source.git.commit,
    sourceDigest: input.digest,
    nodes,
    effectAuthority: false,
    semanticAcceptance: "UNVERIFIED",
  };
}

/** Patch frozen upstream seams before native validation; no post-delivery DOM rewrite. */
export async function applyNativeSemanticPassport(toolRoot, passport, expected) {
  const names = [RENDERER, CLI, TEMPLATE],
    before = Object.fromEntries(
      await Promise.all(
        names.map(async (n) => [n, await fs.readFile(path.join(toolRoot, n), "utf8")]),
      ),
    );
  for (const name of names)
    if (!/^[a-f0-9]{64}$/.test(expected?.[name] ?? "") || hash(before[name]) !== expected[name])
      throw Error("Semantic passport digest mismatch: " + name);
  if (passport.effectAuthority !== false || !passport.nodes || !Object.keys(passport.nodes).length)
    throw Error("Derived passport required");
  const after = { ...before };
  const replace = (file, old, next) => {
    if (after[file].split(old).length !== 2)
      throw Error("Semantic passport seam mismatch: " + file);
    after[file] = after[file].replace(old, next);
  };
  const literal = JSON.stringify(passport.nodes).replaceAll("<", "\\u003c");
  replace(
    RENDERER,
    "function renderComponent(c) {",
    `const nativeSemanticPassport = ${literal};\nfunction renderComponent(c) {\n  const semantic = nativeSemanticPassport[c.id];\n  if (!semantic) throw Error('Missing exact semantic passport: ' + c.id);`,
  );
  replace(
    RENDERER,
    "return scopes.length ? scopes.join(' › ') : i18nText(arch.meta.locale, 'node.context.architecture');",
    "return scopes.length ? scopes.join(' › ') : '';",
  );
  replace(
    RENDERER,
    "const passport = { kind: c.type, sublabel: c.sublabel, tag: c.tag, context: componentContext(c), ...brandMetadataFor(c) };",
    "const passport = { kind: semantic.kind, representation: semantic.representation, sourceEntities: JSON.stringify(semantic.entities), sublabel: c.sublabel, tag: c.tag, context: [componentContext(c), semantic.representation === 'visual-aggregate' && semantic.kind !== 'visual-aggregate' ? 'Visual aggregate' : ''].filter(Boolean).join(' · '), ...brandMetadataFor(c) };",
  );
  // This is an unbound external-system icon, not a product entity or edge.
  // No replacement ornament is introduced. Native geometry and focus targets remain.
  replace(RENDERER, "renderSemanticSigil(c.type, { x: c.x + 6, y: c.y + 6 })", "''");
  replace(
    CLI,
    "    ['data-node-kind', metadata.kind],",
    "    ['data-node-kind', metadata.kind],\n    ['data-node-representation', metadata.representation],\n    ['data-node-source-entities', metadata.sourceEntities],",
  );
  replace(
    CLI,
    "const detail = [metadata.sublabel, metadata.context, metadata.brand]",
    "const detail = [String(metadata.kind || '').replace(/[-_]+/g, ' '), metadata.sublabel, metadata.context, metadata.brand]",
  );
  const sourceDetails = `            <details id="focus-source-entities" class="semantic-source-entities" hidden>
              <summary>Source entities</summary>
              <p>Source declarations; not implementation evidence.</p>
              <dl id="focus-source-entities-list"></dl>
            </details>
`;
  replace(
    TEMPLATE,
    '            <span class="relationship-lens-summary" id="focus-summary" aria-live="polite"></span>',
    sourceDetails +
      '            <span class="relationship-lens-summary" id="focus-summary" aria-live="polite"></span>',
  );
  replace(
    TEMPLATE,
    "      function renderPassport(id, node) {",
    `      function renderBoundEntities(node) {
        var panel = document.getElementById('focus-source-entities');
        var list = document.getElementById('focus-source-entities-list');
        list.replaceChildren(); panel.open = false; panel.hidden = true;
        var entities;
        try { entities = JSON.parse(node.getAttribute('data-node-source-entities') || '[]'); } catch (_) { return; }
        if (!Array.isArray(entities) || !entities.length) return;
        entities.forEach(function (entity) {
          var term = document.createElement('dt');
          term.textContent = entity.label;
          var definition = document.createElement('dd');
          var identifier = document.createElement('code');
          identifier.textContent = entity.id;
          var facts = document.createElement('span');
          facts.textContent = 'Type: ' + viewerKindLabel(entity.kind) + '; declaration: ' + (entity.maturity || 'unspecified');
          definition.appendChild(identifier); definition.appendChild(facts);
          list.appendChild(term); list.appendChild(definition);
        });
        panel.hidden = false;
      }
      function renderPassport(id, node) {
        renderBoundEntities(node);`,
  );
  const css = `    .semantic-source-entities { margin: 12px 0 0; font: 12px/1.5 system-ui,sans-serif; }
    .semantic-source-entities[hidden] { display: none; }
    .semantic-source-entities summary { cursor: pointer; font-weight: 600; }
    .semantic-source-entities p { margin: 8px 0; color: var(--text-muted); }
    .semantic-source-entities dl { max-height: 28vh; overflow: auto; margin: 0; padding: 0 12px 0 0; }
    .semantic-source-entities dt { margin-top: 12px; font-weight: 600; overflow-wrap: anywhere; }
    .semantic-source-entities dd { margin: 4px 0 0; overflow-wrap: anywhere; }
    .semantic-source-entities code, .semantic-source-entities dd span { display: block; white-space: normal; }
`;
  replace(TEMPLATE, "    .semantic-passport-detail {", css + "    .semantic-passport-detail {");
  // Avoid clipping the representation qualifier; only the native passport changes.
  replace(
    TEMPLATE,
    '    .semantic-passport-meta [data-passport="kind"] {',
    '    .semantic-passport-meta [data-passport="context"] { white-space: normal; overflow: visible; overflow-wrap: anywhere; }\n    .semantic-passport-meta [data-passport="kind"] {',
  );
  // All transformations are checked before any temporary toolchain file is written.
  for (const name of names) await fs.writeFile(path.join(toolRoot, name), after[name]);
  return {
    schema: "ethos.native-semantic-passport/v1",
    sourceRevision: passport.sourceRevision,
    sourceDigest: passport.sourceDigest,
    nodeCount: Object.keys(passport.nodes).length,
    entityBindings: Object.values(passport.nodes).reduce((n, p) => n + p.entities.length, 0),
    nodes: passport.nodes,
    patchedFiles: names.map((name) => ({
      path: name,
      before: hash(before[name]),
      after: hash(after[name]),
    })),
    scope:
      "Source-declared kinds and explicit aggregates feed native lens, passport, ARIA and SVG metadata; generic external icon removed. No source, geometry, permission or maturity promotion.",
    semanticAcceptance: "UNVERIFIED",
    browserAcceptance: "UNVERIFIED",
  };
}
