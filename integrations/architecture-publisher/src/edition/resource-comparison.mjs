import fs from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
import { validateProjectionEnvelope } from "../adapter/projection.mjs";

const hash = (b) => createHash("sha256").update(b).digest("hex");
const TEMPLATE = "d6564c78ed8e32d42c590286ab50b593036ed7c5e871c0d8388d7583dca44675";
const escape = (value) =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
const names = {
  candidate_integration_effect: "Candidate ref",
  ethos_effect: "Accepted root",
  greenfield_effect: "Greenfield",
  brownfield_effect: "Brownfield",
  adopter_peer_effect: "Autonomous peer",
  publication_effect: "Independent remote",
};

/** Source projection, not six re-authored contracts or a new truth store. */
export function deriveResourceComparison(raw) {
  const input = validateProjectionEnvelope(raw, raw?.digest),
    contracts = input.semantics.contracts.effect_contracts;
  if (JSON.stringify(Object.keys(contracts).sort()) !== JSON.stringify(Object.keys(names).sort()))
    throw Error("Exact resource set required");
  return Object.entries(names).map(([id, label]) => {
    const c = contracts[id],
      gate = input.semantics.contracts.gates[c.admission_gate];
    for (const field of [
      "expected_pre_state",
      "fresh_recheck",
      "admitted_runner",
      "linearization_point",
      "post_observation",
      "effect_attestation",
    ]) {
      if (input.semantics.nodes[c[field]]?.attributes.reality_boundary !== c.repository_boundary)
        throw Error("Wrong local resource binding: " + id + "." + field);
    }
    const judgments = input.semantics.relations.filter(
      (e) => e.kind === "conforms" && e.from === c.repository_boundary,
    );
    if (judgments.length > 1) throw Error("Ambiguous local conformance: " + id);
    const relation = judgments[0],
      judgment = relation && input.semantics.nodes[relation.to];
    if (
      relation &&
      (judgment?.kind !== "conformance" ||
        judgment.attributes.reality_boundary !== c.repository_boundary)
    )
      throw Error("Wrong local conformance: " + id);
    const conformance = relation
      ? {
          id: relation.to,
          label: judgment.label,
          meaning: judgment.attributes.semantics,
          sourceRelation: relation.id,
        }
      : null;
    const stages = {
      prestate: c.expected_pre_state,
      pass: c.pass_verdict,
      cas: c.linearization_point,
      post: c.post_observation,
      attestation: c.effect_attestation,
    };
    const labels = Object.fromEntries(
      Object.entries(stages).map(([key, id]) => {
        const label = input.semantics.nodes[id]?.label;
        if (typeof label !== "string" || !label.trim())
          throw Error("Missing readable source label: " + id);
        return [key, label];
      }),
    );
    return {
      id,
      label,
      resource: c.repository_boundary,
      scope: c.resource_scope,
      ...stages,
      labels,
      selector: gate.required_claim_selector,
      conformance,
      effectAuthority: false,
    };
  });
}

