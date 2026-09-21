import fs from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
import { validateProjectionEnvelope } from "../adapter/projection.mjs";

const hash = (b) => createHash("sha256").update(b).digest("hex");
const TEMPLATE = "d6564c78ed8e32d42c590286ab50b593036ed7c5e871c0d8388d7583dca44675";
const esc = (v) =>
  String(v)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

/** A source-bound explanatory table, not a second proof schema or predicate
 * registry. Required gate inputs are read verbatim from the source model. */
export function deriveVerificationDetails(raw) {
  const p = validateProjectionEnvelope(raw, raw?.digest),
    gate = p.semantics.contracts.gates.effect_admission_gate;
  const independent = p.source.bindings.find((b) => b.id === "independent_verification");
  if (!independent || gate.mode !== "all")
    throw Error("Exact independent verification and conjunctive gate source required");
  const skillContract = p.semantics.relations.find((r) => r.id === "contracts-constrain-skills");
  if (
    !skillContract ||
    skillContract.from !== "capability_contract" ||
    skillContract.to !== "skills" ||
    skillContract.kind !== "narrows" ||
    skillContract.attributes.effect_capable !== false
  )
    throw Error("Non-authorizing Skill contract relation required");
  const editorial = {
    local_claim: {
      production: "Execute falsifiable checks against the exact repository object and Commitment.",
      boundary:
        "The local executed result proves only its named predicate, bindings and plane. It cannot claim hosted or independent verification.",
    },
    independent_claim: {
      production:
        "A separate trust identity re-executes or checks the declared proof. Bind verifier, target repository, target HEAD, exact command, result and immutable evidence location.",
      boundary:
        "Required when risk or policy (or the requested completion plane) demands it; otherwise optional. An independent receipt does not grant permission in any repository.",
    },
    hosted_claim: {
      production:
        "Observe the named hosted environment and bind the observation to the exact subject and verifier.",
      boundary:
        "A hosted observation is its own plane. Neither local success nor an independent receipt implies that the hosted observation occurred.",
    },
  };
  const rows = Object.entries(editorial).map(([id, e]) => {
    const n = p.semantics.nodes[id];
    if (n?.kind !== "proof_claim") throw Error("Unknown proof plane " + id);
    return {
      id,
      label: n.label,
      plane: n.attributes.plane,
      sourceMeaning: n.attributes.semantics ?? null,
      ...e,
    };
  });
  return {
    sourceDigest: p.digest,
    sourceRevision: p.source.git.commit,
    independentSource: independent.sha256,
    rows,
    capabilityContract: p.semantics.nodes.capability_contract.attributes.semantics,
    skillBoundary: p.semantics.nodes.skills.attributes.semantics,
    requiredInputs: gate.required_inputs.map((id) => ({
      id,
      label: p.semantics.nodes[id].label,
    })),
    selector: gate.required_claim_selector,
    compositeVerifier: p.semantics.nodes.composite_verifier.attributes.semantics,
    compositeClaim: p.semantics.nodes.composite_claim.attributes.semantics,
    assertions: {
      verification: p.documents.copy.assertions.verification.text,
      evidence: p.documents.copy.assertions.evidence.text,
    },
    scope:
      "Author interpretation of the exact product and independent-verification sources; not semantic acceptance or proof of implemented adapters.",
  };
}

