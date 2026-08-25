# Heallio UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the generic Material-3-default look of the Flutter app (`health_app/`) with a cohesive, premium design system (typography, color, shadows, spacing, motion) applied consistently to every patient and doctor screen, with doctor mode visually distinguished by an indigo accent.

**Architecture:** All visual changes flow through three layers: (1) design tokens in `theme/app_theme.dart`, (2) a rebuilt component library in `widgets/common_widgets.dart` (+ new `widgets/status_pill.dart`, `widgets/metric_ring.dart`, `widgets/avatar_with_status.dart`, `widgets/section_header.dart`), (3) screen files that consume those components. Screens are touched only where they bypass the shared components with hardcoded styling (raw `Card`, hand-rolled badges, manual gradients). No backend, routing, or state-management changes.

**Tech Stack:** Flutter (Dart), Riverpod (existing), `google_fonts` (new dependency).

## Global Constraints

- Flutter SDK: `^3.11.3` (from `health_app/pubspec.yaml`) — do not use APIs newer than this constraint allows.
- No new animation package — use only `AnimatedContainer`, `AnimatedSwitcher`, `TweenAnimationBuilder`, `AnimatedSize`, `AnimatedOpacity`, `CustomPaint` (all built into Flutter).
- No dark mode in this pass — `AppTheme.lightTheme` and `AppTheme.doctorTheme` are both light themes.
- No backend/API changes — do not touch anything under `backend/`.
- Preserve all existing public constructors' required parameters where screens call them, unless a task explicitly changes a widget's API (in which case every call site is updated in the same task).
- Run `flutter analyze` from `health_app/` after each task; it must report no new issues before moving to the next task.

---

### Task 1: Add `google_fonts` dependency and verify the build

**Files:**
- Modify: `health_app/pubspec.yaml`

**Interfaces:**
- Produces: `google_fonts` package available for import as `package:google_fonts/google_fonts.dart` in Task 4.

- [ ] **Step 1: Add the dependency**

In `health_app/pubspec.yaml`, under `dependencies:` (after `http: ^1.2.2`), add:

```yaml
  google_fonts: ^6.2.1
```

So the `dependencies:` block reads:

```yaml
dependencies:
  flutter:
    sdk: flutter

  cupertino_icons: ^1.0.8
  http: ^1.2.2
  google_fonts: ^6.2.1
  image: ^4.5.4
  image_picker: ^1.1.2
  shared_preferences: ^2.3.2
  flutter_riverpod: ^2.4.9
  riverpod: ^2.4.9
  web_socket_channel: ^3.0.1
```

- [ ] **Step 2: Fetch packages**

Run: `cd health_app && flutter pub get`
Expected: Completes with `google_fonts` resolved, no errors. If the environment is offline and resolution fails, stop and report this — do not silently skip the dependency; the fallback path (bundled static font assets) is a separate decision, not an automatic substitution.

- [ ] **Step 3: Commit**

```bash
git add health_app/pubspec.yaml health_app/pubspec.lock
git commit -m "chore: add google_fonts dependency"
```

(This repo has no `.git` — if `git` is unavailable, skip commit steps throughout this plan and rely on the working tree as the record of progress.)

---

### Task 2: Design tokens — `AppSpacing` and `AppShadows`

**Files:**
- Modify: `health_app/lib/theme/app_theme.dart`

**Interfaces:**
- Produces: `AppSpacing.{xs,sm,md,lg,xl,xxl}` (all `double`), `AppShadows.resting` and `AppShadows.raised` (both `List<BoxShadow>`).
- Consumed by: Task 8 (`AppCard`), Task 3/5 (theme), and screen tasks.

- [ ] **Step 1: Add `AppSpacing` and `AppShadows` classes**

In `health_app/lib/theme/app_theme.dart`, immediately after the closing `}` of the `AppColors` class (currently ending at line 38, before `class AppTheme {`), insert:

```dart
class AppSpacing {
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 24;
  static const double xxl = 32;
}

class AppShadows {
  static List<BoxShadow> get resting => [
        BoxShadow(
          color: Colors.black.withValues(alpha: 0.04),
          blurRadius: 12,
          offset: const Offset(0, 4),
        ),
      ];

  static List<BoxShadow> get raised => [
        BoxShadow(
          color: Colors.black.withValues(alpha: 0.08),
          blurRadius: 24,
          offset: const Offset(0, 10),
        ),
      ];
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd health_app && flutter analyze lib/theme/app_theme.dart`
Expected: `No issues found!`

- [ ] **Step 3: Commit**

```bash
git add health_app/lib/theme/app_theme.dart
git commit -m "feat: add AppSpacing and AppShadows design tokens"
```

---

### Task 3: Extend `AppColors` — deepened emerald, doctor indigo palette, semantic bg/fg pairs

**Files:**
- Modify: `health_app/lib/theme/app_theme.dart`

**Interfaces:**
- Produces: `AppColors.primaryDeep`, `AppColors.doctorPrimary`, `AppColors.doctorPrimaryDeep`, `AppColors.doctorPrimaryLight`, `AppColors.successBg`/`successFg`, `AppColors.warningBg`/`warningFg`, `AppColors.errorBg`/`errorFg`, `AppColors.infoBg`/`infoFg`.
- Consumed by: Task 5 (`AppTheme.doctorTheme`), Task 9 (`StatusPill`), all screen tasks.

- [ ] **Step 1: Add the new color constants**

In `health_app/lib/theme/app_theme.dart`, inside `class AppColors`, replace the block from `// Secondary colors` through `static const Color info = Color(0xFF0EA5E9);` (lines 9–17) with:

```dart
  // Secondary colors
  static const Color secondary = Color(0xFF3B82F6); // Blue
  static const Color accent = Color(0xFFF59E0B); // Amber

  // Deepened primary for gradients
  static const Color primaryDeep = Color(0xFF0D9488);

  // Doctor-mode accent (indigo) — used for all doctor-only chrome
  static const Color doctorPrimary = Color(0xFF4F46E5);
  static const Color doctorPrimaryDeep = Color(0xFF4338CA);
  static const Color doctorPrimaryLight = Color(0x1A4F46E5);

  // Semantic colors
  static const Color success = Color(0xFF10B981);
  static const Color warning = Color(0xFFEAB308);
  static const Color error = Color(0xFFEF4444);
  static const Color info = Color(0xFF0EA5E9);

  // Semantic tint/foreground pairs for pills, badges, banners
  static const Color successBg = Color(0xFFE7F8F1);
  static const Color successFg = Color(0xFF0D9488);
  static const Color warningBg = Color(0xFFFEF6E7);
  static const Color warningFg = Color(0xFFB45309);
  static const Color errorBg = Color(0xFFFDECEC);
  static const Color errorFg = Color(0xFFDC2626);
  static const Color infoBg = Color(0xFFE7F4FD);
  static const Color infoFg = Color(0xFF0369A1);
```

- [ ] **Step 2: Verify it compiles**

Run: `cd health_app && flutter analyze lib/theme/app_theme.dart`
Expected: `No issues found!`

- [ ] **Step 3: Commit**

```bash
git add health_app/lib/theme/app_theme.dart
git commit -m "feat: extend AppColors with doctor palette and semantic bg/fg pairs"
```

---

### Task 4: Typography — Manrope headings + Inter body via `google_fonts`

**Files:**
- Modify: `health_app/lib/theme/app_theme.dart`

**Interfaces:**
- Consumes: `google_fonts` package (Task 1).
- Produces: `_buildTextTheme()` now returns a `TextTheme` built with `GoogleFonts.manropeTextTheme()`/`GoogleFonts.interTextTheme()` — same style names as before (`displayLarge` … `labelSmall`), so no call site outside this file needs to change.

- [ ] **Step 1: Add the import**

In `health_app/lib/theme/app_theme.dart`, at the top of the file, after `import 'package:flutter/material.dart';`, add:

```dart
import 'package:google_fonts/google_fonts.dart';
```

- [ ] **Step 2: Rewrite `_buildTextTheme()`**

Replace the entire `static TextTheme _buildTextTheme()` method (from `static TextTheme _buildTextTheme() {` to its closing `}`) with:

