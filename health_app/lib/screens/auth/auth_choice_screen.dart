import 'package:flutter/material.dart';

import '../../theme/app_theme.dart';
import '../../widgets/common_widgets.dart';

class AuthChoiceScreen extends StatelessWidget {
  const AuthChoiceScreen({
    super.key,
    required this.onPatientTap,
    required this.onDoctorTap,
  });

  final VoidCallback onPatientTap;
  final VoidCallback onDoctorTap;

  @override
  Widget build(BuildContext context) {
    // Pre-auth this always resolves to AppTheme.lightTheme (see main.dart),
    // which is correct here — the patient half of this screen is genuinely
    // blue-mode. The doctor card below intentionally breaks from theme
    // accent and uses AppColors.doctorPrimary directly, per spec Section 8
    // screen 1: this is the one screen allowed to show both accents at once.
    final accent = Theme.of(context).colorScheme.primary;

    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [Color(0xFF0D0E12), Color(0xFF12151B), Color(0xFF161A22)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: SafeArea(
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(AppSpacing.xl, 20, AppSpacing.xl, AppSpacing.xxl),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Centered brand mark (choose_role.html).
                Center(
                  child: Container(
                    width: 80,
                    height: 80,
                    decoration: BoxDecoration(
                      color: AppColors.glassPanel,
                      shape: BoxShape.circle,
                      border: Border.all(color: AppColors.frostEdge),
                    ),
                    child: Icon(Icons.health_and_safety, color: accent, size: 34),
                  ),
                ),
                const SizedBox(height: 48),
                Padding(
                  padding: const EdgeInsets.only(right: 48),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Initialize Profile', style: Theme.of(context).textTheme.displaySmall),
                      const SizedBox(height: 8),
                      Text(
                        'Select your operational environment to calibrate the interface.',
                        style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.grey500),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 36),
                _Reveal(
                  delayMs: 100,
                  child: AppCard(
                    onTap: onPatientTap,
                    child: _RoleCardContent(
                      icon: Icons.personal_injury_outlined,
                      title: 'Patient Access',
                      description: 'Monitor live vitals, review encrypted clinical data, and initiate telehealth modules.',
                      actionLabel: 'Select Protocol',
                      accent: accent,
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                _Reveal(
                  delayMs: 220,
                  child: AppCard(
                    onTap: onDoctorTap,
                    child: _RoleCardContent(
                      icon: Icons.medical_services_outlined,
                      title: 'Clinical Authority',
                      description: 'Manage patient telemetry, analyze longitudinal charts, and authorize protocols.',
                      actionLabel: 'Select Protocol',
                      accent: AppColors.doctorPrimary,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Staggered rise + fade reveal for the role cards, per spec Section 6.
class _Reveal extends StatelessWidget {
  const _Reveal({required this.child, required this.delayMs});

  final Widget child;
  final int delayMs;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: Duration(milliseconds: 380 + delayMs),
      curve: Curves.easeOutCubic,
      builder: (context, t, c) => Opacity(
        opacity: t,
        child: Transform.translate(offset: Offset(0, (1 - t) * 12), child: c),
      ),
      child: child,
    );
  }
}

class _RoleCardContent extends StatelessWidget {
  const _RoleCardContent({
    required this.icon,
    required this.title,
    required this.description,
    required this.actionLabel,
    required this.accent,
  });

  final IconData icon;
  final String title;
  final String description;
  final String actionLabel;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    // Vertical card layout per choose_role.html: icon tile on top, title,
    // description, then an uppercase accent footer with a forward arrow.
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [accent.withValues(alpha: 0.18), accent.withValues(alpha: 0.06)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: AppColors.frostEdge),
          ),
          child: Icon(icon, color: accent, size: 24),
        ),
        const SizedBox(height: 20),
        Text(title, style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 6),
        Text(
          description,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.grey500),
        ),
        const SizedBox(height: 20),
        Row(
          children: [
            Text(
              actionLabel.toUpperCase(),
              style: AppFonts.mono(
                Theme.of(context).textTheme.labelSmall!.copyWith(
                      color: accent,
                      letterSpacing: 1.6,
                    ),
              ),
            ),
            const SizedBox(width: 8),
            Icon(Icons.arrow_forward_rounded, size: 16, color: accent),
          ],
        ),
      ],
    );
  }
}
