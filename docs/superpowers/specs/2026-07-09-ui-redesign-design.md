# Heallio UI Redesign — Patient & Doctor Experience

## Goal

Replace the current generic Material-3-default look of the Flutter app (`health_app/`) with a clean, advanced, professional, and visually distinctive design system, applied consistently across every patient and doctor screen.

## Context

The app currently uses stock Material 3 styling: default Roboto font, flat `elevation: 0` bordered cards, 8–12px corner radii, a single emerald-green palette shared identically between patient and doctor roles. It works functionally but reads as a generic Flutter template. Cleanup of dead code/docs (orphaned screen files, stale root markdown docs, duplicate/leftover files) was completed separately before this redesign.

## Non-goals

- No backend/API changes.
- No new features/screens beyond what already exists (auth, home, chat, health tracking, body/food scan, insights, profile, doctor console, consultation chat).
- No dark mode in this pass (light theme only, but design tokens should not preclude adding it later).
- No changes to app architecture (Riverpod providers, API client, routing structure) except as strictly needed to wire up new theme/components.

## 1. Design system foundations

### Typography
Add `google_fonts` dependency. Use:
- **Manrope** for headings (display/headline/title text styles) — geometric, confident, modern.
- **Inter** for body/label text styles — high legibility at small sizes.

### Color
Extend `AppColors` in `theme/app_theme.dart`:
- Primary emerald range deepened slightly toward teal: keep `primary = #10B981`, add `primaryDeep = #0D9488` for gradients.
- Patient accent stays amber (`#F59E0B`) for streaks/achievements.
- **New `doctorPrimary` (indigo, ~`#4F46E5`) and `doctorPrimaryDeep`** — used for all doctor-only chrome (nav, primary buttons, badges, section accents) so doctor mode is visually distinct at a glance, while sharing the same neutrals, type, and components as the patient side.
- Neutral grey scale shifted slightly cooler; keep existing naming (`grey50`...`grey900`).
- Semantic colors (success/warning/error/info) get paired `Bg`/`Fg` tint variants for pills/badges (e.g. `successBg`, `successFg`).

### Elevation, shape, spacing
- Introduce two shadow tiers (`AppShadows.resting`, `AppShadows.raised`) — soft, low-opacity, replacing flat bordered cards.
- Default corner radius raised from 12px to 20px for cards, 12px for inputs/buttons/pills.
- New `AppSpacing` class with constants: `xs=4, sm=8, md=12, lg=16, xl=24, xxl=32` — used in place of ad-hoc `EdgeInsets.all(n)` in new/touched code.
- Icon containers use a subtle gradient tint (two-stop, same hue) instead of flat `color.withValues(alpha: 0.1)`.

### Role-based theming
`AppTheme` gains a second theme getter (e.g. `AppTheme.doctorTheme`) that swaps `primary`/`colorScheme` to the indigo doctor palette but reuses all typography, shadows, spacing, and shared component styling. The Flutter app already branches on role in `AuthWrapper` (`main.dart`) — wrap `MainNavigationScreen` and `DoctorNavigationScreen` each in a `Theme(data: ..., child: ...)` override (or restructure into two `MaterialApp`-level themes selected at the `AuthWrapper` level) so switching roles switches the accent throughout.

## 2. Component library (`widgets/`)

Rebuild `common_widgets.dart` (splitting into a few files if it grows past ~300 lines is fine, follow existing single-file convention otherwise) to add/replace:

- **Buttons**: `PrimaryButton` (gradient fill, scale-down press animation ~0.97, loading/disabled states — extend existing), `SecondaryButton` (outlined), `GhostButton` (text-only).
- **`AppCard`**: base card with soft shadow + 20px radius; `HealthCard`/`StatCard` rebuilt on top, adding an optional trend indicator (e.g. "↑12% this week").
- **`StatusPill`**: label + semantic color pair, used for consultation status, doctor availability, health score bands.
- **`CustomTextField`**: floating-label style, icon slot, refined focus ring (extend existing, don't break its public API more than necessary).
- **`EmptyState`/`LoadingState`/`ErrorState`**: keep existing structure, restyle to new tokens.
- **New `SectionHeader`**: title + optional trailing action, used across dashboards/lists.
- **New `AvatarWithStatus`**: avatar + small colored status dot (online/offline, availability).
- **New `MetricRing`**: circular progress ring for health score / daily goal completion, animated fill.

All new/rebuilt components live under `widgets/`, consumed by screens — no screen should hand-roll card/button/pill styling inline going forward.

## 3. Screens

### Patient (warm, consumer-friendly, emerald accent)
- **Auth choice / patient auth / doctor auth** (`screens/auth/`): hero header with gradient background, animated role-selection cards on the choice screen, restyled forms using new `CustomTextField`/`PrimaryButton`.
- **Home** (`screens/home/home_screen.dart`): scrollable dashboard — greeting header, `MetricRing` health-score hero, horizontal-scroll stat cards (steps/heart rate/calories), quick-action row (chat/scan/log), recent-insight teaser card.
- **Chat** (`screens/chat/chat_screen.dart`): gradient-filled user bubbles, distinct assistant bubble style, typing indicator, suggested-prompt chips row.
- **Health tracking** (`screens/health/health_tracking_screen.dart`): segmented tabs (Health/Diet/Sleep), sparkline-style trend charts replacing raw list rows where feasible without new chart dependencies (hand-rolled `CustomPaint` sparkline, no new package unless justified).
- **Body/food scan** (`screens/scan/body_scan_screen.dart`, `widgets/food_scan_widget.dart`): camera capture card with scanning animation overlay, result card with confidence/breakdown using `StatusPill`.
- **Insights** (`screens/insights/insights_screen.dart`): card feed grouped by category, colored left-accent bar per category.
- **Profile** (`screens/profile/profile_screen.dart`): avatar header with gradient banner, grouped settings list with leading icons.

### Doctor (data-dense, professional, indigo accent)
- **Doctor navigation/console** (`screens/doctor/doctor_navigation_screen.dart`): dashboard with today's queue count, prominent availability toggle, quick stats (patients seen, rating) using `StatCard`/`MetricRing`.
- **Consultation queue** (within doctor console or `screens/consultation/`): list with `AvatarWithStatus`, wait time, urgency `StatusPill`, one-tap accept button.
- **Consultation chat** (`screens/consultation/consultation_chat_screen.dart`): same bubble system as patient chat, clinical header (patient name/context), indigo accent throughout.

## 4. Motion

- Extend the existing `AnimatedSwitcher` slide/fade pattern (already in `main.dart`'s `AuthNavigationScreen`) to other top-level navigation transitions where reasonable.
- Button press: scale to ~0.97 on tap-down, spring back on release.
- List/card feeds: staggered fade+slide-in on first build (short duration, ~250–400ms, no external animation package needed — `AnimatedList`/`TweenAnimationBuilder` suffice).
- Stat values: animated count-up (`TweenAnimationBuilder<double>`) instead of static text.
- Scan result / chat typing indicator: smooth expand/collapse via `AnimatedSize`/`AnimatedOpacity`.

No new animation package dependency — everything achievable with Flutter's built-in animation widgets.

## 5. Rollout approach

1. Add `google_fonts` dependency; build out design tokens (`AppColors`, `AppShadows`, `AppSpacing`, text theme, `AppTheme.lightTheme` + `AppTheme.doctorTheme`).
2. Rebuild `widgets/common_widgets.dart` component library against the new tokens.
3. Apply to patient screens in this order: auth → home → chat → health tracking → scan → insights → profile.
4. Apply to doctor screens: doctor navigation/console → consultation queue → consultation chat.
5. Manual pass in a running emulator/web build to check spacing, contrast, and animation feel across both roles; adjust tokens/components as needed (not a new design round — tuning within this spec).

## Testing / verification

- `flutter analyze` must pass with no new warnings.
- Existing widget test (`health_app/test/widget_test.dart`) must still pass (update if it references removed/renamed widgets).
- Manual verification: run the app (web or emulator), walk through patient flow (auth → home → chat → health → scan → insights → profile) and doctor flow (auth → console → queue → consultation chat), confirm role-based theming switches correctly and no layout overflows/errors appear.

## Open questions / risks

- None blocking. If `google_fonts` cannot fetch fonts at build time in this environment (offline), fall back to bundling static font files under `assets/fonts/` instead of the network-fetching variant of the package — decide at implementation time based on what works.