```dart
  static TextTheme _buildTextTheme() {
    final headingFont = GoogleFonts.manrope();
    final bodyFont = GoogleFonts.inter();

    return TextTheme(
      displayLarge: headingFont.copyWith(
        fontSize: 32,
        fontWeight: FontWeight.w700,
        color: AppColors.grey900,
        height: 1.2,
      ),
      displayMedium: headingFont.copyWith(
        fontSize: 28,
        fontWeight: FontWeight.w700,
        color: AppColors.grey900,
        height: 1.3,
      ),
      displaySmall: headingFont.copyWith(
        fontSize: 24,
        fontWeight: FontWeight.w700,
        color: AppColors.grey900,
        height: 1.3,
      ),
      headlineLarge: headingFont.copyWith(
        fontSize: 22,
        fontWeight: FontWeight.w600,
        color: AppColors.grey900,
        height: 1.4,
      ),
      headlineMedium: headingFont.copyWith(
        fontSize: 20,
        fontWeight: FontWeight.w600,
        color: AppColors.grey900,
        height: 1.4,
      ),
      headlineSmall: headingFont.copyWith(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        color: AppColors.grey900,
        height: 1.4,
      ),
      titleLarge: headingFont.copyWith(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: AppColors.grey900,
        height: 1.5,
      ),
      titleMedium: headingFont.copyWith(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        color: AppColors.grey800,
        height: 1.5,
      ),
      titleSmall: headingFont.copyWith(
        fontSize: 12,
        fontWeight: FontWeight.w600,
        color: AppColors.grey700,
        height: 1.5,
      ),
      bodyLarge: bodyFont.copyWith(
        fontSize: 16,
        fontWeight: FontWeight.w500,
        color: AppColors.grey700,
        height: 1.5,
      ),
      bodyMedium: bodyFont.copyWith(
        fontSize: 14,
        fontWeight: FontWeight.w500,
        color: AppColors.grey600,
        height: 1.5,
      ),
      bodySmall: bodyFont.copyWith(
        fontSize: 12,
        fontWeight: FontWeight.w500,
        color: AppColors.grey600,
        height: 1.5,
      ),
      labelLarge: bodyFont.copyWith(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        color: AppColors.grey700,
        height: 1.4,
        letterSpacing: 0.5,
      ),
      labelMedium: bodyFont.copyWith(
        fontSize: 12,
        fontWeight: FontWeight.w600,
        color: AppColors.grey600,
        height: 1.4,
        letterSpacing: 0.5,
      ),
      labelSmall: bodyFont.copyWith(
        fontSize: 11,
        fontWeight: FontWeight.w600,
        color: AppColors.grey500,
        height: 1.3,
        letterSpacing: 0.3,
      ),
    );
  }
```

- [ ] **Step 3: Verify it compiles and run the app**

Run: `cd health_app && flutter analyze lib/theme/app_theme.dart`
Expected: `No issues found!`

Run: `cd health_app && flutter run -d chrome` (or any available device), confirm the app launches and text renders with the new fonts (headings look geometric/rounded, body text is Inter). Stop the run once confirmed.

- [ ] **Step 4: Commit**

```bash
git add health_app/lib/theme/app_theme.dart
git commit -m "feat: switch typography to Manrope headings + Inter body via google_fonts"
```

---

### Task 5: `AppTheme.lightTheme` refinement + new `AppTheme.doctorTheme`

**Files:**
- Modify: `health_app/lib/theme/app_theme.dart`

**Interfaces:**
- Consumes: `AppSpacing`, `AppShadows`, `AppColors.doctorPrimary`/`doctorPrimaryDeep` (Tasks 2–3).
- Produces: `AppTheme.lightTheme` (existing getter, updated shape/elevation values) and new `AppTheme.doctorTheme` (same shape as `lightTheme` but with `primaryColor`/`colorScheme` swapped to the doctor palette). Both build on the same `_buildTextTheme()`.

- [ ] **Step 1: Update `lightTheme` corner radii and card styling**

In `health_app/lib/theme/app_theme.dart`, inside `static ThemeData get lightTheme`, replace the `cardTheme` block:

```dart
      cardTheme: CardThemeData(
        color: AppColors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: AppColors.grey100),
        ),
      ),
```

with:

```dart
      cardTheme: CardThemeData(
        color: AppColors.white,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
      ),
```

- [ ] **Step 2: Update input and button radii**

Replace every `BorderRadius.circular(8)` inside `inputDecorationTheme`, `elevatedButtonTheme`, and `textButtonTheme` (four occurrences: `enabledBorder`, `focusedBorder`, `errorBorder`, `border` in `inputDecorationTheme`, plus the shapes in `elevatedButtonTheme` and `textButtonTheme`) with `BorderRadius.circular(14)`. The full `inputDecorationTheme` becomes:

```dart
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.grey100,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.grey200),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.grey200),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.error),
        ),
        labelStyle: const TextStyle(color: AppColors.grey600),
        hintStyle: const TextStyle(color: AppColors.grey400),
      ),
```

and `elevatedButtonTheme`/`textButtonTheme` become:

```dart
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: AppColors.white,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          elevation: 0,
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.primary,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ),
```

- [ ] **Step 3: Add `AppTheme.doctorTheme`**

In `health_app/lib/theme/app_theme.dart`, immediately after the closing `}` of `static ThemeData get lightTheme` (before `static TextTheme _buildTextTheme()`), add:

```dart
  static ThemeData get doctorTheme {
    return lightTheme.copyWith(
      primaryColor: AppColors.doctorPrimary,
      colorScheme: lightTheme.colorScheme.copyWith(
        primary: AppColors.doctorPrimary,
        secondary: AppColors.doctorPrimaryDeep,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.doctorPrimary,
          foregroundColor: AppColors.white,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          elevation: 0,
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.doctorPrimary,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ),
      inputDecorationTheme: lightTheme.inputDecorationTheme.copyWith(
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: AppColors.doctorPrimary, width: 2),
        ),
      ),
    );
  }
```

- [ ] **Step 4: Verify it compiles**

Run: `cd health_app && flutter analyze lib/theme/app_theme.dart`
Expected: `No issues found!`

- [ ] **Step 5: Commit**

```bash
git add health_app/lib/theme/app_theme.dart
git commit -m "feat: refine light theme radii and add doctorTheme"
```

---

### Task 6: Wire role-based theme switching in `main.dart`

**Files:**
- Modify: `health_app/lib/main.dart:23-35` (the `MyApp` widget), `health_app/lib/main.dart:37-54` (`AuthWrapper`)

**Interfaces:**
- Consumes: `AppTheme.lightTheme`, `AppTheme.doctorTheme` (Task 5).
- Produces: `MaterialApp` picks its `theme` based on the authenticated user's role, so `DoctorNavigationScreen` renders with indigo accents and `MainNavigationScreen` keeps emerald.

- [ ] **Step 1: Replace `MyApp` and `AuthWrapper` to select the theme by role**

In `health_app/lib/main.dart`, replace both classes (lines 23–54, from `class MyApp extends StatelessWidget {` through the closing `}` of `AuthWrapper`) with:

```dart
class MyApp extends ConsumerWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final isDoctor = authState.user?.role == 'doctor';

    return MaterialApp(
      title: 'Heallio',
      debugShowCheckedModeBanner: false,
      theme: isDoctor ? AppTheme.doctorTheme : AppTheme.lightTheme,
      home: const AuthWrapper(),
    );
  }
}

class AuthWrapper extends ConsumerWidget {
  const AuthWrapper({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);

    if (authState.isAuthenticated) {
      final role = authState.user?.role ?? 'user';
      if (role == 'doctor') {
        return const DoctorNavigationScreen();
      }
      return const MainNavigationScreen();
    } else {
      return const AuthNavigationScreen();
    }
  }
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd health_app && flutter analyze lib/main.dart`
Expected: `No issues found!`

- [ ] **Step 3: Manual check**

Run: `cd health_app && flutter run -d chrome`. Log in as a patient account, confirm emerald accent. Log out, log in as a doctor account, confirm the app bar/buttons switch to indigo. (If no doctor account exists yet, sign up via the doctor auth screen with `role: 'doctor'`.)