function renderResourceComparison(rows, sourceDigest) {
  const stages = [
    ["prestate", "Exact prestate"],
    ["pass", "Own admission"],
    ["cas", "Local CAS"],
    ["post", "Post-observation"],
    ["attestation", "Attestation"],
  ];
  return `<style id="ethos-resource-comparison-style">
.resource-comparison{margin:48px 0 0;color:var(--text);font:14px/1.6 system-ui,sans-serif}
.resource-comparison h2{font:400 28px/1.2 Georgia,serif;margin:0 0 16px}
.resource-comparison p{max-width:78ch;margin:0 0 24px;color:var(--text-muted)}
.resource-comparison table{width:100%;border-collapse:collapse;table-layout:fixed;text-align:left}
.resource-comparison caption{text-align:left;font-size:14px;color:var(--text-muted);margin:0 0 16px}
.resource-comparison th,.resource-comparison td{padding:24px 24px 24px 0;vertical-align:top;overflow-wrap:break-word;hyphens:none}
.resource-comparison th:last-child,.resource-comparison td:last-child{padding-right:0}
.resource-comparison thead th{border-bottom:1px solid var(--panel-border);font-size:13px;font-weight:600}
.resource-comparison tbody tr+tr>*{border-top:1px solid var(--panel-border)}
.resource-comparison th[scope=row]{font-weight:600}.resource-comparison th p{font-weight:400;font-size:13px;margin:8px 0 0}
.resource-comparison td{font-size:13px}.resource-comparison code{display:block;font:12px/1.7 ui-monospace,Menlo,monospace}
.resource-comparison .resource-law{display:flex;flex-wrap:wrap;gap:8px 24px;padding:0;margin:0 0 28px;list-style:none}
.resource-comparison .resource-law li{white-space:nowrap}.resource-comparison details{margin:24px 0 0}.resource-comparison summary{cursor:pointer}
.resource-comparison dl{display:grid;grid-template-columns:minmax(10em,1fr) minmax(0,3fr);gap:18px 28px;margin:24px 0}
.resource-comparison dt{font-weight:600}.resource-comparison dd{margin:0;overflow-wrap:anywhere}
.resource-binding-set{padding:24px 0;border-bottom:1px solid var(--panel-border)}
.resource-binding-set h3{font:600 16px/1.4 system-ui,sans-serif;margin:0}
.resource-binding-set dl{margin:16px 0 0}
@media(max-width:800px){.resource-comparison th,.resource-comparison td{padding-right:12px}.resource-comparison dl{grid-template-columns:1fr}}
</style>
<section data-resource-comparison class="resource-comparison" aria-labelledby="resource-comparison-title" data-source-digest="${escape(sourceDigest)}">
<h2 id="resource-comparison-title">Resource-local effects</h2>
<p>Each row has its own state, admission, CAS and result. Repositories judge imported grammar against fresh local facts; conformance and remote claims grant no permission. The common protocol creates no shared transaction.</p>
<ul class="resource-law" aria-label="Common effect protocol"><li>Bind exact state</li><li>Evaluate → own PASS</li><li>Recheck freshness</li><li>Single-use runner → local CAS</li><li>Post-observe → attest</li></ul>
<table><caption>Read across a row for one boundary. Read down a column to compare bindings.</caption>
<colgroup><col style="width:19%"><col style="width:15%"><col style="width:13%"><col style="width:10%"><col style="width:13%"><col style="width:15%"><col style="width:15%"></colgroup>
<thead><tr><th scope="col">Resource and scope</th><th scope="col">Local judgment</th>${stages.map(([, title]) => `<th scope="col">${title}</th>`).join("")}</tr></thead><tbody>
${rows.map((r) => `<tr data-resource-contract="${escape(r.id)}"><th scope="row">${escape(r.label)}<p>${escape(r.scope)}</p></th><td>${r.conformance ? `<div data-conformance="${escape(r.conformance.id)}" data-source-relation="${escape(r.conformance.sourceRelation)}">${escape(r.conformance.label)}</div>` : "Not a repository judgment"}</td>${stages.map(([key]) => `<td data-source-node="${escape(r[key])}">${escape(r.labels[key])}</td>`).join("")}</tr>`).join("\n")}
</tbody></table>
<details data-resource-bindings><summary>Source identifiers and claim selectors</summary>${rows.map((r) => `<section class="resource-binding-set"><h3>${escape(r.label)}</h3><dl>${stages.map(([key, title]) => `<dt>${title}</dt><dd><code>${escape(r[key])}</code></dd>`).join("")}<dt>Claim selector</dt><dd>${escape(r.selector)}</dd></dl></section>`).join("\n")}</details>
</section>`;
}

/** Normal-flow supporting table, inserted before native delivery. No SVG,
 * layout script, event listener, or renderer substitution is added. */
export async function applyResourceComparison(toolRoot, input, expectedTemplateDigest = TEMPLATE) {
  const rows = deriveResourceComparison(input),
    file = path.join(toolRoot, "assets/template.html");
  const before = await fs.readFile(file, "utf8");
  if (hash(before) !== expectedTemplateDigest)
    throw Error("Unsupported resource-comparison template digest");
  if (before.includes("<section data-resource-comparison")) throw Error("Duplicate resource table");
  const seam = "    <!-- ARCHIFY:CARDS_SLOT_START -->";
  if (before.split(seam).length !== 2) throw Error("Ambiguous native table seam");
  const after = before.replace(seam, renderResourceComparison(rows, input.digest) + "\n" + seam);
  await fs.writeFile(file, after);
  return {
    schema: "ethos.native-resource-comparison/v1",
    resourceCount: rows.length,
    sourceDigest: input.digest,
    before: hash(before),
    after: hash(after),
    scope:
      "Source-derived normal-flow HTML table; canonical SVG and native viewer scripts unchanged",
    semanticAcceptance: "UNVERIFIED",
    browserAcceptance: "UNVERIFIED",
  };
}
