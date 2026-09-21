import fs from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";

const digest = (b) => createHash("sha256").update(b).digest("hex");
const esc = (s) =>
  s
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
const TEMPLATE_SHA256 = "d6564c78ed8e32d42c590286ab50b593036ed7c5e871c0d8388d7583dca44675";

/** Remove only pinned template marks with no product or reader function.
 * Locale payloads, native controls, attribution and SVG slots remain exact. */
function removeTemplateDecorations(template) {
  if (digest(template) !== TEMPLATE_SHA256) throw Error("Unsupported native template digest");
  const seams = [
    [
      "editorial plate",
      /^    html\[data-preset="editorial"\] \.diagram-container::after \{[^}]*\}\n    html\[data-embed="true"\]\[data-preset="editorial"\] \.diagram-container::after \{ display: none; \}\n/gm,
      1,
    ],
    [
      "style headings",
      /^    html\[data-preset="(?:signal-flow|blueprint|editorial)"\] \.header-row::after \{[^}]*\}\n/gm,
      3,
    ],
    [
      "blueprint corners",
      /^    html\[data-preset="blueprint"\] \.diagram-container::after \{[^}]*\}\n/gm,
      1,
    ],
    [
      "ambient scan",
      /^    html\[data-motion-capable="true"\]\[data-preset="signal-flow"\]\[data-ambient-motion="running"\] \.diagram-container::before \{[^}]*\}\n/gm,
      1,
    ],
    ["badge attributes", /\n +data-preset-badge-[a-z-]+="[^"]*"/g, 4],
    ["heading ornament", /^        <div class="pulse-dot"><\/div>\n/gm, 1],
    [
      "card accent stripes",
      /^    html\[data-preset="(?:editorial|blueprint)"\] \.card::before \{[^}]*\}\n/gm,
      2,
    ],
  ];
  for (const [name, pattern, count] of seams) {
    if ([...template.matchAll(pattern)].length !== count)
      throw Error("Missing pinned " + name + " seam");
    template = template.replace(pattern, "");
  }
  const changes = [
    ["    .card-dot {\n", "    .card-dot {\n      display: none;\n"],
    [
      "    .card-header {\n      display: flex;\n      align-items: center;\n      gap: 0.5rem;",
      "    .card-header {\n      display: flex;\n      align-items: center;\n      gap: 0;",
    ],
    ["      margin-left: 1.75rem;", "      margin-left: 0;"],
  ];
  for (const [before, after] of changes) {
    if (template.split(before).length !== 2) throw Error("Missing pinned ornament-spacing seam");
    template = template.replace(before, after);
  }
  return template;
}

/** One pre-delivery policy for standalone diagrams and atlas pages. */
export async function applyNativePresentation(toolRoot) {
  const file = path.join(toolRoot, "assets/template.html"),
    before = await fs.readFile(file, "utf8");
  const after = removeTemplateDecorations(before);
  await fs.writeFile(file, after);
  return {
    schema: "ethos.native-presentation/v1",
    template: "assets/template.html",
    before: digest(before),
    after: digest(after),
    removed: [
      "template plate",
      "style headings",
      "blueprint corners",
      "ambient scan",
      "badge attributes",
      "heading ornament",
      "card accent stripes",
    ],
    suppressed: ["unbound card dots"],
    realigned: ["subtitle", "card headings"],
    scope:
      "Pinned template decoration only; native SVG, controls, scripts, palette and attribution unchanged.",
    browserAcceptance: "UNVERIFIED",
  };
}

/** Atlas is a long-form document, not a single-screen slide. Keep one native owner. */
function accountForAtlasNavigation(template) {
  const changes = [
    [
      "      function detailLevel() {",
      "      function detailLevel() {\n        if (document.querySelector('[data-ethos-atlas-navigation]')) return 'full';",
    ],
    [
      "      var cards = shell && shell.querySelector('.cards');",
      "      var cards = shell && shell.querySelector('.cards');\n      var atlasNavigation = shell && shell.querySelector('[data-ethos-atlas-navigation]');",
    ],
    [
      "          shell && diagram && svg && ratio >= WIDE_RATIO &&",
      "          shell && !atlasNavigation && diagram && svg && ratio >= WIDE_RATIO &&",
    ],
    [
      "outerHeight(header) + outerHeight(guided) + outerHeight(cards);",
      "outerHeight(header) + outerHeight(guided) + outerHeight(cards) + outerHeight(atlasNavigation);",
    ],
    [
      "[header, guided, cards].forEach(function (element) { if (element) resizeObserver.observe(element); });",
      "[header, guided, cards, atlasNavigation].forEach(function (element) { if (element) resizeObserver.observe(element); });",
    ],
  ];
  if (template.includes("var atlasNavigation ="))
    throw Error("Atlas reader budget already adapted");
  for (const [before, after] of changes) {
    if (template.split(before).length !== 2) throw Error("Unsupported native reader budget seam");
    template = template.replace(before, after);
  }
  return template;
}