- [ ] **Step 4: Commit**

```bash
git add health_app/lib/main.dart
git commit -m "feat: switch MaterialApp theme by authenticated user role"
```

---

### Task 7: Rebuild buttons — press animation, `SecondaryButton`, `GhostButton`

**Files:**
- Modify: `health_app/lib/widgets/common_widgets.dart:4-42` (existing `PrimaryButton`)

**Interfaces:**
- Produces: `PrimaryButton` (same public API: `label`, `onPressed`, `isLoading`, `isEnabled` — now with a tap-scale animation), new `SecondaryButton` (outlined, same API shape), new `GhostButton` (text-only, same API shape).
- Consumed by: every screen already using `PrimaryButton` (no call-site changes needed); `SecondaryButton`/`GhostButton` consumed starting in later screen tasks.

- [ ] **Step 1: Replace `PrimaryButton` with an animated version and add `SecondaryButton`/`GhostButton`**

In `health_app/lib/widgets/common_widgets.dart`, replace the entire `PrimaryButton` widget and its state class (lines 4–42, from `class PrimaryButton extends StatefulWidget {` through the closing `}` of `_PrimaryButtonState`) with:

```dart
class _PressableScale extends StatefulWidget {
  const _PressableScale({required this.enabled, required this.child});

  final bool enabled;
  final Widget child;

  @override
  State<_PressableScale> createState() => _PressableScaleState();
}

class _PressableScaleState extends State<_PressableScale> {
  bool _pressed = false;

  void _setPressed(bool value) {
    if (!widget.enabled) return;
    setState(() => _pressed = value);
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => _setPressed(true),
      onTapUp: (_) => _setPressed(false),
      onTapCancel: () => _setPressed(false),
      child: AnimatedScale(
        scale: _pressed ? 0.97 : 1.0,
        duration: const Duration(milliseconds: 100),
        curve: Curves.easeOut,
        child: widget.child,
      ),
    );
  }
}

class PrimaryButton extends StatelessWidget {
  final String label;
  final VoidCallback onPressed;
  final bool isLoading;
  final bool isEnabled;

  const PrimaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.isLoading = false,
    this.isEnabled = true,
  });

  @override
  Widget build(BuildContext context) {
    final enabled = isEnabled && !isLoading;
    return _PressableScale(
      enabled: enabled,
      child: SizedBox(
        width: double.infinity,
        child: ElevatedButton(
          onPressed: enabled ? onPressed : null,
          child: isLoading
              ? const SizedBox(
                  height: 20,
                  width: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor: AlwaysStoppedAnimation<Color>(AppColors.white),
                  ),
                )
              : Text(label),
        ),
      ),
    );
  }
}

class SecondaryButton extends StatelessWidget {
  final String label;
  final VoidCallback onPressed;
  final bool isLoading;
  final bool isEnabled;
  final IconData? icon;

  const SecondaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.isLoading = false,
    this.isEnabled = true,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    final enabled = isEnabled && !isLoading;
    final primary = Theme.of(context).colorScheme.primary;
    return _PressableScale(
      enabled: enabled,
      child: SizedBox(
        width: double.infinity,
        child: OutlinedButton.icon(
          onPressed: enabled ? onPressed : null,
          style: OutlinedButton.styleFrom(
            foregroundColor: primary,
            side: BorderSide(color: primary.withValues(alpha: 0.4)),
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          ),
          icon: isLoading
              ? SizedBox(
                  height: 16,
                  width: 16,
                  child: CircularProgressIndicator(strokeWidth: 2, color: primary),
                )
              : (icon != null ? Icon(icon) : const SizedBox.shrink()),
          label: Text(label),
        ),
      ),
    );
  }
}

class GhostButton extends StatelessWidget {
  final String label;
  final VoidCallback onPressed;
  final bool isEnabled;

  const GhostButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.isEnabled = true,
  });

  @override
  Widget build(BuildContext context) {
    return _PressableScale(
      enabled: isEnabled,
      child: TextButton(
        onPressed: isEnabled ? onPressed : null,
        child: Text(label),
      ),
    );
  }
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd health_app && flutter analyze lib/widgets/common_widgets.dart`
Expected: `No issues found!` (existing `PrimaryButton` call sites across the app keep working since the public API is unchanged.)

- [ ] **Step 3: Commit**

```bash
git add health_app/lib/widgets/common_widgets.dart
git commit -m "feat: add press-scale animation to PrimaryButton, add SecondaryButton/GhostButton"
```

---

### Task 8: `AppCard` base + rebuild `HealthCard`/`StatCard` with trend indicator

**Files:**
- Modify: `health_app/lib/widgets/common_widgets.dart` (the `HealthCard` and `StatCard` classes, originally lines 103-239)

**Interfaces:**
- Consumes: `AppShadows`, `AppSpacing` (Task 2).
- Produces: new `AppCard` widget (`child`, optional `onTap`, optional `padding`), `HealthCard` (existing API `title, value, subtitle, icon, iconColor, onTap` — unchanged, now built on `AppCard`), `StatCard` (existing API `label, value, unit, icon, backgroundColor` unchanged, plus new optional `trend` (`String?`, e.g. `"+12%"`) and `trendPositive` (`bool`, default `true`)).
- Consumed by: `home_screen.dart`, `health_tracking_screen.dart`, `doctor_navigation_screen.dart`, `food_scan_widget.dart` (existing call sites keep compiling unchanged; `trend` is opt-in).

- [ ] **Step 1: Add `AppCard` and replace `HealthCard`/`StatCard`**

In `health_app/lib/widgets/common_widgets.dart`, replace the `HealthCard` and `StatCard` classes in full (the two classes spanning from `class HealthCard extends StatelessWidget {` through the closing `}` of `StatCard`) with:

```dart
class AppCard extends StatelessWidget {
  final Widget child;
  final VoidCallback? onTap;
  final EdgeInsetsGeometry padding;
  final bool raised;

  const AppCard({
    super.key,
    required this.child,
    this.onTap,
    this.padding = const EdgeInsets.all(16),
    this.raised = false,
  });

  @override
  Widget build(BuildContext context) {
    final content = Container(
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: raised ? AppShadows.raised : AppShadows.resting,
      ),
      child: Padding(padding: padding, child: child),
    );

    if (onTap == null) return content;

    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(20),
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onTap,
        child: content,
      ),
    );
  }
}

class HealthCard extends StatelessWidget {
  final String title;
  final String value;
  final String? subtitle;
  final IconData icon;
  final Color iconColor;
  final VoidCallback? onTap;

  const HealthCard({
    super.key,
    required this.title,
    required this.value,
    this.subtitle,
    required this.icon,
    this.iconColor = AppColors.primary,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return AppCard(
      onTap: onTap,
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [iconColor.withValues(alpha: 0.16), iconColor.withValues(alpha: 0.08)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, color: iconColor, size: 24),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.bodyMedium),
                const SizedBox(height: 4),
                Text(value, style: Theme.of(context).textTheme.headlineSmall),
                if (subtitle != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    subtitle!,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.grey500),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class StatCard extends StatelessWidget {
  final String label;
  final String value;
  final String? unit;
  final IconData? icon;
  final Color? backgroundColor;
  final String? trend;
  final bool trendPositive;

  const StatCard({
    super.key,
    required this.label,
    required this.value,
    this.unit,
    this.icon,
    this.backgroundColor,
    this.trend,
    this.trendPositive = true,
  });

  @override
  Widget build(BuildContext context) {
    final numericValue = double.tryParse(value);

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(label, style: Theme.of(context).textTheme.bodyMedium),
              if (icon != null) Icon(icon, color: Theme.of(context).colorScheme.primary, size: 20),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              if (numericValue != null)
                TweenAnimationBuilder<double>(
                  tween: Tween(begin: 0, end: numericValue),
                  duration: const Duration(milliseconds: 600),
                  curve: Curves.easeOutCubic,
                  builder: (context, animatedValue, _) => Text(
                    numericValue == numericValue.roundToDouble()
                        ? animatedValue.round().toString()
                        : animatedValue.toStringAsFixed(1),
                    style: Theme.of(context).textTheme.displaySmall?.copyWith(
                          color: Theme.of(context).colorScheme.primary,
                        ),
                  ),
                )
              else
                Text(
                  value,
                  style: Theme.of(context).textTheme.displaySmall?.copyWith(
                        color: Theme.of(context).colorScheme.primary,
                      ),
                ),
              if (unit != null) ...[
                const SizedBox(width: 4),
                Text(unit!, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.grey500)),
              ],
            ],
          ),
          if (trend != null) ...[
            const SizedBox(height: 6),
            Row(
              children: [
                Icon(
                  trendPositive ? Icons.trending_up : Icons.trending_down,
                  size: 14,
                  color: trendPositive ? AppColors.successFg : AppColors.errorFg,
                ),
                const SizedBox(width: 4),
                Text(
                  trend!,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: trendPositive ? AppColors.successFg : AppColors.errorFg,
                      ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
```

