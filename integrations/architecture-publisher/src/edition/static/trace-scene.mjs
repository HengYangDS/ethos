const TRACE_PAINT = {
  paper: "#f5f3ed",
  ink: "#29372f",
  muted: "#657064",
  line: "#637767",
  accepted: "#324f3e",
  proof: "#78684e",
  soft: "#e6eae1",
  ghost: "#b9bfb2",
};

const kinds = new Set([
  "state",
  "intent",
  "gate",
  "proof",
  "evidence",
  "junction",
  "worktree",
  "outcome",
]);
const TRACE_ARROW = { length: 8, halfWidth: 4, strokeWidth: 1.25 };
const TRACE_CORNER_RADIUS = 4;
const markStroke = (kind) =>
  kind === "evidence"
    ? 1.3
    : ["gate", "intent", "worktree"].includes(kind)
      ? 1.5
      : kind === "outcome"
        ? 2.5
        : 1.7;
function markPaintBox(m) {
  const half = markStroke(m.kind) / 2,
    rx = m.kind === "evidence" ? Math.max(m.r, 8) : m.r,
    ry = m.kind === "evidence" ? Math.max(m.r, 5) : m.r;
  return {
    x: m.x - rx - half,
    y: m.y - ry - half,
    width: 2 * (rx + half),
    height: 2 * (ry + half),
  };
}
const esc = (s) => s.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll('"', "&quot;");
function validateTraceDocument(d) {
  const marks = new Set();
  for (const m of d.marks) {
    if (marks.has(m.id)) throw new Error("duplicate mark");
    marks.add(m.id);
    if (!kinds.has(m.kind)) throw new Error(`unsupported mark kind ${m.kind}`);
  }
  const labels = new Set();
  for (const l of d.labels) {
    if (labels.has(l.id)) throw new Error("duplicate label");
    labels.add(l.id);
    if (/\p{Script=Han}/u.test(l.text.replaceAll("问道", ""))) throw new Error("unapproved Han");
    if (l.about && !marks.has(l.about)) throw new Error(`unknown label subject ${l.id}:${l.about}`);
  }
  const semantics = new Set(d.labels.filter((l) => l.text.trim()).flatMap((l) => l.semantics));
  for (const id of d.required) if (!semantics.has(id)) throw new Error(`missing semantics ${id}`);
  const byId = new Map(d.marks.map((m) => [m.id, m]));
  for (const aperture of d.apertures ?? []) {
    if (aperture.stateInput === aperture.admissionInput)
      throw new Error("effect requires independent admission and state inputs");
    if (byId.get(aperture.mark)?.kind !== "gate") throw new Error("effect aperture is not a gate");
    for (const [source, kind] of [
      [aperture.stateInput, "state"],
      [aperture.admissionInput, "admission"],
    ]) {
      if (
        !d.relations.some(
          (e) =>
            e.source === source &&
            e.target === aperture.mark &&
            (kind === "state"
              ? ["candidate-state", "accepted-state", "target-state"].includes(e.kind)
              : e.kind === "admission"),
        )
      )
        throw new Error(`missing ${kind} input at ${aperture.mark}`);
    }
    if (aperture.objectInput !== undefined) {
      if (
        [aperture.stateInput, aperture.admissionInput, aperture.mark].includes(aperture.objectInput)
      )
        throw new Error("effect requires independent object input");
      if (
        !d.relations.some(
          (e) =>
            e.source === aperture.objectInput &&
            e.target === aperture.mark &&
            e.kind === "object-binding",
        )
      )
        throw new Error(`missing object input at ${aperture.mark}`);
    }
  }
  const connected = new Set();
  for (const e of d.relations) {
    if (!marks.has(e.source) || !marks.has(e.target)) throw new Error(`unknown endpoint ${e.id}`);
    if (e.points.length < 2) throw new Error(`incomplete path ${e.id}`);
    for (const [id, p] of [
      [e.source, e.points[0]],
      [e.target, e.points.at(-1)],
    ]) {
      connected.add(id);
      const m = byId.get(id);
      const dx = Math.abs(p.x - m.x),
        dy = Math.abs(p.y - m.y);
      const attached =
        (Math.abs(dx - m.r) < 0.01 && dy <= m.r) || (Math.abs(dy - m.r) < 0.01 && dx <= m.r);
      if (!attached) throw new Error(`detached endpoint ${e.id}:${id}`);
    }
  }
  for (const id of marks) if (!connected.has(id)) throw new Error(`unconnected mark ${id}`);
  const segments = d.relations.flatMap((e) =>
    e.points.slice(1).map((z, i) => ({ id: e.id, a: e.points[i], z })),
  );
  for (let i = 0; i < segments.length; i++)
    for (let j = i + 1; j < segments.length; j++) {
      const a = segments[i],
        b = segments[j];
      if (a.id === b.id) continue;
      const horizontal = a.a.y === a.z.y && b.a.y === b.z.y && a.a.y === b.a.y;
      const vertical = a.a.x === a.z.x && b.a.x === b.z.x && a.a.x === b.a.x;
      const axis = horizontal ? "x" : vertical ? "y" : null;
      if (
        axis &&
        Math.min(Math.max(a.a[axis], a.z[axis]), Math.max(b.a[axis], b.z[axis])) >
          Math.max(Math.min(a.a[axis], a.z[axis]), Math.min(b.a[axis], b.z[axis]))
      )
        throw new Error(`overlapping relations ${a.id}/${b.id}`);
    }
}
export function compileTraceScene(d, measure) {
  validateTraceDocument(d);
  return {
    document: d,
    paint: { ...TRACE_PAINT },
    width: 1600,
    height: 900,
    referenceWidth: 1600,
    nodes: d.marks.map((m) => ({
      id: m.id,
      box: { x: m.x - m.r, y: m.y - m.r, width: m.r * 2, height: m.r * 2 },
      paintBox: markPaintBox(m),
      strokeWidth: markStroke(m.kind),
    })),
    texts: d.labels.map((l) => {
      const weight = l.weight ?? "400",
        m = measure(l.text, l.size, weight),
        g = m.glyph;
      if (
        g &&
        (![g.x, g.y, g.width, g.height].every(Number.isFinite) || g.width < 0 || g.height < 0)
      )
        throw Error("Invalid measured glyph " + l.id);
      const box = g
        ? {
            x: l.x + g.x,
            y: l.y - g.y - g.height,
            width: g.width,
            height: g.height,
          }
        : {
            x: l.x,
            y: l.y - m.ascent,
            width: m.width,
            height: m.ascent + m.descent,
          };
      return {
        id: l.id,
        text: l.text,
        fontSize: l.size,
        visible: true,
        semanticIds: l.semantics,
        box,
        baseline: l.y,
        weight,
        tone: l.tone ?? "ink",
        ...(g ? { glyphOffsetX: g.x } : {}),
      };
    }),
    edges: d.relations.map((r) => ({
      ...r,
      strokeWidth:
        r.kind === "accepted-state"
          ? 4
          : r.kind === "effect"
            ? 2
            : r.kind === "candidate-state"
              ? 2
              : r.kind === "feedback"
                ? 0.8
                : 1.15,
      arrow: r.arrow !== false,
      ...(r.arrow !== false ? { arrowGeometry: TRACE_ARROW } : {}),
    })),
    decorations: d.rules.map((r) => ({ ...r, strokeWidth: 1, role: "rule" })),
    requiredSemanticIds: d.required,
  };
}
const poly = (points) => points.map((p, i) => `${i ? "L" : "M"} ${p.x} ${p.y}`).join(" ");
function rounded(points) {
  if (points.length < 3) return poly(points);
  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 1; i < points.length - 1; i++) {
    const a = points[i - 1],
      b = points[i],
      c = points[i + 1];
    const ux = b.x - a.x,
      uy = b.y - a.y,
      vx = c.x - b.x,
      vy = c.y - b.y;
    const u = Math.hypot(ux, uy),
      v = Math.hypot(vx, vy);
    if (!u || !v || ux * vy - uy * vx === 0) {
      d += ` L ${b.x} ${b.y}`;
      continue;
    }
    const r = Math.min(TRACE_CORNER_RADIUS, u / 2, v / 2);
    d += ` L ${b.x - (ux / u) * r} ${b.y - (uy / u) * r} Q ${b.x} ${b.y} ${b.x + (vx / v) * r} ${b.y + (vy / v) * r}`;
  }
  const z = points.at(-1);
  return `${d} L ${z.x} ${z.y}`;
}

