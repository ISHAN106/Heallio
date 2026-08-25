import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Color values are pulled directly from the Material color tokens baked
/// into docs/stitch_screens/html/*.html (the Stitch-generated mockups —
/// same tailwind config repeated verbatim across every screen), not from
/// the earlier docs/stitch_design_prompt.md spec's bespoke "Signal Blue"
/// palette. The HTML is the source of truth for exact colors.
class AppColors {
  // Primary brand color (patient mode) — mockup's "primary" / "primary-fixed-dim".
  static const Color primary = Color(0xFFACC7FF);
  static const Color primaryDeep = Color(0xFF005BBE); // mockup "inverse-primary"
  static const Color primaryLight = Color(0x33ACC7FF);
  static const Color primaryDark = Color(0xFF005BBE); // alias kept for compatibility
  static const Color onPrimary = Color(0xFF002F67); // mockup "on-primary" — dark text/icons on the pale primary fill

  // Secondary / accent
  static const Color secondary = Color(0xFFC4C6CE); // mockup "tertiary"
  static const Color accent = Color(0xFFF3BE65); // mockup "secondary-fixed-dim"

  // Doctor-mode accent (gold) — mockup's secondary/gold tonal family.
  static const Color doctorPrimary = Color(0xFFF3BE65); // "secondary-fixed-dim"
  static const Color doctorPrimaryDeep = Color(0xFF7E5700); // "secondary-container"
  static const Color doctorPrimaryLight = Color(0x33F3BE65);

  // Semantic colors
  static const Color success = Color(0xFF4ADE80);
  static const Color warning = Color(0xFFF3BE65);
  static const Color error = Color(0xFFFFB4AB); // mockup "error"
  static const Color onError = Color(0xFF690005); // mockup "on-error" — dark text/icons on the pale error fill
  static const Color info = Color(0xFF38BDF8);

  // Semantic tint/foreground pairs — dark-tinted bg + bright fg for pills/badges
  static const Color successBg = Color(0xFF14301F);
  static const Color successFg = Color(0xFF4ADE80);
  static const Color warningBg = Color(0xFF332412);
  static const Color warningFg = Color(0xFFFBBF24);
  static const Color errorBg = Color(0xFF93000A); // mockup "error-container"
  static const Color errorFg = Color(0xFFFFB4AB); // mockup "error"
  static const Color infoBg = Color(0xFF122A3A);
  static const Color infoFg = Color(0xFF60C7F5);

  // Elevated surfaces (cards, app bar, dialogs, sheets)
  static const Color surface = Color(0xFF1F1F24); // mockup "surface-container"
  static const Color surfaceRaised = Color(0xFF292A2E); // mockup "surface-container-high"

  // Liquid-glass surface tokens (frosted glassmorphism). Base colors from
  // the mockups' surface-container tonal steps; alpha/blur amounts kept
  // from the original glass design (the HTML uses the same /55, /65, /70
  // opacity conventions on these exact classes).
  static const Color glassPanel = Color(0x8C292A2E); // surface-container-high/55
  static const Color glassRaised = Color(0xA6343439); // surface-container-highest/65
  static const Color glassWell = Color(0xB31A1B20); // surface-container-low/70
  static const Color frostEdge = Color(0x1AFFFFFF); // mockup ".frost-edge": rgba(255,255,255,0.1)
  static const Color frostEdgeTop = Color(0x29FFFFFF); // brighter top edge (design embellishment, not in mockup CSS)

  // Neutral colors — mapped from the mockups' on-surface tonal ramp. Names
  // kept for compatibility with existing call sites; values run darkest
  // (grey50) to near-white (grey900) so headings/body text/backgrounds stay
  // correctly contrasted on the dark theme.
  static const Color white = Color(0xFFFFFFFF);
  static const Color black = Color(0xFF000000);
  static const Color grey50 = Color(0xFF0D0E12); // mockup "surface-container-lowest" — scaffold background
  static const Color grey100 = Color(0xFF1A1B20); // mockup "surface-container-low" — fills (inputs, chips)
  static const Color grey200 = Color(0xFF414754); // mockup "outline-variant" — borders, dividers
  static const Color grey300 = Color(0xFF5C6270); // muted icons
  static const Color grey400 = Color(0xFF767C8C); // hint text
  static const Color grey500 = Color(0xFF8B909F); // mockup "outline" — muted secondary text
  static const Color grey600 = Color(0xFFA8ADBC); // secondary body text
  static const Color grey700 = Color(0xFFC1C6D6); // mockup "on-surface-variant" — primary body text
  static const Color grey800 = Color(0xFFD1D4DE); // titleMedium text
  static const Color grey900 = Color(0xFFE3E2E7); // mockup "on-surface" — headings