`backgroundColor` is intentionally dropped from `StatCard`'s rendering (it previously tinted the whole card; the new `AppCard` is always white for consistency) — remove the `backgroundColor` field reads but keep the constructor parameter accepting and ignoring it so existing call sites (which pass `backgroundColor: AppColors.primaryLight` etc.) keep compiling without edits in this task. Do this by leaving `final Color? backgroundColor;` in the class and simply not referencing it in `build()`, as shown above.

- [ ] **Step 2: Verify it compiles**

Run: `cd health_app && flutter analyze lib/widgets/common_widgets.dart`
Expected: `No issues found!`

- [ ] **Step 3: Manual check**

Run: `cd health_app && flutter run -d chrome`, navigate to Home screen, confirm stat cards show soft shadows, 20px radius, and animated count-up numbers.

- [ ] **Step 4: Commit**

```bash
git add health_app/lib/widgets/common_widgets.dart
git commit -m "feat: add AppCard base, rebuild HealthCard/StatCard with shadows and trend indicator"
```

---

### Task 9: `StatusPill` component

**Files:**
- Create: `health_app/lib/widgets/status_pill.dart`

**Interfaces:**
- Produces: `StatusPill({required String label, required StatusPillTone tone})` where `StatusPillTone` is an enum `{success, warning, error, info, neutral}`, each mapping to a `Bg`/`Fg` color pair from `AppColors`.
- Consumed by: Task 18 (body/food scan urgency + confidence), Task 21 (doctor queue severity), Task 22 (consultation status badges).

- [ ] **Step 1: Create the widget**

```dart
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

enum StatusPillTone { success, warning, error, info, neutral }

class StatusPill extends StatelessWidget {
  const StatusPill({super.key, required this.label, this.tone = StatusPillTone.neutral, this.icon});

  final String label;
  final StatusPillTone tone;
  final IconData? icon;

  (Color bg, Color fg) _colors() {
    switch (tone) {
      case StatusPillTone.success:
        return (AppColors.successBg, AppColors.successFg);
      case StatusPillTone.warning:
        return (AppColors.warningBg, AppColors.warningFg);
      case StatusPillTone.error:
        return (AppColors.errorBg, AppColors.errorFg);
      case StatusPillTone.info:
        return (AppColors.infoBg, AppColors.infoFg);
      case StatusPillTone.neutral:
        return (AppColors.grey100, AppColors.grey700);
    }
  }

  @override
  Widget build(BuildContext context) {
    final (bg, fg) = _colors();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 13, color: fg),
            const SizedBox(width: 4),
          ],
          Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(color: fg, fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd health_app && flutter analyze lib/widgets/status_pill.dart`
Expected: `No issues found!`

- [ ] **Step 3: Commit**

```bash
git add health_app/lib/widgets/status_pill.dart
git commit -m "feat: add StatusPill component"
```

---

### Task 10: Restyle `CustomTextField`

**Files:**
- Modify: `health_app/lib/widgets/common_widgets.dart:44-101` (existing `CustomTextField`)

**Interfaces:**
- Produces: `CustomTextField` — same public API (`label, hint, controller, keyboardType, obscureText, validator, prefixIcon, suffixIcon`), visually refined label style and spacing.
- Consumed by: every screen that already uses it (no call-site changes).

- [ ] **Step 1: Update the label style and spacing**

In `health_app/lib/widgets/common_widgets.dart`, inside `_CustomTextFieldState.build()`, replace:

```dart
        Text(
          widget.label,
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
```

with:

```dart
        Text(
          widget.label,
          style: Theme.of(context).textTheme.labelLarge?.copyWith(color: AppColors.grey700),
        ),
        const SizedBox(height: AppSpacing.sm),
```

- [ ] **Step 2: Verify it compiles**

Run: `cd health_app && flutter analyze lib/widgets/common_widgets.dart`
Expected: `No issues found!`

- [ ] **Step 3: Commit**

```bash
git add health_app/lib/widgets/common_widgets.dart
git commit -m "style: refine CustomTextField label styling"
```

---

### Task 11: New components — `SectionHeader`, `AvatarWithStatus`, `MetricRing`

**Files:**
- Create: `health_app/lib/widgets/section_header.dart`
- Create: `health_app/lib/widgets/avatar_with_status.dart`
- Create: `health_app/lib/widgets/metric_ring.dart`

**Interfaces:**
- Produces:
  - `SectionHeader({required String title, String? actionLabel, VoidCallback? onActionTap})`
  - `AvatarWithStatus({required IconData icon, required bool isOnline, double size = 44})`
  - `MetricRing({required double value, required double maxValue, required String centerLabel, String? centerSubLabel, double size = 120, Color? color})` — animated circular progress ring drawn with `CustomPainter`.
- Consumed by: Task 15 (Home — `MetricRing` for health score, `SectionHeader` for "This Week"), Task 21 (Doctor dashboard — `AvatarWithStatus`, `SectionHeader`).

- [ ] **Step 1: Create `SectionHeader`**

```dart
import 'package:flutter/material.dart';

class SectionHeader extends StatelessWidget {
  const SectionHeader({
    super.key,
    required this.title,
    this.actionLabel,
    this.onActionTap,
  });

  final String title;
  final String? actionLabel;
  final VoidCallback? onActionTap;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(title, style: Theme.of(context).textTheme.titleLarge),
        if (actionLabel != null)
          TextButton(
            onPressed: onActionTap,
            child: Text(actionLabel!),
          ),
      ],
    );
  }
}
```

- [ ] **Step 2: Create `AvatarWithStatus`**

```dart
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class AvatarWithStatus extends StatelessWidget {
  const AvatarWithStatus({
    super.key,
    required this.icon,
    required this.isOnline,
    this.size = 44,
  });

  final IconData icon;
  final bool isOnline;
  final double size;

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;
    final dotSize = size * 0.28;

    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Container(
            width: size,
            height: size,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(
                colors: [primary.withValues(alpha: 0.18), primary.withValues(alpha: 0.08)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
            child: Icon(icon, color: primary, size: size * 0.5),
          ),
          Positioned(
            right: -1,
            bottom: -1,
            child: Container(
              width: dotSize,
              height: dotSize,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: isOnline ? AppColors.success : AppColors.grey400,
                border: Border.all(color: AppColors.white, width: 2),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
```

- [ ] **Step 3: Create `MetricRing`**

```dart
import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class MetricRing extends StatelessWidget {
  const MetricRing({
    super.key,
    required this.value,
    required this.maxValue,
    required this.centerLabel,
    this.centerSubLabel,
    this.size = 120,
    this.color,
  });

  final double value;
  final double maxValue;
  final String centerLabel;
  final String? centerSubLabel;
  final double size;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final ringColor = color ?? Theme.of(context).colorScheme.primary;
    final fraction = maxValue <= 0 ? 0.0 : (value / maxValue).clamp(0.0, 1.0);

    return SizedBox(
      width: size,
      height: size,
      child: TweenAnimationBuilder<double>(
        tween: Tween(begin: 0, end: fraction),
        duration: const Duration(milliseconds: 800),
        curve: Curves.easeOutCubic,
        builder: (context, animatedFraction, _) {
          return CustomPaint(
            painter: _RingPainter(fraction: animatedFraction, color: ringColor),
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(centerLabel, style: Theme.of(context).textTheme.headlineSmall),
                  if (centerSubLabel != null)
                    Text(
                      centerSubLabel!,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.grey500),
                    ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  _RingPainter({required this.fraction, required this.color});

  final double fraction;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.shortestSide - 12) / 2;

    final trackPaint = Paint()
      ..color = color.withValues(alpha: 0.12)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 10
      ..strokeCap = StrokeCap.round;

    final progressPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 10
      ..strokeCap = StrokeCap.round;

    canvas.drawCircle(center, radius, trackPaint);
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -math.pi / 2,
      2 * math.pi * fraction,
      false,
      progressPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _RingPainter oldDelegate) =>
      oldDelegate.fraction != fraction || oldDelegate.color != color;
}
```

