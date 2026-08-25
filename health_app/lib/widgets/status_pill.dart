import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

enum StatusPillTone { success, warning, error, info, neutral }

class SeverityMeta {
  const SeverityMeta(this.bg, this.fg, this.icon);

  final Color bg;
  final Color fg;
  final IconData icon;
}

/// Shared severity -> (bg, fg, icon) mapping for consultation ticket severity
/// levels ("critical" | "high" | "medium" | anything else, treated as low).
/// Keep this the single source of truth — the doctor queue and the patient
/// consultation screen must always render the same severity in the same color.
SeverityMeta severityMeta(String severityLevel) {
  switch (severityLevel.toLowerCase()) {
    case 'critical':
      return const SeverityMeta(AppColors.errorBg, AppColors.errorFg, Icons.warning_amber_outlined);
    case 'high':
      return const SeverityMeta(AppColors.warningBg, AppColors.warningFg, Icons.warning_amber_outlined);
    case 'medium':
      return const SeverityMeta(AppColors.infoBg, AppColors.infoFg, Icons.info_outline);
    default:
      return const SeverityMeta(AppColors.successBg, AppColors.successFg, Icons.check_circle_outline);
  }
}

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
            style: AppFonts.mono(
              Theme.of(context).textTheme.labelSmall!.copyWith(color: fg, fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
    );
  }
}
