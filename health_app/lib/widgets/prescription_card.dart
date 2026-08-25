import 'package:flutter/material.dart';

import '../models/models.dart';
import '../theme/app_theme.dart';
import 'common_widgets.dart';
import 'status_pill.dart';

const List<String> _kMonthAbbrev = [
  'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC',
];

String _formatMonoDate(DateTime date) {
  final local = date.toLocal();
  return '${_kMonthAbbrev[local.month - 1]} ${local.day.toString().padLeft(2, '0')}, ${local.year}';
}

/// Repeated inside prescription list screens, so blur is disabled per the
/// shared-component perf rule for densely-repeated cards.
class PrescriptionCard extends StatelessWidget {
  const PrescriptionCard({
    super.key,
    required this.prescription,
    this.onSupersede,
  });

  final Prescription prescription;
  final VoidCallback? onSupersede;

  (StatusPillTone, String) _statusMeta() {
    switch (prescription.status.toLowerCase()) {
      case 'active':
        return (StatusPillTone.success, 'ACTIVE');
      case 'superseded':
        return (StatusPillTone.neutral, 'SUPERSEDED');
      case 'completed':
        return (StatusPillTone.info, 'COMPLETED');
      default:
        return (StatusPillTone.neutral, prescription.status.toUpperCase());
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final primary = theme.colorScheme.primary;
    final (tone, label) = _statusMeta();
    final isSuperseded = prescription.status.toLowerCase() == 'superseded';

    return AppCard(
      enableBlur: false,
      child: Opacity(
        opacity: isSuperseded ? 0.7 : 1,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    prescription.doctorName != null ? 'From ${prescription.doctorName}' : 'Prescription',
                    style: theme.textTheme.titleSmall,
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    StatusPill(label: label, tone: tone),
                    const SizedBox(height: AppSpacing.xs),
                    Text(
                      _formatMonoDate(prescription.createdAt),
                      style: AppFonts.mono(
                        theme.textTheme.labelSmall!.copyWith(color: AppColors.grey500),
                      ),
                    ),
                  ],
                ),
              ],
            ),
            if (prescription.items.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.md),
              for (final item in prescription.items)
                Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Text(
                              item.medicationName,
                              style: theme.textTheme.titleSmall?.copyWith(color: primary),
                            ),
                          ),
                          const SizedBox(width: AppSpacing.sm),
                          Text(
                            [item.dosage, item.frequency, item.duration]
                                .where((part) => part != null && part.isNotEmpty)
                                .join(' • '),
                            style: AppFonts.mono(theme.textTheme.bodySmall!),
                          ),
                        ],
                      ),
                      if (item.instructions != null && item.instructions!.isNotEmpty) ...[
                        const SizedBox(height: AppSpacing.xs),
                        Text(
                          item.instructions!,
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: AppColors.grey500,
                            fontStyle: FontStyle.italic,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
            ],
            if (prescription.notes != null && prescription.notes!.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.xs),
              Text(
                prescription.notes!,
                style: theme.textTheme.bodyMedium?.copyWith(color: AppColors.grey500),
              ),
            ],
            if (prescription.followUpDate != null) ...[
              const SizedBox(height: AppSpacing.sm),
              Row(
                children: [
                  const Icon(Icons.event_outlined, size: 14, color: AppColors.grey500),
                  const SizedBox(width: AppSpacing.xs),
                  Text(
                    'Follow up by ${_formatMonoDate(prescription.followUpDate!)}',
                    style: AppFonts.mono(
                      theme.textTheme.bodySmall!.copyWith(color: AppColors.grey500),
                    ),
                  ),
                ],
              ),
            ],
            if (onSupersede != null && prescription.isActive) ...[
              const SizedBox(height: AppSpacing.md),
              SecondaryButton(label: 'Supersede with correction', onPressed: onSupersede!),
            ],
          ],
        ),
      ),
    );
  }
}