- [ ] **Step 4: Verify all three compile**

Run: `cd health_app && flutter analyze lib/widgets/section_header.dart lib/widgets/avatar_with_status.dart lib/widgets/metric_ring.dart`
Expected: `No issues found!`

- [ ] **Step 5: Commit**

```bash
git add health_app/lib/widgets/section_header.dart health_app/lib/widgets/avatar_with_status.dart health_app/lib/widgets/metric_ring.dart
git commit -m "feat: add SectionHeader, AvatarWithStatus, MetricRing components"
```

---

### Task 12: Restyle auth-choice screen

**Files:**
- Modify: `health_app/lib/screens/auth/auth_choice_screen.dart`

**Interfaces:**
- Consumes: `AppColors.primaryDeep` (Task 3), `AppSpacing`/`AppShadows` (Task 2).
- No public API change (`onPatientTap`, `onDoctorTap` unchanged).

- [ ] **Step 1: Deepen the hero gradient and card shadow**

In `health_app/lib/screens/auth/auth_choice_screen.dart`, replace the outer `Container`'s `decoration` (lines 18–23):

```dart
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [Color(0xFFF7FBFF), Color(0xFFEAF7F2)],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        ),
      ),
```

with:

```dart
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [Color(0xFFF3FAF7), Color(0xFFE8F6EF), Color(0xFFF7FBFF)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
```

- [ ] **Step 2: Add a staggered fade-in to the two choice cards**

Replace the two `_ChoiceCard` usages (lines 92–104):

```dart
                _ChoiceCard(
                  icon: Icons.person_outline,
                  title: 'Patient',
                  description: 'Track health, chat with the assistant, and manage your records.',
                  onTap: onPatientTap,
                ),
                const SizedBox(height: 14),
                _ChoiceCard(
                  icon: Icons.medical_services_outlined,
                  title: 'Doctor',
                  description: 'Open the doctor portal for consultations and availability.',
                  onTap: onDoctorTap,
                ),
```

with:

```dart
                TweenAnimationBuilder<double>(
                  tween: Tween(begin: 0, end: 1),
                  duration: const Duration(milliseconds: 400),
                  curve: Curves.easeOut,
                  builder: (context, t, child) => Opacity(
                    opacity: t,
                    child: Transform.translate(offset: Offset(0, (1 - t) * 12), child: child),
                  ),
                  child: _ChoiceCard(
                    icon: Icons.person_outline,
                    title: 'Patient',
                    description: 'Track health, chat with the assistant, and manage your records.',
                    onTap: onPatientTap,
                  ),
                ),
                const SizedBox(height: 14),
                TweenAnimationBuilder<double>(
                  tween: Tween(begin: 0, end: 1),
                  duration: const Duration(milliseconds: 500),
                  curve: Curves.easeOut,
                  builder: (context, t, child) => Opacity(
                    opacity: t,
                    child: Transform.translate(offset: Offset(0, (1 - t) * 12), child: child),
                  ),
                  child: _ChoiceCard(
                    icon: Icons.medical_services_outlined,
                    title: 'Doctor',
                    description: 'Open the doctor portal for consultations and availability.',
                    onTap: onDoctorTap,
                  ),
                ),
```

- [ ] **Step 2: Verify it compiles**

Run: `cd health_app && flutter analyze lib/screens/auth/auth_choice_screen.dart`
Expected: `No issues found!`

- [ ] **Step 3: Commit**

```bash
git add health_app/lib/screens/auth/auth_choice_screen.dart
git commit -m "style: refine auth choice screen gradient and add entrance animation"
```

---

### Task 13: Restyle patient login/signup forms

**Files:**
- Modify: `health_app/lib/screens/auth/login_screen.dart:66-83` (header block)
- Modify: `health_app/lib/screens/auth/signup_screen.dart:85-101` (header block)

**Interfaces:** No public API changes — both screens keep their existing constructors.

- [ ] **Step 1: Add an icon badge above the login header**

In `health_app/lib/screens/auth/login_screen.dart`, replace:

```dart
                const SizedBox(height: 40),
                // Header
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Welcome Back',
                      style: Theme.of(context).textTheme.displaySmall,
                    ),
```

with:

```dart
                const SizedBox(height: 24),
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [AppColors.primary.withValues(alpha: 0.18), AppColors.primary.withValues(alpha: 0.08)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: const Icon(Icons.favorite, color: AppColors.primary, size: 28),
                ),
                const SizedBox(height: 20),
                // Header
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Welcome Back',
                      style: Theme.of(context).textTheme.displaySmall,
                    ),
```

- [ ] **Step 2: Mirror the same badge on signup**

In `health_app/lib/screens/auth/signup_screen.dart`, replace:

```dart
                const SizedBox(height: 24),
                // Header
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Create Account',
                      style: Theme.of(context).textTheme.displaySmall,
                    ),
```

with:

```dart
                const SizedBox(height: 16),
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [AppColors.primary.withValues(alpha: 0.18), AppColors.primary.withValues(alpha: 0.08)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: const Icon(Icons.person_add_alt_1, color: AppColors.primary, size: 28),
                ),
                const SizedBox(height: 20),
                // Header
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Create Account',
                      style: Theme.of(context).textTheme.displaySmall,
                    ),
```

- [ ] **Step 3: Verify it compiles**

Run: `cd health_app && flutter analyze lib/screens/auth/login_screen.dart lib/screens/auth/signup_screen.dart`
Expected: `No issues found!`

- [ ] **Step 4: Commit**

```bash
git add health_app/lib/screens/auth/login_screen.dart health_app/lib/screens/auth/signup_screen.dart
git commit -m "style: add icon badge to login and signup headers"
```

---

### Task 14: Restyle doctor auth screen

**Files:**
- Modify: `health_app/lib/screens/auth/doctor_auth_screen.dart:111-124` (header block)

**Interfaces:** No public API change.

- [ ] **Step 1: Add an indigo icon badge and align copy with doctor branding**

Replace:

```dart
                const SizedBox(height: 16),
                Text(
                  _isLoginMode ? 'Doctor Sign In' : 'Doctor Sign Up',
                  style: Theme.of(context).textTheme.displaySmall,
                ),
                const SizedBox(height: 8),
                Text(
                  _isLoginMode
                      ? 'Access the doctor dashboard and consultation queue.'
                      : 'Create a doctor account to manage consultations and availability.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: AppColors.grey500,
                      ),
                ),
```

with:

```dart
                const SizedBox(height: 12),
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [AppColors.doctorPrimaryLight, Color(0x0D4F46E5)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: const Icon(Icons.medical_services, color: AppColors.doctorPrimary, size: 28),
                ),
                const SizedBox(height: 16),
                Text(
                  _isLoginMode ? 'Doctor Sign In' : 'Doctor Sign Up',
                  style: Theme.of(context).textTheme.displaySmall,
                ),
                const SizedBox(height: 8),
                Text(
                  _isLoginMode
                      ? 'Access the doctor dashboard and consultation queue.'
                      : 'Create a doctor account to manage consultations and availability.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: AppColors.grey500,
                      ),
                ),
```

Note: since this screen is shown before login (before the role-based `MaterialApp` theme applies), its primary button still renders with the patient `AppTheme.lightTheme` emerald color — that is expected; only the icon badge signals doctor branding pre-login. Full indigo theming applies once a doctor is authenticated (Task 6).

- [ ] **Step 2: Verify it compiles**

Run: `cd health_app && flutter analyze lib/screens/auth/doctor_auth_screen.dart`
Expected: `No issues found!`

