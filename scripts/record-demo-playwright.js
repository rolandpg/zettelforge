/**
 * Record the ZettelForge demo as an animated GIF using Playwright.
 *
 * Usage:
 *   npx playwright test scripts/record-demo-playwright.js
 *   — or —
 *   node scripts/record-demo-playwright.js
 *
 * Output: docs/assets/demo.gif
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

// ── Simulated demo output (matches demo.py exactly) ────────────────────────
const LINES = [
  { text: "$ python -m zettelforge demo", delay: 600, style: "prompt" },
  { text: "", delay: 300 },
  {
    text: "============================================================",
    delay: 40,
  },
  { text: "  ZettelForge Demo — CTI Agentic Memory", delay: 40 },
  {
    text: "============================================================",
    delay: 40,
  },
  { text: "", delay: 200 },
  { text: "[1/4] Ingesting 5 CTI reports...", delay: 400, style: "header" },
  { text: "", delay: 150 },
  {
    text: "  [1/5] APT28 Lateral Movement Campaign",
    delay: 300,
    style: "title",
  },
  {
    text: "        Entities: APT28, Cobalt Strike, CVE-2024-3094, XAgent, T1021",
    delay: 60,
    style: "detail",
  },
  { text: "        Time: 847ms", delay: 60, style: "dim" },
  { text: "", delay: 200 },
  {
    text: "  [2/5] Lazarus Group Cryptocurrency Theft",
    delay: 300,
    style: "title",
  },
  {
    text: "        Entities: Lazarus Group, FALLCHILL, 185.29.8.18, CVE-2023-42793, T1195.002 (+1 more)",
    delay: 60,
    style: "detail",
  },
  { text: "        Time: 623ms", delay: 60, style: "dim" },
  { text: "", delay: 200 },
  {
    text: "  [3/5] Volt Typhoon Infrastructure Targeting",
    delay: 300,
    style: "title",
  },
  {
    text: "        Entities: Volt Typhoon, T1059.001, T1018",
    delay: 60,
    style: "detail",
  },
  { text: "        Time: 512ms", delay: 60, style: "dim" },
  { text: "", delay: 200 },
  { text: "  [4/5] CVE-2024-3094 Analysis", delay: 300, style: "title" },
  {
    text: "        Entities: CVE-2024-3094, APT28, a]f5b6a8c7d9e2...",
    delay: 60,
    style: "detail",
  },
  { text: "        Time: 591ms", delay: 60, style: "dim" },
  { text: "", delay: 200 },
  {
    text: "  [5/5] Ransomware Trends Q1 2025",
    delay: 300,
    style: "title",
  },
  {
    text: "        Entities: CVE-2023-4966, BlackCat, LockBit, Mimikatz, T1003",
    delay: 60,
    style: "detail",
  },
  { text: "        Time: 704ms", delay: 60, style: "dim" },
  { text: "", delay: 300 },
  {
    text: "------------------------------------------------------------",
    delay: 40,
  },
  {
    text: "[2/4] Entity recall by threat actor...",
    delay: 400,
    style: "header",
  },
  { text: "", delay: 150 },
  {
    text: '  Query: mm.recall_actor("apt28")',
    delay: 200,
    style: "code",
  },
  { text: "  Results: 2 notes found", delay: 200, style: "detail" },
  {
    text: '  Top hit: "APT28 (also known as Fancy Bear) has been observed using Cobalt Strike fo..."',
    delay: 100,
    style: "detail",
  },
  {
    text: "  Note: APT28 = Fancy Bear — aliases stored in entity_aliases.json",
    delay: 100,
    style: "dim",
  },
  { text: "", delay: 300 },
  {
    text: "------------------------------------------------------------",
    delay: 40,
  },
  {
    text: "[3/4] Semantic recall across all memories...",
    delay: 400,
    style: "header",
  },
  { text: "", delay: 150 },
  {
    text: '  Query: mm.recall("supply chain attacks on open source")',
    delay: 200,
    style: "code",
  },
  { text: "  Results: 3 notes found", delay: 200, style: "detail" },
  {
    text: '  [1] CVE-2024-3094 is a critical backdoor discovered in XZ Utils versions 5.6...',
    delay: 80,
    style: "detail",
  },
  {
    text: '  [2] Lazarus Group conducted a supply chain attack targeting cryptocurrency e...',
    delay: 80,
    style: "detail",
  },
  {
    text: '  [3] APT28 (also known as Fancy Bear) has been observed using Cobalt Strike f...',
    delay: 80,
    style: "detail",
  },
  { text: "", delay: 300 },
  {
    text: "------------------------------------------------------------",
    delay: 40,
  },
  {
    text: "[4/4] Knowledge graph built automatically",
    delay: 400,
    style: "header",
  },
  { text: "", delay: 150 },
  { text: "  Total unique entities: 18", delay: 100, style: "detail" },
  { text: "  Total entity-note mappings: 24", delay: 100, style: "detail" },
  { text: "", delay: 100 },
  {
    text: "    intrusion_set: 4 entities",
    delay: 60,
    style: "dim",
  },
  {
    text: "    attack_pattern: 6 entities",
    delay: 60,
    style: "dim",
  },
  { text: "    vulnerability: 3 entities", delay: 60, style: "dim" },
  { text: "    malware: 4 entities", delay: 60, style: "dim" },
  { text: "    ipv4_addr: 1 entities", delay: 60, style: "dim" },
  { text: "", delay: 200 },
  {
    text: "============================================================",
    delay: 40,
  },
  { text: "  Demo complete.", delay: 100 },
  { text: "", delay: 100 },
  { text: "  Next steps:", delay: 80 },
  {
    text: "    from zettelforge import MemoryManager",
    delay: 60,
    style: "code",
  },
  {
    text: '    mm = MemoryManager()  # persists to ~/.amem/',
    delay: 60,
    style: "code",
  },
  {
    text: '    mm.remember("your threat intel here")',
    delay: 60,
    style: "code",
  },
  { text: "", delay: 100 },
  { text: "  Docs: https://docs.threatrecall.ai", delay: 60, style: "dim" },
  {
    text: "  GitHub: https://github.com/rolandpg/zettelforge",
    delay: 60,
    style: "dim",
  },
  {
    text: "============================================================",
    delay: 40,
  },
];

// ── HTML template ───────────────────────────────────────────────────────────
function buildHTML() {
  return `<!DOCTYPE html>
<html>
<head>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: #1a1b26;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    min-height: 100vh;
    padding: 0;
  }
  #terminal {
    width: 720px;
    background: #1a1b26;
    border-radius: 10px;
    overflow: hidden;
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'SF Mono', 'Consolas', monospace;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
  }
  #titlebar {
    background: #24283b;
    padding: 10px 16px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .dot { width: 12px; height: 12px; border-radius: 50%; }
  .dot-red { background: #f7768e; }
  .dot-yellow { background: #e0af68; }
  .dot-green { background: #9ece6a; }
  #titlebar-text {
    color: #565f89;
    font-size: 12px;
    margin-left: 8px;
    font-family: -apple-system, sans-serif;
  }
  #content {
    padding: 16px 20px;
    font-size: 13.5px;
    line-height: 1.55;
    color: #a9b1d6;
    min-height: 520px;
    overflow: hidden;
  }
  .line { white-space: pre; }
  .line-prompt { color: #9ece6a; font-weight: bold; }
  .line-header { color: #7aa2f7; font-weight: bold; }
  .line-title { color: #bb9af7; }
  .line-detail { color: #a9b1d6; }
  .line-code { color: #73daca; }
  .line-dim { color: #565f89; }
  .cursor {
    display: inline-block;
    width: 8px;
    height: 16px;
    background: #c0caf5;
    animation: blink 1s step-end infinite;
    vertical-align: text-bottom;
  }
  @keyframes blink {
    50% { opacity: 0; }
  }
</style>
</head>
<body>
  <div id="terminal">
    <div id="titlebar">
      <span class="dot dot-red"></span>
      <span class="dot dot-yellow"></span>
      <span class="dot dot-green"></span>
      <span id="titlebar-text">zettelforge — bash</span>
    </div>
    <div id="content"></div>
  </div>
  <script>
    const lines = ${JSON.stringify(LINES)};
    const content = document.getElementById('content');
    let lineIdx = 0;

    // Signal to Playwright that we're done
    window.__demoState = 'running';

    function addLine() {
      if (lineIdx >= lines.length) {
        window.__demoState = 'done';
        return;
      }
      const l = lines[lineIdx];
      const div = document.createElement('div');
      div.className = 'line' + (l.style ? ' line-' + l.style : '');
      div.textContent = l.text;
      content.appendChild(div);
      // auto-scroll
      content.scrollTop = content.scrollHeight;
      lineIdx++;
      setTimeout(addLine, l.delay || 40);
    }
    addLine();
  </script>
</body>
</html>`;
}

// ── Recording ───────────────────────────────────────────────────────────────
async function record() {
  const outDir = path.join(__dirname, "..", "docs", "assets");
  fs.mkdirSync(outDir, { recursive: true });

  const htmlPath = path.join(outDir, "_demo-terminal.html");
  fs.writeFileSync(htmlPath, buildHTML());

  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 760, height: 580 },
    deviceScaleFactor: 2, // retina-quality
  });
  const page = await context.newPage();
  await page.goto(`file://${htmlPath}`);

  // Collect screenshots as frames
  const frames = [];
  const frameInterval = 100; // ms between frames
  const maxDuration = 25000; // safety cap

  const startTime = Date.now();
  while (Date.now() - startTime < maxDuration) {
    const state = await page.evaluate(() => window.__demoState);
    const buf = await page.screenshot({ type: "png" });
    frames.push(buf);
    if (state === "done") {
      // Capture a few more frames at the end for the final state
      for (let i = 0; i < 15; i++) {
        const endBuf = await page.screenshot({ type: "png" });
        frames.push(endBuf);
      }
      break;
    }
    await page.waitForTimeout(frameInterval);
  }

  await browser.close();

  // Write frames to temp PNGs, then use Playwright's built-in or ffmpeg
  // We'll use a simple approach: save frames and convert via Python/Pillow
  const framesDir = path.join(outDir, "_frames");
  fs.mkdirSync(framesDir, { recursive: true });

  for (let i = 0; i < frames.length; i++) {
    const fname = path.join(framesDir, `frame_${String(i).padStart(4, "0")}.png`);
    fs.writeFileSync(fname, frames[i]);
  }

  console.log(`Captured ${frames.length} frames to ${framesDir}`);
  console.log("Converting to GIF...");

  // Clean up HTML
  fs.unlinkSync(htmlPath);

  return { framesDir, outDir, frameCount: frames.length };
}

record()
  .then(({ framesDir, outDir, frameCount }) => {
    console.log(`Done. ${frameCount} frames in ${framesDir}`);
    console.log(
      `Run: python3 scripts/frames-to-gif.py ${framesDir} ${outDir}/demo.gif`
    );
  })
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
