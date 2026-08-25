# Design System: Heallio — Liquid Glass Health Platform

Use this as the master prompt for every screen. Paste the whole thing into Stitch, then append the per-screen line from Section 8.

## 1. Visual Theme & Atmosphere
A calm, clinical-yet-warm mobile health app with a **liquid-glass (frosted glassmorphism) surface language** over a deep graphite canvas. Think modern iOS 18 / visionOS translucency — not neon cyberpunk. Density is "daily-app balanced": airy hero zones, compact data zones. Layouts are confidently asymmetric — offset headers, zig-zag content rows, never three equal cards in a row. Motion is fluid and weighty: spring physics, staggered card reveals, soft perpetual pulses on live health data. The overall feeling: a premium medical instrument you trust with your body — precise, quiet, glassy, never playful-cartoonish.

## 2. Color Palette & Roles
- **Graphite Canvas** (#0D0E12) — app background; never pure black
- **Deep Surface** (#16181E) — base layer under glass panels
- **Glass Panel** (rgba(27,30,36,0.55) with 24px backdrop blur) — all cards, sheets, nav bars; 1px inner border of rgba(255,255,255,0.08)
- **Glass Raised** (rgba(36,40,48,0.65) with 32px blur) — dialogs, bottom sheets, active states
- **Frost Edge** (rgba(255,255,255,0.10)) — hairline borders on every glass element, top edge slightly brighter (rgba(255,255,255,0.16)) to simulate light hitting glass
- **Signal Blue** (#3E8BFF, ~70% saturation) — the ONLY patient-mode accent: primary CTAs, active tabs, progress rings, focus rings
- **Clinical Gold** (#D4A24C) — the ONLY doctor-mode accent; replaces Signal Blue on every doctor screen (dashboard, queue, prescriptions authoring). Never show blue and gold on the same screen.
- **Ink White** (#F5F6F8) — headings
- **Body Grey** (#CBCDD4) — primary body text
- **Muted Grey** (#8A8E99) — metadata, timestamps, hints
- **Vital Green** (#4ADE80 on rgba(20,48,31,0.6) glass tint) — healthy / success pills
- **Caution Amber** (#FBBF24 on rgba(51,36,18,0.6) glass tint) — warnings, moderate urgency
- **Alert Red** (#F87171 on rgba(58,21,24,0.6) glass tint) — errors, high urgency, crisis banners
- Max one accent per screen. No purple. No neon glows. No gradients on text.

## 3. Typography Rules
- **Display / Headlines:** Satoshi (or Outfit) — weight 700, tight tracking (-0.02em), hierarchy via weight and color, never via screaming size. Screen titles ~28px, section headers ~18px.
- **Body:** Geist — 15–16px, relaxed 1.5 leading, max 65 characters per line, Body Grey.
- **Numbers & vitals:** Geist Mono — every health metric (steps, heart rate, sleep hours, confidence %) renders in monospace so digits align and feel instrument-grade.
- **Banned:** Inter, Roboto, generic serifs. No serif anywhere — this is a software UI.

## 4. Component Stylings
- **Glass Cards:** ONE card system app-wide — 24px radius, Glass Panel fill, 24px backdrop blur, Frost Edge hairline, shadow tinted to canvas (0 12px 32px rgba(0,0,0,0.35)). Interior padding 20px. Tappable cards depress 1px + brighten border on press. Never mix flat cards and glass cards on the same screen.
- **Buttons:** Primary = solid accent fill (Signal Blue or Clinical Gold), 16px radius, 52px height, tactile press (scale 0.97). Secondary = glass fill with accent-tinted 1px border and accent text. Never two solid primaries side by side — choose one primary, demote the other to glass-secondary.
- **Inputs:** Label above field in Muted Grey caps-label; field is a glass well (rgba(22,24,30,0.7)) with 14px radius; focus ring = 2px accent; error text below in Alert Red. Dropdowns and date pickers use the exact same glass-well styling as text fields — no raw platform defaults.
- **Pills / status badges:** Fully rounded glass chips with the semantic tint pairs above; 12px mono label; icon optional at 13px.
- **Progress rings:** 10px stroke, rounded caps, accent color on 12%-alpha track, animated sweep on load; center value in Geist Mono.
- **Bottom nav:** Floating glass dock, detached from screen edge by 12px, 28px radius, active tab in accent with a soft 4px underglow dot (glow stays subtle, contained inside the dock).
- **Loading:** Skeleton shimmer blocks matching the real layout — never a lone circular spinner.
- **Empty states:** Composed glass illustration tile + one-line title + one-line guidance + a single action button. Never bare "No data" text.
- **Errors:** Inline glass banner (Alert Red tint) with icon, human-readable message, and a Retry action. Never raw exception text.

## 5. Layout Principles
- Mobile-first, single column below 768px, 20px screen gutters, 8-point spacing scale (8 / 12 / 16 / 24 / 32) used everywhere — no arbitrary gaps.
- Section rhythm: section header (left-aligned, with optional trailing action link) → content → 32px gap. Every section uses the same header pattern.
- Hero zones (greeting, health score) are asymmetric: text block left, ring or visual right — never dead-centered.
- Stat grids are 2-column with equal glass cards; feature rows zig-zag; never 3 equal cards horizontally.
- Nothing overlaps. Content scrolls under the frosted top bar and glass dock, blurring as it passes beneath them — that's the only "layering."
- Full-height screens use dynamic viewport height; no horizontal scroll ever.
- All touch targets ≥ 48px. Text links get padded hit areas — no bare tappable text.

## 6. Motion & Interaction
- Spring physics everywhere (stiffness 100, damping 20). No linear easing.
- Screens enter with a 40ms-staggered cascade of glass cards rising 12px + fading in.
- Live health data breathes: progress rings pulse ±2% opacity on a slow loop; the AI chat "typing" state uses a three-dot shimmer inside a glass bubble.
- Tab/mode switches cross-fade + slide 16px over 300ms.
- Animate only transform and opacity. Blur values are static per surface, never animated.

## 7. Anti-Patterns (Banned)
- No emojis in UI chrome. No Inter. No pure #000000. No purple/neon glows or oversaturated accents.
- No gradient text. No custom cursors. No overlapping text/images.
- No 3-equal-card rows. No centered hero blocks. No "Scroll to explore" / chevron filler.
- No light-pastel card fills (#FFE8E8-style) on the dark canvas — every tint must be a dark glass tint from Section 2.
- No dead controls: every visible button, settings row, or bell icon must lead somewhere or not exist.
- No raw platform dropdowns/spinners breaking the glass language.
- No generic names ("John Doe", "Acme"), no fake round stats, no AI clichés ("Elevate", "Seamless", "Unleash").
- No two identical primary buttons side by side.

## 8. Screens to Generate (append one line per generation)
Patient mode (Signal Blue):
1. **Role Choice** — brand mark, one-line value prop, two large glass role cards (Patient / Doctor), doctor card carries a subtle gold edge tint.
2. **Login / Sign Up** — glass form card, labeled fields, single primary CTA, mode-toggle link with full-width tap area.
3. **Home Dashboard** — greeting hero (asymmetric), health-score glass card with progress ring, 2×2 vitals grid (mono numbers), AI insight teaser card, consult-suggestion card.
4. **Health Tracking** — segmented glass pill tabs (Health / Food Scan / Sleep), log form, recent-entries list of glass rows.
5. **AI Health Chat** — glass chat bubbles (user = accent-tinted glass right, AI = neutral glass left), consent banner variant, suggestion chips, glass composer bar with mono send button.
6. **Insights** — vertical feed of insight glass cards, category icon + matching accent edge per category, recommendation callout inset.
7. **Body Scan** — image picker zone (dashed glass well), one primary Analyze CTA + glass-secondary Choose Image, result card with condition, mono confidence %, urgency pill, disclaimer banner.
8. **Prescriptions** — list of prescription glass cards with status pills, pull-to-refresh, composed empty state.
9. **Profile & Settings** — glass avatar header, grouped settings sections, every row functional-looking with chevrons, destructive Sign Out in Alert Red tint.

Doctor mode (Clinical Gold — regenerate shared patterns with gold accent):
10. **Doctor Auth** — same auth pattern but gold accent from the first screen, professional-attestation checkbox row (whole row tappable).
11. **Doctor Dashboard** — availability glass toggle card with explicit state feedback, urgent-case alert (Alert Red glass), "Today" 2×2 stat grid in mono, open queue list with Accept actions.
12. **Consultation Detail** — severity banner, primary Open Chat action, prescription authoring entry, star rating in gold with labeled stars.
13. **Consultation Thread** — clinical chat variant of screen 5, gold accents, connection-lost shown as inline banner above history (history never disappears).
14. **Prescription Form** — sectioned glass form: repeatable medication rows with labeled remove buttons, care instructions, follow-up date as glass field, validation inline.