- [ ] **Step 3: Commit**

```bash
git add health_app/lib/screens/auth/doctor_auth_screen.dart
git commit -m "style: add indigo icon badge to doctor auth header"
```

---

### Task 15: Restyle Home screen

**Files:**
- Modify: `health_app/lib/screens/home/home_screen.dart`

**Interfaces:**
- Consumes: `AppColors.primaryDeep` (Task 3), `SectionHeader`, `MetricRing` (Task 11), `AppCard` (Task 8).

- [ ] **Step 1: Import new widgets**

In `health_app/lib/screens/home/home_screen.dart`, after the existing imports, add:

```dart
import '../../widgets/section_header.dart';
import '../../widgets/metric_ring.dart';
```

- [ ] **Step 2: Update the welcome gradient to use `primaryDeep`**

Replace:

```dart
                gradient: const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [AppColors.primary, AppColors.primaryDark],
                ),
                borderRadius: BorderRadius.circular(12),
```

with:

```dart
                gradient: const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [AppColors.primary, AppColors.primaryDeep],
                ),
                borderRadius: BorderRadius.circular(20),
```

- [ ] **Step 3: Replace the "This Week" row with `SectionHeader` and add a `MetricRing` health-score hero above it**

Replace:

```dart
            // Health metrics
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'This Week',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      TextButton(
                        onPressed: onNavigateInsights,
                        child: const Text('View All'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                ],
              ),
            ),
```

with:

```dart
            // Health score hero
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: AppCard(
                child: Row(
                  children: [
                    MetricRing(
                      value: (10 - healthReview.reasons.length).clamp(0, 10).toDouble(),
                      maxValue: 10,
                      centerLabel: '${(10 - healthReview.reasons.length).clamp(0, 10)}',
                      centerSubLabel: '/ 10',
                      size: 88,
                    ),
                    const SizedBox(width: 20),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Health score', style: Theme.of(context).textTheme.titleMedium),
                          const SizedBox(height: 4),
                          Text(
                            healthReview.statusLabel,
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.grey500),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Health metrics
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: SectionHeader(
                title: 'This Week',
                actionLabel: 'View All',
                onActionTap: onNavigateInsights,
              ),
            ),
            const SizedBox(height: 12),
```

- [ ] **Step 4: Verify it compiles**

Run: `cd health_app && flutter analyze lib/screens/home/home_screen.dart`
Expected: `No issues found!`

- [ ] **Step 5: Manual check**

Run: `cd health_app && flutter run -d chrome`, log in as a patient, confirm the Home screen shows the health-score ring, refined gradient, and animated stat cards.

- [ ] **Step 6: Commit**

```bash
git add health_app/lib/screens/home/home_screen.dart
git commit -m "feat: add health-score MetricRing hero and SectionHeader to Home screen"
```

---

### Task 16: Restyle Chat screen bubbles

**Files:**
- Modify: `health_app/lib/screens/chat/chat_screen.dart`

**Interfaces:** No public API change (`initialMessage` constructor param unchanged).

- [ ] **Step 1: Gradient-fill the user bubble and round both bubbles more**

Replace:

```dart
                        // User message
                        Align(
                          alignment: Alignment.centerRight,
                          child: Container(
                            margin: const EdgeInsets.only(left: 32),
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: AppColors.primary,
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text(
                              message.message,
                              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                    color: AppColors.white,
                                  ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        // AI response
                        Align(
                          alignment: Alignment.centerLeft,
                          child: Container(
                            margin: const EdgeInsets.only(right: 32),
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: AppColors.grey100,
                              borderRadius: BorderRadius.circular(12),
                            ),
```

with:

```dart
                        // User message
                        Align(
                          alignment: Alignment.centerRight,
                          child: Container(
                            margin: const EdgeInsets.only(left: 32),
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              gradient: const LinearGradient(
                                colors: [AppColors.primary, AppColors.primaryDeep],
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                              ),
                              borderRadius: const BorderRadius.only(
                                topLeft: Radius.circular(18),
                                topRight: Radius.circular(18),
                                bottomLeft: Radius.circular(18),
                                bottomRight: Radius.circular(4),
                              ),
                            ),
                            child: Text(
                              message.message,
                              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                    color: AppColors.white,
                                  ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        // AI response
                        Align(
                          alignment: Alignment.centerLeft,
                          child: Container(
                            margin: const EdgeInsets.only(right: 32),
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: AppColors.grey100,
                              borderRadius: const BorderRadius.only(
                                topLeft: Radius.circular(18),
                                topRight: Radius.circular(18),
                                bottomLeft: Radius.circular(4),
                                bottomRight: Radius.circular(18),
                              ),
                            ),
```

- [ ] **Step 2: Verify it compiles**

Run: `cd health_app && flutter analyze lib/screens/chat/chat_screen.dart`
Expected: `No issues found!`

- [ ] **Step 3: Commit**

```bash
git add health_app/lib/screens/chat/chat_screen.dart
git commit -m "style: gradient-fill chat bubbles with asymmetric corner radii"
```

---

### Task 17: Restyle Health Tracking tab bar

**Files:**
- Modify: `health_app/lib/screens/health/health_tracking_screen.dart:64-82` (`_buildTabButton`)

**Interfaces:** No public API change.

- [ ] **Step 1: Round the tab pills further and add a subtle shadow when selected**

Replace `_buildTabButton`:

```dart
  Widget _buildTabButton(BuildContext context, String label, int index) {
    final isSelected = _selectedTab == index;
    return GestureDetector(
      onTap: () => setState(() => _selectedTab = index),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.primary : AppColors.grey100,
          borderRadius: BorderRadius.circular(24),
        ),
        child: Text(
          label,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                color: isSelected ? AppColors.white : AppColors.grey700,
              ),
        ),
      ),
    );
  }
```

with:

```dart
  Widget _buildTabButton(BuildContext context, String label, int index) {
    final isSelected = _selectedTab == index;
    final primary = Theme.of(context).colorScheme.primary;
    return GestureDetector(
      onTap: () => setState(() => _selectedTab = index),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
        decoration: BoxDecoration(
          color: isSelected ? primary : AppColors.grey100,
          borderRadius: BorderRadius.circular(999),
          boxShadow: isSelected
              ? [BoxShadow(color: primary.withValues(alpha: 0.28), blurRadius: 12, offset: const Offset(0, 4))]
              : null,
        ),
        child: Text(
          label,
          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                color: isSelected ? AppColors.white : AppColors.grey700,
              ),
        ),
      ),
    );
  }
```

- [ ] **Step 2: Verify it compiles**

Run: `cd health_app && flutter analyze lib/screens/health/health_tracking_screen.dart`
Expected: `No issues found!`

- [ ] **Step 3: Commit**

```bash
git add health_app/lib/screens/health/health_tracking_screen.dart
git commit -m "style: animate health tracking tab pills with theme-aware color and shadow"
```

---

### Task 18: Restyle body-scan and food-scan result badges with `StatusPill`

**Files:**
- Modify: `health_app/lib/screens/scan/body_scan_screen.dart`
- Modify: `health_app/lib/widgets/food_scan_widget.dart`

**Interfaces:**
- Consumes: `StatusPill`, `StatusPillTone` (Task 9).

- [ ] **Step 1: Import `StatusPill` in body scan**

In `health_app/lib/screens/scan/body_scan_screen.dart`, after the existing imports, add:

```dart
import '../../widgets/status_pill.dart';
```

- [ ] **Step 2: Replace the plain urgency text with a `StatusPill`**

Replace:

```dart
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          const Text('Urgency: '),
                          Text(
                            _result!.urgencyLevel,
                            style: TextStyle(
                              color: _urgencyColor(_result!.urgencyLevel),
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
```

with:

```dart
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          const Text('Urgency: '),
                          const SizedBox(width: 8),
                          StatusPill(
                            label: _result!.urgencyLevel.toUpperCase(),
                            tone: _urgencyTone(_result!.urgencyLevel),
                          ),
                        ],
                      ),
```

- [ ] **Step 3: Add the tone-mapping helper next to the existing `_urgencyColor`**

Replace:

