import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/models.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common_widgets.dart';
import '../../providers/app_providers.dart';
import '../../widgets/section_header.dart';
import '../../widgets/metric_ring.dart';
import '../../widgets/status_pill.dart';

class HomeScreen extends ConsumerWidget {
  final VoidCallback onNavigateChat;
  final ValueChanged<String> onNavigateChatWithPrompt;
  final VoidCallback onNavigateHealth;
  final VoidCallback onNavigateInsights;
  final VoidCallback onNavigateProfile;

  const HomeScreen({
    super.key,
    required this.onNavigateChat,
    required this.onNavigateChatWithPrompt,
    required this.onNavigateHealth,
    required this.onNavigateInsights,
    required this.onNavigateProfile,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final userAsync = ref.watch(userProvider);
    final recentHealthAsync = ref.watch(recentHealthProvider);
    final recentSleepAsync = ref.watch(recentSleepProvider);
    final recentDietAsync = ref.watch(recentDietProvider);
    final insightsAsync = ref.watch(insightsProvider);
    final availableDoctorsAsync = ref.watch(availableDoctorsProvider(null));

    final healthReview = _buildHealthReview(
      health: recentHealthAsync.maybeWhen(data: (data) => data, orElse: () => <HealthData>[]),
      sleep: recentSleepAsync.maybeWhen(data: (data) => data, orElse: () => <SleepData>[]),
      diet: recentDietAsync.maybeWhen(data: (data) => data, orElse: () => <DietData>[]),
    );

    final displayName = authState.user?.username ??
        userAsync.maybeWhen(data: (user) => user.username, orElse: () => null);

    final theme = Theme.of(context);
    final primary = theme.colorScheme.primary;

    // Real vitals for the Telemetry grid (no fabricated values).
    final health = recentHealthAsync.maybeWhen(data: (d) => d, orElse: () => <HealthData>[]);
    final sleep = recentSleepAsync.maybeWhen(data: (d) => d, orElse: () => <SleepData>[]);
    final diet = recentDietAsync.maybeWhen(data: (d) => d, orElse: () => <DietData>[]);
    final hr = health.isNotEmpty ? health.first.heartRate : null;
    final steps = health.isNotEmpty ? health.first.steps : null;
    final sleepHours = sleep.isNotEmpty ? sleep.first.duration.inMinutes / 60.0 : null;
    final score10 = (10 - healthReview.reasons.length).clamp(0, 10);
    final score100 = score10 * 10;

    return Scaffold(
      appBar: CustomAppBar(
        title: 'Home',
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: AppSpacing.lg),
            child: GestureDetector(
              onTap: onNavigateProfile,
              child: Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(color: primary, shape: BoxShape.circle),
                child: Icon(Icons.person, color: AppColors.onPrimary, size: 18),
              ),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.lg,
          AppSpacing.xl,
          AppSpacing.lg,
          AppSpacing.navClearance,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Greeting hero — asymmetric text block (home.html), name in accent.
            Padding(
              padding: const EdgeInsets.only(right: 48),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${_greeting()},', style: theme.textTheme.headlineMedium),
                  Text(
                    displayName != null ? '$displayName.' : 'there.',
                    style: theme.textTheme.displaySmall?.copyWith(color: primary),
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    healthReview.statusSubtitle,
                    style: theme.textTheme.bodyLarge?.copyWith(color: AppColors.grey500),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.xl),

            // Health score card — value block left, progress ring right.
            AppCard(
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'HEALTH SCORE',
                          style: theme.textTheme.labelSmall?.copyWith(
                                color: AppColors.grey400,
                                letterSpacing: 1.2,
                              ),
                        ),
                        const SizedBox(height: AppSpacing.sm),
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.baseline,
                          textBaseline: TextBaseline.alphabetic,
                          children: [
                            Text('$score100', style: AppFonts.mono(theme.textTheme.displayLarge!)),
                            const SizedBox(width: 4),
                            Text('/100', style: AppFonts.mono(theme.textTheme.titleMedium!.copyWith(color: primary))),
                          ],
                        ),
                        const SizedBox(height: AppSpacing.sm),
                        StatusPill(label: healthReview.pillLabel, tone: healthReview.tone),
                      ],
                    ),
                  ),
                  const SizedBox(width: AppSpacing.lg),
                  Stack(
                    alignment: Alignment.center,
                    children: [
                      MetricRing(
                        value: score100.toDouble(),
                        maxValue: 100,
                        centerLabel: '',
                        size: 84,
                      ),
                      Icon(Icons.monitor_heart, color: primary, size: 26),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.xxl),

            // Telemetry — 2x2 real-vitals grid (home.html), mono instrument values.
            SectionHeader(
              title: 'Telemetry',
              actionLabel: 'Live View',
              onActionTap: onNavigateHealth,
            ),
            const SizedBox(height: AppSpacing.md),
            Row(
              children: [
                Expanded(
                  child: _TelemetryCard(
                    icon: Icons.favorite,
                    iconColor: AppColors.errorFg,
                    unit: 'BPM',
                    value: hr != null ? '${hr.toInt()}' : '--',
                    caption: hr != null ? 'Latest reading' : 'No reading yet',
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: _TelemetryCard(
                    icon: Icons.bedtime,
                    iconColor: primary,
                    unit: 'HRS',
                    value: sleepHours != null ? sleepHours.toStringAsFixed(1) : '--',
                    caption: sleepHours != null ? 'Last night' : 'Not logged',
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            Row(
              children: [
                Expanded(
                  child: _TelemetryCard(
                    icon: Icons.directions_walk,
                    iconColor: AppColors.successFg,
                    unit: 'STP',
                    value: steps != null ? '$steps' : '--',
                    caption: 'Goal 10,000',
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: _TelemetryCard(
                    icon: Icons.restaurant_menu,
                    iconColor: AppColors.warningFg,
                    unit: 'MEAL',
                    value: '${diet.length}',
                    caption: 'Logged this week',
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.xxl),

            // AI insight teaser card.
            AppCard(
              onTap: onNavigateInsights,
              raised: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.psychology_outlined, color: primary, size: 20),
                      const SizedBox(width: AppSpacing.sm),
                      Text(
                        'AI ANALYSIS',
                        style: theme.textTheme.labelSmall?.copyWith(
                              color: primary,
                              letterSpacing: 1.2,
                            ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.md),
                  Text(
                    insightsAsync.maybeWhen(
                      data: (insights) => insights.isNotEmpty
                          ? (insights.first.recommendation?.isNotEmpty == true
                              ? insights.first.recommendation!
                              : insights.first.description)
                          : 'Keep logging health, sleep, and meals to unlock personalized analysis.',
                      orElse: () => 'Get personalized health recommendations based on your data.',
                    ),
                    style: theme.textTheme.bodyLarge?.copyWith(color: AppColors.grey700),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      Text(
                        'Read full analysis',
                        style: theme.textTheme.labelLarge?.copyWith(color: primary),
                      ),
                      const SizedBox(width: AppSpacing.xs),
                      Icon(Icons.arrow_forward, size: 16, color: primary),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.xxl),

            // Available-doctor card (home.html): real available doctor, not
            // a fabricated name/photo — falls back to nothing if none online.
            availableDoctorsAsync.maybeWhen(
              data: (doctors) {
                if (doctors.isEmpty) return const SizedBox.shrink();
                final doctor = doctors.first;
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    AppCard(
                      enableBlur: false,
                      padding: const EdgeInsets.all(AppSpacing.sm),
                      child: Row(
                        children: [
                          Container(
                            width: 56,
                            height: 56,
                            decoration: BoxDecoration(
                              color: primary.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(16),
                            ),
                            child: Icon(Icons.medical_services, color: primary, size: 26),
                          ),
                          const SizedBox(width: AppSpacing.md),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'AVAILABLE NOW',
                                  style: theme.textTheme.labelSmall?.copyWith(
                                        color: AppColors.grey400,
                                        letterSpacing: 1.0,
                                      ),
                                ),
                                Text(doctor.doctorName, style: AppFonts.mono(theme.textTheme.titleMedium!)),
                                Text(
                                  '${doctor.categoryName} Specialist',
                                  style: theme.textTheme.bodySmall?.copyWith(color: AppColors.grey500),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ],
                            ),
                          ),
                          SizedBox(
                            width: 128,
                            child: PrimaryButton(
                              label: 'Consult',
                              onPressed: () => onNavigateChatWithPrompt(
                                'I would like to consult with ${doctor.doctorName} (${doctor.categoryName}).',
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: AppSpacing.xxl),
                  ],
                );
              },
              orElse: () => const SizedBox.shrink(),
            ),

            // Consult-suggestion card.
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(AppSpacing.sm),
                        decoration: BoxDecoration(
                          color: healthReview.tintBg,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Icon(
                          Icons.medical_services_outlined,
                          color: healthReview.tintFg,
                          size: 20,
                        ),
                      ),
                      const SizedBox(width: AppSpacing.md),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Health consult review', style: theme.textTheme.titleMedium),
                            const SizedBox(height: 2),
                            Text(
                              healthReview.statusLabel,
                              style: theme.textTheme.labelSmall?.copyWith(
                                    color: healthReview.tintFg,
                                    fontWeight: FontWeight.w600,
                                  ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.md),
                  Text(
                    healthReview.summary,
                    style: theme.textTheme.bodyMedium?.copyWith(color: AppColors.grey700),
                  ),
                  if (healthReview.reasons.isNotEmpty) ...[
                    const SizedBox(height: AppSpacing.md),
                    Wrap(
                      spacing: AppSpacing.sm,
                      runSpacing: AppSpacing.sm,
                      children: healthReview.reasons
                          .map((reason) => StatusPill(label: reason, tone: StatusPillTone.warning))
                          .toList(),
                    ),
                  ],
                  const SizedBox(height: AppSpacing.lg),
                  Row(
                    children: [
                      Expanded(
                        child: SecondaryButton(
                          label: 'Ask AI',
                          icon: Icons.smart_toy_outlined,
                          onPressed: () => onNavigateChatWithPrompt(healthReview.aiPrompt),
                        ),
                      ),
                      const SizedBox(width: AppSpacing.md),
                      Expanded(
                        child: PrimaryButton(
                          label: 'Consult doctor',
                          onPressed: () => onNavigateChatWithPrompt(healthReview.doctorPrompt),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    'Based on your recent calories, sleep, steps, and logged nutrients.',
                    style: theme.textTheme.labelSmall?.copyWith(color: AppColors.grey500),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _greeting() {
    final hour = DateTime.now().hour;
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  }
}

/// Telemetry vitals tile (home.html): icon circle top-left, unit chip
/// top-right, big mono value, caption. Blur disabled — it repeats in a grid.
class _TelemetryCard extends StatelessWidget {
  const _TelemetryCard({
    required this.icon,
    required this.iconColor,
    required this.unit,
    required this.value,
    required this.caption,
  });

  final IconData icon;
  final Color iconColor;
  final String unit;
  final String value;
  final String caption;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return AppCard(
      enableBlur: false,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(color: iconColor.withValues(alpha: 0.18), shape: BoxShape.circle),
                child: Icon(icon, color: iconColor, size: 18),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppColors.glassWell,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  unit,
                  style: AppFonts.mono(theme.textTheme.labelSmall!.copyWith(color: AppColors.grey400)),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),
          Text(value, style: AppFonts.mono(theme.textTheme.displaySmall!)),
          const SizedBox(height: 4),
          Text(caption, style: theme.textTheme.labelSmall?.copyWith(color: AppColors.grey500)),
        ],
      ),
    );
  }
}

class _HealthReview {
  const _HealthReview({
    required this.summary,
    required this.statusLabel,
    required this.pillLabel,
    required this.tone,
    required this.aiPrompt,
    required this.doctorPrompt,
    required this.reasons,
  });

  final String summary;
  final String statusLabel;
  final String pillLabel;
  final StatusPillTone tone;
  final String aiPrompt;
  final String doctorPrompt;
  final List<String> reasons;

  /// Greeting-hero subtitle (home.html's dynamic clinical-status line),
  /// derived from the same real review used everywhere else on this screen.
  String get statusSubtitle {
    switch (tone) {
      case StatusPillTone.success:
        return 'System normalized. All vitals are tracking within optimal ranges.';
      case StatusPillTone.warning:
        return 'A few recent metrics need attention — see the review below.';
      case StatusPillTone.error:
        return 'Recent metrics suggest it may be worth talking to a doctor.';
      case StatusPillTone.info:
      case StatusPillTone.neutral:
        return 'Keep tracking your daily health metrics.';
    }
  }

  Color get tintFg {
    switch (tone) {
      case StatusPillTone.error:
        return AppColors.errorFg;
      case StatusPillTone.warning:
        return AppColors.warningFg;
      case StatusPillTone.success:
        return AppColors.successFg;
      case StatusPillTone.info:
        return AppColors.infoFg;
      case StatusPillTone.neutral:
        return AppColors.grey700;
    }
  }

  Color get tintBg {
    switch (tone) {
      case StatusPillTone.error:
        return AppColors.errorBg;
      case StatusPillTone.warning:
        return AppColors.warningBg;
      case StatusPillTone.success:
        return AppColors.successBg;
      case StatusPillTone.info:
        return AppColors.infoBg;
      case StatusPillTone.neutral:
        return AppColors.grey100;
    }
  }
}

_HealthReview _buildHealthReview({
  required List<HealthData> health,
  required List<SleepData> sleep,
  required List<DietData> diet,
}) {
  final reasons = <String>[];
  var score = 0;

  double? averageCalories;
  if (diet.isNotEmpty) {
    final calorieValues = diet.where((entry) => entry.calories != null).map((entry) => entry.calories!.toDouble()).toList();
    if (calorieValues.isNotEmpty) {
      averageCalories = calorieValues.reduce((a, b) => a + b) / calorieValues.length;
      if (averageCalories < 1200) {
        score += 2;
        reasons.add('Calories low');
      } else if (averageCalories > 2800) {
        score += 2;
        reasons.add('Calories high');
      } else if (averageCalories < 1600 || averageCalories > 2400) {
        score += 1;
        reasons.add('Calories uneven');
      }
    }
  }

  double? averageSleepHours;
  if (sleep.isNotEmpty) {
    averageSleepHours = sleep.map((entry) => entry.duration.inMinutes / 60.0).reduce((a, b) => a + b) / sleep.length;
    final poorSleepQuality = sleep.where((entry) => entry.quality.toLowerCase() == 'poor' || entry.quality.toLowerCase() == 'fair').length;
    if (averageSleepHours < 6) {
      score += 2;
      reasons.add('Sleep low');
    } else if (averageSleepHours < 7) {
      score += 1;
      reasons.add('Sleep short');
    }
    if (poorSleepQuality > 0) {
      score += 1;
      reasons.add('Sleep quality');
    }
  }

  final stepsValues = health.where((entry) => entry.steps != null).map((entry) => entry.steps!.toDouble()).toList();
  if (stepsValues.isNotEmpty) {
    final averageSteps = stepsValues.reduce((a, b) => a + b) / stepsValues.length;
    if (averageSteps < 3000) {
      score += 1;
      reasons.add('Low steps');
    }
  }

  final heartRateValues = health.where((entry) => entry.heartRate != null).map((entry) => entry.heartRate!).toList();
  if (heartRateValues.isNotEmpty) {
    final averageHeartRate = heartRateValues.reduce((a, b) => a + b) / heartRateValues.length;
    if (averageHeartRate > 100) {
      score += 2;
      reasons.add('High heart rate');
    } else if (averageHeartRate > 90) {
      score += 1;
      reasons.add('Heart rate');
    }
  }

  final nutrientSignals = diet
      .expand((entry) => entry.nutrients ?? const <String>[])
      .map((item) => item.toLowerCase())
      .toSet();
  if (nutrientSignals.isNotEmpty && nutrientSignals.length < 3) {
    score += 1;
    reasons.add('Few nutrients logged');
  }

  final hasData = health.isNotEmpty || sleep.isNotEmpty || diet.isNotEmpty;
  final statusLabel = score >= 5
      ? 'Consider a doctor consultation'
      : score >= 2
          ? 'Review with AI first'
          : hasData
              ? 'Healthy baseline'
              : 'Start tracking to get a review';

  final tone = score >= 5
      ? StatusPillTone.error
      : score >= 2
          ? StatusPillTone.warning
          : hasData
              ? StatusPillTone.success
              : StatusPillTone.info;

  final pillLabel = score >= 5
      ? 'Needs attention'
      : score >= 2
          ? 'Worth a review'
          : hasData
              ? 'On track'
              : 'No data yet';

  final summary = !hasData
      ? 'Track meals, sleep, and daily activity to get a consult recommendation that can guide you toward AI advice or a doctor visit.'
      : score >= 5
          ? 'Your recent pattern suggests it may be worth talking to a doctor, especially before the issue grows.'
          : score >= 2
              ? 'Your recent pattern has a few flags. Start with the AI review, and escalate to a doctor if the symptoms persist.'
              : 'Your recent food, sleep, and activity logs look reasonably balanced. Keep tracking and use AI for routine questions.';

  final insightDetails = [
    if (averageCalories != null) 'Average calories: ${averageCalories.toStringAsFixed(0)}',
    if (averageSleepHours != null) 'Average sleep: ${averageSleepHours.toStringAsFixed(1)} h',
    if (stepsValues.isNotEmpty) 'Recent step logs: ${stepsValues.length}',
  ].join(' | ');

  final aiPrompt = [
    'Review my recent health logs and tell me if I should change my diet, sleep, or activity habits.',
    if (insightDetails.isNotEmpty) insightDetails,
  ].join(' ');

  final doctorPrompt = [
    'I want a doctor consultation.',
    if (insightDetails.isNotEmpty) 'Recent review: $insightDetails.',
    if (reasons.isNotEmpty) 'Concerns: ${reasons.join(', ')}.',
    'Please help me decide whether I should book a doctor visit.',
  ].join(' ');

  return _HealthReview(
    summary: summary,
    statusLabel: statusLabel,
    pillLabel: pillLabel,
    tone: tone,
    aiPrompt: aiPrompt,
    doctorPrompt: doctorPrompt,
    reasons: reasons,
  );
}