function renderVerificationDetails(d) {
  return `<style id="ethos-verification-details-style">
.verification-details{margin:48px 0 0;color:var(--text);font:14px/1.7 system-ui,sans-serif}
.verification-details h2{font:400 28px/1.2 Georgia,serif;margin:0 0 16px}
.verification-details h3{font:600 16px/1.4 system-ui,sans-serif;margin:0 0 14px}
.verification-details p{margin:0 0 18px;max-width:85ch}
.verification-details table{width:100%;border-collapse:collapse;table-layout:fixed;text-align:left}
.verification-details caption{text-align:left;color:var(--text-muted);margin:0 0 20px}
.verification-details th,.verification-details td{padding:20px 28px 20px 0;vertical-align:top;overflow-wrap:anywhere}
.verification-details thead th{font-weight:600;border-bottom:1px solid var(--panel-border)}
.verification-details tbody th{font-weight:600}.verification-details tbody th small{display:block;color:var(--text-muted);font-size:12px;font-weight:400}
.verification-details .verification-conditions{display:grid;grid-template-columns:1fr 1fr;gap:48px;margin:40px 0 0}
.verification-details ul{padding-left:20px;margin:0 0 18px}.verification-details li{margin:0 0 7px}
.verification-details .verification-source{color:var(--text-muted);font-size:12px;overflow-wrap:anywhere}
@media(max-width:800px){.verification-details .verification-conditions{grid-template-columns:1fr}.verification-details th,.verification-details td{padding-right:12px}}
</style>
<section class="verification-details" data-verification-details data-source-digest="${esc(d.sourceDigest)}" aria-labelledby="verification-details-title">
<h2 id="verification-details-title">What each proof can establish</h2>
<table><caption>Returned proof claims retain these distinct planes. A claim is selected by exact applicability, not by recency, tool name or a shared path.</caption>
<colgroup><col style="width:20%"><col style="width:40%"><col style="width:40%"></colgroup>
<thead><tr><th scope="col">Evidence plane</th><th scope="col">Production and binding</th><th scope="col">Validity and boundary</th></tr></thead><tbody>
${d.rows.map((r) => `<tr data-proof-identity="${esc(r.id)}"><th scope="row">${esc(r.label)}<small>${esc(r.plane)}</small></th><td>${esc(r.production)}</td><td>${esc(r.boundary)}</td></tr>`).join("\n")}
</tbody></table>
<div class="verification-conditions">
<section aria-labelledby="verification-composite-title"><h3 id="verification-composite-title">Composition is optional, not a vote</h3>
<p>A responsible verifier applies an explicit rule to named input claims. The output is a new claim with its own provenance and bounded scope. It cannot amplify the authority or scope of its inputs, erase their planes, or become a reusable PASS.</p>
<p>Raw applicable claims can support admission directly. The source composite path names local and independent inputs; this view does not invent a hosted-to-composite relation.</p>
<h3>History survives; applicability may not</h3>
<p>Historical results remain queryable. A newer receipt for another Commitment, tree, policy, verifier or plane cannot satisfy the current query. Re-observe stale bindings and rerun the selected proof when required; do not relabel old evidence.</p>
</section>
<section aria-labelledby="verification-admission-title"><h3 id="verification-admission-title">Fresh effect admission</h3>
<p>All source-declared inputs are required:</p><ul>${d.requiredInputs.map((n) => `<li data-semantic-input="${esc(n.id)}">${esc(n.label)}</li>`).join("")}</ul>
<p><strong>Claim selector:</strong> ${esc(d.selector)}.</p>
<p>Missing, stale or conflicting required evidence yields BLOCK / UNKNOWN, not an effect. Unrelated historical evidence cannot invalidate the selected candidate merely because it concerns another input. Only local admission may yield PASS; the subsequent fresh recheck and resource-local effect protocol remain mandatory.</p>
</section></div>
<section data-source-relation="contracts-constrain-skills" aria-labelledby="verification-capability-title" style="margin-top:40px">
<h3 id="verification-capability-title">Capability contracts constrain Skills</h3>
<p>${esc(d.capabilityContract)}</p>
<p>${esc(d.skillBoundary)}</p>
<p>Contract conformance is not permission to act. The Plan selects capabilities; only the action's own PASS admits execution. An independent verifier additionally requires a separate trust identity.</p>
</section>
<p class="verification-source">Target mechanism · source ${esc(d.sourceRevision)}. Tables and diagrams are explanatory projections, not executed verification evidence.</p>
</section>`;
}

export async function applyVerificationDetails(toolRoot, input, expectedTemplateDigest = TEMPLATE) {
  const details = deriveVerificationDetails(input),
    file = path.join(toolRoot, "assets/template.html"),
    before = await fs.readFile(file, "utf8");
  if (hash(before) !== expectedTemplateDigest)
    throw Error("Unsupported verification-details template digest");
  if (before.includes('<section class="verification-details"'))
    throw Error("Duplicate verification details");
  const seam = "    <!-- ARCHIFY:CARDS_SLOT_START -->";
  if (before.split(seam).length !== 2) throw Error("Ambiguous native details seam");
  const after = before.replace(seam, renderVerificationDetails(details) + "\n" + seam);
  await fs.writeFile(file, after);
  return {
    schema: "ethos.native-verification-details/v1",
    sourceDigest: input.digest,
    proofPlanes: details.rows.length,
    before: hash(before),
    after: hash(after),
    scope:
      "Source-bound normal-flow comparison and admission details; native SVG and viewer scripts unchanged",
    semanticAcceptance: "UNVERIFIED",
    browserAcceptance: "UNVERIFIED",
  };
}
