# ZettelForge — Brand Identity

> Canonical reference for agents, designers, and contributors producing any visual
> artifact for ZettelForge: diagrams, READMEs, slides, social cards, docs, UI.
>
> **The brand has one direction: Neural Dark.** Light mode exists only as a
> utility swap for print/GitHub-light-reader parity. Do not invent alternate
> "themes," "accents," or seasonal variants.

---

## 1. The idea in one line

**ZettelForge is signal memory — a recall loop, drawn as a nervous system.**

Every brand artifact should feel like an instrument panel for a living memory:
calm, monospaced, terminal-adjacent, with one channel of neon-green signal
punching through. Think threat-intel SOC meets Zettelkasten meets a quiet
black-paper notebook. Never corporate SaaS, never playful, never gradient-y.

---

## 2. Core visual DNA

Five non-negotiable motifs. If a piece is missing three of them, it is off-brand.

1. **Neuron-chain as metaphor.** Pipelines, architectures, and flows are drawn
   as a vertical chain of circular *soma* nodes connected by dashed *axons*.
   Dendrites (short curves ending in dots) radiate from active nodes. The
   living stage gets a glow; dormant stages do not.
2. **Single signal color.** Exactly one accent — **Signal Neon `#00FFA3`** —
   used sparingly to mark what is *live*, *current*, or *you-are-here*. Never
   decorative. If everything glows, nothing does.
3. **Graphite + fog neutrals.** Deep near-black backgrounds, graphite card
   surfaces, cool grey "fog" type. No pure black, no pure white on dark.
4. **Dashed recall trails.** Connections between stages are dashed (`1.5 7`
   pattern), never solid. Solid strokes are reserved for node borders and
   rules. The dash evokes signal pulses traveling an axon.
5. **Monospace is the voice.** Code, specs, metrics, chip labels, section
   eyebrows, and stage indices are monospace. Sans is only used for headlines
   and body prose.

---

## 3. Color system

All colors are fixed hex values. Do not introduce additional hues.

### Neural Dark (canonical)

| Token            | Hex       | Use                                                     |
| ---------------- | --------- | ------------------------------------------------------- |
| `bg`             | `#0A0E17` | Page / canvas background                                |
| `card`           | `#161B22` | Card, panel, stage-description surface                  |
| `node`           | `#0D1117` | Soma (neuron circle) fill                               |
| `chip`           | `#21262D` | Pill / chip background                                  |
| `border`         | `#30363D` | Default 1px borders                                     |
| `borderBright`   | `#484F58` | Node borders, emphasized dividers                       |
| `edgeDim`        | `#484F58` | Dormant axons + dendrites                               |
| `rule`           | `#21262D` | Section rules                                           |
| `fg-1`           | `#C9D1D9` | Primary text, headlines, live numerals                  |
| `fg-2`           | `#8B949E` | Secondary text, eyebrows                                |
| `fg-3`           | `#6B7280` | Tertiary / muted metrics, stage subtitles               |
| **`accent`**     | **`#00FFA3`** | **Signal — live stage only**                        |
| `pillInk`        | `#0A0E17` | Text *inside* a filled accent pill (inverts for legibility) |

### Neural Light (parity only)

| Token          | Hex       |
| -------------- | --------- |
| `bg`           | `#FFFFFF` |
| `card`         | `#FFFFFF` |
| `node`         | `#F4F6FA` |
| `chip`         | `#F4F6FA` |
| `border`       | `#E5E9F0` |
| `borderBright` | `#C9D1D9` |
| `edgeDim`      | `#C9D1D9` |
| `rule`         | `#E5E9F0` |
| `fg-1`         | `#1F2937` |
| `fg-2`         | `#6B7280` |
| `fg-3`         | `#9CA3AF` |
| **`accent`**   | **`#5EAE78`** (muted sage — neon reads as radioactive on white) |
| `pillInk`      | `#FFFFFF` |

**Accent rule of thumb:** if you are about to use `#00FFA3` on more than ~5%
of the pixels in a frame, stop and use a neutral instead.

---

## 4. Typography

Two families, deliberately paired. No third font.

- **Sans (headlines + prose):** `Inter, system-ui, -apple-system, "Segoe UI", sans-serif`
- **Mono (everything technical):** `"JetBrains Mono", ui-monospace, Menlo, Consolas, monospace`

### Scale & treatment

| Role                    | Font  | Size | Weight | Letter-spacing | Color  |
| ----------------------- | ----- | ---- | ------ | -------------- | ------ |
| Display headline        | sans  | 28   | 700    | -0.02em        | fg-1   |
| Stage title             | sans  | 15   | 600    | -0.01em        | fg-1   |
| Body prose              | sans  | 12–14 | 400    | normal         | fg-2   |
| Eyebrow / section label | sans  | 11   | 600    | 0.08em UPPER   | fg-2   |
| Stage detail / code     | mono  | 11.5 | 500    | normal         | fg-1   |
| Stage subtitle          | mono  | 11.5 | 500    | normal         | fg-3   |
| Stage index (01, 02…)   | mono  | 10.5 | 700    | 0.12em         | fg-1 (accent if live) |
| Chip label              | mono  | 12   | 600    | normal         | fg-1   |
| LIVE pill               | mono  | 10   | 700    | 0.14em UPPER   | pillInk |

Headlines should use `text-wrap: pretty` where possible. Never use all-caps
for prose — only for eyebrows, stage indices, and the LIVE pill.

---

## 5. The neural diagram pattern

