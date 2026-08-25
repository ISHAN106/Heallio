import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/app_providers.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common_widgets.dart';
import 'login_screen.dart';
import 'signup_screen.dart';

class PatientAuthScreen extends ConsumerStatefulWidget {
  const PatientAuthScreen({
    super.key,
    required this.onBackToIntroTap,
  });

  final VoidCallback onBackToIntroTap;

  @override
  ConsumerState<PatientAuthScreen> createState() => _PatientAuthScreenState();
}

class _PatientAuthScreenState extends ConsumerState<PatientAuthScreen> {
  bool _isLoginMode = true;

  @override
  Widget build(BuildContext context) {
    // Patient flow — ambient pre-auth theme (AppTheme.lightTheme) is correct
    // here, so Theme.of(context).colorScheme.primary is the right accent.
    final accent = Theme.of(context).colorScheme.primary;

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.md, AppSpacing.lg, 0),
              child: Row(
                children: [
                  TextButton.icon(
                    onPressed: widget.onBackToIntroTap,
                    icon: const Icon(Icons.arrow_back),
                    label: const Text('Back to choices'),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
              child: AppCard(
                padding: const EdgeInsets.all(AppSpacing.lg),
                enableBlur: false,
                child: Row(
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: accent.withValues(alpha: 0.14),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Icon(Icons.favorite, color: accent),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Patient Portal',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Sign in to track your health and access your care tools.',
                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                  color: AppColors.grey500,
                                ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Expanded(
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 350),
                switchInCurve: Curves.easeOutCubic,
                switchOutCurve: Curves.easeInCubic,
                transitionBuilder: (child, animation) {
                  final curvedAnimation = CurvedAnimation(
                    parent: animation,
                    curve: Curves.easeOut,
                  );
                  return FadeTransition(
                    opacity: curvedAnimation,
                    child: SlideTransition(
                      position: Tween<Offset>(
                        begin: const Offset(0.06, 0),
                        end: Offset.zero,
                      ).animate(curvedAnimation),
                      child: child,
                    ),
                  );
                },
                child: _isLoginMode
                    ? LoginScreen(
                        key: const ValueKey('patient-login'),
                        onLoginSuccess: () {},
                        onSignupTap: () {
                          ref.read(authProvider.notifier).clearError();
                          setState(() => _isLoginMode = false);
                        },
                      )
                    : SignupScreen(
                        key: const ValueKey('patient-signup'),
                        onSignupSuccess: () {},
                        onLoginTap: () {
                          ref.read(authProvider.notifier).clearError();
                          setState(() => _isLoginMode = true);
                        },
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
