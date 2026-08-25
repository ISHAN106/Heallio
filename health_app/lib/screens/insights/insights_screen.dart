import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common_widgets.dart';
import '../../providers/app_providers.dart';

String _statusLabel(String status) {
  switch (status) {
    case 'poor':
      return 'ALERT';
    case 'average':
      return 'REVIEW';
    case 'good':
      return 'GOOD';
    default:
      return status.toUpperCase();
  }
}

/// Splits the backend's recommendation text into standalone bullets rather
/// than inventing separate fake tips per card — it's often 1-2 sentences
/// (e.g. "Your routine needs attention. Focus on sleep regularity and
/// nutrition."), which reads naturally as a short bulleted list.
List<String> _asSteps(String recommendation) {
  return recommendation
      .split(RegExp(r'(?<=[.!?])\s+'))
      .map((s) => s.trim())
      .where((s) => s.isNotEmpty)
      .toList();
}

class InsightsScreen extends ConsumerWidget {
  const InsightsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final insightsAsync = ref.watch(insightsProvider);
    final primary = Theme.of(context).colorScheme.primary;

    return Scaffold(
      appBar: const CustomAppBar(title: 'Insights'),
      body: insightsAsync.when(
        data: (insights) {
          if (insights.isEmpty) {
            return EmptyState(
              title: 'No insights yet',
              message: 'Keep tracking your health to get personalized insights',
              icon: Icons.lightbulb_outline,
            );
          }

          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.lg,
              AppSpacing.lg,
              AppSpacing.lg,
              AppSpacing.navClearance,
            ),
            itemCount: insights.length,
            separatorBuilder: (_, _) => const SizedBox(height: AppSpacing.lg),
            itemBuilder: (context, index) {
              final insight = insights[index];
              return ClipRRect(
                borderRadius: BorderRadius.circular(24),
                child: Stack(
                  children: [
                    AppCard(
                      enableBlur: false,
                      padding: const EdgeInsets.fromLTRB(24, 20, 20, 20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Container(
                                width: 40,
                                height: 40,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: primary.withValues(alpha: 0.1),
                                ),
                                child: Icon(
                                  _getIconForCategory(insight.category),
                                  color: primary,
                                  size: 20,
                                ),
                              ),
                              const SizedBox(width: AppSpacing.md),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      insight.title,
                                      style: Theme.of(context).textTheme.headlineSmall,
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      insight.category.toUpperCase(),
                                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                            color: AppColors.grey500,
                                            letterSpacing: 1.0,
                                          ),
                                    ),
                                  ],
                                ),
                              ),
                              if (insight.status != null)
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: AppColors.glassWell,
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: Text(
                                    _statusLabel(insight.status!),
                                    style: AppFonts.mono(
                                      Theme.of(context).textTheme.labelSmall!.copyWith(color: primary),
                                    ),
                                  ),
                                ),
                            ],
                          ),
                          const SizedBox(height: AppSpacing.lg),
                          Text(
                            insight.description,
                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                  color: AppColors.grey600,
                                ),
                          ),
                          if (insight.recommendation != null && insight.recommendation!.trim().isNotEmpty) ...[
                            const SizedBox(height: AppSpacing.lg),
                            Container(
                              padding: const EdgeInsets.all(AppSpacing.md),
                              decoration: BoxDecoration(
                                color: Colors.black.withValues(alpha: 0.18),
                                borderRadius: BorderRadius.circular(14),
                                border: Border.all(color: AppColors.frostEdge),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Icon(Icons.bolt, color: primary, size: 16),
                                      const SizedBox(width: AppSpacing.xs),
                                      Text(
                                        'ACTIONABLE STEPS',
                                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                              color: primary,
                                              letterSpacing: 1.0,
                                            ),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: AppSpacing.sm),
                                  for (final step in _asSteps(insight.recommendation!))
                                    Padding(
                                      padding: const EdgeInsets.only(top: 4),
                                      child: Row(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Padding(
                                            padding: const EdgeInsets.only(top: 7),
                                            child: Container(
                                              width: 5,
                                              height: 5,
                                              decoration: BoxDecoration(color: primary, shape: BoxShape.circle),
                                            ),
                                          ),
                                          const SizedBox(width: AppSpacing.sm),
                                          Expanded(
                                            child: Text(
                                              step,
                                              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                                    color: AppColors.grey700,
                                                  ),
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                ],
                              ),
                            ),
                          ],
                          const SizedBox(height: AppSpacing.md),
                          Text(
                            'Generated ${_formatDate(insight.generatedAt)}',
                            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                  color: AppColors.grey500,
                                ),
                          ),
                        ],
                      ),
                    ),
                    // Category accent edge - same theme accent for every
                    // card (max one accent per screen), never per-category
                    // colors.
                    Positioned(
                      left: 0,
                      top: 0,
                      bottom: 0,
                      child: Container(width: 3, color: primary),
                    ),
                  ],
                ),
              );
            },
          );
        },
        loading: () => const LoadingState(message: 'Loading insights...'),
        error: (error, _) => ErrorState(
          message: error.toString(),
          onRetry: () => ref.refresh(insightsProvider),
        ),
      ),
    );
  }

  IconData _getIconForCategory(String category) {
    switch (category.toLowerCase()) {
      case 'health':
        return Icons.favorite;
      case 'diet':
        return Icons.restaurant_menu;
      case 'sleep':
        return Icons.bedtime;
      case 'exercise':
        return Icons.directions_run;
      default:
        return Icons.lightbulb;
    }
  }

  String _formatDate(DateTime date) {
    final now = DateTime.now();
    final difference = now.difference(date);

    if (difference.inDays == 0) {
      if (difference.inHours == 0) {
        return '${difference.inMinutes} minutes ago';
      }
      return '${difference.inHours} hours ago';
    } else if (difference.inDays == 1) {
      return 'Yesterday';
    } else {
      return '${difference.inDays} days ago';
    }
  }
}
