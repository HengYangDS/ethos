// Pure observed-layout predicates; no browser startup or source replay.
export function viewportFindings(m, typography) {
  if (
    !m?.viewport ||
    !Array.isArray(m.texts) ||
    !m.texts.length ||
    !Number.isFinite(m.scrollWidth) ||
    !Number.isFinite(typography?.effective_font_px_min_at_reference)
  )
    throw Error("Incomplete browser observation");
  const failures = [];
  if (m.graphCount !== 1) failures.push({ code: "graph-count", count: m.graphCount });
  if (m.scrollWidth > m.viewport.width)
    failures.push({
      code: "horizontal-overflow",
      pixels: m.scrollWidth - m.viewport.width,
    });
  if (!m.subtitleVisible) failures.push({ code: "hidden-scope" });
  for (const [field, code] of [
    ["hiddenTexts", "hidden-graph-text"],
    ["overlaps", "overlap"],
    ["overflow", "clipped-graph-text"],
    ["occludedText", "occluded-text"],
    ["notesHidden", "hidden-notes"],
    ["supportOverlaps", "support-overlap"],
    ["supportOverflow", "support-overflow"],
  ]) {
    if (!Array.isArray(m[field])) throw Error("Incomplete browser observation: " + field);
    for (const item of m[field]) failures.push({ code, detail: item });
  }
  for (const detail of m.supportTruncations ?? [])
    failures.push({ code: "support-truncation", detail });
  for (const t of m.texts) {
    if (!Number.isFinite(t.effectiveFont)) throw Error("Incomplete text CTM");
    if (t.effectiveFont + 0.01 < typography.effective_font_px_min_at_reference)
      failures.push({
        code: "font-floor",
        text: t.text,
        actual: t.effectiveFont,
        minimum: typography.effective_font_px_min_at_reference,
      });
  }
  return failures;
}

/** A story is a scoped camera, not a complete-map screenshot. */
export function storyFindings(m, typography) {
  if (!m.story?.nodeId || !m.panel || !m.viewport) throw Error("Incomplete story observation");
  const failures = [],
    focal = m.texts.filter((t) => t.owner === m.story.nodeId);
  if (!focal.length) failures.push({ code: "missing-focal-text", node: m.story.nodeId });
  const aperture = {
    x: Math.max(0, m.panel.x),
    y: Math.max(0, m.panel.y),
    right: Math.min(m.viewport.width, m.panel.right),
    bottom: Math.min(m.viewport.height, m.panel.bottom),
  };
  for (const t of focal) {
    if (
      t.box.x < aperture.x - 1 ||
      t.box.right > aperture.right + 1 ||
      t.box.y < aperture.y - 1 ||
      t.box.bottom > aperture.bottom + 1
    )
      failures.push({
        code: "focal-outside-aperture",
        text: t.text,
        box: t.box,
        aperture,
      });
    if (
      t.opacity <= 0 ||
      !Number.isFinite(t.effectiveFont) ||
      t.effectiveFont + 0.01 < typography.effective_font_px_min_at_reference
    )
      failures.push({
        code: "focal-unreadable",
        text: t.text,
        font: t.effectiveFont,
        opacity: t.opacity,
      });
  }
  if (m.scrollWidth > m.viewport.width)
    failures.push({
      code: "horizontal-overflow",
      pixels: m.scrollWidth - m.viewport.width,
    });
  for (const [field, code] of [
    ["supportOverlaps", "support-overlap"],
    ["supportOverflow", "support-overflow"],
    ["occludedText", "occluded-text"],
  ])
    for (const detail of m[field]) failures.push({ code, detail });
  for (const detail of m.supportTruncations ?? [])
    failures.push({ code: "support-truncation", detail });
  return failures;
}