```dart
  Color _urgencyColor(String urgency) {
    final value = urgency.toLowerCase();
    if (value == 'moderate' || value == 'high') return AppColors.error;
    if (value == 'review') return AppColors.accent;
    return AppColors.secondary;
  }
```

with:

```dart
  Color _urgencyColor(String urgency) {
    final value = urgency.toLowerCase();
    if (value == 'moderate' || value == 'high') return AppColors.error;
    if (value == 'review') return AppColors.accent;
    return AppColors.secondary;
  }

  StatusPillTone _urgencyTone(String urgency) {
    final value = urgency.toLowerCase();
    if (value == 'moderate' || value == 'high') return StatusPillTone.error;
    if (value == 'review') return StatusPillTone.warning;
    return StatusPillTone.info;
  }
```

- [ ] **Step 4: Import `StatusPill` in the food scan widget**

In `health_app/lib/widgets/food_scan_widget.dart`, after the existing imports, add:

```dart
import 'status_pill.dart';
```

- [ ] **Step 5: Replace the confidence badge with `StatusPill`**

Replace:

```dart
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                            decoration: BoxDecoration(
                              color: _confidenceColor(_result!.confidence).withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(999),
                            ),
                            child: Text(
                              '${(_result!.confidence * 100).toStringAsFixed(0)}%',
                              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                                    color: _confidenceColor(_result!.confidence),
                                    fontWeight: FontWeight.w700,
                                  ),
                            ),
                          ),
```

with:

```dart
                          StatusPill(
                            label: '${(_result!.confidence * 100).toStringAsFixed(0)}%',
                            tone: _confidenceTone(_result!.confidence),
                          ),
```

- [ ] **Step 6: Add the tone-mapping helper next to `_confidenceColor`**

Replace:

```dart
  Color _confidenceColor(double confidence) {
    if (confidence >= 0.8) return AppColors.success;
    if (confidence >= 0.6) return AppColors.accent;
    return AppColors.error;
  }
```

with:

```dart
  Color _confidenceColor(double confidence) {
    if (confidence >= 0.8) return AppColors.success;
    if (confidence >= 0.6) return AppColors.accent;
    return AppColors.error;
  }

  StatusPillTone _confidenceTone(double confidence) {
    if (confidence >= 0.8) return StatusPillTone.success;
    if (confidence >= 0.6) return StatusPillTone.warning;
    return StatusPillTone.error;
  }
```

- [ ] **Step 7: Verify it compiles**

Run: `cd health_app && flutter analyze lib/screens/scan/body_scan_screen.dart lib/widgets/food_scan_widget.dart`
Expected: `No issues found!`

- [ ] **Step 8: Commit**

```bash
git add health_app/lib/screens/scan/body_scan_screen.dart health_app/lib/widgets/food_scan_widget.dart
git commit -m "feat: use StatusPill for body/food scan confidence and urgency badges"
```

---

### Task 19: Restyle Insights feed with `AppCard` and left-accent bar

**Files:**
- Modify: `health_app/lib/screens/insights/insights_screen.dart`

**Interfaces:**
- Consumes: `AppCard` (Task 8).

- [ ] **Step 1: Replace the raw `Card` with a color-accented `AppCard`**

Replace:

```dart
              final insight = insights[index];
              return Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
```

with:

```dart
              final insight = insights[index];
              final categoryColor = Theme.of(context).colorScheme.primary;
              return Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(20),
                  border: Border(left: BorderSide(color: categoryColor, width: 4)),
                ),
                child: AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
```

Then, immediately before the final closing of that `itemBuilder` return value, replace the trailing:

```dart
                    ],
                  ),
                ),
              );
```

with:

```dart
                    ],
                  ),
                ),
              );
```

(no change needed here — the widget tree still closes with the same nesting depth since `AppCard` takes the place of `Card`+`Padding` as a single wrapper; verify indentation matches after the edit and run `dart format lib/screens/insights/insights_screen.dart` if the analyzer flags formatting.)

- [ ] **Step 2: Verify it compiles**

