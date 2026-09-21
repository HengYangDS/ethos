import fs from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
import { validateProjectionEnvelope } from "../adapter/projection.mjs";
const hash = (b) => createHash("sha256").update(b).digest("hex");
const esc = (v) =>
  String(v)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
const excerpt =
  "The write boundary is deliberately ordered: target path, repository root, context refresh, status, prewrite, write, then post-write audit.";
/** One source-text interpretation; these steps are not canonical graph nodes. */
export function deriveWriteBoundary(raw, sourceBytes) {
  const p = validateProjectionEnvelope(raw, raw?.digest),
    source = p.source.bindings.find((b) => b.id === "runner_mutation");
  const normalized = sourceBytes.toString().replace(/\s+/g, " ").trim();
  if (!source || hash(sourceBytes) !== source.sha256 || !normalized.includes(excerpt))
    throw Error("Write boundary source bytes or exact order changed");
  const terms = [
    "target path",
    "repository root",
    "context refresh",
    "status",
    "prewrite",
    "write",
    "post-write audit",
  ];
  const descriptions = [
    "Select exact paths",
    "Resolve their owning repository",
    "Refresh the owning context",
    "Observe the current decision",
    "Admit these tracked paths",
    "Apply the admitted edit",
    "Audit the resulting paths",
  ];
  return {
    sourceRevision: p.source.git.commit,
    sourceDigest: p.digest,
    sourcePath: source.path,
    sourceSha256: source.sha256,
    excerpt,
    steps: terms.map((term, i) => ({
      id: term.replaceAll(" ", "-"),
      label: term[0].toUpperCase() + term.slice(1),
      description: descriptions[i],
    })),
    bindings: ["exact_base", "lease"].map((id) => ({
      id,
      label: p.semantics.nodes[id].label,
      kind: p.semantics.nodes[id].kind,
      meaning: p.semantics.nodes[id].attributes.semantics,
    })),
    prewrite: p.semantics.nodes.prewrite_admission.attributes.semantics,
    effectAuthority: false,
    semanticAcceptance: "UNVERIFIED",
  };
}
function renderWriteBoundary(d) {
  return `<style id="ethos-write-boundary-style">
.write-boundary{margin:40px 0;color:var(--text);font:14px/1.6 system-ui,sans-serif}
.write-boundary h2{font:400 26px/1.2 Georgia,serif;margin:0 0 16px}
.write-boundary p{max-width:100ch;margin:0 0 20px}
.write-order{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:24px;list-style:none;padding:0;margin:24px 0 28px}
.write-order li{min-width:0;position:relative;border-top:1px solid var(--panel-border);padding-top:14px}
.write-order li+li::before{content:'→';position:absolute;left:-19px;top:14px;color:var(--text-muted)}
.write-order strong,.write-order span{display:block;overflow-wrap:anywhere}.write-order span{margin-top:8px;color:var(--text-muted)}
.write-bindings{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:40px;margin:24px 0}
.write-bindings dt{font-weight:600}.write-bindings dd{margin:8px 0 0}
.write-scope{color:var(--text-muted)}
@media(max-width:900px){.write-order{grid-template-columns:1fr;gap:20px}.write-order li{padding:0 0 0 24px;border-top:0}.write-order li+li::before{content:'↓';left:0;top:-16px}.write-bindings{grid-template-columns:1fr;gap:24px}}
</style>
<section class="write-boundary" data-write-boundary="source-order" data-source-digest="${esc(d.sourceDigest)}" aria-labelledby="write-boundary-title">
<h2 id="write-boundary-title">Each tracked edit has an admission boundary</h2>
<p class="write-scope">Source-bound order explanation for every work lane; not canonical workflow nodes, not a second admission and not evidence that an edit occurred.</p>
<ol class="write-order">${d.steps.map((s) => `<li data-write-step="${esc(s.id)}"><strong>${esc(s.label)}</strong><span>${esc(s.description)}</span></li>`).join("")}</ol>
<dl class="write-bindings">${d.bindings.map((b) => `<div data-write-binding="${esc(b.id)}"><dt>${esc(b.label)}</dt><dd>${esc(b.meaning)}</dd></div>`).join("")}</dl>
<p>${esc(d.prewrite)}</p>
<p class="write-scope">The executing package owns its topology policy; the audited checkout cannot override it. A write does not itself establish lane proof, candidate integration or accepted-root closeout.</p>
<details><summary>Exact source and interpretation boundary</summary><p>${esc(d.excerpt)}</p><p>${esc(d.sourcePath)} · ${esc(d.sourceRevision)}. Source declarations are not implementation or execution evidence.</p></details>
</section>`;
}
export async function applyWriteBoundary(toolRoot, details, expectedTemplateDigest) {
  const file = path.join(toolRoot, "assets/template.html"),
    before = await fs.readFile(file, "utf8");
  if (hash(before) !== expectedTemplateDigest)
    throw Error("Write boundary template digest mismatch");
  const seam = "    <!-- ARCHIFY:CARDS_SLOT_START -->";
  if (before.split(seam).length !== 2 || before.includes("data-write-boundary="))
    throw Error("Duplicate or missing write explanation owner");
  const after = before.replace(seam, renderWriteBoundary(details) + "\n" + seam);
  await fs.writeFile(file, after);
  return {
    schema: "ethos.native-write-boundary/v1",
    sourceDigest: details.sourceDigest,
    sourceRevision: details.sourceRevision,
    sourceSha256: details.sourceSha256,
    before: hash(before),
    after: hash(after),
    steps: details.steps.map((s) => s.id),
    scope: "Normal-flow source-text explanation; canonical SVG and native reader logic unchanged",
    semanticAcceptance: "UNVERIFIED",
    browserAcceptance: "UNVERIFIED",
  };
}
