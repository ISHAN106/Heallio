import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/models.dart';
import '../../providers/app_providers.dart';
import '../../services/api_client.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common_widgets.dart';
import '../../widgets/status_pill.dart';

class ConnectedSessionsScreen extends ConsumerStatefulWidget {
  const ConnectedSessionsScreen({super.key});

  @override
  ConsumerState<ConnectedSessionsScreen> createState() => _ConnectedSessionsScreenState();
}

class _ConnectedSessionsScreenState extends ConsumerState<ConnectedSessionsScreen> {
  String? _revokingId;

  Future<void> _revoke(UserSession session) async {
    setState(() => _revokingId = session.id);
    try {
      await ApiClient.revokeSession(session.id);
      ref.invalidate(connectedSessionsProvider);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to sign out that device: $e')),
      );
    } finally {
      if (mounted) setState(() => _revokingId = null);
    }
  }

  String _timeAgo(DateTime? time) {
    if (time == null) return 'Not seen yet';
    final diff = DateTime.now().difference(time);
    if (diff.inMinutes < 1) return 'Active now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }

  @override
  Widget build(BuildContext context) {
    final sessionsAsync = ref.watch(connectedSessionsProvider);
    final primary = Theme.of(context).colorScheme.primary;

    return Scaffold(
      appBar: const CustomAppBar(title: 'Connected Hardware'),
      body: sessionsAsync.when(
        data: (sessions) {
          if (sessions.isEmpty) {
            return EmptyState(
              title: 'No active sessions',
              message: 'Devices you sign in on will show up here.',
              icon: Icons.devices_other_outlined,
            );
          }
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(connectedSessionsProvider),
            child: ListView.separated(
              padding: const EdgeInsets.all(AppSpacing.lg),
              itemCount: sessions.length,
              separatorBuilder: (_, _) => const SizedBox(height: AppSpacing.md),
              itemBuilder: (context, index) {
                final session = sessions[index];
                return AppCard(
                  enableBlur: false,
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: primary.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Icon(Icons.devices_other_outlined, color: primary, size: 22),
                      ),
                      const SizedBox(width: AppSpacing.md),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    session.deviceLabel ?? 'Unknown device',
                                    style: Theme.of(context).textTheme.titleMedium,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                                if (session.isCurrent)
                                  const StatusPill(label: 'This device', tone: StatusPillTone.success),
                              ],
                            ),
                            const SizedBox(height: 4),
                            Text(
                              [
                                if (session.ipAddress != null) session.ipAddress!,
                                _timeAgo(session.lastSeenAt ?? session.createdAt),
                              ].join(' · '),
                              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.grey500),
                            ),
                          ],
                        ),
                      ),
                      if (!session.isCurrent)
                        _revokingId == session.id
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : IconButton(
                                icon: const Icon(Icons.logout, color: AppColors.errorFg, size: 20),
                                tooltip: 'Sign out this device',
                                onPressed: () => _revoke(session),
                              ),
                    ],
                  ),
                );
              },
            ),
          );
        },
        loading: () => const LoadingState(message: 'Loading connected devices...'),
        error: (e, _) => ErrorState(
          message: e.toString(),
          onRetry: () => ref.invalidate(connectedSessionsProvider),
        ),
      ),
    );
  }
}