export function renderTraceSvg(s) {
  const colors = s.paint ?? TRACE_PAINT;
  if (Object.keys(TRACE_PAINT).some((key) => !/^#[a-fA-F0-9]{6}$/.test(colors[key])))
    throw Error("Invalid scene paint");
  const color = (name) => colors[name] ?? colors.ink;
  const marks = s.document.marks
    .map((m) => {
      const c = color(m.tone),
        common = `data-mark="${esc(m.id)}" data-mark-kind="${m.kind}"`;
      if (m.kind === "gate") {
        // Preserve every declared side contact. The ring expresses a bounded
        // conjunctive aperture; an inner seed marks its non-delegable decision.
        return `<g ${common} data-aperture="true"><circle cx="${m.x}" cy="${m.y}" r="${m.r}" fill="${colors.paper}" stroke="${c}" stroke-width="${markStroke(m.kind)}"/><circle cx="${m.x}" cy="${m.y}" r="${Math.max(2, m.r * 0.26)}" fill="${c}"/></g>`;
      }
      if (m.kind === "intent")
        return `<g ${common}><path d="M ${m.x - m.r} ${m.y - m.r} H ${m.x + m.r - 10} L ${m.x + m.r} ${m.y - m.r + 10} V ${m.y + m.r} H ${m.x - m.r} Z" fill="${colors.paper}" stroke="${c}" stroke-width="${markStroke(m.kind)}"/><path d="M ${m.x - m.r + 7} ${m.y - 5} H ${m.x + m.r - 7} M ${m.x - m.r + 7} ${m.y + 3} H ${m.x + m.r - 7}" fill="none" stroke="${c}" stroke-width="1"/></g>`;
      if (m.kind === "worktree")
        return `<g ${common} fill="none" stroke="${c}" stroke-width="${markStroke(m.kind)}"><circle cx="${m.x - m.r + 3}" cy="${m.y}" r="3"/><path d="M ${m.x - m.r + 3} ${m.y} H ${m.x + m.r - 3} M ${m.x} ${m.y} V ${m.y - m.r}"/><circle cx="${m.x + m.r - 3}" cy="${m.y}" r="3"/><circle cx="${m.x}" cy="${m.y - m.r + 3}" r="3"/></g>`;
      if (m.kind === "evidence")
        return `<g ${common} fill="none" stroke="${c}" stroke-width="${markStroke(m.kind)}"><path d="M ${m.x - m.r} ${m.y - m.r} H ${m.x + m.r} V ${m.y + m.r} H ${m.x - m.r} Z"/><path d="M ${m.x - 8} ${m.y - 5} H ${m.x + 8} M ${m.x - 8} ${m.y + 2} H ${m.x + 8}"/></g>`;
      return `<circle ${common} cx="${m.x}" cy="${m.y}" r="${m.r}" fill="${m.kind === "junction" ? c : colors.paper}" stroke="${c}" stroke-width="${markStroke(m.kind)}"/>`;
    })
    .join("");
  const edges = s.edges
    .map(
      (e) =>
        `<path data-edge="${esc(e.id)}" data-kind="${e.kind}" data-source="${esc(e.source)}" data-target="${esc(e.target)}" d="${rounded(e.points)}" fill="none" stroke="${["effect", "accepted-state"].includes(e.kind) ? colors.accepted : e.kind === "retain" ? colors.proof : colors.line}" stroke-width="${e.strokeWidth}"${["feedback", "refresh", "retain", "support", "observation"].includes(e.kind) ? ' stroke-dasharray="5 5"' : ""}${e.arrow ? ' marker-end="url(#arrow)"' : ""}/>`,
    )
    .join("");
  const labels = s.texts
    .map(
      (t) =>
        `<text data-id="${esc(t.id)}" data-semantics="${esc(t.semanticIds.join(" "))}" x="${t.box.x - (t.glyphOffsetX ?? 0)}" y="${t.baseline}" font-size="${t.fontSize}" font-weight="${t.weight === "serif" ? "400" : t.weight}" font-family="${t.weight === "serif" ? "Georgia" : "Avenir Next"}, sans-serif" fill="${color(t.tone)}">${esc(t.text)}</text>`,
    )
    .join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900" role="img" aria-labelledby="title desc" data-source-commit="${s.document.binding.commit}"><title id="title">${esc(s.document.title)}</title><desc id="desc">${esc(s.document.subtitle)} Terminal-design candidate; not an implementation claim.</desc><defs><marker id="arrow" markerUnits="userSpaceOnUse" markerWidth="${TRACE_ARROW.length}" markerHeight="${TRACE_ARROW.halfWidth * 2}" refX="${TRACE_ARROW.length}" refY="${TRACE_ARROW.halfWidth}" orient="auto"><path d="M 0 0 L ${TRACE_ARROW.length} ${TRACE_ARROW.halfWidth} L 0 ${TRACE_ARROW.halfWidth * 2}" fill="none" stroke="${colors.line}" stroke-width="${TRACE_ARROW.strokeWidth}"/></marker></defs><rect width="1600" height="900" fill="${colors.paper}"/>${s.document.rules.map((r) => `<path data-rule="${esc(r.id)}" d="${poly(r.points)}" stroke="${color(r.tone ?? "ghost")}" fill="none" stroke-width="1"/>`).join("")}${edges}${marks}${labels}</svg>`;
}
