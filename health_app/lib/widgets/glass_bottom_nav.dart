import 'dart:ui';

import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class GlassNavItem {
  final IconData icon;
  final IconData activeIcon;
  final String label;

  const GlassNavItem({
    required this.icon,
    required this.activeIcon,
    required this.label,
  });
}

/// Floating glass dock — detached from the screen edge, 28px radius, active
/// tab in the current theme's accent with a soft underglow dot. Used by both
/// the patient shell (Signal Blue, via [AppTheme.lightTheme]) and the doctor
/// shell (Clinical Gold, via [AppTheme.doctorTheme]) — the accent always
/// comes from `Theme.of(context).colorScheme.primary`, never hardcoded, so
/// this one widget can never leak the wrong mode's color.
class GlassBottomNav extends StatelessWidget {
  final List<GlassNavItem> items;
  final int currentIndex;
  final ValueChanged<int> onTap;

  const GlassBottomNav({
    super.key,
    required this.items,
    required this.currentIndex,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final accent = Theme.of(context).colorScheme.primary;

    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, AppSpacing.md),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(28),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
            child: Stack(
              children: [
                Container(
                  height: 72,
                  decoration: BoxDecoration(
                    color: AppColors.glassPanel,
                    borderRadius: BorderRadius.circular(28),
                    // Uniform border — see AppCard's doc comment in
                    // common_widgets.dart for why a per-side color can't be
                    // combined with borderRadius.
                    border: Border.all(color: AppColors.frostEdge, width: 1),
                    boxShadow: AppShadows.raised,
                  ),
                  child: Row(
                    children: [
                      for (var i = 0; i < items.length; i++)
                        Expanded(
                          child: _GlassNavTab(
                            item: items[i],
                            selected: i == currentIndex,
                            accent: accent,
                            onTap: () => onTap(i),
                          ),
                        ),
                    ],
                  ),
                ),
                Positioned(
                  top: 1,
                  left: 24,
                  right: 24,
                  child: IgnorePointer(
                    child: Container(
                      height: 1,
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [
                            AppColors.frostEdgeTop.withValues(alpha: 0),
                            AppColors.frostEdgeTop,
                            AppColors.frostEdgeTop.withValues(alpha: 0),
                          ],
                        ),
                      ),
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

class _GlassNavTab extends StatelessWidget {
  final GlassNavItem item;
  final bool selected;
  final Color accent;
  final VoidCallback onTap;

  const _GlassNavTab({
    required this.item,
    required this.selected,
    required this.accent,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(28),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              selected ? item.activeIcon : item.icon,
              color: selected ? accent : AppColors.grey400,
              size: 22,
            ),
            const SizedBox(height: 4),
            Text(
              item.label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: selected ? accent : AppColors.grey400,
                    fontWeight: selected ? FontWeight.w700 : FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 4),
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: selected ? 4 : 0,
              height: 4,
              decoration: BoxDecoration(
                color: accent,
                borderRadius: BorderRadius.circular(2),
                boxShadow: selected
                    ? [
                        BoxShadow(
                          color: accent.withValues(alpha: 0.65),
                          blurRadius: 6,
                          spreadRadius: 1,
                        ),
                      ]
                    : null,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