/** Chapter controls describe reading actions, not graph-set arithmetic.
 * Keep native focus/handoff/playback ownership; remove only their diagnostic copy. */
function clarifyAtlasReader(template) {
  const functions = [
    [
      "buildChapterIndex",
      "1c637d4541f459b7a1a0caa719f6d35877a9c3024f724d2274e754f1640bf13c",
      `      function buildChapterIndex() {
        chapterButtons = [];
        chapterList.textContent = '';
        views.forEach(function (view, index) {
          var item = document.createElement('li');
          var button = document.createElement('button');
          button.type = 'button';
          button.className = 'guided-view-chapter';
          button.setAttribute('data-guided-view-id', view.id);
          button.setAttribute('aria-pressed', 'false');
          button.setAttribute('tabindex', index === 0 ? '0' : '-1');
          button.setAttribute('aria-label', viewerText('viewer.guided.chapter.open', { label: view.label }));
          button.title = view.label + (view.note ? ' — ' + view.note : '');
          var title = document.createElement('span');
          title.className = 'guided-view-chapter-title';
          title.textContent = view.label;
          button.appendChild(title);
          item.appendChild(button);
          chapterList.appendChild(item);
          chapterButtons.push(button);
        });
      }
`,
    ],
    [
      "syncChapterIndex",
      "e5a325eaef54aba7813c9b4c8eea1ac0031f0201d160951fe6ae65d31cb647bf",
      `      function syncChapterIndex() {
        chapterButtons.forEach(function (button, index) {
          var current = index === activeIndex;
          var position = activeIndex < 0 ? 'available' : (current ? 'current' : (index < activeIndex ? 'before' : 'after'));
          button.setAttribute('data-chapter-position', position);
          button.setAttribute('aria-pressed', current ? 'true' : 'false');
          button.setAttribute('tabindex', current || (activeIndex < 0 && index === 0) ? '0' : '-1');
          button.setAttribute('aria-label', viewerText(current ? 'viewer.guided.chapter.current' : 'viewer.guided.chapter.open', { label: views[index].label }));
          button.title = views[index].label + (views[index].note ? ' — ' + views[index].note : '');
          if (current) button.setAttribute('aria-current', 'step');
          else button.removeAttribute('aria-current');
          if (button.parentElement) button.parentElement.setAttribute('data-chapter-position', position);
        });
        if (activeIndex >= 0) centerChapterButton(chapterButtons[activeIndex]);
      }
`,
    ],
  ];
  for (const [name, expected, replacement] of functions) {
    const start = template.indexOf("      function " + name + "("),
      end = template.indexOf("\n      function ", start + 1);
    if (start < 0 || end < 0 || digest(template.slice(start, end)) !== expected)
      throw Error("Unsupported native chapter reader seam: " + name);
    template = template.slice(0, start) + replacement + template.slice(end);
  }
  const caption =
    "step.edgeLabels.slice(0, 3).join(' + ') + (step.edgeLabels.length > 3 ? viewerText('viewer.guided.caption.more', { count: step.edgeLabels.length - 3 }) : '')";
  if (template.split(caption).length !== 2)
    throw Error("Unsupported native relationship caption seam");
  template = template.replace(caption, "step.edgeLabels.join(' · ')");
  const handoff =
    /          var node = findNode\(anchor\);\n          var nodeLabel = node \? \(node.getAttribute\('data-node-label'\) \|\| anchor\) : anchor;\n          handoffReceipt.textContent = viewerText\('viewer.guided.handoff', \{[\s\S]*?          handoffReceipt.hidden = false;\n/g;
  if ([...template.matchAll(handoff)].length !== 1)
    throw Error("Unsupported native handoff receipt seam");
  template = template.replace(handoff, "");
  const guideOrdinals =
    /            <span class="diagram-guide-index" aria-hidden="true">0[1-6]<\/span>\n/g;
  if ([...template.matchAll(guideOrdinals)].length !== 6)
    throw Error("Unsupported native guide ordinal seams");
  template = template.replace(guideOrdinals, "");
  const guideGrid =
    "    .diagram-guide-action {\n      --guide-accent: var(--frontend-stroke);\n      display: grid;\n      grid-template-columns: auto minmax(0, 1fr) auto;";
  if (template.split(guideGrid).length !== 2) throw Error("Unsupported native guide grid seam");
  template = template.replace(
    guideGrid,
    guideGrid.replace("auto minmax(0, 1fr) auto", "minmax(0, 1fr) auto"),
  );
  return template;
}

/** Change English viewer copy at its single catalog owner, before localization.
 * Runtime messages, tooltips and rendered HTML receive the same wording. */
function clarifyAtlasMessages(source) {
  if (digest(source) !== "da0320ac6c002f421c516cb4921e9b806a4ba5b3e9a4f6cbcdef0b16e2917d47")
    throw Error("Unsupported native message catalog digest");
  const messages = {
    "viewer.guided.chapter.open": "Open chapter: {label}",
    "viewer.guided.chapter.current": "Current chapter: {label}",
    "viewer.guided.chapter.current.title": "{label} — current chapter",
    "viewer.motion.live": "Motion on",
    "viewer.motion.still": "Motion off",
    "viewer.motion.yielding.title": "Diagram motion enabled · yielding to {owner}",
    "viewer.guided.motionUnavailable": "Story playback unavailable while diagram motion is off",
    "viewer.guided.enableMotion": "Enable diagram motion to play the guided story",
    "viewer.route.motionRequired": "Automatic route playback requires diagram motion",
    "viewer.present.enter": "Enter presentation mode",
    "viewer.present.enter.title": "Presentation mode (F)",
    "viewer.present.exit": "Exit presentation mode",
    "viewer.present.exit.title": "Exit presentation mode (F or Escape)",
    "viewer.guide.inspecting": "Explore this diagram",
    "viewer.guide.map.hint": "Open the diagram overview and locate the current viewport.",
    "viewer.guide.lens.hint": "Compare node kinds and their authored relationships.",
    "viewer.guide.present": "Enter presentation mode",
    "viewer.guide.present.hint":
      "Read the current page with its notes and conditions; scroll for the full document.",
    "viewer.guide.story.hint": "Follow the chapters and authored relationships.",
    "viewer.guide.story.available.one": "Follow {count} chapter and its authored relationships.",
    "viewer.guide.story.available.other":
      "Follow {count} chapters and their authored relationships.",
    "viewer.passport.eyebrow": "Node details",
    "viewer.passport.close": "Close node details",
    "viewer.lens.instruction":
      "Choose up to two node kinds. One highlights its authored relationships; two compare only their direct links.",
    "viewer.radar.title": "Diagram overview",
    "viewer.radar.openFull": "Open full diagram overview",
    "viewer.radar.open": "Open overview",
    "viewer.radar.close": "Close diagram overview",
    "viewer.radar.space": "The diagram overview needs more visible space.",
    "viewer.radar.nodes": "Diagram overview nodes",
    "viewer.radar.focus": "Focus {label} from the diagram overview",
    "viewer.radar.compacted": "Overview compacted to avoid covering node details or map controls.",
    "viewer.radar.cancelWaiting": "Cancel the diagram overview waiting for more space",
    "viewer.radar.needsSpace": "The diagram overview needs more visible space",
    "viewer.nav.radar": "Open diagram overview",
    "viewer.nav.radar.title": "Diagram overview (M)",
  };
  for (const [key, value] of Object.entries(messages)) {
    const pattern = new RegExp(
      "(  '" + key.replaceAll(".", "\\.") + "': \\[)'(?:[^'\\\\]|\\\\.)*'(,)",
      "g",
    );
    if ([...source.matchAll(pattern)].length !== 1)
      throw Error("Unsupported native message key: " + key);
    source = source.replace(pattern, (_, prefix, comma) => prefix + JSON.stringify(value) + comma);
  }
  return { source, keys: Object.keys(messages) };
}

/** Correct native camera/follow coordination; preserve one playback owner. */
function adaptAtlasStoryCamera(template) {
  const changes = [
    [
      "        state.y = Math.min(0, Math.max(height - height * state.scale, state.y));",
      `        var visibleTop = 0, visibleBottom = height;
        if (state.mode === 'semantic' && document.querySelector('[data-ethos-atlas-navigation]')) {
          var svgTop = container.getBoundingClientRect().top + (svg.offsetTop || 0);
          visibleTop = Math.max(0, -svgTop);
          visibleBottom = Math.max(1, Math.min(height, window.innerHeight - svgTop));
        }
        state.y = Math.min(visibleTop, Math.max(visibleBottom - height * state.scale, state.y));`,
    ],
    [
      `        var visibleTop = Math.max(0, -containerRect.top);
        var visibleBottom = Math.min(svgHeight, window.innerHeight - containerRect.top);`,
      `        var svgTop = containerRect.top + (svg.offsetTop || 0);
        var visibleTop = Math.max(0, -svgTop);
        var visibleBottom = Math.min(svgHeight, window.innerHeight - svgTop);`,
    ],
    [
      `        if (visibleBottom - visibleTop >= 240) {
          top = Math.max(top, visibleTop + padding);
          bottom = Math.min(bottom, visibleBottom - Math.max(padding, 72));
        }`,
      `        if (visibleBottom - visibleTop >= 240) {
          top = Math.max(top, visibleTop + padding);
          bottom = Math.min(bottom, visibleBottom - Math.max(padding, 72));
        } else if (visibleBottom > visibleTop && document.querySelector('[data-ethos-atlas-navigation]')) {
          // A short document aperture is still the viewport, never the full SVG.
          var shortPadding = Math.min(24, (visibleBottom - visibleTop) / 8);
          top = visibleTop + shortPadding;
          bottom = visibleBottom - shortPadding;
        }`,
    ],
    [
      "          reason: options.manual === true ? 'story-beat' : 'story-follow',",
      "          reason: options.manual === true ? 'story-beat' : 'story-follow',\n          focalId: step.nodeId,",
    ],
    [
      "        targetScale = Math.max(1, Math.min(maxScale, targetScale));",
      `        targetScale = Math.max(1, Math.min(maxScale, targetScale));
        // Stage fit can shrink a tall SVG before the camera applies its zoom.
        // Restore document-width scale for the active beat, not for the whole map.
        // Keep the native zoom bound and fit the complete focal node in the aperture.
        var stageFocal = options.focalId && document.querySelector('[data-ethos-atlas-navigation]')
          && boxesFor([options.focalId], false)[0];
        if (stageFocal && contentScale > 0) {
          var widthScale = svgWidth / viewBox.width / contentScale;
          var focalFit = Math.min((right - left) / (stageFocal.width * contentScale),
            (bottom - top) / (stageFocal.height * contentScale));
          var readableScale = Math.min(3, focalFit, Math.ceil(widthScale * 100) / 100);
          if (widthScale > 1) targetScale = Math.max(targetScale, readableScale);
        }`,
    ],
    [
      "        target.y = (top + bottom) / 2 - (bounds.y + bounds.height / 2) * target.scale;",
      `        target.y = (top + bottom) / 2 - (bounds.y + bounds.height / 2) * target.scale;
        // Context frames the scene; the current beat must remain in the visible aperture.
        var focalBox = options.focalId && boxesFor([options.focalId], false)[0];
        if (focalBox) {
          var focalLeft = (contentOffsetX + focalBox.x * contentScale) * target.scale;
          var focalTop = (contentOffsetY + focalBox.y * contentScale) * target.scale;
          var focalWidth = focalBox.width * contentScale * target.scale;
          var focalHeight = focalBox.height * contentScale * target.scale;
          target.x = focalWidth <= right - left
            ? Math.max(left - focalLeft, Math.min(right - focalLeft - focalWidth, target.x))
            : (left + right) / 2 - focalLeft - focalWidth / 2;
          target.y = focalHeight <= bottom - top
            ? Math.max(top - focalTop, Math.min(bottom - focalTop - focalHeight, target.y))
            : (top + bottom) / 2 - focalTop - focalHeight / 2;
        }`,
    ],
  ];
  for (const [before, after] of changes) {
    if (template.split(before).length !== 2) throw Error("Unsupported native story camera seam");
    template = template.replace(before, after);
  }
  // A pending handoff can outlive pause -> resume. Keep the native playback
  // generation as the single cancellation authority for both deferred starts.
  const start =
    "        renderPlayback();\n        afterHandoff(function () {\n          if (!playing) return;";
  if (template.split(start).length !== 3) throw Error("Unsupported native playback-start seams");
  template = template.replaceAll(
    start,
    "        renderPlayback();\n        var playbackGeneration = ++storyPlaybackGeneration;\n        afterHandoff(function () {\n          if (!playing || playbackGeneration !== storyPlaybackGeneration) return;",
  );
  const chapter =
    "          activate(destinationIndex, { playback: true });\n          afterHandoff(function () {\n            if (!playing || activeIndex !== destinationIndex) return;";
  if (template.split(chapter).length !== 2) throw Error("Unsupported native chapter-playback seam");
  template = template.replace(
    chapter,
    "          activate(destinationIndex, { playback: true });\n          var playbackGeneration = ++storyPlaybackGeneration;\n          afterHandoff(function () {\n            if (!playing || playbackGeneration !== storyPlaybackGeneration || activeIndex !== destinationIndex) return;",
  );
  return template;
}

/** Native exporter policy: readable full diagram, never a fixed-height thumbnail.
 * The caller supplies the admitted source typography floor. No new exporter. */
function adaptAtlasExports(template, minimumFontPx) {
  if (!Number.isFinite(minimumFontPx) || minimumFontPx <= 0)
    throw Error("Source export typography floor required");
  const changes = [
    [
      "        if (target.closest('[data-node-id], [data-relationship-hit-key], .overview-map')) return;",
      "        if (target.closest('[data-node-id], [data-relationship-hit-key], .overview-map, .export-wrap')) return;",
    ],
    [
      "      var SHARE_CARD_WIDTH = 1200;\n      var SHARE_CARD_HEIGHT = 630;",
      "      var SHARE_CARD_WIDTH = 1600;\n      var SHARE_CARD_HEIGHT = 0;",
    ],
    [
      "      function renderShareCard(options) {",
      `      function atlasShareLayout(width, height, minFont) {
        if (![width,height,minFont].every(Number.isFinite) || width <= 0 || height <= 0 || minFont <= 0) throw Error('Invalid export dimensions');
        var scale = Math.max((1600 - 72) / width, ${minimumFontPx} / minFont);
        var result = { width: Math.ceil(width * scale) + 72, height: Math.ceil(height * scale) + 168, scale: scale };
        if (result.width * result.height > MAX_CANVAS_PIXELS) throw Error('A readable image exceeds the canvas limit; export SVG instead.');
        return result;
      }

      function atlasShareLines(ctx, text, maxWidth) {
        var lines = [], line = '';
        String(text || '').trim().split(/\\s+/).forEach(function (word) {
          if (ctx.measureText(word).width > maxWidth) throw Error('Export scope contains an unbreakable label; use SVG.');
          var next = line ? line + ' ' + word : word;
          if (line && ctx.measureText(next).width > maxWidth) { lines.push(line); line = word; }
          else line = next;
        });
        if (line) lines.push(line);
        return lines;
      }

      function renderShareCard(options) {`,
    ],
    [
      "        var sourceScale = Math.min(2, pickSafeScale(vb.width, vb.height));",
      `        var minFont = Math.min.apply(null, Array.prototype.map.call(svg.querySelectorAll('text'), function (node) { return parseFloat(getComputedStyle(node).fontSize); }));
        var layout = atlasShareLayout(vb.width, vb.height, minFont);
        var sourceScale = layout.scale;`,
    ],
    [
      "        var data = serializeSvg(sourceScale, { routeSnapshot: routeSnapshot, reachSnapshot: reachSnapshot });",
      "        var data = serializeSvg(sourceScale, { routeSnapshot: routeSnapshot, reachSnapshot: reachSnapshot, omitAtlasFrame: true });",
    ],
    [
      "        // Scale width/height so the browser rasterizes the vectors at target",
      `        if (!opts.omitAtlasFrame) {
          var minDiagramFont = Math.min.apply(null, Array.prototype.map.call(svg.querySelectorAll('text'), function (node) { return parseFloat(getComputedStyle(node).fontSize); }));
          var frameMinimum = Math.max(18, minDiagramFont);
          vb = { x: vb.x, y: vb.y - 112, width: vb.width, height: vb.height + 168 };
          clone.setAttribute('viewBox', [vb.x, vb.y, vb.width, vb.height].join(' '));
          var frame = document.createElementNS('http://www.w3.org/2000/svg', 'g');
          frame.setAttribute('data-atlas-export-scope', 'diagram-only');
          function frameText(text, y, size, weight) {
            var line = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            line.setAttribute('x', vb.x + 36); line.setAttribute('y', y);
            line.setAttribute('font-size', size); line.setAttribute('font-weight', weight);
            line.setAttribute('fill', 'var(--text)'); line.textContent = text; frame.appendChild(line);
          }
          frameText(document.querySelector('.header h1').textContent, vb.y + 44, 30, 700);
          frameText(document.querySelector('.header .subtitle').textContent, vb.y + 78, Math.max(20, frameMinimum), 400);
          frameText('Diagram only · Full protocol and notes: HTML atlas', vb.y + vb.height - 20, frameMinimum, 400);
          clone.appendChild(frame);
        }
        // Scale width/height so the browser rasterizes the vectors at target`,
    ],
    [
      "        var bgRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');",
      `        var bgRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        bgRect.setAttribute('x', vb.x); bgRect.setAttribute('y', vb.y);`,
    ],
    [
      "              canvas.width = SHARE_CARD_WIDTH;\n              canvas.height = SHARE_CARD_HEIGHT;",
      `              canvas.width = layout.width;
              canvas.height = layout.height;`,
    ],
    [
      "              var fittedTitle = fitCanvasText(ctx, title, SHARE_CARD_WIDTH - SHARE_CARD_PADDING * 2 - 330, 29, 18, '700');",
      "              var fittedTitle = fitCanvasText(ctx, title, layout.width - SHARE_CARD_PADDING * 2, 29, 18, '700');",
    ],
    [
      "              var fittedSubtitle = fitCanvasText(ctx, subtitle, SHARE_CARD_WIDTH - SHARE_CARD_PADDING * 2 - 280, 13, 11, '500');\n              ctx.fillText(fittedSubtitle, SHARE_CARD_PADDING, 87);",
      `              ctx.font = "500 14px 'ETHOS JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
              scopeLines.forEach(function (line, index) { ctx.fillText(line, SHARE_CARD_PADDING, 87 + index * 20); });`,
    ],
    [
      "              ctx.fillText(cardLabel, SHARE_CARD_WIDTH - SHARE_CARD_PADDING, 50);",
      `              // The page title names the product. Template/style/theme badges add no meaning.
              ctx.fillStyle = muted;
              ctx.fillText('Target architecture · Diagram only · Full protocol and notes: HTML atlas', layout.width - SHARE_CARD_PADDING, layout.height - 24);`,
    ],
    [
      "                  : subtitleNode ? subtitleNode.textContent : \x27\x27;",
      `                  : subtitleNode ? subtitleNode.textContent : '';
              if (routeSnapshot || reachSnapshot) subtitle = (subtitleNode ? subtitleNode.textContent + ' · ' : '') + subtitle + ' · Relationship highlight, not execution authority';`,
    ],
    [
      "              ctx.fillStyle = bg;\n              ctx.fillRect(0, 0, SHARE_CARD_WIDTH, SHARE_CARD_HEIGHT);",
      `              ctx.font = "500 14px 'ETHOS JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
              var scopeLines = atlasShareLines(ctx, subtitle, layout.width - SHARE_CARD_PADDING * 2);
              var extraHeader = Math.max(0, scopeLines.length - 1) * 20;
              var atlasShareHeader = SHARE_CARD_HEADER + extraHeader;
              layout.height += extraHeader;
              if (layout.width * layout.height > MAX_CANVAS_PIXELS) throw Error('A readable image exceeds the canvas limit; export SVG instead.');
              canvas.height = layout.height;
              ctx.fillStyle = bg;
              ctx.fillRect(0, 0, layout.width, layout.height);`,
    ],
    [
      "svg[data-share-route] [data-node-id], svg[data-share-route] [data-edge-from] { opacity: 0.18; }",
      "svg[data-share-route] [data-node-id], svg[data-share-route] [data-edge-from] { opacity: 1; }",
    ],
    [
      "svg[data-share-reach] [data-node-id], svg[data-share-reach] [data-edge-from] { opacity: 0.14; }",
      "svg[data-share-reach] [data-node-id], svg[data-share-reach] [data-edge-from] { opacity: 1; }",
    ],
    [
      "              var availableWidth = SHARE_CARD_WIDTH - SHARE_CARD_PADDING * 2;\n              var availableHeight = SHARE_CARD_HEIGHT - SHARE_CARD_HEADER - SHARE_CARD_PADDING;",
      `              var availableWidth = layout.width - SHARE_CARD_PADDING * 2;
              var availableHeight = layout.height - atlasShareHeader - 56;`,
    ],
    [
      "              var drawY = SHARE_CARD_HEADER + (availableHeight - drawHeight) / 2;",
      "              var drawY = atlasShareHeader + (availableHeight - drawHeight) / 2;",
    ],
    [
      "                else resolve(blob);\n              }, 'image/png');",
      `                else { blob.atlasDimensions = { width: layout.width, height: layout.height }; resolve(blob); }
              }, 'image/png');`,
    ],
    [
      "      function recordExportReceipt(format, blob, canonical, dimensions, variant, routeStateClean, reachStateClean) {",
      `      function recordExportReceipt(format, blob, canonical, dimensions, variant, routeStateClean, reachStateClean) {
        if (blob.atlasDimensions) dimensions = blob.atlasDimensions;`,
    ],
  ];
  for (const [before, after] of changes) {
    if (template.split(before).length !== 2)
      throw Error("Unsupported native export seam: " + before.slice(0, 75));
    template = template.replace(before, after);
  }
  if (template.split("1200&times;630 PNG").length !== 4)
    throw Error("Unsupported share menu dimension hints");
  template = template.replaceAll("1200&times;630 PNG", "Readable PNG · adaptive height");
  return template;
}

/** A page catalog is navigation, never a second semantic graph. */
export function validateAtlasCatalog(catalog) {
  if (
    catalog?.schema !== "ethos.native-atlas/v1" ||
    !/^[a-f0-9]{64}$/.test(catalog.sourceDigest ?? "")
  )
    throw Error("Invalid atlas source binding");
  if (!Array.isArray(catalog.pages) || catalog.pages.length < 2)
    throw Error("Atlas pages required");
  const ids = new Set(),
    paths = new Set();
  for (const p of catalog.pages) {
    if (!/^[a-z][a-z0-9-]*$/.test(p.id ?? "") || ids.has(p.id))
      throw Error("Invalid or duplicate atlas identity");
    ids.add(p.id);
    if (
      typeof p.label !== "string" ||
      !p.label.trim() ||
      p.label.length > 48 ||
      /[\r\n]/.test(p.label) ||
      /\p{Script=Han}/u.test(p.label.replaceAll("问道", ""))
    )
      throw Error("Invalid atlas label");
    if (
      typeof p.path !== "string" ||
      !/^([a-z0-9][a-z0-9-]*\/)*index\.html$/.test(p.path) ||
      paths.has(p.path)
    )
      throw Error("Invalid or duplicate atlas path");
    paths.add(p.path);
  }
  if (catalog.pages[0].id !== "overview" || catalog.pages[0].path !== "index.html")
    throw Error("Overview must be the sole root entry");
  return catalog;
}

function renderAtlasNavigation(catalog, pageId) {
  validateAtlasCatalog(catalog);
  const current = catalog.pages.find((p) => p.id === pageId);
  if (!current) throw Error("Unknown atlas page");
  const links = catalog.pages
    .map((p) => {
      const href = path.posix.relative(path.posix.dirname(current.path), p.path) + "?theme=light";
      return `<a href="${esc(href)}"${p.id === pageId ? ' aria-current="page"' : ""}>${esc(p.label)}</a>`;
    })
    .join("\n");
  return `<style id="ethos-atlas-navigation-style">
/* Functional helper text must not inherit the preset's decorative faint ink. */
html[data-preset="editorial"][data-theme]{--text-dim:var(--text-muted);--text-faint:var(--text-muted)}
/* In a long atlas, desktop actions scroll away with the header. Stage/embed retain native rules. */
@media (min-width:721px){html[data-preset]:not([data-present="true"]):not([data-embed="true"]) .toolbar{position:absolute}}
/* A complete atlas is a document, including in presentation. Do not trade
   essential conditions or readable type for a finite-height stage. Preserve
   native camera/playback; document scrolling is not a second layout engine. */
html[data-present="true"][data-preset]:not([data-embed="true"]) body{height:auto;min-height:100dvh;overflow:visible}
html[data-present="true"][data-preset]:not([data-embed="true"]) .container{display:block;height:auto;max-width:1440px}
html[data-present="true"][data-preset]:not([data-embed="true"]) .container > .cards{display:grid}
html[data-present="true"][data-preset]:not([data-embed="true"]) .container > :is([data-resource-comparison],[data-verification-details],[data-write-boundary]){display:block}
html[data-present="true"][data-preset]:not([data-embed="true"]) .diagram-container{display:block;flex:none}
html[data-present="true"][data-preset]:not([data-embed="true"]) .diagram-container > svg{height:auto;width:100%;flex:none}
html[data-present="true"][data-preset]:not([data-embed="true"]) .subtitle{display:block;overflow:visible;white-space:normal}
html[data-present="true"][data-preset]:not([data-embed="true"]) .header{margin-bottom:24px}
html[data-present="true"][data-preset]:not([data-embed="true"]) .guided-views{margin-bottom:16px}
@media (min-width:721px){html[data-present="true"][data-preset]:not([data-embed="true"]) .toolbar{position:absolute}}
/* Tags here contain authority, validity and outcome qualifiers. Level of
   detail may guide attention, never erase those conditions from the graph. */
html[data-preset] .diagram-container[data-detail-level="map"] svg [data-detail],
html[data-preset] .diagram-container[data-detail-level="read"] svg [data-detail]{opacity:1;pointer-events:auto}
html[data-preset] .diagram-container[data-detail-level="map"] svg [data-detail-anchor]{transform:none}
/* Chapter names are the controls. Keep native progress separately; no graph
   counters, diagnostic deltas or decorative ordinals in the chapter index. */
html[data-preset] .guided-views[data-active-view="all"]{grid-template-columns:minmax(0,1fr) auto;gap:8px 16px}
html[data-preset] .guided-views[data-active-view="all"] .guided-view-index{grid-column:1 / -1;grid-row:2;padding:8px 0 0;border-left:0;border-top:1px solid var(--panel-border)}
html[data-preset] .guided-view-chapters{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));gap:8px;overflow:visible}
html[data-preset] .guided-view-chapters li{min-width:0}
html[data-preset] .guided-view-chapter{grid-template-columns:minmax(0,1fr);gap:0;align-items:center;overflow:visible}
html[data-preset] .guided-view-chapter-title{grid-column:1;grid-row:1;white-space:normal;overflow:visible;text-overflow:clip;font-size:12px;line-height:1.4}
html[data-preset] .guided-story-caption{grid-template-columns:72px minmax(0,1fr) minmax(160px,22%);gap:6px 14px;overflow:visible}
html[data-preset] .guided-story-caption :is(strong,small){white-space:normal;overflow:visible;text-overflow:clip;font-size:12px;line-height:1.5}
html[data-preset] .guided-story-caption-next{min-width:0;max-width:none}
html[data-preset] .guided-view-copy > :is(strong,small){white-space:normal;overflow:visible;text-overflow:clip}
@media(max-width:720px){html[data-preset] .guided-story-caption{grid-template-columns:56px minmax(0,1fr)}html[data-preset] .guided-story-caption-next{grid-column:2;grid-row:3;border-left:0;padding-left:0}}
/* Notes share native document flow; whitespace, not repeated boxes, separates ideas. */
html[data-preset] .container > .cards{grid-template-columns:repeat(auto-fit,minmax(min(100%,360px),1fr));gap:32px 40px;margin-top:48px;align-items:start}
html[data-preset] .container > .cards > .card{padding:0;border:0;border-radius:0;background:none;box-shadow:none;min-width:0}
html[data-preset] .container > .cards > .card::before,html[data-preset] .container > .cards > .card::after{content:none}
html[data-preset] .container > .cards .card-header{gap:0;margin-bottom:16px}
html[data-preset] .container > .cards .card-dot{display:none}
html[data-preset] .container > .cards h3{font-size:18px;line-height:1.35}
html[data-preset] .container > .cards ul{font:14px/1.7 system-ui,sans-serif;overflow-wrap:anywhere}
html[data-preset] .container > .cards li{margin-bottom:14px}
html[data-preset] .container > .cards li:last-child{margin-bottom:0}
.ethos-atlas-navigation{display:flex;flex-wrap:wrap;align-items:center;gap:8px 24px;margin:0 0 22px;padding:0 0 14px;border-bottom:1px solid var(--panel-border);font:500 14px/1.6 system-ui,sans-serif}
.ethos-atlas-navigation a{color:var(--text-muted);text-decoration:none;padding:4px 0;text-underline-offset:6px}
.ethos-atlas-navigation a[aria-current="page"]{color:var(--text);text-decoration:underline;text-decoration-thickness:2px}
.ethos-atlas-navigation a:hover{text-decoration:underline;color:var(--text)}
.ethos-atlas-navigation a:focus-visible{outline:2px solid currentColor;outline-offset:5px}
@media print{.ethos-atlas-navigation{display:none}}
</style>
<nav class="ethos-atlas-navigation no-print" data-ethos-atlas-navigation aria-label="Architecture pages">
${links}
</nav>
`;
}

/** Apply before native validate/deliver in the disposable pinned toolchain. */
export async function applyAtlasNavigation(
  toolRoot,
  catalog,
  pageId,
  expectedTemplateDigest,
  exportTypographyFloor,
) {
  const navigation = renderAtlasNavigation(catalog, pageId),
    file = path.join(toolRoot, "assets/template.html");
  const before = await fs.readFile(file, "utf8");
  if (digest(before) !== (expectedTemplateDigest ?? TEMPLATE_SHA256))
    throw Error("Unsupported native template digest");
  const clean = expectedTemplateDigest === undefined ? removeTemplateDecorations(before) : before;
  if (/content:\s*attr\(data-preset-badge-/.test(clean))
    throw Error("Native presentation must precede atlas navigation");
  const marker = "    <!-- Main Diagram -->";
  if (before.split(marker).length !== 2) throw Error("Ambiguous native diagram seam");
  const navigated = adaptAtlasStoryCamera(
    clarifyAtlasReader(accountForAtlasNavigation(clean.replace(marker, navigation + marker))),
  );
  const after =
    exportTypographyFloor === undefined
      ? navigated
      : adaptAtlasExports(navigated, exportTypographyFloor);
  const messagesFile = path.join(toolRoot, "renderers/shared/i18n.mjs"),
    messagesBefore = await fs.readFile(messagesFile, "utf8");
  const messagesAfter = clarifyAtlasMessages(messagesBefore);
  await fs.writeFile(file, after);
  await fs.writeFile(messagesFile, messagesAfter.source);
  return {
    schema: "ethos.native-atlas-navigation/v1",
    pageId,
    sourceDigest: catalog.sourceDigest,
    catalogObjectSha256: digest(JSON.stringify(catalog)),
    template: "assets/template.html",
    before: digest(before),
    after: digest(after),
    readerBudget: {
      owner: "Archify.readerLayout",
      mode: "document-flow",
      included: ["atlas-navigation"],
      newLayoutControllers: 0,
    },
    storyCamera: {
      owner: "Archify.view",
      focus: "current-beat",
      viewport: "visible-svg-aperture",
      newLayoutControllers: 0,
    },
    playbackHandoff: {
      owner: "Archify.guidedViews",
      cancellation: "existing-storyPlaybackGeneration",
      newControllers: 0,
    },
    chapterControls: {
      owner: "Archify.guidedViews",
      labels: "chapter-names",
      removed: [
        "focus-delta counts",
        "node-stop counts",
        "decorative ordinals",
        "ordinal handoff receipt",
      ],
      relationshipCaptions: "complete-labels",
      newControllers: 0,
    },
    readerMessages: {
      owner: "Archify.i18n",
      path: "renderers/shared/i18n.mjs",
      before: digest(messagesBefore),
      after: digest(messagesAfter.source),
      locale: "en",
      keys: messagesAfter.keys,
    },
    presentation: {
      owner: "Archify.presentation",
      layout: "scrolling-document",
      notes: "retained",
      qualifiers: "always-visible",
      newControllers: 0,
    },
    exports:
      exportTypographyFloor === undefined
        ? null
        : {
            owner: "Archify.exportMenu",
            minimumFontPx: exportTypographyFloor,
            shareLayout: "complete-diagram-adaptive-height",
            scope: "Diagram only; full protocol and notes remain in HTML",
            newControllers: 0,
          },
    scope:
      "HTML navigation, decoration, contrast and normal-flow notes, including presentation; preserve zoom-level semantic qualifiers. Native camera follows the current beat and native playback generation cancels superseded handoff callbacks. No graph or SVG geometry modification.",
    browserAcceptance: "UNVERIFIED",
  };
}