  // Chart colors
  static const List<Color> chartGradient = [
    Color(0xFFACC7FF),
    Color(0xFFC4C6CE),
  ];
}

/// Geist Mono, per spec: every health metric (steps, heart rate, sleep hours,
/// confidence %) renders in monospace so digits align and feel instrument-grade.
/// Bundled as an asset (see pubspec.yaml) rather than via `google_fonts` —
/// the installed google_fonts package doesn't yet recognize 'Geist Mono' by
/// name (`getFont` throws), even though the family is live on Google Fonts.
class AppFonts {
  static TextStyle mono(TextStyle base) {
    return base.copyWith(fontFamily: 'GeistMono');
  }
}

class AppSpacing {
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 24;
  static const double xxl = 32;

  /// Bottom clearance for scrollable/fixed content on screens hosted inside
  /// [MainNavigationScreen] / [DoctorNavigationScreen]'s `extendBody: true`
  /// shell — those Scaffolds let content extend behind the floating
  /// [GlassBottomNav] dock (72px tall + 12px bottom margin = 84px) so it can
  /// blur beneath it per the design spec. Without this, the last card or a
  /// fixed bottom bar (e.g. the chat composer) ends up hidden behind the
  /// dock instead of merely blurred under it.
  static const double navClearance = 96;
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

class AppTheme {
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      primaryColor: AppColors.primary,
      scaffoldBackgroundColor: AppColors.grey50,
      colorScheme: const ColorScheme.dark(
        primary: AppColors.primary,
        secondary: AppColors.secondary,
        tertiary: AppColors.accent,
        error: AppColors.error,
        surface: AppColors.surface,
        surfaceContainer: AppColors.surfaceRaised,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.surface,
        elevation: 0,
        centerTitle: false,
        iconTheme: IconThemeData(color: AppColors.grey800),
        titleTextStyle: TextStyle(
          color: AppColors.grey900,
          fontSize: 20,
          fontWeight: FontWeight.w600,
        ),
      ),
      cardTheme: CardThemeData(
        color: AppColors.surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.glassWell,
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
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primary,
          foregroundColor: AppColors.onPrimary,
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
      textTheme: _buildTextTheme(),
      dividerTheme: const DividerThemeData(color: AppColors.grey200),
    );
  }

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
          foregroundColor: AppColors.black,
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

  static TextTheme _buildTextTheme() {
    // Headings: Outfit (spec's "Satoshi (or Outfit)" — Satoshi isn't on Google
    // Fonts, but Outfit has a typed google_fonts helper). Body: Geist,
    // bundled directly (see AppFonts doc comment above). Inter and Manrope
    // are banned by the design spec.
    final headingFont = GoogleFonts.outfit();
    const bodyFont = TextStyle(fontFamily: 'Geist');

    // Tight tracking (-0.02em) on every heading size, per spec.
    TextStyle heading({
      required double fontSize,
      required FontWeight fontWeight,
      required Color color,
      required double height,
    }) {
      return headingFont.copyWith(
        fontSize: fontSize,
        fontWeight: fontWeight,
        color: color,
        height: height,
        letterSpacing: fontSize * -0.02,
      );
    }

    return TextTheme(
      displayLarge: heading(
        fontSize: 32,
        fontWeight: FontWeight.w700,
        color: AppColors.grey900,
        height: 1.2,
      ),
      displayMedium: heading(
        fontSize: 28,
        fontWeight: FontWeight.w700,
        color: AppColors.grey900,
        height: 1.3,
      ),
      displaySmall: heading(
        fontSize: 24,
        fontWeight: FontWeight.w700,
        color: AppColors.grey900,
        height: 1.3,
      ),
      headlineLarge: heading(
        fontSize: 22,
        fontWeight: FontWeight.w600,
        color: AppColors.grey900,
        height: 1.4,
      ),
      headlineMedium: heading(
        fontSize: 20,
        fontWeight: FontWeight.w600,
        color: AppColors.grey900,
        height: 1.4,
      ),
      headlineSmall: heading(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        color: AppColors.grey900,
        height: 1.4,
      ),
      titleLarge: heading(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: AppColors.grey900,
        height: 1.5,
      ),
      titleMedium: heading(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        color: AppColors.grey800,
        height: 1.5,
      ),
      titleSmall: heading(
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
}
