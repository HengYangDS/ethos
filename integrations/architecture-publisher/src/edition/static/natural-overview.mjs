import { deriveEffectRows } from "./effect-matrix.mjs";
import { verifyMeaningCarriers } from "../evolution.mjs";

/** One source-bound authored view. Grouping is editorial ownership, never
 * effect authority. Type and spacing obligations remain source-owned. */
export function composeNaturalOverview(
  input,
  measure,
  quality,
  options = {},
  sourceDocuments = [],
) {
  const refresh = options.refresh;
  const authored = options.carriers;
  const authoredEdits = new Map();
  if (authored !== undefined) {
    if (
      !authored ||
      Object.keys(authored).sort().join(",") !== "edits,meaning" ||
      !Array.isArray(authored.edits) ||
      !authored.edits.length ||
      !Array.isArray(authored.meaning) ||
      !authored.meaning.length
    )
      throw Error("Explicit authored static carriers required");
    for (const edit of authored.edits) {
      if (
        !edit ||
        Object.keys(edit).sort().join(",") !== "after,before,id" ||
        typeof edit.id !== "string" ||
        authoredEdits.has(edit.id) ||
        typeof edit.before !== "string" ||
        typeof edit.after !== "string" ||
        !edit.after.trim() ||
        edit.after.length > 10000 ||
        /[\r\n]/.test(edit.after) ||
        Object.hasOwn(options.labels ?? {}, edit.id)
      )
        throw Error("Invalid or duplicate authored static carrier");
      authoredEdits.set(edit.id, edit);
    }
    verifyMeaningCarriers(
      input,
      authored.meaning,
      Object.fromEntries(authored.edits.map((e) => [e.id, e.after])),
      sourceDocuments,
    );
    const bound = new Set(authored.meaning.flatMap((m) => m.carriers));
    if (authored.edits.some((e) => !bound.has(e.id)))
      throw Error("Unbound authored static carrier");
  }
  const consumedAuthored = new Set();
  if (refresh) {
    if (Object.keys(refresh).sort().join(",") !== "merge,pending,replay,sha256")
      throw Error("Explicit refresh meaning and carriers required");
    verifyMeaningCarriers(
      input,
      [
        {
          kind: "node",
          id: "candidate_base_stale",
          sha256: refresh.sha256,
          carriers: ["replay", "merge", "pending"],
        },
      ],
      refresh,
    );
  }
  const laneCount = options.laneCount ?? 3;
  if (![2, 3, 4].includes(laneCount))
    throw Error("This composition supports two to four visible lanes, not arbitrary capacity");
  const growth = quality?.hard_gates?.geometry_each_scale?.font_width_growth_fraction;
  if (!Number.isFinite(growth) || growth < 0) throw Error("Source quality font growth required");
  const labelSites = new Set([
    "compile-title",
    "combination-label",
    "candidate-state-label",
    "accepted-state-label",
    "protocol-state-label",
  ]);
  for (const [id, value] of Object.entries(options.labels ?? {})) {
    if (!labelSites.has(id)) throw Error("Undeclared label override " + id);
    if (typeof value !== "string" || !value.trim() || /[\r\n]/.test(value))
      throw Error("Single nonempty label required " + id);
  }
  const rows = deriveEffectRows(input),
    source = input.source.bindings.find((b) => b.id === "product_contract");
  const trustedPublication =
    input.semantics.contracts.gates.publication_admission_gate.required_inputs.includes(
      "git_substrate",
    );
  const separateReclamation =
    input.semantics.nodes.runtime_generation_retirement.attributes.required_consumer_observations.includes(
      "linked_interpreter_bindings",
    );
  if (!source) throw Error("Product contract binding required");
  // A single painted schema is instantiated by each named row. These bindings
  // describe six local protocols; they do not turn one runner into six owners.
  const protocolFor = (row) => {
    const c = row.contract,
      g = row.gate;
    const admission =
      row.id === "candidate_integration_effect"
        ? "candidate_integration_evaluation"
        : "effect_evaluation";
    const sourceRelation = (from, to, kind) => {
      const found = input.semantics.relations.filter(
        (r) => r.from === from && r.to === to && r.kind === kind,
      );
      if (found.length !== 1)
        throw Error("Ambiguous local protocol relation " + row.id + ":" + from + "/" + to);
      return found[0].id;
    };
    return {
      mode: "resource-local-schematic",
      effectAuthority: false,
      gate: c.admission_gate,
      requiredInputs: [...g.required_inputs],
      claimSelector: g.required_claim_selector,
      stages: {
        "protocol-admit": [admission, c.pass_verdict],
        "protocol-state": [c.expected_pre_state],
        "protocol-recheck": [c.fresh_recheck],
        "protocol-run": [c.admitted_runner],
        "protocol-cas": [c.linearization_point],
        "protocol-observe": [c.post_observation],
        "protocol-receipt": [c.effect_attestation],
        "protocol-refusal": [...g.failure_outputs],
      },
      relations: [
        {
          view: "protocol-admit-recheck",
          source: [sourceRelation(c.pass_verdict, c.fresh_recheck, "admits")],
        },
        {
          view: "protocol-state-recheck",
          source: [sourceRelation(c.expected_pre_state, c.fresh_recheck, "binds")],
        },
        {
          view: "protocol-recheck-run",
          source: [sourceRelation(c.fresh_recheck, c.admitted_runner, "admits")],
        },
        { view: "protocol-run-cas", source: [row.ingress.id] },
        {
          view: "protocol-cas-observe",
          source: [sourceRelation(c.linearization_point, c.post_observation, "post_observes")],
        },
        {
          view: "protocol-observe-receipt",
          source: [sourceRelation(c.post_observation, c.effect_attestation, "attests")],
        },
        {
          view: "protocol-refusal",
          source: g.failure_outputs.map((v) => sourceRelation(admission, v, "branches")),
        },
      ],
      conditions: {
        beforeRun: {
          view: "protocol-refusal",
          sourceVerdicts: [...g.failure_outputs],
          effectAllowed: false,
        },
        stale: {
          view: "protocol-recheck",
          guard: "effect_time_freshness",
          runnerAllowed: false,
        },
        mismatch: {
          view: "protocol-cas",
          scope: "this-resource-cas-update",
          globalRollback: false,
        },
        uncertain: {
          view: "protocol-observe",
          source: "outcome_unknown",
          replayAllowed: false,
        },
      },
      labels: [
        "protocol-title",
        "protocol-scope",
        "protocol-admit-label",
        "protocol-state-label",
        "protocol-recheck-label",
        "protocol-run-label",
        "protocol-cas-label",
        "protocol-observe-label",
        "protocol-receipt-label",
        "protocol-refusal-text",
        "missing-facts-condition",
        "protocol-stale-text",
        "protocol-reject-text",
        "protocol-unknown-text",
        "protocol-unknown-condition",
      ],
    };
  };
  const d = {
    title: input.title,
    subtitle: input.documents.copy.subtitle,
    brand: "ETHOS · 问道",
    binding: {
      state: "DESIGN_CANDIDATE",
      commit: input.source.git.commit,
      digest: source.sha256,
    },
    labels: [],
    marks: [],
    relations: [],
    rules: [],
    required: Object.keys(input.documents.copy.assertions),
    sourceAssertions: {},
    apertures: [],
  };
  Object.assign(d.binding, { source: source.path });
  const groups = [],
    lanes = [],
    resourceRows = [];
  const witnesses = { marks: {}, relations: {} };
  const routingMarks = {},
    routingEdges = {};
  const conditionalConsequences = [];
  // Reclaim height in the identity, not by squeezing type or causal geometry.
  // Every lower field uses one authored origin, including its edge waypoints.
  const fieldOffsetY = -20;
  let group = "";
  const liftedCore = new Set(["intent", "parallel-work", "selection", "local-effects", "outcomes"]);
  const lowerShift = laneCount === 4 ? (separateReclamation ? 10 : 12) : 0;
  const supportShift = separateReclamation ? 14 : 0;
  // Whole-band allocation: preserve graph internals and source section gaps.
  // The measured ink envelope recovers space previously reserved for line-box
  // ascenders/descenders, without reducing the authored font sizes.
  const bandLift = () =>
    separateReclamation
      ? ["protocol", "resource-comparison"].includes(group)
        ? 4
        : ["responsibilities", "verification", "continuity"].includes(group)
          ? 6.5
          : 0
      : 0;
  const placeY = (y) =>
    group === "identity"
      ? y
      : y +
        fieldOffsetY -
        (liftedCore.has(group) ? 47 : 0) -
        (["protocol", "resource-comparison", "runtime"].includes(group) ? 25 : 0) +
        (!liftedCore.has(group) && !separateReclamation ? lowerShift : 0) +
        ([
          "protocol",
          "resource-comparison",
          "responsibilities",
          "verification",
          "continuity",
        ].includes(group)
          ? supportShift
          : 0) -
        bandLift() +
        (refresh &&
        [
          "protocol",
          "resource-comparison",
          "responsibilities",
          "verification",
          "continuity",
        ].includes(group)
          ? 4.5
          : 0);
  const section = (id) => {
    group = id;
    groups.push({ id, labels: [] });
  };
  const text = (id, value, x, y, semantic = [], size = 12.5, weight = "400", about) => {
    if (d.labels.some((l) => l.id === id)) throw Error("Duplicate label " + id);
    const authoredEdit = authoredEdits.get(id);
    if (authoredEdit) {
      if (authoredEdit.before !== value) throw Error("Stale authored label " + id);
      consumedAuthored.add(id);
    }
    const replacement = authoredEdit?.after ?? options.labels?.[id];
    if (replacement !== undefined) {
      value = replacement;
      const width = measure(value, size, weight).width * (1 + growth);
      const clearance =
        quality.hard_gates.geometry_each_scale
          .text_to_nonowner_geometry_clearance_px_at_reference_min;
      if (!Number.isFinite(width) || width <= 0 || !Number.isFinite(clearance) || clearance < 0)
        throw Error("Invalid label allocation metric " + id);
      if (id === "compile-title") {
        // Fork junction: x=395, radius=2, painted half-stroke=.85.
        // Keep the native baseline and fit leftwards, never shrink or reroute.
        x = Math.min(x, 395 - 2 - 0.85 - clearance - width);
        if (x < 210) throw Error("Label exceeds measured local allocation " + id);
      } else if (id === "combination-label" && !separateReclamation) {
        // Below the object, retention and candidate-request bound a narrow
        // corridor. Wider copy belongs above the same object, not over a route.
        const left = 880 + 0.575 + clearance,
          right = 1000 - 0.575 - clearance;
        x = Math.min(x, right - width - 1);
        if (x <= left) {
          x = 1058 - 4 - 0.85 - clearance - width - 1;
          y = 241;
        }
        if (x + width >= 1058 - 4 - 0.85 - clearance)
          throw Error("Label exceeds measured local allocation " + id);
      }
    }
    // Measured header rails preserve the source inset and peer-group gap.
    // Move only text baselines; never shrink type or move semantic endpoints.
    const headerShift = group === "identity" && !["brand", "title"].includes(id) ? 9 : 0;
    const headingShift = [
      "inquiry-title",
      "meaning-title",
      "work-title",
      "candidate-title",
      "accepted-title",
      "candidate-qualifier",
      "accepted-qualifier",
      "admit-column",
      "actor-column",
      "work-column",
      "worktree-column",
      "prewrite-column",
      "proof-column",
    ].includes(id)
      ? 9
      : 0;
    d.labels.push({
      id,
      text: value,
      x,
      y: placeY(y) + headerShift + headingShift,
      size,
      weight,
      tone: weight === "400" ? "muted" : "ink",
      semantics: semantic,
      ...(about ? { about } : {}),
    });
    groups.find((g) => g.id === group).labels.push(id);
    for (const s of semantic) {
      if (!input.documents.copy.assertions[s]) throw Error("Unknown assertion " + s);
      (d.sourceAssertions[s] ??= []).push(id);
    }
  };
  const paragraph = (id, value, x, y, width, semantic, size = 12.5, leading = 18) => {
    const lines = [];
    let line = "";
    for (const word of value.split(/\s+/)) {
      const next = line ? line + " " + word : word;
      if (measure(next, size, "400").width * (1 + growth) <= width) {
        line = next;
      } else {
        if (!line) throw Error("Word exceeds measured column " + id);
        lines.push(line);
        line = word;
      }
    }
    if (line) lines.push(line);
    lines.forEach((l, i) => text(id + "-" + i, l, x, y + i * leading, semantic, size));
    return y + (lines.length - 1) * leading;
  };
  const measuredLabel = (id) => {
    const label = d.labels.find((l) => l.id === id);
    if (!label) throw Error("Missing layout label " + id);
    const metric = measure(label.text, label.size, label.weight);
    return { label, ink: metric.glyph };
  };
  const alignInkLeft = (id, reference) => {
    const a = measuredLabel(id),
      b = measuredLabel(reference);
    a.label.x = b.label.x + b.ink.x - a.ink.x;
  };
  const mark = (id, kind, x, y, r, sourceIds) => {
    for (const s of sourceIds)
      if (!input.semantics.nodes[s]) throw Error("Unknown source mark " + s);
    d.marks.push({
      id,
      kind,
      x,
      y: placeY(y),
      r,
      tone: kind === "gate" ? "accepted" : kind === "evidence" ? "proof" : "line",
    });
    witnesses.marks[id] = sourceIds;
  };
  const edge = (id, from, to, kind, sourceIds, via = [], arrow = true) => {
    for (const s of sourceIds)
      if (!input.semantics.relations.some((r) => r.id === s))
        throw Error("Unknown source relation " + s);
    via = via.map((p) => ({ x: p.x, y: placeY(p.y) }));
    const a = d.marks.find((m) => m.id === from),
      b = d.marks.find((m) => m.id === to);
    if (!a || !b) throw Error("Unknown endpoint");
    const port = (m, t) =>
      Math.abs(t.x - m.x) > Math.abs(t.y - m.y)
        ? { x: m.x + Math.sign(t.x - m.x) * m.r, y: m.y }
        : { x: m.x, y: m.y + Math.sign(t.y - m.y) * m.r };
    d.relations.push({
      id,
      source: from,
      target: to,
      kind,
      arrow,
      points: [port(a, via[0] ?? b), ...via, port(b, via.at(-1) ?? a)],
    });
    witnesses.relations[id] = sourceIds;
  };

  section("identity");
  text("brand", d.brand, 48, 46, [], 18, "600");
  text("title", "Reliable repository evolution", 210, 46, ["purpose"], 36, "serif");
  text(
    "roles",
    "Work authors · candidate integrates · proposal reviews · dev accepts · main releases",
    730,
    16,
    ["accepted"],
    12.5,
    "600",
  );
  text(
    "kernel-scope",
    separateReclamation ? "Small trust kernel; no compatibility residue." : "Small trust kernel.",
    1305,
    16,
    ["purpose", "norms"],
    12.5,
  );
  text(
    "thesis",
    separateReclamation
      ? "Plan selects official/mature Skills/tools; people/Agents in session."
      : "Understand intent. Compose capabilities. Verify real outcomes.",
    730,
    35,
    separateReclamation ? ["capabilities", "authority"] : ["purpose", "capabilities"],
    12.5,
  );
  text("maturity", input.documents.copy.maturity_notice, 1160, 35, ["maturity"], 12.5);
  text("review", "MR/PR or authorized maintainer: same object.", 730, 54, ["accepted"], 12.5);
  text(
    "review-exit",
    "Retire proposal: dev acceptance + review closure; not main release.",
    1050,
    54,
    ["accepted", "exit"],
    12.5,
  );
  if (refresh) {
    for (const id of ["kernel-scope", "maturity", "review-exit"]) {
      const { label, ink } = measuredLabel(id);
      label.x = 1552 - ink.x - ink.width;
    }
  }
  if (
    input.documents.copy.assertions.compile.text.includes(
      "Source acceptance, delivery and Change completion are distinct",
    )
  ) {
    text(
      "change-milestones",
      "Source acceptance / delivery / completion: distinct. Same active Change; archive after duties settle.",
      48,
      70,
      ["compile", "accepted", "exit"],
      12.5,
    );
  }

  section("intent");
  text("inquiry-title", "Investigate", 48, 177, ["intent"], 19, "serif", "inquiry");
  text("meaning-title", "Accept meaning", 185, 177, ["intent"], 19, "serif", "meaning");
  paragraph(
    "intent-scope",
    separateReclamation
      ? "Problem research: examples test scope, exceptions, assumptions and guarantees. Compilation is not understanding."
      : "Examples challenge scope, exceptions, assumptions and guarantees. Compilation is not understanding.",
    48,
    204,
    295,
    ["purpose", "intent", "compile"],
  );
  mark("inquiry", "state", 72, 275, 5, ["problem_observation", "research", "intent_alignment"]);
  mark("meaning", "intent", 212, 275, 10, ["openspec_carrier", "commitment_n"]);
  mark("plan", "state", 356, 275, 5, ["compile_plan", "transition_plan"]);
  text("compile-title", "Compile", 292, 250, ["compile"], 18, "serif", "plan");
  edge("align", "inquiry", "meaning", "flow", [
    "research-informs-alignment",
    "alignment-proposes-accepted-intent",
  ]);
  edge("compile", "meaning", "plan", "flow", [
    "carrier-realizes-commitment",
    "commitment-compile",
    "compile-plan",
  ]);
  text(
    "intent-status",
    separateReclamation
      ? "Accept; supersede; pending verification; reject"
      : "Accept / supersede / pending / reject.",
    48,
    313,
    ["intent"],
  );
  text("intent-carrier", "Accepted OpenSpec → Commitment.", 48, 334, ["intent", "compile"]);
  paragraph(
    "compile-inputs",
    "All applicable prior Attestations: Plan/policy selects. Fresh Facts → bounded Plan + proof obligations.",
    48,
    360,
    330,
    ["compile", "evidence"],
  );
  text(
    "action-conjunction",
    separateReclamation
      ? "Subject delegates to Actor: policy/intent/Facts/Plan."
      : "Act only with subject + policy + intent + Facts + Plan.",
    48,
    403,
    ["authority"],
  );

  section("parallel-work");
  text("work-title", "Parallel work", 420, 171, ["lanes"], 22, "serif");
  text(
    "lane-input-order",
    separateReclamation ? "Below: Base (ref/HEAD/tree) · Lease" : "Below Lane: Base · Lease",
    590,
    164,
    ["lanes", "coordination"],
    12.5,
  );
  for (const [id, label, x, sem] of [
    ["admit", "Admit", 437, ["authority"]],
    ["actor", "Actor", 501, ["lanes", "authority"]],
    ["work", "Lane", 565, ["lanes"]],
    ["worktree", "Worktree", 632, ["lanes"]],
    ["prewrite", "Prewrite", 708, ["lanes", "authority"]],
    ["proof", "Claim", 773, ["verification"]],
  ])
    text(id + "-column", label, x - measure(label, 12.5, "600").width / 2, 190, sem, 12.5, "600");
  // Joint allocation: preserve the center hub's >=14-unit terminal,
  // keep prewrite clear of adjacent rows, and end before the fixed captions.
  const laneY =
    laneCount === 2 ? [231, 310] : laneCount === 4 ? [225, 257, 293, 325] : [231, 275, 310];
  const prewriteDepth = laneCount === 4 ? 20 : 23;
  for (const [i, y] of laneY.entries()) {
    const depth = prewriteDepth;
    const preparationDepth = separateReclamation && laneCount === 4 && i === 3 ? 18 : depth;
    for (const [id, kind, x, r, s] of [
      ["fork", "junction", 395, 2, []],
      ["admit", "gate", 437, 6, ["action_evaluation", "action_pass"]],
      ["actor", "state", 501, 4, ["actor"]],
      ["work", "state", 565, 4, ["work_lane"]],
      ["offer", "junction", 827, 2, []],
    ])
      mark(id + "-" + i, kind, x, y, r, s);
    routingMarks["fork-" + i] = {
      role: "routing-only",
      purpose: "Distribute planning inputs to independent admission, never one shared PASS.",
    };
    routingMarks["offer-" + i] = {
      role: "routing-only",
      purpose: "Gather offered lane results before contribution selection; not a candidate object.",
    };
    edge("admit-" + i, "fork-" + i, "admit-" + i, "admission", ["plan-evaluate-action"]);
    edge("actor-" + i, "admit-" + i, "actor-" + i, "flow", ["pass-admits-actor"]);
    edge("work-" + i, "actor-" + i, "work-" + i, "flow", ["actor-executes-lane"]);
    mark("base-" + i, "state", 537, y + depth, 4, ["exact_base"]);
    mark("lease-" + i, "state", 593, y + depth, 4, ["lease"]);
    mark("lane-inputs-" + i, "junction", 565, y + depth, 2, []);
    routingMarks["lane-inputs-" + i] = {
      role: "routing-only",
      purpose:
        "This lane is bound to its own exact Base and coordinated by its own Lease; conjunction grants no permission.",
    };
    edge("base-lane-" + i, "base-" + i, "lane-inputs-" + i, "support", ["base-binds-lane"]);
    edge("lease-lane-" + i, "lease-" + i, "lane-inputs-" + i, "support", [
      "lease-coordinates-lane",
    ]);
    edge("lane-binding-" + i, "lane-inputs-" + i, "work-" + i, "support", [], [], false);
    routingEdges["lane-binding-" + i] = {
      role: "routing-only",
      purpose: "Only this lane consumes its Base and Lease; no cross-lane borrowing.",
    };
    mark("worktree-" + i, "worktree", 632, y + preparationDepth, 8, ["linked_worktree"]);
    mark("worktree-fork-" + i, "junction", 606, y, 2, []);
    routingMarks["worktree-fork-" + i] = {
      role: "routing-only",
      purpose:
        "The owned lane supplies its worktree and proof preparation through distinct branches.",
    };
    edge("worktree-fork-input-" + i, "work-" + i, "worktree-fork-" + i, "flow", [], [], false);
    routingEdges["worktree-fork-input-" + i] = {
      role: "routing-only",
      purpose: "Fan out this lane without overlapping parallel paths.",
    };
    edge(
      "coordinate-tree-" + i,
      "worktree-fork-" + i,
      "worktree-" + i,
      "support",
      ["lane-coordinates-worktree"],
      [{ x: 606, y: y + preparationDepth }],
    );
    mark("lane-check-fork-" + i, "junction", 669, y, 2, []);
    routingMarks["lane-check-fork-" + i] = {
      role: "routing-only",
      purpose:
        "The same owned lane supplies proof and its separate prewrite check, not a second lane or shared authorization.",
    };
    edge(
      "lane-check-input-" + i,
      "worktree-fork-" + i,
      "lane-check-fork-" + i,
      "flow",
      [],
      [],
      false,
    );
    routingEdges["lane-check-input-" + i] = {
      role: "routing-only",
      purpose:
        "Fan out the owned lane to proof and prewrite without using an empty worktree icon boundary.",
    };
    mark("proof-fork-" + i, "junction", 773, y, 2, []);
    routingMarks["proof-fork-" + i] = {
      role: "routing-only",
      purpose:
        "This Lane offers work for selection and supplies its own proof claim; neither branch is a candidate object.",
    };
    edge("proof-fork-input-" + i, "lane-check-fork-" + i, "proof-fork-" + i, "flow", [], [], false);
    routingEdges["proof-fork-input-" + i] = {
      role: "routing-only",
      purpose: "Carry the owned Lane to its proof and selection branches.",
    };
    mark("proof-" + i, "proof", 773, y + depth, 4, ["lane_proof_claim"]);
    edge("prove-" + i, "proof-fork-" + i, "proof-" + i, "evidence", ["lane-witnesses-proof"]);
    edge("offer-" + i, "proof-fork-" + i, "offer-" + i, "evidence", ["lanes-offer-results"]);
    mark("prewrite-" + i, "gate", 708, y + preparationDepth, 5, ["prewrite_admission"]);
    mark("prewrite-inputs-" + i, "junction", 669, y + preparationDepth, 2, []);
    routingMarks["prewrite-inputs-" + i] = {
      role: "routing-only",
      purpose:
        "Conjoin the named Lane and its linked worktree before their own prewrite. Its own Lease is a separately stated obligation, not an implicit routing input.",
    };
    edge(
      "lane-prewrite-input-" + i,
      "lane-check-fork-" + i,
      "prewrite-inputs-" + i,
      "support",
      [],
      [],
      false,
    );
    edge(
      "tree-prewrite-input-" + i,
      "worktree-" + i,
      "prewrite-inputs-" + i,
      "support",
      [],
      [],
      false,
    );
    for (const id of ["lane-prewrite-input-" + i, "tree-prewrite-input-" + i])
      routingEdges[id] = {
        role: "routing-only",
        purpose:
          "Carry the separately drawn lane and linked-worktree inputs into this lane-local prewrite conjunction.",
      };
    edge("check-prewrite-" + i, "prewrite-inputs-" + i, "prewrite-" + i, "support", [
      "lane-evaluates-prewrite",
      "worktree-binds-prewrite",
    ]);
    lanes.push({
      admission: "admit-" + i,
      actor: "actor-" + i,
      work: "work-" + i,
      base: "base-" + i,
      lease: "lease-" + i,
      worktree: "worktree-" + i,
      proof: "proof-" + i,
      prewrite: "prewrite-" + i,
      mode: "unassigned",
    });
  }
  const forkHub = laneCount === 3 ? "fork-1" : "fork-hub",
    offerHub = laneCount === 3 ? "offer-1" : "offer-hub";
  const busEdges = [];
  if (laneCount === 3) {
    for (const i of [0, 2]) {
      edge("fork-" + i, "fork-1", "fork-" + i, "flow", [], [], false);
      edge("collect-" + i, "offer-" + i, "offer-1", "evidence", [], [], false);
      busEdges.push("fork-" + i, "collect-" + i);
    }
  } else {
    for (const [id, x] of [
      [forkHub, 395],
      [offerHub, 827],
    ]) {
      mark(id, "junction", x, 275, 2, []);
      routingMarks[id] = {
        role: "routing-only",
        purpose:
          id === forkHub
            ? "Distribute planning inputs; no shared PASS."
            : "Collect offered results; not an admitted candidate.",
      };
    }
    // Adjacent bus segments never overpaint each other. Forks point outward;
    // collection points inward, including when no lane occupies the center.
    for (const side of [-1, 1]) {
      const order = laneY
        .map((y, i) => ({ y, i }))
        .filter((p) => Math.sign(p.y - 275) === side)
        .sort((a, b) => Math.abs(a.y - 275) - Math.abs(b.y - 275));
      let priorFork = forkHub,
        priorOffer = offerHub;
      for (const { i } of order) {
        const f = "fork-" + i,
          c = "collect-" + i;
        edge(f, priorFork, "fork-" + i, "flow", [], [], false);
        edge(c, "offer-" + i, priorOffer, "evidence", [], [], false);
        busEdges.push(f, c);
        priorFork = "fork-" + i;
        priorOffer = "offer-" + i;
      }
    }
  }
  edge("plan-work", "plan", forkHub, "flow", []);
  const laneAdmissionRows = [];
  for (const [i, [key, value]] of [
    ["Lane", "Actor, Commitment, Plan, base, current Lease"],
    [
      separateReclamation ? "Claim" : "Base",
      separateReclamation
        ? "Exact Commitment/base/current Lease/HEAD/proof"
        : "Candidate ref / HEAD / tree",
    ],
    [
      "Any action",
      separateReclamation ? "Own PASS only; BLOCK / UNKNOWN stop" : "BLOCK stops; UNKNOWN",
    ],
  ].entries()) {
    const id = "lane-admission-" + i,
      y = (i === 2 ? 367 : 385 + i * 18) + lowerShift;
    // Shared ink rails, not one offset chosen independently for a long row.
    const keyBearing = separateReclamation ? (measure(key, 12.5, "600").glyph?.x ?? 0) : 0;
    const valueBearing = separateReclamation ? (measure(value, 12.5, "400").glyph?.x ?? 0) : 0;
    text(
      id + "-key",
      key,
      409 - keyBearing,
      y,
      ["lanes", "authority"],
      12.5,
      "600",
      i === 2 ? "action-check" : undefined,
    );
    text(id + "-value", value, 500 - valueBearing, y, ["lanes", "authority", "candidate"]);
    laneAdmissionRows.push([id + "-key", id + "-value"]);
  }
  // A universally scoped action example avoids N identical recovery loops.
  // This is not a shared admission: each lane retains its own PASS gate.
  // Keep the expanded lane gate clear of the full grown intent-text envelope.
  mark("action-check", "gate", 386, 362 + lowerShift - (laneCount === 4 ? 4 : 0), 5, [
    "action_evaluation",
  ]);
  mark("action-unknown", "state", 386, 330, 4, ["action_unknown"]);
  mark("action-reobserve", "state", 356, 330, 4, ["recovery_anchor", "fresh_facts"]);
  text(
    "action-facts-label",
    "Facts",
    307,
    334,
    ["recovery", "compile"],
    12.5,
    "400",
    "action-reobserve",
  );
  edge("action-unknown-branch", "action-check", "action-unknown", "retain", [
    "action-unknown-branch",
  ]);
  edge("action-unknown-recovery", "action-unknown", "action-reobserve", "refresh", [
    "action-unknown-to-recovery",
  ]);
  edge("action-reobserve-plan", "action-reobserve", "plan", "refresh", [
    "recovery-reobserves",
    "facts-compile",
    "compile-plan",
  ]);
  const actionRecovery = {
    appliesTo: lanes.map((l) => l.admission),
    entry: "action-unknown",
    anchor: "action-reobserve",
    plan: "plan",
  };
  const leasePrewrite = {
    appliesTo: lanes.map((l) => ({ lease: l.lease, prewrite: l.prewrite })),
    sourceRelation: "lease-binds-prewrite",
    effectAuthority: false,
    visibleLabels: [
      "lane-input-order",
      ...(separateReclamation ? ["prewrite-facts-key"] : []),
      "prewrite-facts-0",
    ],
  };

  section("selection");
  let proofGroupX = 941,
    modeGroupShift = 0;
  if (separateReclamation && options.labels?.["combination-label"] !== undefined) {
    const m = measure(options.labels["combination-label"], 12.5, "600");
    const clearance =
      quality.hard_gates.geometry_each_scale
        .text_to_nonowner_geometry_clearance_px_at_reference_min;
    // Fit the entire proof group left of the painted candidate-state boundary.
    // Keep its vertical rhythm; moving just the title would cross its qualifiers.
    proofGroupX = Math.min(proofGroupX, 1058 - 4 - 0.85 - clearance - m.width * (1 + growth) - 1);
    const peer = measure("Zero or one", 12.5, "400");
    const peerRight = 848 + (peer.glyph?.width ?? peer.width) * (1 + growth);
    modeGroupShift = Math.max(0, peerRight - (proofGroupX + (m.glyph?.x ?? 0)) + 1);
  }
  text(
    "selection-title",
    "Select",
    848,
    separateReclamation ? 255 : 250,
    ["selection"],
    21,
    "serif",
    "selection",
  );
  mark("selection", "state", 880, 275, 6, ["collaboration_selection"]);
  edge("select", offerHub, "selection", "evidence", []);
  for (const id of ["plan-work", ...busEdges, "select"])
    routingEdges[id] = {
      role: "routing-only",
      purpose:
        id.startsWith("fork") || id === "plan-work"
          ? "Planning-input distribution"
          : "Offered-result collection; selection occurs only at its named node",
    };
  if (separateReclamation) {
    // Two independent modes, with a shared title/value rhythm. Do not let
    // paragraph wrapping attach one mode's name to the other's explanation.
    for (const [i, [value, y, weight]] of [
      ["Cooperate", 155, "600"],
      ["Compatible many", 171, "400"],
      ["or synthesis", 187, "400"],
      ["Compete", 207, "600"],
      ["Zero or one", 223, "400"],
    ].entries()) {
      const bearing = measure(value, 12.5, weight).glyph?.x ?? 0;
      text("modes-" + i, value, 848 - bearing - modeGroupShift, y, ["selection"], 12.5, weight);
    }
  } else
    paragraph(
      "modes",
      "Cooperate: compatible many or synthesis. Compete: zero or one.",
      848,
      164,
      132,
      ["selection"],
    );
  mark("combination", "proof", 958, 275, 5, ["candidate_bundle"]);
  edge("combination", "selection", "combination", "evidence", ["selection-binds-combination"]);
  // One explicit proof label group above its object; never attach qualifiers
  // visually to the independent retained-findings branch on the left.
  text(
    "combination-label",
    "Prove object",
    separateReclamation ? proofGroupX : 917,
    separateReclamation ? 215 : 247,
    ["candidate", "verification"],
    12.5,
    "600",
    "combination",
  );
  text(
    "combination-scope",
    "Selected only",
    separateReclamation ? proofGroupX : 901,
    separateReclamation ? 233 : 309,
    ["candidate", "lanes"],
    12.5,
    "600",
    "combination",
  );
  text(
    "combination-provenance",
    "Base/prewrite",
    separateReclamation ? proofGroupX : 901,
    separateReclamation ? 251 : 327,
    ["candidate", "lanes"],
    12.5,
    "400",
    "combination",
  );
  const candidateGate = input.semantics.contracts.gates.candidate_integration_gate;
  const selectedProvenance = {
    target: "combination",
    appliesOnlyToSelected: true,
    lanes: lanes.map((l) => ({
      work: l.work,
      base: l.base,
      prewrite: l.prewrite,
      proof: l.proof,
    })),
    sourceRelations: [
      "exact-base-to-candidate",
      "lane-to-candidate-bundle",
      "lane-proof-admits-candidate",
    ],
    visibleLabels: [
      "combination-scope",
      "combination-provenance",
      ...(separateReclamation ? ["lane-admission-1-key", "lane-admission-1-value"] : []),
    ],
    claimSelector: candidateGate.required_claim_selector,
    gate: "candidate_integration_gate",
    effectAuthority: false,
  };
  mark("retained", "evidence", 880, 334, 8, ["durable_evidence"]);
  edge("retain", "selection", "retained", "retain", ["selection-preserves-knowledge"]);
  text(
    "retention-explore",
    "Explore: knowledge only.",
    separateReclamation ? 848 : 824,
    separateReclamation ? 372 : 370,
    ["selection", "evidence"],
  );
  if (separateReclamation)
    text("retention-results", "Negative/inconclusive too.", 848, 388, ["selection", "evidence"]);
  text(
    "retention-drop",
    "All-drop: keep useful findings.",
    separateReclamation ? 848 : 824,
    separateReclamation ? 404 : 388,
    ["selection", "evidence"],
  );

  section("local-effects");
  for (const [id, x, title, resource, before, next, admission, post, receipt] of [
    [
      "candidate",
      1058,
      "Candidate · serial CAS",
      "candidate_integration_effect",
      "candidate_state",
      "candidate_next",
      "candidate_integration_pass",
      "candidate_post_observation",
      "candidate_effect_attestation",
    ],
    [
      "accepted",
      1285,
      "Accepted root",
      "ethos_effect",
      "accepted_n",
      "accepted_next",
      "effect_pass",
      "post_observation",
      "attestation_n",
    ],
  ]) {
    const row = rows.find((r) => r.id === resource),
      c = row.contract;
    text(
      id + "-title",
      title,
      x - 72,
      169,
      [id === "candidate" ? "candidate" : "accepted"],
      20,
      "serif",
    );
    text(
      id + "-qualifier",
      id === "candidate"
        ? separateReclamation
          ? "CAS stales bases: refresh/prove/re-admit"
          : "Stale base: refresh/prove/re-admit"
        : "Separate acceptance",
      id === "candidate" && separateReclamation ? 958 : x - 72,
      190,
      id === "candidate" ? ["effect", "candidate", "lanes"] : ["effect", "self"],
      12.5,
    );
    mark(id + "-before", "state", x, 222, 4, [before]);
    mark(id + "-cas", "gate", x, 275, 8, [
      c.fresh_recheck,
      c.admitted_runner,
      c.linearization_point,
    ]);
    mark(id + "-next", "state", x + 90, 275, 5, [next]);
    mark(id + "-admission", "gate", x, id === "candidate" && separateReclamation ? 311 : 348, 6, [
      admission,
    ]);
    const postY = id === "candidate" ? 311 : 325,
      receiptY = id === "candidate" ? 350 : 373;
    mark(id + "-post", "state", x + 90, postY, 4, [post]);
    mark(id + "-receipt", "evidence", x + 90, receiptY, 8, [receipt]);
    text(
      id + "-state-label",
      "Git ref / HEAD / tree",
      id === "accepted" ? 1303 : x + 18,
      id === "accepted" ? 241 : 227,
      ["effect"],
    );
    if (id === "candidate" && separateReclamation) {
      mark("candidate-evaluation", "gate", x, 348, 6, ["candidate_integration_evaluation"]);
      text(
        "candidate-evaluation-label",
        "All inputs",
        x - 20,
        383,
        ["candidate", "authority"],
        12.5,
        "600",
        "candidate-evaluation",
      );
      text(id + "-pass-label", "PASS", x + 18, 315, ["authority"], 12.5, "400", id + "-admission");
      edge("candidate-pass", "candidate-evaluation", id + "-admission", "admission", [
        "candidate-integration-pass-branch",
      ]);
    } else text(id + "-pass-label", "Own PASS", x - 20, 383, ["authority"]);
    text(id + "-post-label", "Observe", id === "accepted" ? 1304 : x + 114, postY + 4, ["effect"]);
    text(id + "-receipt-label", "Attestation", x + 114, id === "accepted" ? 386 : receiptY + 4, [
      "evidence",
    ]);
    edge(
      id + "-state",
      id + "-before",
      id + "-cas",
      id === "candidate" ? "candidate-state" : "accepted-state",
      [id === "candidate" ? "candidate-state-to-recheck" : "accepted-state-binds-effect-recheck"],
    );
    edge(id + "-permission", id + "-admission", id + "-cas", "admission", [
      id === "candidate" ? "candidate-pass-to-recheck" : "effect-pass-to-recheck",
    ]);
    const relation = input.semantics.relations.find(
      (r) => r.from === c.linearization_point && r.to === next,
    );
    if (!relation) throw Error("Missing state transition");
    edge(id + "-change", id + "-cas", id + "-next", "effect", [row.ingress.id, relation.id]);
    edge(id + "-observe", id + "-next", id + "-post", "observation", [
      id === "candidate"
        ? "candidate-next-to-post-observation"
        : "accepted-next-to-post-observation",
    ]);
    edge(id + "-attest", id + "-post", id + "-receipt", "evidence", [
      id === "candidate" ? "candidate-post-observation-attests" : "post-to-attestation",
    ]);
    d.apertures.push({
      mark: id + "-cas",
      stateInput: id + "-before",
      admissionInput: id + "-admission",
    });
  }
  mark("lane-retirement", "state", 1148, 382, 5, ["lane_retirement"]);
  edge("candidate-result-exit", "candidate-receipt", "lane-retirement", "retain", [
    "candidate-attestation-binds-retirement",
  ]);
  text(
    "lane-retirement-label",
    "Guarded exit",
    1168,
    386,
    ["exit"],
    12.5,
    "400",
    "lane-retirement",
  );
  edge(
    "candidate-request",
    "combination",
    separateReclamation ? "candidate-evaluation" : "candidate-admission",
    "support",
    separateReclamation
      ? ["candidate-bundle-binds-integration"]
      : ["candidate-bundle-binds-integration", "candidate-integration-pass-branch"],
    [
      { x: 1000, y: 275 },
      { x: 1000, y: 348 },
    ],
  );
  mark("review-fork", "junction", 1254, 275, 2, []);
  routingMarks["review-fork"] = {
    role: "routing-only",
    purpose:
      "The same reviewed candidate supplies both admission and effect-time object recheck; this junction grants no permission.",
  };
  edge("review-object-input", "candidate-next", "review-fork", "support", [], [], false);
  routingEdges["review-object-input"] = {
    role: "routing-only",
    purpose: "Carry the same candidate object to its two separate consumers.",
  };
  edge(
    "review-object",
    "review-fork",
    "accepted-admission",
    "support",
    ["candidate-next-to-effect-evaluation", "effect-pass-branch"],
    [{ x: 1254, y: 348 }],
  );
  edge("review-object-recheck", "review-fork", "accepted-cas", "object-binding", [
    "candidate-next-to-recheck",
  ]);
  d.apertures.find((a) => a.mark === "accepted-cas").objectInput = "review-fork";
  text("same-object", "Exact reviewed object", 1112, 250, ["accepted"], 12.5);

  section("outcomes");
  mark("use", "outcome", 1500, 275, 8, ["use_outcome"]);
  edge("use", "accepted-next", "use", "observation", ["accepted-identifies-use"]);
  text("use-title", "Actual use", 1474, 245, ["outcomes"], 22, "serif", "use");
  paragraph(
    "benefit",
    "Benefit, not delivery. Bind deployed identity, context, baseline and time window.",
    1404,
    310,
    160,
    ["outcomes"],
  );
  if (separateReclamation) {
    for (const [i, line] of [
      "Use/findings challenge",
      "goals/intent/code/assumptions.",
      "No silent authority/history edits.",
      "Can invalidate applicability.",
    ].entries())
      text("feedback-" + i, line, 1370, 156 + i * 18, ["feedback", "outcomes"]);
  } else
    paragraph(
      "feedback",
      "Use + findings challenge intent/code/assumptions; never authority or history. Reassess applicability.",
      1390,
      156,
      176,
      ["feedback", "outcomes"],
    );
  mark("learning", "state", 1580, 407, 6, ["feedback_learning"]);
  text(
    "learning-label",
    separateReclamation ? "Reopen inquiry" : "Reopen",
    separateReclamation ? 1454 : 1492,
    separateReclamation ? 411 : 384,
    ["feedback"],
    14,
    "600",
    "learning",
  );
  edge(
    "use-learning",
    "use",
    "learning",
    "feedback",
    ["use-informs-feedback"],
    [{ x: 1580, y: 275 }],
  );
  const feedbackPredicates = separateReclamation
    ? {
        effectAuthority: false,
        from: ["use", "retained"],
        via: "learning",
        target: "inquiry",
        sourceRelations: [
          "evidence-informs-learning",
          "feedback-revisits-problem",
          "feedback-proposes-intent",
        ],
        visibleLabels: [
          "learning-label",
          ...d.labels.filter((l) => l.id.startsWith("feedback-")).map((l) => l.id),
        ],
      }
    : undefined;
  if (!separateReclamation) {
    edge(
      "findings-learning",
      "retained",
      "learning",
      "feedback",
      ["evidence-informs-learning"],
      [
        { x: 800, y: 334 },
        { x: 800, y: 407 + lowerShift },
        { x: 1540, y: 407 + lowerShift },
        { x: 1540, y: 407 },
      ],
    );
    edge(
      "learning-inquiry",
      "learning",
      "inquiry",
      "feedback",
      ["feedback-revisits-problem", "feedback-proposes-intent"],
      [
        { x: 1580, y: 423 + lowerShift },
        { x: 28, y: 423 + lowerShift },
        { x: 28, y: 275 },
      ],
    );
  }

  section("protocol");
  text(
    "protocol-title",
    "Per-resource effect protocol",
    48,
    536,
    ["effect", "capabilities"],
    24,
    "serif",
  );
  text(
    "protocol-scope",
    "Each row: own gate/state/runner/CAS/result; no global rollback.",
    410,
    536,
    ["effect", "evidence", "faithfulness"],
  );
  const steps = [
    ["admit", 76, "gate", "effect_evaluation", "All inputs; own PASS"],
    ["recheck", 220, "state", "effect_recheck", "Recheck authority"],
    ["run", 395, "state", "admitted_runner", "Single-use runner"],
    ["cas", 510, "gate", "repo_cas", "CAS"],
    ["observe", 655, "state", "post_observation", "Observe"],
    ["receipt", 800, "evidence", "attestation_n", "Attest"],
  ];
  for (const [id, x, kind, s, label] of steps) {
    mark("protocol-" + id, kind, x, 592, kind === "evidence" ? 7 : 5, [s]);
    text(
      "protocol-" + id + "-label",
      label,
      id === "recheck" ? 243 : id === "run" ? 382 : id === "cas" ? 514 : x - 22,
      id === "recheck" ? 619 : 565,
      ["effect"],
      12.5,
      "600",
      "protocol-" + id,
    );
  }
  mark("protocol-state", "state", 220, 566, 4, ["accepted_n"]);
  text(
    "protocol-state-label",
    "Expected state",
    243,
    570,
    ["effect"],
    12.5,
    "400",
    "protocol-state",
  );
  edge("protocol-state-recheck", "protocol-state", "protocol-recheck", "accepted-state", [
    "accepted-state-binds-effect-recheck",
  ]);
  for (const [a, b, s] of [
    ["admit", "recheck", ["effect-pass-branch", "effect-pass-to-recheck"]],
    ["recheck", "run", ["recheck-admits-runner"]],
    ["run", "cas", ["runner-applies-cas"]],
    ["cas", "observe", ["cas-to-post-observation"]],
    ["observe", "receipt", ["post-to-attestation"]],
  ])
    edge(
      "protocol-" + a + "-" + b,
      "protocol-" + a,
      "protocol-" + b,
      a === "run" ? "effect" : "flow",
      s,
    );
  // Only source-backed recovery states are nodes. Definite refusal conditions
  // stay adjacent to their owning steps; they do not invent canonical edges.
  for (const [id, from, x] of [
    ["refusal", "admit", 76],
    ["unknown", "observe", 655],
  ]) {
    mark(
      "protocol-" + id,
      "state",
      x,
      650,
      4,
      id === "refusal" ? ["effect_block", "effect_unknown"] : ["outcome_unknown"],
    );
    edge(
      "protocol-" + id,
      "protocol-" + from,
      "protocol-" + id,
      "retain",
      id === "unknown"
        ? ["post-to-outcome-unknown"]
        : ["effect-block-branch", "effect-unknown-branch"],
    );
  }
  for (const [id, x, copy, owner] of [
    ["refusal", 76, trustedPublication ? "BLOCK: no run" : "BLOCK: no attempt", "protocol-refusal"],
    ["stale", 220, "Stale: no runner", "protocol-recheck"],
    ["reject", 510, "CAS rejects mismatch", "protocol-cas"],
    ["unknown", 655, "Observe before retry", "protocol-unknown"],
  ]) {
    text(
      "protocol-" + id + "-text",
      copy,
      trustedPublication && id === "refusal"
        ? 98
        : trustedPublication && id === "stale"
          ? 230
          : x - (id === "stale" ? 17 : id === "unknown" ? 6 : 20),
      trustedPublication && ["refusal", "stale"].includes(id) ? 676.5 : 682,
      ["effect", "recovery"],
      12.5,
      "600",
      owner,
    );
  }
  text(
    "protocol-unknown-condition",
    "Uncertain attempt",
    649,
    703,
    ["effect", "recovery"],
    12.5,
    "400",
    "protocol-unknown",
  );
  mark("protocol-reobserve", "state", 365, 650, 4, ["recovery_anchor", "fresh_facts"]);
  mark("protocol-recompile", "state", 365, trustedPublication ? 695 : 711, 4, [
    "compile_plan",
    "transition_plan",
  ]);
  edge("missing-facts-reobserve", "protocol-refusal", "protocol-reobserve", "refresh", [
    "effect-unknown-to-recovery",
  ]);
  text("missing-facts-condition", "UNKNOWN", 103, 620, ["recovery"]);
  const lossRecovery = separateReclamation
    ? {
        event: "protocol-loss",
        anchor: "protocol-reobserve",
        interrupts: "session_host",
        sourceRelations: ["loss-interrupts-session", "loss-to-recovery-anchor"],
        effectAuthority: false,
        visibleLabels: [
          "protocol-loss-label",
          "fresh-facts",
          "fresh-plan",
          "protocol-unknown-text",
          "continuation-2-value",
        ],
      }
    : undefined;
  if (lossRecovery) {
    mark("protocol-loss", "state", 474, 625, 4, ["executor_loss"]);
    text(
      "protocol-loss-label",
      "Actor/session/host loss",
      494,
      623,
      ["recovery"],
      12.5,
      "400",
      "protocol-loss",
    );
    mark("protocol-recovery-join", "junction", 474, 650, 2, []);
    routingMarks["protocol-recovery-join"] = {
      role: "routing-only",
      purpose:
        "Merge loss and uncertain-result recovery into fresh observation; grants no authority.",
    };
    edge("uncertain-reobserve", "protocol-unknown", "protocol-recovery-join", "refresh", [
      "outcome-unknown-to-recovery",
    ]);
    edge("loss-reobserve", "protocol-loss", "protocol-recovery-join", "refresh", [
      "loss-to-recovery-anchor",
    ]);
    edge(
      "recovery-join-observe",
      "protocol-recovery-join",
      "protocol-reobserve",
      "refresh",
      [],
      [],
      false,
    );
    routingEdges["recovery-join-observe"] = {
      role: "routing-only",
      purpose:
        "Carry both recovery triggers to the same observation anchor; never an execution shortcut.",
    };
  } else
    edge("uncertain-reobserve", "protocol-unknown", "protocol-reobserve", "refresh", [
      "outcome-unknown-to-recovery",
    ]);
  edge("reobserve-compile", "protocol-reobserve", "protocol-recompile", "refresh", [
    "recovery-reobserves",
    "facts-compile",
    "compile-plan",
  ]);
  edge(
    "compile-new-admission",
    "protocol-recompile",
    "protocol-admit",
    "refresh",
    ["plan-binds-effect-evaluation"],
    [
      { x: 28, y: trustedPublication ? 695 : 711 },
      { x: 28, y: 592 },
    ],
  );
  text(
    "fresh-facts",
    "Fresh Facts",
    388,
    trustedPublication ? 623 : 682,
    ["recovery", "compile"],
    12.5,
    "400",
    "protocol-reobserve",
  );
  text(
    "fresh-plan",
    trustedPublication ? "Recompile Plan" : "Recompile · fresh Plan",
    388,
    trustedPublication ? 680 : 713,
    ["recovery", "compile"],
    12.5,
    "400",
    "protocol-recompile",
  );
  // Publication offers the exact Git object; it is not downstream permission
  // from an accepted-root result. Retain old-source history explicitly.
  if (trustedPublication) {
    mark("protocol-publication-source", "state", 800, 639, 5, ["git_substrate"]);
    mark("protocol-publication-remote", "state", 800, 691, 5, ["publication_remote"]);
    edge(
      "publication-request",
      "protocol-publication-source",
      "protocol-publication-remote",
      "support",
      ["git-projects-publication-object"],
    );
    text(
      "publication-request-label",
      "Git object",
      690,
      620,
      ["publication"],
      12.5,
      "600",
      "protocol-publication-source",
    );
    text(
      "publication-request-boundary",
      "no permission",
      690,
      640,
      ["publication", "authority"],
      12.5,
      "400",
      "protocol-publication-source",
    );
  } else {
    mark("protocol-publication-remote", "state", 800, 639, 5, ["publication_remote"]);
    edge("publication-request", "protocol-receipt", "protocol-publication-remote", "support", [
      "attestation-projects-publication-request",
    ]);
    text(
      "publication-request-label",
      "Request",
      690,
      618,
      ["publication"],
      12.5,
      "600",
      "protocol-publication-remote",
    );
    text(
      "publication-request-boundary",
      "no permission",
      690,
      636,
      ["publication", "authority"],
      12.5,
      "400",
      "protocol-publication-remote",
    );
  }

  section("resource-comparison");
  text("resources-title", "Local effects", 842, 536, ["effect"], 18, "serif");
  const repositoryRows = rows.filter((row) => row.repositoryWorld !== null);
  if (
    repositoryRows.map((row) => row.id).join(",") !==
      "ethos_effect,greenfield_effect,brownfield_effect,adopter_peer_effect" ||
    repositoryRows.some((row) => row.contract.admission_gate !== "effect_admission_gate")
  )
    throw Error("Repository grammar changed; explicit visual migration required");
  const resourceGrammar = {
    label: "resource-repository-grammar",
    appliesTo: repositoryRows.map((row) => row.id),
    gate: "effect_admission_gate",
    sharedPermission: false,
  };
  paragraph(
    resourceGrammar.label,
    "Root, Greenfield, Brownfield, Peers: own subject, current policy, Commitment, fresh Facts, Plan, candidate, local proof.",
    842,
    558,
    724,
    ["accepted", "self", "greenfield", "brownfield", "peers", "authority"],
    12.5,
  );
  paragraph(
    "resource-local-claims",
    "Local PASS only. All applicable declared proof-plane claims: exact subject/predicate/scope/bindings/validity/verifier.",
    842,
    separateReclamation ? 573 : 576,
    724,
    ["accepted", "self", "greenfield", "brownfield", "peers", "verification"],
    12.5,
  );
  const repositoryLocalInputs = {
    sharedAuthority: false,
    labels: d.labels
      .filter(
        (l) =>
          l.id.startsWith(resourceGrammar.label + "-") || l.id.startsWith("resource-local-claims-"),
      )
      .map((l) => l.id),
    rows: repositoryRows.map((row) => ({
      contract: row.id,
      repository: row.contract.repository_boundary,
      inputOwner: row.contract.repository_boundary,
      gate: row.contract.admission_gate,
      requiredInputs: [...row.gate.required_inputs],
      claimSelector: row.gate.required_claim_selector,
      prestate: row.contract.expected_pre_state,
      linearization: row.contract.linearization_point,
      ...(separateReclamation
        ? {
            conformance: (() => {
              const conforms = input.semantics.relations.filter(
                (r) => r.from === row.contract.repository_boundary && r.kind === "conforms",
              );
              if (conforms.length !== 1) throw Error("Ambiguous local conformance " + row.id);
              const subject = conforms[0].to,
                grammar = input.semantics.relations.filter(
                  (r) => r.from === "protocol_grammar" && r.to === subject && r.kind === "narrows",
                );
              if (
                grammar.length !== 1 ||
                input.semantics.nodes[subject].attributes.reality_boundary !==
                  row.contract.repository_boundary
              )
                throw Error("Wrong local conformance " + row.id);
              return {
                subject,
                grammar: "protocol_grammar",
                sourceRelations: [conforms[0].id, grammar[0].id],
                effectAuthority: false,
              };
            })(),
          }
        : {}),
    })),
  };
  resourceGrammar.label = repositoryLocalInputs.labels[0];
  const localInputLabel = (term) => {
    const label = d.labels.find(
      (l) => repositoryLocalInputs.labels.includes(l.id) && l.text.includes(term),
    );
    if (!label) throw Error("Unpainted local input " + term);
    return label.id;
  };
  const resourceTable = {
    columns: [
      { id: "resource", label: "Resource", x: 842, width: 108 },
      { id: "binding", label: "Local binding", x: 979, width: 258 },
      { id: "constraints", label: "Constraints", x: 1266, width: 290 },
    ],
    rows: [],
  };
  for (const c of resourceTable.columns.filter((c) => separateReclamation || c.id !== "resource"))
    text(
      "resource-column-" + c.id,
      c.label,
      c.x,
      separateReclamation ? 593 : 536,
      ["effect"],
      12.5,
      "600",
    );
  if (separateReclamation)
    paragraph(
      "resource-conformance",
      "Repositories judge imported grammar + fresh local facts; conformance is not permission.",
      1003,
      536,
      549,
      ["self", "greenfield", "brownfield", "peers", "authority"],
      12.5,
    );
  const names = {
    candidate_integration_effect: separateReclamation
      ? [
          "Candidate ref",
          "All: Proven object + state + Commitment",
          "Policy/Facts/Plan; one selected Lane proof",
          ["candidate"],
        ]
      : [
          "Candidate ref",
          "Exact Commitment/base/Lease/HEAD",
          "Policy + Facts + Plan; one selected Lane proof",
          ["candidate"],
        ],
    ethos_effect: [
      "Accepted root",
      "Own state; exact reviewed object",
      "Own PASS; local proof + all applicable claims",
      ["accepted", "self", "verification"],
    ],
    greenfield_effect: [
      "Greenfield",
      "Own founding state / absence",
      separateReclamation ? "Minimal native Skills scaffold" : "Skills scaffold",
      ["greenfield"],
    ],
    brownfield_effect: [
      "Brownfield",
      "Own inherited state",
      "Keep layout; expose conflicts",
      ["brownfield"],
    ],
    adopter_peer_effect: [
      "Peer repos",
      "Own state; exchange",
      "claims/artifacts/conformance; not permission",
      ["peers"],
    ],
    publication_effect: [
      "Remote refs",
      "accepted OIDs; every selected target ref | Full ref / request digest / common-dir",
      "Subject / policy / Attestation | fresh observation / signature trust",
      ["publication"],
    ],
  };
  if (trustedPublication)
    names.publication_effect = [
      "Remote refs",
      "trusted OID + introduced range | 0/1/many; same OIDs; full refs",
      "Review: no completed-product proof | Accepted/release: proof + closeout",
      ["publication"],
    ];
  const inputLabels = {
    candidate_integration_gate: {
      authority_reference: "resource-candidate_integration_effect-obligation",
      commitment_n: "resource-candidate_integration_effect-detail",
      fresh_facts: "resource-candidate_integration_effect-obligation",
      transition_plan: "resource-candidate_integration_effect-obligation",
      candidate_bundle: "combination-label",
      candidate_state: "candidate-state-label",
      lane_proof_claim: "resource-candidate_integration_effect-obligation",
    },
    effect_admission_gate: {
      authorized_subject: localInputLabel("subject"),
      authority_reference: localInputLabel("policy"),
      commitment_n: localInputLabel("Commitment"),
      fresh_facts: localInputLabel("Facts"),
      transition_plan: localInputLabel("Plan"),
      candidate_next: localInputLabel("candidate"),
      local_claim: localInputLabel("proof"),
    },
    publication_admission_gate: {
      authorized_subject: "resource-publication_effect-obligation",
      authority_reference: "resource-publication_effect-obligation",
      attestation_n: "resource-publication_effect-obligation",
      accepted_next: "resource-publication_effect-detail",
      publication_remote_observation: "resource-publication_effect-obligation-1",
      publication_remote: "resource-publication_effect-detail",
    },
  };
  if (separateReclamation)
    Object.assign(inputLabels.candidate_integration_gate, {
      candidate_bundle: "resource-candidate_integration_effect-detail",
      candidate_state: "resource-candidate_integration_effect-detail",
    });
  if (trustedPublication)
    inputLabels.publication_admission_gate = {
      authorized_subject: "publication-admission",
      authority_reference: "publication-admission",
      git_substrate: "resource-publication_effect-detail",
      publication_remote_observation: "publication-result-0",
      publication_remote: "resource-publication_effect-detail-1",
    };
  const admissionBindings = rows.map((row) => {
    const gateId = row.contract.admission_gate,
      mapped = inputLabels[gateId];
    if (
      !mapped ||
      row.gate.required_inputs.some((id) => !mapped[id]) ||
      Object.keys(mapped).some((id) => !row.gate.required_inputs.includes(id))
    )
      throw Error("Unmapped admission input " + gateId);
    return {
      contract: row.id,
      gate: gateId,
      inputs: row.gate.required_inputs.map((source) => ({
        source,
        label: mapped[source],
      })),
      scope: "Visible copy mapping, not proof of semantic sufficiency or shared admission",
    };
  });
  // The reader sees evaluation and PASS separately. One factored all-input
  // predicate binds the named input labels instead of seven crossing arrows.
  // This is diagram semantics, not an executable permission evaluator.
  const candidateAdmission = separateReclamation
    ? {
        gate: "candidate_integration_gate",
        mode: candidateGate.mode,
        evaluation: "candidate-evaluation",
        pass: "candidate-admission",
        effectAuthority: false,
        claimSelector: candidateGate.required_claim_selector,
        failureOutputs: [...candidateGate.failure_outputs],
        labels: ["candidate-evaluation-label", "candidate-pass-label"],
        inputs: admissionBindings
          .find((b) => b.gate === "candidate_integration_gate")
          .inputs.map((binding) => {
            const kind = binding.source === "lane_proof_claim" ? "returns" : "binds";
            const relations = input.semantics.relations.filter(
              (r) =>
                r.from === binding.source &&
                r.to === "candidate_integration_evaluation" &&
                r.kind === kind,
            );
            if (relations.length !== 1)
              throw Error("Ambiguous candidate admission input " + binding.source);
            return { ...binding, relation: relations[0].id };
          }),
      }
    : undefined;
  if (candidateAdmission && candidateAdmission.mode !== "all")
    throw Error("Candidate admission requires every source conjunct");
  const cell = (id, value, c, y, semantic, weight = "400", about) => {
    const parts = [];
    let line = "";
    for (const word of value.split(/\s+/)) {
      if (word === "|") {
        if (line) parts.push(line);
        line = "";
        continue;
      }
      const next = line ? line + " " + word : word;
      if (measure(next, 12.5, weight).width * (1 + growth) <= c.width) line = next;
      else {
        if (!line) throw Error("Resource cell word exceeds allocation " + id);
        parts.push(line);
        line = word;
      }
    }
    if (line) parts.push(line);
    return parts.map((part, i) => {
      const key = i ? id + "-" + i : id,
        ink = measure(part, 12.5, weight).glyph;
      // A negative sidebearing is actual ink outside a left-aligned cell.
      text(
        key,
        part,
        c.x - Math.min(0, ink?.x ?? 0),
        y + i * (separateReclamation ? 16 : 18),
        semantic,
        12.5,
        weight,
        about,
      );
      return key;
    });
  };
  let resourceY = separateReclamation ? 608 : 597;
  for (const row of rows) {
    const [name, detail, obligation, semantic] = names[row.id];
    const fields = [
      ["resource-" + row.id, name],
      ["resource-" + row.id + "-detail", detail],
      ["resource-" + row.id + "-obligation", obligation],
    ];
    const cells = fields.map(([id, value], i) => ({
      labels: cell(
        id,
        value,
        resourceTable.columns[i],
        resourceY,
        semantic,
        i === 0 ? "600" : "400",
        i === 0 && row.id === "publication_effect" ? "protocol-publication-remote" : undefined,
      ),
    }));
    if (row.id === "candidate_integration_effect")
      selectedProvenance.visibleLabels.push(...cells[1].labels, ...cells[2].labels);
    const labels = cells.flatMap((c) => c.labels);
    resourceRows.push({
      contract: row.id,
      resource: row.contract.repository_boundary,
      sharedPermission: false,
      labels,
      protocol: protocolFor(row),
    });
    resourceTable.rows.push({
      contract: row.id,
      y: placeY(resourceY),
      cells,
    });
    resourceY += Math.max(...cells.map((c) => c.labels.length)) * (separateReclamation ? 16 : 18);
  }
  // Use asymmetric support fields: the protocol owns recovery space, while
  // adoption remains immediately below the resource table it qualifies.
  section("protocol");
  if (trustedPublication) {
    text(
      "publication-admission",
      "Subject + prior policy; request binds intent, not authority. Remotes: absent/unavailable/pending/divergent/UNKNOWN.",
      48,
      724,
      ["publication", "authority"],
    );
    paragraph(
      "publication-result",
      "Per effect/equality claim: fresh trust/proof/policy/old refs. Peer-local atomic set; not cross-peer. Keep partial/UNKNOWN.",
      48,
      742,
      750,
      ["publication"],
    );
  } else
    paragraph(
      "publication-result",
      "Remotes: 0/1/many; absent/unavailable/pending/divergent/unknown. Recheck each; no cross-provider atomicity.",
      48,
      742,
      750,
      ["publication"],
    );
  section("resource-comparison");
  paragraph(
    "adoption",
    "Preview native domain/layout/provider/observations; preserve customization/provenance. Idempotent, gradual; reversible before first effect. Without verified OpenSpec: observe only. No retroactive approval.",
    842,
    724,
    711,
    ["greenfield", "brownfield", "norms"],
  );
  for (const binding of admissionBindings)
    for (const entry of binding.inputs)
      if (!d.labels.some((l) => l.id === entry.label))
        throw Error("Unpainted admission input " + entry.source);

  section("responsibilities");
  text(
    "responsibilities-title",
    separateReclamation
      ? "Native owners"
      : "Native owners; bounded lifecycle; capabilities grant no authority",
    48,
    779,
    ["norms", "capabilities", "authority"],
    18,
    "serif",
  );
  if (separateReclamation)
    text(
      "capability-boundaries",
      "Interchangeable capabilities: roles; versioned interpretation; no authority/lifecycle ownership.",
      200,
      779,
      ["capabilities", "authority", "peers"],
    );
  const responsibilities = [
    [
      "owners",
      separateReclamation
        ? "ETHOS repo: source + durable evidence"
        : "Code/tests/specs/docs/rules/Skills",
      separateReclamation
        ? "One owner/current consumer; executable rules; bounded lifecycle."
        : "One owner/current consumer; enforce rules; no compatibility residue.",
      ["norms", "self", "evidence"],
    ],
    [
      "values",
      separateReclamation ? "Transient Commitment · Facts · Plan" : "Commitment · Facts · Plan",
      separateReclamation
        ? "OpenSpec/Git carriers, not roots; no-spec/archive retain proof identity."
        : "Transient. OpenSpec/Git carriers, not roots. No-spec/archive keep proof identity.",
      ["compile", "intent", "evidence"],
    ],
    [
      "methods",
      separateReclamation
        ? "Skills/tools/generators/verifiers/observers"
        : "Actors in sessions · Skills/tools",
      separateReclamation
        ? "Small contracts: I/O, identity/version, permission, cancel/failure."
        : "Plan selects; official, mature. I/O, identity/version, permission, cancel/failure.",
      ["capabilities", "authority", "peers"],
    ],
    [
      "views",
      separateReclamation ? "Rebuildable CLI/JSON · SDK · CI/Forge" : "Native source/evidence",
      separateReclamation
        ? "From native source/evidence; same verdict/gaps; optional MCP/A2A."
        : "Rebuildable CLI/JSON, SDK, CI/Forge, optional MCP/A2A; same verdict/gaps.",
      ["projection", "evidence"],
    ],
    [
      "learning",
      "OpenSpec intent + exact evidence",
      separateReclamation
        ? "Derived experiments/relations; no workflow/feedback/memory truth."
        : "Derived experiments/relations; no workflow, feedback or memory truth.",
      ["intent", "projection", "evidence"],
    ],
  ];
  const responsibilityRows = [];
  for (const [i, [key, object, constraint, semantic]] of responsibilities.entries()) {
    const id = "responsibility-" + key,
      y = 800 + i * (separateReclamation ? 16 : 18);
    text(id + "-label", object, 48, y, semantic, 12.5, "600");
    text(id + "-value", constraint, separateReclamation ? 338 : 292, y, semantic);
    responsibilityRows.push([id + "-label", id + "-value"]);
  }
  paragraph(
    "attestation-scope",
    separateReclamation
      ? "Sole durable semantic result: Attestation; no permission. Binds Commitment/pre/effect/post; predicate/validity/verifier."
      : "Sole durable semantic result: Attestation; no permission. Commitment/pre/effect/post; predicate/validity/verifier.",
    48,
    separateReclamation ? 881 : 891,
    732,
    ["evidence"],
  );
  section("verification");
  text(
    "verification-title",
    "Candidate HEAD",
    separateReclamation ? 806 : 810,
    779,
    ["verification"],
    18,
    "serif",
    "verification-subject",
  );
  mark("verification-subject", "state", 852, 801, 5, ["candidate_state"]);
  mark("verification-independent", "state", 1020, 801, 5, ["independent_verifier"]);
  mark("verification-claim", "proof", 1150, 801, 5, ["independent_claim"]);
  mark("verification-local", "proof", 852, 825, 5, ["local_claim"]);
  text(
    "verification-verifier-label",
    separateReclamation ? "Independent verifier" : "Verifier",
    separateReclamation ? 981 : 995,
    779,
    ["verification", "capabilities"],
    12.5,
    "600",
    "verification-independent",
  );
  text(
    "verification-claim-label",
    "Receipt",
    separateReclamation ? 1134 : 1127,
    779,
    ["verification", "evidence"],
    12.5,
    "600",
    "verification-claim",
  );
  text(
    "verification-local-label",
    "Local claim",
    875,
    829,
    ["verification", "evidence"],
    12.5,
    "400",
    "verification-local",
  );
  text(
    "verification-trust",
    separateReclamation ? "Hosted: observe; no permission" : "Separate trust identity; no effects",
    separateReclamation ? 965 : 968,
    separateReclamation ? 829 : 835,
    ["verification", "capabilities"],
  );
  edge("verification-execute", "verification-subject", "verification-independent", "evidence", [
    "candidate-state-to-independent",
  ]);
  edge("verification-return", "verification-independent", "verification-claim", "evidence", [
    "independent-to-claim",
  ]);
  edge("verification-local-proof", "verification-subject", "verification-local", "evidence", [
    "candidate-state-witnesses-local",
  ]);
  text(
    "verification-applicability",
    separateReclamation
      ? "Falsifiable; separate trust; optional unless risk/policy requires."
      : "Falsifiable; independent optional unless risk/policy requires.",
    separateReclamation ? 808 : 810,
    separateReclamation ? 854 : 855,
    ["verification"],
  );
  text(
    "verification-optional",
    separateReclamation
      ? "Optional: local/independent claim IDs + explicit rule."
      : "Optional composite: responsible verifier, rule, claim IDs.",
    810,
    separateReclamation ? 869 : 873,
    ["verification"],
  );
  text(
    "verification-limits",
    separateReclamation
      ? "Responsible verifier → new composite claim. No scope gain."
      : "No scope gain. Hosted: observed separately; never PASS.",
    810,
    separateReclamation ? 885 : 891,
    ["verification", "authority"],
  );
  const capabilityContract = separateReclamation
    ? {
        source: "capability_contract",
        effectAuthority: false,
        sourceRelations: ["contracts-constrain-skills", "contracts-constrain-verification"],
        verifier: "verification-independent",
        labels: [
          "thesis",
          "capability-boundaries",
          "responsibility-methods-label",
          "responsibility-methods-value",
          "verification-verifier-label",
        ],
      }
    : undefined;

  // Runtime/continuity stay in the complete main field rather than a detached
  // hidden appendix. Their compact adjacent callouts do not create new edges.
  section("runtime");
  const runtimeRows = [];
  const writeOrder = [
    "target path",
    "repository root",
    "context refresh",
    "status",
    "prewrite",
    "write",
    "post-write audit",
  ];
  const writeText =
    (separateReclamation ? "Tracked edit: " : "Every tracked edit: ") +
    writeOrder.join(" → ") +
    ".";
  if (separateReclamation) {
    // Two aligned reading columns, no box or extra authority. Conditions remain
    // on the same baseline as their owner; the ordered edit row locates prewrite
    // before mutation. The existing separation audit owns all spacing minima.
    const entries = [
      [
        "runtime",
        "Git-common",
        "One runtime coordinates worktrees/Leases: lane/holder/generation/expiry; not intent or permission.",
        ["coordination", "lanes"],
      ],
      [
        "prewrite-facts",
        "Every prewrite",
        "Fresh root, branch role, actor, own four-field Lease, Git state, changed paths, official OpenSpec.",
        ["lanes", "authority"],
      ],
      [
        "tracked-write-order",
        "Tracked edit:",
        writeOrder.join(" → ") + ".",
        ["lanes", "authority"],
      ],
      [
        "prewrite-artifacts",
        "Artifacts",
        "Distinct origin/existence/placement/effect; native producer, exact staged bytes, surviving consumers.",
        ["lanes", "norms"],
      ],
      [
        "capability-purity",
        "Norms",
        "Code/tests/specs/config/docs/rules/Skills + temporary resources. Pure semantics; bounded effects.",
        ["norms", "capabilities", "authority"],
      ],
      [
        "runtime-upgrade",
        "Activation",
        "Locked immutable runtime: migrate state, rebind hooks; verify every worktree. Failure: exact rollback.",
        ["coordination"],
      ],
      [
        "runtime-reclamation",
        "Each removal",
        "After activation: reclaim unused generations; fresh operational dependencies + exact owned directory.",
        ["coordination"],
      ],
      [
        "runtime-reclamation-unknown",
        "UNKNOWN",
        "Defers deletion; preserves activation/partial results. Historical observations are not executable leases.",
        ["coordination", "recovery"],
      ],
      [
        "topology-owner",
        "Topology",
        "Policy: immutable package, not audited checkout. Selector fence is not global process isolation.",
        ["norms", "coordination"],
      ],
      [
        "runtime-family",
        "Report",
        "Activation report: hooks path/runtime; all worktrees checked/repaired; generations retained/removed.",
        ["coordination", "projection"],
      ],
    ];
    for (const [i, [id, key, value, semantics]] of entries.entries()) {
      // Four lanes need two more units before the first runtime row. The five
      // rows still end at the same baseline; glyph growth is audited below.
      const right = i >= 5,
        y =
          408 + (laneCount === 4 ? 2 : 0) + (i % 5) * (refresh ? 16 : laneCount === 4 ? 18 : 18.5);
      text(id + "-key", key, right ? 808 : 48, y, semantics, 12.5, "600");
      text(id + "-0", value, right ? 917 : 164, y, semantics);
      runtimeRows.push([id + "-key", id + "-0"]);
    }
  } else {
    const runtimeWidth =
      770 - 48 - quality.hard_gates.geometry_each_scale.semantic_peer_group_gap_px_at_reference_min;
    paragraph(
      "runtime",
      "One Git-common runtime coordinates worktrees/Leases: lane/holder/generation/expiry; not intent or permission.",
      48,
      428,
      runtimeWidth,
      ["coordination", "lanes"],
    );
    paragraph(
      "runtime-upgrade",
      "Locked immutable runtime: migrate state, rebind hooks; report every worktree. Exact rollback; retire after consumers discharge.",
      770,
      428,
      783,
      ["coordination"],
    );
    paragraph(
      "prewrite-facts",
      "Every prewrite: before writes, fresh root, branch role, actor, own four-field Lease, Git state, changed paths, official OpenSpec.",
      48,
      450,
      788,
      ["lanes", "authority"],
    );
    paragraph("tracked-write-order", writeText, 48, 468, 782, ["lanes", "authority"]);
    paragraph(
      "topology-owner",
      "Executable topology policy belongs to its immutable package; the audited checkout cannot override it.",
      860,
      468,
      693,
      ["norms", "coordination"],
    );
    paragraph(
      "prewrite-artifacts",
      "Artifacts: origin/existence/placement/effect differ; native producer, exact staged bytes, surviving consumers.",
      860,
      450,
      693,
      ["lanes", "norms"],
    );
  }
  const runnerSource = input.source.bindings.find((b) => b.id === "runner_mutation");
  if (!runnerSource) throw Error("Write-order source required");
  if (refresh) {
    const semantics = ["lanes", "candidate", "recovery"];
    text("refresh-key", "Refresh", 48, 488, semantics, 12.5, "600");
    text("refresh-options", [refresh.replay, refresh.merge].join(" · "), 164, 488, semantics);
    text("refresh-pending-key", "Pending", 808, 488, semantics, 12.5, "600");
    text("refresh-pending", refresh.pending, 917, 488, semantics);
    alignInkLeft("refresh-key", "runtime-key");
    alignInkLeft("refresh-options", "runtime-0");
    alignInkLeft("refresh-pending-key", "runtime-upgrade-key");
    alignInkLeft("refresh-pending", "runtime-upgrade-0");
    runtimeRows.push(["refresh-key", "refresh-options"]);
    runtimeRows.push(["refresh-pending-key", "refresh-pending"]);
  }
  d.sourceExplanations = [
    {
      id: "tracked-write-order",
      sourceId: "runner_mutation",
      sourceSha256: runnerSource.sha256,
      excerpt:
        "The write boundary is deliberately ordered: target path, repository root, context refresh, status, prewrite, write, then post-write audit.",
      labels: d.labels.filter((l) => l.id.startsWith("tracked-write-order-")).map((l) => l.id),
      orderedTerms: writeOrder,
      visibleText: writeText,
      effectAuthority: false,
      scope: "source-text-explanation",
    },
  ];
  const prewriteFacts = {
    source: "prewrite_admission",
    before: "tracked-mutation",
    appliesTo: lanes.map((l) => l.prewrite),
    labelIds: groups
      .find((g) => g.id === "runtime")
      .labels.filter((id) => id.startsWith("prewrite-")),
  };
  section("continuity");
  mark("exit-conditions", "gate", 1452, 769, 4, ["adoption_exit"]);
  mark("exit-retirement", "state", 1498, 769, 4, ["lane_retirement"]);
  edge("all-duties-retirement", "exit-conditions", "exit-retirement", "support", [
    "exit-controls-retirement",
  ]);
  text(
    "continuity-title",
    "Every lane handoff / exit",
    1210,
    779,
    ["recovery", "model", "exit"],
    18,
    "serif",
    "exit-conditions",
  );
  text("exit-retire-label", "Retire", 1522, 779, ["exit"], 12.5, "600", "exit-retirement");
  const continuityRows = [];
  for (const [i, [key, value, semantic]] of [
    ["Block", "Gap/contradiction: affected effects/retirement", ["model"]],
    ["If gap", "Counterexample; smallest model; recompile", ["model"]],
    ["Account", "Git/Attestations; unique work/results; loss-safe", ["recovery", "exit"]],
    ["Quiesce", "All writers; coordinate until disposal ends", ["recovery", "exit"]],
    ["Require", "Fresh authority; own exact preimage; duties met", ["recovery", "exit"]],
    ["Hold", "Unknown liveness/drift blocks disposal", ["recovery", "exit"]],
  ].entries()) {
    const id = "continuation-" + i,
      y = 800 + i * (separateReclamation ? 14.2 : 18);
    text(id + "-key", key, 1210, y, semantic, 12.5, "600", "exit-conditions");
    text(id + "-value", value, 1288, y, semantic, 12.5, "400", "exit-conditions");
    continuityRows.push([id + "-key", id + "-value"]);
  }
  const exitBinding = {
    appliesTo: lanes.map((l) => l.work),
    conditionLabels: continuityRows.flat(),
    admission: "exit-conditions",
    retirement: "exit-retirement",
  };
  if (separateReclamation) {
    text("exit-discharge-key", "Remove", 1210, 885.2, ["exit"], 12.5, "600", "exit-conditions");
    text(
      "exit-discharge",
      "Discharged runtime/install projections",
      1288,
      885.2,
      ["exit"],
      12.5,
      "400",
      "exit-conditions",
    );
    exitBinding.conditionLabels.push("exit-discharge-key", "exit-discharge");
    continuityRows.push(["exit-discharge-key", "exit-discharge"]);
  }
  const supportMarks = new Set([
    "exit-conditions",
    "exit-retirement",
    ...d.marks.filter((m) => m.id.startsWith("verification-")).map((m) => m.id),
  ]);
  const band = (id, ids) => ({
    id,
    labels: groups.filter((g) => ids.includes(g.id)).flatMap((g) => g.labels),
    marks: d.marks
      .filter((m) =>
        id === "support"
          ? supportMarks.has(m.id)
          : id === "core"
            ? !m.id.startsWith("protocol-") && !supportMarks.has(m.id)
            : id === "protocol-and-applications"
              ? m.id.startsWith("protocol-")
              : false,
      )
      .map((m) => m.id),
    paths: d.relations
      .filter((e) =>
        id === "support"
          ? supportMarks.has(e.source)
          : id === "core"
            ? !e.source.startsWith("protocol-") && !supportMarks.has(e.source)
            : id === "protocol-and-applications"
              ? e.source.startsWith("protocol-")
              : false,
      )
      .map((e) => e.id),
  });
  const peer = (id, axis, members) => ({ id, axis, groups: members });
  const groupLabels = (id) => groups.find((g) => g.id === id).labels;
  const prefixLabels = (prefix) => d.labels.filter((l) => l.id.startsWith(prefix)).map((l) => l.id);
  const separation = {
    ...(refresh
      ? {
          alignments: [
            {
              id: "header-scope",
              edge: "right",
              labels: ["kernel-scope", "maturity", "review-exit"],
            },
            {
              id: "header-review-baseline",
              edge: "baseline",
              labels: ["review", "review-exit"],
            },
            {
              id: "refresh-left-key",
              edge: "left",
              labels: ["runtime-key", "refresh-key"],
            },
            {
              id: "refresh-left-value",
              edge: "left",
              labels: ["runtime-0", "refresh-options"],
            },
            {
              id: "refresh-right-key",
              edge: "left",
              labels: ["runtime-upgrade-key", "refresh-pending-key"],
            },
            {
              id: "refresh-right-value",
              edge: "left",
              labels: ["runtime-upgrade-0", "refresh-pending"],
            },
            {
              id: "refresh-row",
              edge: "baseline",
              labels: ["refresh-key", "refresh-options", "refresh-pending-key", "refresh-pending"],
            },
          ],
        }
      : {}),
    bands: [
      band("core", [
        "intent",
        "parallel-work",
        "selection",
        "local-effects",
        "outcomes",
        "runtime",
      ]),
      band("protocol-and-applications", ["protocol", "resource-comparison"]),
      band("support", ["responsibilities", "verification", "continuity"]),
    ],
    tables: [
      ...(refresh ? [{ id: "header-review", rows: [["review", "review-exit"]] }] : []),
      { id: "responsibility-table", rows: responsibilityRows },
      { id: "lane-admission", rows: laneAdmissionRows },
      { id: "continuity-conditions", rows: continuityRows },
      ...(runtimeRows.length ? [{ id: "runtime-conditions", rows: runtimeRows }] : []),
    ],
    cellTables: [
      {
        id: "resource-bindings",
        columns: resourceTable.columns,
        rows: resourceTable.rows.map((r) => ({
          id: r.contract,
          cells: r.cells.map((c) => c.labels),
        })),
      },
    ],
    peers: [
      ...(runtimeRows.length
        ? [
            peer("runtime-columns", "x", [
              {
                id: "write-boundary",
                labels: [...runtimeRows.slice(0, 5).flat(), ...(refresh ? runtimeRows[10] : [])],
              },
              {
                id: "runtime-lifecycle",
                labels: [...runtimeRows.slice(5, 10).flat(), ...(refresh ? runtimeRows[11] : [])],
              },
            ]),
          ]
        : []),
      peer(
        "recovery-statuses",
        "x",
        [
          "protocol-refusal-text",
          "protocol-stale-text",
          "fresh-facts",
          "protocol-reject-text",
          "protocol-unknown-text",
        ].map((id) => ({ id, labels: [id] })),
      ),
      peer("lane-and-exploration", "x", [
        { id: "lane-admission", labels: prefixLabels("lane-admission-") },
        { id: "retention", labels: prefixLabels("retention-") },
      ]),
      peer("support-columns", "x", [
        { id: "responsibilities", labels: groupLabels("responsibilities") },
        { id: "verification", labels: groupLabels("verification") },
        { id: "continuity", labels: groupLabels("continuity") },
      ]),
      peer(
        "verification-headings",
        "x",
        ["verification-title", "verification-verifier-label", "verification-claim-label"].map(
          (id) => ({ id, labels: [id] }),
        ),
      ),
    ],
  };
  if (consumedAuthored.size !== authoredEdits.size) throw Error("Unknown authored static carrier");
  return {
    document: d,
    ...(authored ? { authoredCarriers: structuredClone(authored) } : {}),
    groups,
    lanes,
    leasePrewrite,
    selectedProvenance,
    repositoryLocalInputs,
    ...(capabilityContract ? { capabilityContract } : {}),
    ...(candidateAdmission ? { candidateAdmission } : {}),
    ...(feedbackPredicates ? { feedbackPredicates } : {}),
    ...(lossRecovery ? { lossRecovery } : {}),
    actionRecovery,
    exitBinding,
    prewriteFacts,
    ...(refresh
      ? {
          refresh: {
            ...refresh,
            node: "candidate_base_stale",
            labels: ["refresh-options", "refresh-pending"],
          },
        }
      : {}),
    resourceRows,
    resourceGrammar,
    resourceTable,
    admissionBindings,
    witnesses,
    routingMarks,
    routingEdges,
    conditionalConsequences,
    separation,
    semanticAcceptance: "UNVERIFIED",
    sourceDigest: input.digest,
    status: "DESIGN_CANDIDATE",
    note: "Complete obligation references are not proof of faithful visual explanation.",
  };
}