This is the signature brand shape. Any pipeline, lifecycle, or flow diagram
must follow it.

```
┌───────────────────────────────────────── header ──┐
│ EYEBROW                                            │
│ Display headline                                   │
│ One-line sub                                       │
└───────────────────────── rule ────────────────────┘

         ● ── dendrites (only on active node)
        (●)   soma, r=28, 1.25px border
         │    dashed axon, pattern 1.5 7
        (●)
         │
      ╔══(●)══╗  ← LIVE stage: glow, accent border, LIVE pill
         │
        (●)
         ╲│╱   terminal burst (short lines) on final stage

┌───────────────────────── rule ────────────────────┐
│ STORAGE / EXTENSIONS footer: cards + chip row      │
└────────────────────────────────────────────────────┘
```

### Rules

- **Geometry:** soma `r=28` (or `r=30` for live), soma-center spacing `110px`
  vertical. Description card sits to the right of each soma, left edge at
  `x = soma.cx + 56`, height `72px`, corner radius `8`.
- **Axon:** `stroke-width 1.5` (or `1.75` entering live), `stroke-dasharray
  "1.5 7"`, `stroke-linecap round`, color `edgeDim` (or `accent` on the
  segment entering live).
- **Dendrites:** cubic Béziers from soma edge ending in `r=2` dots. Only the
  **live** node gets colored dendrites. Dormant nodes may get one pair of
  grey dendrites at the top of the chain (ingestion) to signal "input," and
  a terminal burst at the bottom (synthesis) to signal "output."
- **Glow:** implement with a simple `feGaussianBlur stdDeviation=3` +
  `feMerge` filter applied to the live soma, its inner dot, and the LIVE
  pill. Do not apply glow to text.
- **LIVE pill:** filled `accent`, 56×18, radius 9, with a 2.25px inner dot at
  `cx+10` and the word `LIVE` in mono/700/0.14em tracking, `pillInk` color.
- **Exactly one** stage may be LIVE per diagram. Pick the moment the reader
  is supposed to feel. If you can't pick one, you're making a reference
  diagram, not a brand diagram — leave them all dormant.

---

## 6. Components beyond the diagram

- **Cards:** `card` fill, `border` stroke, radius `8`, no shadow. On dark,
  shadows disappear — rely on border contrast instead.
- **Chips / pills:** `chip` fill, `border` stroke, radius `9`, mono 12/600
  label. Use for taxonomy (extensions, tags, capabilities). Never use them
  as CTAs.
- **Rules:** 1px `rule` color. Horizontal only. Use to separate header /
  body / footer zones. No vertical rules.
- **Metrics:** right-aligned, mono, `fg-3`. Example: `66.9% LOCOMO · +33%`.
  Numbers earn their place — cut any that are decorative.
- **Checkered / diagonal backdrops** (for showcase pages, not the SVGs
  themselves): `repeating-linear-gradient(45deg, rgba(255,255,255,0.015) 0
  2px, transparent 2px 10px)` over `#05080F`. Extremely subtle — should read
  as "texture," not "pattern."

---

## 7. Voice & copy

Short, precise, technical, unshowy. Sentences end early. Verbs do the work.

- ✅ "Four-stage pipeline; each stage is a node, the axon is the dataflow."
- ✅ "Validated against LOCOMO. 66.9% recall. +33% over baseline."
- ❌ "Unleash the power of AI-driven memory to supercharge your workflow!"
- ❌ "Discover a revolutionary new way to…"

Eyebrows are `UPPER / SLASH / SEPARATED`, e.g. `ZETTELFORGE / ARCHITECTURE`.
Stage subtitles name the module, in mono: `MemoryManager → FactExtractor`.
Stage bodies describe the action in present tense, dot-separated: `validate
→ extract entities → resolve aliases`.

Never use emoji. Never use exclamation marks. Metrics over adjectives.

---

## 8. What to avoid

- Multi-stop gradients, glass-morphism, colored drop shadows.
- Rounded-corner card with a left-border-accent stripe (the SaaS dashboard cliché).
- Illustrated mascots, isometric 3D, generic stock photography.
- Any font that isn't Inter or JetBrains Mono.
- Any accent color that isn't `#00FFA3` (dark) or `#5EAE78` (light).
- Solid connector lines, arrowheads, or labeled arrows between stages.
- "Live" indicators on more than one element per frame.
- Filler icons next to every heading, stat, or chip.

---

## 9. Canonical assets

| File                                   | Purpose                                           |
| -------------------------------------- | ------------------------------------------------- |
| `zettelforge_architecture.svg`         | Architecture diagram, **Neural Dark** — canonical |
| `zettelforge_architecture-light.svg`   | Same diagram, light parity for print/GitHub light |
| `colors_and_type.css`                  | Token source of truth for HTML surfaces           |
| `brandIdentity.md`                     | This document                                     |

When producing a new diagram, copy `zettelforge_architecture.svg` and mutate
it — do not redraw from scratch. Geometry, stroke weights, and font sizes
are tuned; drift breaks the family resemblance.

---

## 10. Quick agent checklist

Before shipping any ZettelForge visual, confirm:

- [ ] Background is `#0A0E17` (or `#FFFFFF` for the light parity swap)
- [ ] Exactly **one** element uses the signal accent
- [ ] All technical text is in JetBrains Mono
- [ ] All connector lines are dashed `1.5 7`
- [ ] At least one soma-node or dendrite motif is present if the piece depicts a flow
- [ ] No gradients, no emoji, no arrowheads, no third font
- [ ] Metrics are specific and earn their place
