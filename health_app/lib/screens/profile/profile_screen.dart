import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common_widgets.dart';
import '../../widgets/status_pill.dart';
import '../../providers/app_providers.dart';
import '../consultation/prescriptions_screen.dart';
import 'connected_sessions_screen.dart';

class ProfileScreen extends ConsumerWidget {
  final VoidCallback onLogout;

  const ProfileScreen({
    super.key,
    required this.onLogout,
  });

  void _showComingSoon(BuildContext context, String feature) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('$feature is coming soon.')),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final userAsync = ref.watch(userProvider);
    final sessionsAsync = ref.watch(connectedSessionsProvider);
    final isDoctor = authState.user?.role == 'doctor';
    final theme = Theme.of(context);
    final primary = theme.colorScheme.primary;

    return Scaffold(
      appBar: const CustomAppBar(title: 'Profile'),
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
            // Glass avatar header.
            (authState.user != null
                    ? AsyncValue.data(authState.user!)
                    : userAsync)
                .when(
              data: (user) {
                return AppCard(
                  raised: true,
                  child: Row(
                    children: [
                      Stack(
                        clipBehavior: Clip.none,
                        children: [
                          Container(
                            width: 72,
                            height: 72,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              gradient: LinearGradient(
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                                colors: [
                                  primary.withValues(alpha: 0.24),
                                  primary.withValues(alpha: 0.06),
                                ],
                              ),
                              border: Border.all(color: AppColors.frostEdgeTop),
                            ),
                            child: Icon(Icons.person, size: 36, color: primary),
                          ),
                          Positioned(
                            right: 2,
                            bottom: 2,
                            child: Container(
                              width: 14,
                              height: 14,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: primary,
                                border: Border.all(color: AppColors.grey50, width: 2),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(width: AppSpacing.lg),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(user.username, style: theme.textTheme.headlineSmall),
                            const SizedBox(height: 2),
                            Text(
                              user.email,
                              style: theme.textTheme.bodySmall?.copyWith(color: AppColors.grey500),
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: AppSpacing.sm),
                            Row(
                              children: [
                                StatusPill(
                                  label: user.emailVerified ? 'Verified' : 'Pending Verification',
                                  tone: user.emailVerified ? StatusPillTone.success : StatusPillTone.warning,
                                  icon: user.emailVerified ? Icons.check_circle_outline : Icons.hourglass_empty,
                                ),
                                const SizedBox(width: AppSpacing.sm),
                                StatusPill(label: user.role.toUpperCase(), tone: StatusPillTone.neutral),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              },
              loading: () => const LoadingState(message: 'Loading profile...'),
              error: (error, _) => ErrorState(
                message: error.toString(),
                onRetry: () => ref.refresh(userProvider),
              ),
            ),
            const SizedBox(height: AppSpacing.xxl),

            // Account section
            Text('Account', style: theme.textTheme.titleLarge),
            const SizedBox(height: AppSpacing.md),
            _SettingsTile(
              title: 'Edit Profile',
              subtitle: 'Update your personal information',
              icon: Icons.person_outline,
              onTap: () => _showComingSoon(context, 'Editing your profile'),
            ),
            _SettingsTile(
              title: 'Change Password',
              subtitle: 'Update your password',
              icon: Icons.lock_outline,
              onTap: () => _showComingSoon(context, 'Changing your password'),
            ),
            if (!isDoctor)
              _SettingsTile(
                title: 'My Prescriptions',
                subtitle: 'View medications and care plans from your consults',
                icon: Icons.medication_outlined,
                onTap: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const PrescriptionsScreen()),
                  );
                },
              ),

            const SizedBox(height: AppSpacing.xxl),

            // Security section (profile.html)
            Text('Security', style: theme.textTheme.titleLarge),
            const SizedBox(height: AppSpacing.md),
            _SettingsTile(
              title: 'Privacy & Permissions',
              subtitle: 'Data access controls',
              icon: Icons.security,
              onTap: () => _showComingSoon(context, 'Privacy & Security settings'),
            ),
            _SettingsTile(
              title: 'Connected Hardware',
              subtitle: sessionsAsync.when(
                data: (sessions) =>
                    '${sessions.length} active session${sessions.length == 1 ? '' : 's'}',
                loading: () => 'Loading...',
                error: (_, _) => 'Tap to view',
              ),
              icon: Icons.devices_other_outlined,
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const ConnectedSessionsScreen()),
                );
              },
            ),

            const SizedBox(height: AppSpacing.xxl),

            // Preferences section
            Text('Preferences', style: theme.textTheme.titleLarge),
            const SizedBox(height: AppSpacing.md),
            _SettingsTile(
              title: 'Notifications',
              subtitle: 'Enable/disable notifications',
              icon: Icons.notifications_outlined,
              onTap: () => _showComingSoon(context, 'Notification preferences'),
            ),
            _SettingsTile(
              title: 'Data Sync',
              subtitle: 'Sync your health data',
              icon: Icons.cloud_sync,
              onTap: () => _showComingSoon(context, 'Data sync'),
            ),
            _SettingsTile(
              title: 'Theme',
              subtitle: 'Light / Dark mode',
              icon: Icons.brightness_6,
              onTap: () => _showComingSoon(context, 'Theme switching'),
            ),

            const SizedBox(height: AppSpacing.xxl),

            // Support section
            Text('Support', style: theme.textTheme.titleLarge),
            const SizedBox(height: AppSpacing.md),
            _SettingsTile(
              title: 'About',
              subtitle: 'App version and information',
              icon: Icons.info_outline,
              onTap: () => _showComingSoon(context, 'The about screen'),
            ),
            _SettingsTile(
              title: 'Help & Support',
              subtitle: 'Get help and contact us',
              icon: Icons.help_outline,
              onTap: () => _showComingSoon(context, 'Help & support'),
            ),

            const SizedBox(height: AppSpacing.xxl),

            // Destructive sign-out row - Alert Red glass tint (mirrors the
            // ErrorState pattern rather than the neutral AppCard fill, since
            // this is the one row on the screen that must read as dangerous).
            ClipRRect(
              borderRadius: BorderRadius.circular(20),
              child: Material(
                color: AppColors.errorBg,
                child: InkWell(
                  onTap: () => _showLogoutDialog(context, ref, onLogout),
                  child: Container(
                    padding: const EdgeInsets.all(AppSpacing.md),
                    decoration: BoxDecoration(
                      border: Border.all(color: AppColors.error.withValues(alpha: 0.3)),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.logout, color: AppColors.errorFg, size: 20),
                        const SizedBox(width: AppSpacing.sm),
                        Text(
                          'Terminate Session',
                          style: theme.textTheme.titleSmall?.copyWith(color: AppColors.errorFg),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showLogoutDialog(
      BuildContext context, WidgetRef ref, VoidCallback onLogout) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.surfaceRaised,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('Terminate Session'),
        content: const Text('Are you sure you want to sign out?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              ref.read(authProvider.notifier).logout();
              onLogout();
            },
            child: const Text('Terminate Session', style: TextStyle(color: AppColors.errorFg)),
          ),
        ],
      ),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final VoidCallback onTap;

  const _SettingsTile({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: AppCard(
        enableBlur: false,
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
            const SizedBox(width: AppSpacing.md),
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
            const Icon(Icons.chevron_right, size: 20, color: AppColors.grey400),
          ],
        ),
      ),
    );
  }
}