Run: `cd health_app && flutter analyze lib/screens/insights/insights_screen.dart`
Expected: `No issues found!` (fix any bracket-matching issues introduced by the wrapper change — `AppCard`'s `child:` replaces the old `Padding(padding: ..., child: Column(...))`, so the inner `Padding` with `EdgeInsets.all(16)` must be removed since `AppCard` already applies `16` default padding.)

- [ ] **Step 3: Commit**

```bash
git add health_app/lib/screens/insights/insights_screen.dart
git commit -m "style: use AppCard with category accent bar for insights feed"
```

---

### Task 20: Restyle Profile screen header and settings tiles

**Files:**
- Modify: `health_app/lib/screens/profile/profile_screen.dart`

**Interfaces:**
- Consumes: `AppColors.primaryDeep` (Task 3), `AppCard` (Task 8).

- [ ] **Step 1: Update the header gradient**

Replace:

```dart
                  gradient: const LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [AppColors.primary, AppColors.primaryDark],
                  ),
                  borderRadius: BorderRadius.circular(12),
```

with:

```dart
                  gradient: const LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [AppColors.primary, AppColors.primaryDeep],
                  ),
                  borderRadius: BorderRadius.circular(24),
```

- [ ] **Step 2: Rebuild `_SettingsTile` on `AppCard`**

In `health_app/lib/screens/profile/profile_screen.dart`, add the import after the existing ones:

```dart
import '../../widgets/status_pill.dart';
```

(imported for later reuse is unnecessary here — skip this import; not needed for this task.)

Replace the `_SettingsTile.build()` method:

```dart
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Card(
        margin: const EdgeInsets.only(bottom: 8),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(icon, color: AppColors.primary, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleSmall,
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subtitle,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: AppColors.grey500,
                          ),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.arrow_forward_ios, size: 16, color: AppColors.grey400),
            ],
          ),
        ),
      ),
    );
  }
```

with:

```dart
  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: AppCard(
        onTap: onTap,
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [primary.withValues(alpha: 0.16), primary.withValues(alpha: 0.08)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: primary, size: 20),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: Theme.of(context).textTheme.titleSmall),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.grey500),
                  ),
                ],
              ),
            ),
            const Icon(Icons.arrow_forward_ios, size: 16, color: AppColors.grey400),
          ],
        ),
      ),
    );
  }
```

Do not add the unused `status_pill.dart` import from earlier in this step — omit it; it was noted only to be skipped.

- [ ] **Step 3: Verify it compiles**

Run: `cd health_app && flutter analyze lib/screens/profile/profile_screen.dart`
Expected: `No issues found!`

- [ ] **Step 4: Commit**

```bash
git add health_app/lib/screens/profile/profile_screen.dart
git commit -m "style: rebuild profile header gradient and settings tiles on AppCard"
```

---

### Task 21: Restyle Doctor dashboard — `AvatarWithStatus`, `SectionHeader`, `StatusPill` for severity

**Files:**
- Modify: `health_app/lib/screens/doctor/doctor_navigation_screen.dart`

**Interfaces:**
- Consumes: `AvatarWithStatus`, `SectionHeader` (Task 11), `StatusPill`/`StatusPillTone` (Task 9).

- [ ] **Step 1: Import the new widgets**

After the existing imports in `health_app/lib/screens/doctor/doctor_navigation_screen.dart`, add:

```dart
import '../../widgets/avatar_with_status.dart';
import '../../widgets/section_header.dart';
import '../../widgets/status_pill.dart';
```

- [ ] **Step 2: Replace the `CircleAvatar` in the profile card with `AvatarWithStatus`**

Replace:

```dart
                      Row(
                        children: [
                          const CircleAvatar(child: Icon(Icons.medical_services)),
                          const SizedBox(width: 12),
```

with:

```dart
                      Row(
                        children: [
                          AvatarWithStatus(icon: Icons.medical_services, isOnline: profile.isAvailable),
                          const SizedBox(width: 12),
```

- [ ] **Step 3: Replace `Text('Today at a glance', ...)` and `Text('Open Queue', ...)` with `SectionHeader`**

Replace:

```dart
                            Text('Today at a glance', style: Theme.of(context).textTheme.titleLarge),
                            const SizedBox(height: 12),
```

with:

```dart
                            const SectionHeader(title: 'Today at a glance'),
                            const SizedBox(height: 12),
```

Replace:

```dart
                            Text('Open Queue', style: Theme.of(context).textTheme.titleLarge),
                            const SizedBox(height: 8),
```

with:

```dart
                            const SectionHeader(title: 'Open Queue'),
                            const SizedBox(height: 8),
```

- [ ] **Step 4: Add a severity-to-tone helper and use `StatusPill` for the urgent-case ticket label**

Replace the module-level `Color _severityColor(String severityLevel) { ... }` function (near the bottom of the file) — keep it as-is, and add a new function directly after it:

```dart
StatusPillTone _severityTone(String severityLevel) {
  switch (severityLevel.toLowerCase()) {
    case 'critical':
      return StatusPillTone.error;
    case 'high':
      return StatusPillTone.warning;
    case 'medium':
      return StatusPillTone.info;
    default:
      return StatusPillTone.success;
  }
}
```

Then, in the queue `ListTile` title inside `DoctorDashboardScreen.build()`, replace:

```dart
                                  title: Text('Ticket #${ticket.id} · ${ticket.severityLevel}'),
```

(the one inside `...prioritizedQueue.take(6).map(...)`) with:

```dart
                                  title: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Text('Ticket #${ticket.id}'),
                                      const SizedBox(width: 8),
                                      StatusPill(label: ticket.severityLevel.toUpperCase(), tone: _severityTone(ticket.severityLevel)),
                                    ],
                                  ),
```

- [ ] **Step 5: Verify it compiles**

Run: `cd health_app && flutter analyze lib/screens/doctor/doctor_navigation_screen.dart`
Expected: `No issues found!`

- [ ] **Step 6: Manual check**

Run: `cd health_app && flutter run -d chrome`, log in as a doctor, confirm the dashboard shows `AvatarWithStatus`, indigo-accented buttons/switch track, and severity pills in the queue.

- [ ] **Step 7: Commit**

```bash
git add health_app/lib/screens/doctor/doctor_navigation_screen.dart
git commit -m "feat: use AvatarWithStatus, SectionHeader, StatusPill in doctor dashboard"
```

---

### Task 22: Restyle Consultation chat — clinical header badges + bubble radii

**Files:**
- Modify: `health_app/lib/screens/consultation/consultation_chat_screen.dart`

**Interfaces:**
- Consumes: `StatusPill`/`StatusPillTone` (Task 9).

- [ ] **Step 1: Import `StatusPill`**

After the existing imports, add:

```dart
import '../../widgets/status_pill.dart';
```

- [ ] **Step 2: Replace the private `_Badge` usages with `StatusPill`**

Replace:

```dart
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _Badge(label: _ticket.severityLevel.toUpperCase()),
                    _Badge(label: _ticket.status.toUpperCase()),
                    _Badge(label: _ticket.triggerSource.toUpperCase()),
                  ],
                ),
```

with:

```dart
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    StatusPill(label: _ticket.severityLevel.toUpperCase(), tone: _severityTone(_ticket.severityLevel)),
                    StatusPill(label: _ticket.status.toUpperCase(), tone: StatusPillTone.info),
                    StatusPill(label: _ticket.triggerSource.toUpperCase(), tone: StatusPillTone.neutral),
                  ],
                ),
```

- [ ] **Step 3: Add the local `_severityTone` helper and remove the now-unused `_Badge` class**

Replace the trailing `class _Badge extends StatelessWidget { ... }` block (the whole class, at the end of the file) with:

```dart
StatusPillTone _severityTone(String severityLevel) {
  switch (severityLevel.toLowerCase()) {
    case 'critical':
      return StatusPillTone.error;
    case 'high':
      return StatusPillTone.warning;
    case 'medium':
      return StatusPillTone.info;
    default:
      return StatusPillTone.success;
  }
}
```

- [ ] **Step 4: Round message bubbles asymmetrically to match Task 16's chat styling**

Replace:

```dart
                                  decoration: BoxDecoration(
                                    color: isMine ? AppColors.primary : AppColors.grey100,
                                    borderRadius: BorderRadius.circular(14),
                                  ),
```

with:

```dart
                                  decoration: BoxDecoration(
                                    color: isMine ? Theme.of(context).colorScheme.primary : AppColors.grey100,
                                    borderRadius: BorderRadius.only(
                                      topLeft: const Radius.circular(18),
                                      topRight: const Radius.circular(18),
                                      bottomLeft: Radius.circular(isMine ? 18 : 4),
                                      bottomRight: Radius.circular(isMine ? 4 : 18),
                                    ),
                                  ),
```

- [ ] **Step 5: Verify it compiles**

Run: `cd health_app && flutter analyze lib/screens/consultation/consultation_chat_screen.dart`
Expected: `No issues found!`

- [ ] **Step 6: Commit**

```bash
git add health_app/lib/screens/consultation/consultation_chat_screen.dart
git commit -m "style: use StatusPill for consultation badges and asymmetric bubble radii"
```

---

### Task 23: Final verification pass

**Files:** None (verification only).

**Interfaces:** None.

- [ ] **Step 1: Full static analysis**

Run: `cd health_app && flutter analyze`
Expected: `No issues found!` across the whole project. Fix any remaining warnings before proceeding.

- [ ] **Step 2: Run the existing widget test**

Run: `cd health_app && flutter test`
Expected: All tests pass. If `test/widget_test.dart` references a widget renamed or removed in this plan (it currently only smoke-tests default `flutter create` counter behavior per the pre-existing file — confirm this by reading it; if it still references the stock counter app rather than `MyApp`, leave it as-is since it's unrelated to this redesign), no changes are needed. If it does reference `MyApp`/`AuthWrapper`, update its expectations to match Task 6's `ConsumerWidget`-based `MyApp`.

- [ ] **Step 3: Manual walkthrough — patient flow**

Run: `cd health_app && flutter run -d chrome`. Walk through: auth choice → patient login/signup → home (health score ring, stat cards, quick actions) → chat (send a message, confirm gradient bubble) → health tracking (switch tabs, log an entry) → body scan (pick an image, analyze, confirm `StatusPill` urgency) → insights (confirm accent-bar cards) → profile (confirm gradient header, settings tiles). Confirm no layout overflow errors in the debug console.

- [ ] **Step 4: Manual walkthrough — doctor flow**

Log out, log in via doctor auth. Confirm indigo theme applies app-wide (buttons, switches, focus rings). Walk through: doctor dashboard (avatar status dot, section headers, severity pills) → open a consultation from the queue → consultation chat (badges, bubble colors) → profile → log out.

- [ ] **Step 5: Fix any issues found during manual walkthrough**

If overflow, contrast, or interaction issues appear, fix them in the relevant screen/component file (not a new design round — targeted fixes within the tokens/components established in Tasks 1–11).

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "chore: verify Heallio UI redesign end to end"
```

---

## Self-Review Notes

- **Spec coverage:** Typography (Task 4) ✓, color/doctor palette (Task 3, 5, 6) ✓, elevation/shape/spacing (Task 2, 5) ✓, role-based theming (Task 6) ✓, component library — buttons/cards/pills/inputs/new components (Tasks 7–11) ✓, all listed patient screens (Tasks 12–20) ✓, all listed doctor screens (Tasks 21–22) ✓, motion — press scale, staggered fade-in, count-up, bubble transitions (Tasks 7, 8, 11, 12) ✓, verification (Task 23) ✓.
- **Placeholder scan:** No TBD/TODO markers; every step carries literal code or an exact command with expected output.
- **Type consistency:** `StatusPillTone` enum values (`success, warning, error, info, neutral`) are used identically across Tasks 9, 18, 21, 22. `AppCard({child, onTap, padding, raised})` signature from Task 8 is used identically in Tasks 15, 19, 20. `MetricRing({value, maxValue, centerLabel, centerSubLabel, size, color})` from Task 11 matches its single usage in Task 15.
- **Risk called out:** Task 19's `Card` → `AppCard` swap requires removing the now-redundant inner `Padding(EdgeInsets.all(16))` — flagged explicitly in that task's Step 2 so the implementer doesn't end up with double padding.
