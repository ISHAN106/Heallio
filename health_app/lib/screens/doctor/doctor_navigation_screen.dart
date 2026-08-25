import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/models.dart';
import '../../providers/app_providers.dart';
import '../../services/api_client.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common_widgets.dart';
import '../consultation/consultation_screen.dart';
import '../profile/profile_screen.dart';
import '../../widgets/avatar_with_status.dart';
import '../../widgets/glass_bottom_nav.dart';
import '../../widgets/status_pill.dart';

String _formatResponseTime(double? seconds) {
  if (seconds == null) return '—';
  final minutes = seconds / 60;
  if (minutes < 60) return '${minutes.round()}m';
  final hours = minutes / 60;
  return '${hours.toStringAsFixed(1)}h';
}

class DoctorNavigationScreen extends ConsumerStatefulWidget {
  const DoctorNavigationScreen({super.key});

  @override
  ConsumerState<DoctorNavigationScreen> createState() => _DoctorNavigationScreenState();
}

class _DoctorNavigationScreenState extends ConsumerState<DoctorNavigationScreen> {
  int _selectedIndex = 0;

  static const _navItems = [
    GlassNavItem(icon: Icons.dashboard_outlined, activeIcon: Icons.dashboard, label: 'Dashboard'),
    GlassNavItem(icon: Icons.medical_services_outlined, activeIcon: Icons.medical_services, label: 'Consults'),
    GlassNavItem(icon: Icons.person_outline, activeIcon: Icons.person, label: 'Profile'),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBody: true,
      body: IndexedStack(
        index: _selectedIndex,
        children: [
          DoctorDashboardScreen(
            onOpenConsultation: (ticket) {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => ConsultationScreen(ticket: ticket),
                ),
              );
            },
            onOpenMyConsultations: () => setState(() => _selectedIndex = 1),
          ),
          DoctorConsultationsScreen(
            onOpenConsultation: (ticket) {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => ConsultationScreen(ticket: ticket),
                ),
              );
            },
          ),
          ProfileScreen(
            onLogout: () {},
          ),
        ],
      ),
      bottomNavigationBar: GlassBottomNav(
        items: _navItems,
        currentIndex: _selectedIndex,
        onTap: (index) => setState(() => _selectedIndex = index),
      ),
    );
  }
}

class DoctorDashboardScreen extends ConsumerWidget {
  const DoctorDashboardScreen({
    super.key,
    required this.onOpenConsultation,
    required this.onOpenMyConsultations,
  });

  final ValueChanged<ConsultationTicket> onOpenConsultation;
  final VoidCallback onOpenMyConsultations;

  String _formatDateTime(DateTime dateTime) {
    final hour = dateTime.hour % 12 == 0 ? 12 : dateTime.hour % 12;
    final minute = dateTime.minute.toString().padLeft(2, '0');
    final suffix = dateTime.hour >= 12 ? 'PM' : 'AM';
    return '${dateTime.month}/${dateTime.day} · $hour:$minute $suffix';
  }

  List<ConsultationTicket> _sortByPriority(List<ConsultationTicket> tickets) {
    final sorted = [...tickets];
    sorted.sort((a, b) {
      final severityComparison = b.severityScore.compareTo(a.severityScore);
      if (severityComparison != 0) return severityComparison;
      return b.createdAt.compareTo(a.createdAt);
    });
    return sorted;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profileAsync = ref.watch(myDoctorProfileProvider);
    final queueAsync = ref.watch(consultationQueueProvider);
    final consultationsAsync = ref.watch(myConsultationsProvider);
    final categoriesAsync = ref.watch(doctorCategoriesProvider);

    return Scaffold(
      appBar: const CustomAppBar(title: 'Doctor Dashboard'),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(myDoctorProfileProvider);
          ref.invalidate(consultationQueueProvider);
          ref.invalidate(myConsultationsProvider);
          ref.invalidate(doctorCategoriesProvider);
        },
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, AppSpacing.navClearance),
          children: [
            profileAsync.when(
              data: (profile) => AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        AvatarWithStatus(icon: Icons.medical_services, isOnline: profile.isAvailable),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Dr. ${profile.categoryName}', style: Theme.of(context).textTheme.titleLarge),
                              const SizedBox(height: 4),
                              Text(
                                '${profile.yearsExperience} years experience · ${profile.isAvailable ? 'On duty' : 'Offline'}',
                                style: Theme.of(context).textTheme.bodyMedium,
                              ),
                            ],
                          ),
                        ),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Switch(
                              value: profile.isAvailable,
                              activeThumbColor: Theme.of(context).colorScheme.primary,
                              onChanged: (value) async {
                                await ApiClient.setDoctorAvailability(value);
                                ref.invalidate(myDoctorProfileProvider);
                              },
                            ),
                            Text(
                              profile.isAvailable ? 'Available' : 'Unavailable',
                              style: AppFonts.mono(
                                Theme.of(context).textTheme.labelMedium!.copyWith(
                                      color: profile.isAvailable ? AppColors.successFg : AppColors.grey500,
                                    ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                    if ((profile.bio ?? '').trim().isNotEmpty) ...[
                      const SizedBox(height: AppSpacing.md),
                      Text(
                        profile.bio!,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                    const SizedBox(height: AppSpacing.lg),
                    Wrap(
                      spacing: AppSpacing.md,
                      runSpacing: AppSpacing.md,
                      children: [
                        StatusPill(label: profile.categoryName, icon: Icons.local_hospital_outlined),
                        StatusPill(label: profile.licenseNumber, icon: Icons.verified_outlined),
                        StatusPill(
                          label: '${profile.averageRating.toStringAsFixed(1)} · ${profile.totalRatings} reviews',
                          icon: Icons.star_outline,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              loading: () => const LoadingState(message: 'Loading doctor profile...'),
              error: (error, _) => ErrorState(
                message: 'Doctor profile missing or unavailable: $error',
                onRetry: () => ref.invalidate(myDoctorProfileProvider),
              ),
            ),
            const SizedBox(height: AppSpacing.xxl),
            profileAsync.maybeWhen(
              data: (profile) => Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Today', style: Theme.of(context).textTheme.headlineMedium),
                  const SizedBox(height: AppSpacing.md),
                  Row(
                    children: [
                      Expanded(
                        child: StatCard(
                          label: 'Active Cases',
                          value: '${profile.activeCases}',
                          icon: Icons.group_outlined,
                        ),
                      ),
                      const SizedBox(width: AppSpacing.md),
                      Expanded(
                        child: StatCard(
                          label: 'Avg Response',
                          value: _formatResponseTime(profile.avgResponseSeconds),
                          icon: Icons.timer_outlined,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.md),
                  Row(
                    children: [
                      Expanded(
                        child: StatCard(
                          label: 'Prescriptions',
                          value: '${profile.prescriptionsIssued}',
                          icon: Icons.medication_outlined,
                        ),
                      ),
                      const SizedBox(width: AppSpacing.md),
                      Expanded(
                        child: StatCard(
                          label: 'Rating',
                          value: profile.averageRating.toStringAsFixed(1),
                          icon: Icons.star_outline,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              orElse: () => const SizedBox.shrink(),
            ),
            const SizedBox(height: 16),
            queueAsync.when(
              data: (queue) {
                final prioritizedQueue = _sortByPriority(queue);
                final urgentTicket = prioritizedQueue.isNotEmpty ? prioritizedQueue.first : null;

                return Column(
                  children: [
                    if (urgentTicket != null)
                      Container(
                        decoration: BoxDecoration(
                          color: AppColors.errorBg,
                          borderRadius: BorderRadius.circular(24),
                          border: Border.all(color: AppColors.error.withValues(alpha: 0.3)),
                        ),
                        padding: const EdgeInsets.all(AppSpacing.lg),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.priority_high, color: AppColors.errorFg),
                            const SizedBox(width: AppSpacing.md),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Urgent Review',
                                    style: Theme.of(context).textTheme.titleLarge?.copyWith(color: AppColors.errorFg),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    'Ticket #${urgentTicket.id} · ${urgentTicket.severityLevel} · ${_formatDateTime(urgentTicket.createdAt)}',
                                    style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.errorFg),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    urgentTicket.triggerReason,
                                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.errorFg),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: AppSpacing.md),
                            ElevatedButton(
                              style: ElevatedButton.styleFrom(
                                backgroundColor: AppColors.error,
                                foregroundColor: AppColors.onError,
                              ),
                              onPressed: () async {
                                try {
                                  final accepted = await ApiClient.acceptConsultation(urgentTicket.id);
                                  if (context.mounted) {
                                    ref.invalidate(consultationQueueProvider);
                                    ref.invalidate(myConsultationsProvider);
                                    onOpenConsultation(accepted);
                                  }
                                } catch (e) {
                                  if (context.mounted) {
                                    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
                                  }
                                }
                              },
                              child: const Text('Review Telemetry'),
                            ),
                          ],
                        ),
                      ),
                    const SizedBox(height: AppSpacing.lg),
                    AppCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Workflow shortcuts', style: Theme.of(context).textTheme.titleLarge),
                          const SizedBox(height: AppSpacing.md),
                          Wrap(
                              spacing: 12,
                              runSpacing: 12,
                              children: [
                                _ActionPill(
                                  icon: Icons.medical_services_outlined,
                                  label: 'My consultations',
                                  onTap: onOpenMyConsultations,
                                ),
                                _ActionPill(
                                  icon: Icons.mark_chat_unread_outlined,
                                  label: 'Secure chat',
                                  onTap: () {
                                    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Open a consultation to continue in secure chat.')));
                                  },
                                ),
                                _ActionPill(
                                  icon: Icons.refresh,
                                  label: 'Refresh queue',
                                  onTap: () {
                                    ref.invalidate(consultationQueueProvider);
                                    ref.invalidate(myConsultationsProvider);
                                    ref.invalidate(myDoctorProfileProvider);
                                  },
                                ),
                                _ActionPill(
                                  icon: Icons.toggle_on,
                                  label: 'Toggle availability',
                                  onTap: () async {
                                    try {
                                      final currentProfile = await ref.read(myDoctorProfileProvider.future);
                                      await ApiClient.setDoctorAvailability(!currentProfile.isAvailable);
                                      ref.invalidate(myDoctorProfileProvider);
                                    } catch (e) {
                                      if (context.mounted) {
                                        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
                                      }
                                    }
                                  },
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    const SizedBox(height: AppSpacing.xxl),
                    Text('Open Queue', style: Theme.of(context).textTheme.headlineMedium),
                    const SizedBox(height: AppSpacing.md),
                    if (queue.isEmpty)
                      AppCard(child: const Text('No pending consultations right now.'))
                    else
                      for (var i = 0; i < prioritizedQueue.take(6).length; i++) ...[
                        AppCard(
                          enableBlur: false,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          'ID: ${prioritizedQueue[i].id}',
                                          style: AppFonts.mono(
                                            Theme.of(context).textTheme.labelSmall!.copyWith(
                                                  color: Theme.of(context).colorScheme.primary,
                                                  letterSpacing: 1.0,
                                                ),
                                          ),
                                        ),
                                        const SizedBox(height: 4),
                                        Text(
                                          prioritizedQueue[i].triggerReason,
                                          style: Theme.of(context).textTheme.bodyMedium,
                                          maxLines: 2,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(width: AppSpacing.sm),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                    decoration: BoxDecoration(
                                      color: AppColors.glassWell,
                                      borderRadius: BorderRadius.circular(4),
                                      border: Border.all(color: AppColors.frostEdge),
                                    ),
                                    child: Text(
                                      'Wait: ${DateTime.now().difference(prioritizedQueue[i].createdAt).inMinutes}m',
                                      style: AppFonts.mono(
                                        Theme.of(context).textTheme.labelSmall!.copyWith(color: AppColors.grey500),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: AppSpacing.md),
                              PrimaryButton(
                                label: 'Accept Consult',
                                onPressed: () async {
                                  try {
                                    final accepted = await ApiClient.acceptConsultation(prioritizedQueue[i].id);
                                    if (context.mounted) {
                                      ref.invalidate(consultationQueueProvider);
                                      ref.invalidate(myConsultationsProvider);
                                      onOpenConsultation(accepted);
                                    }
                                  } catch (e) {
                                    if (context.mounted) {
                                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
                                    }
                                  }
                                },
                              ),
                            ],
                          ),
                        ),
                        if (i != prioritizedQueue.take(6).length - 1) const SizedBox(height: AppSpacing.md),
                      ],
                  ],
                );
              },
              loading: () => const LoadingState(message: 'Loading consultation queue...'),
              error: (error, _) => ErrorState(
                message: error.toString(),
                onRetry: () => ref.invalidate(consultationQueueProvider),
              ),
            ),
            const SizedBox(height: 16),
            consultationsAsync.when(
              data: (consultations) {
                final sortedConsultations = _sortByPriority(consultations);

                return AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Assigned consultations', style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: AppSpacing.sm),
                      if (consultations.isEmpty)
                        const Text('No assigned consultations yet.')
                      else
                        ...sortedConsultations.map(
                          (ticket) => ListTile(
                            contentPadding: EdgeInsets.zero,
                            leading: Icon(
                              ticket.status == 'closed'
                                  ? Icons.check_circle_outline
                                  : ticket.status == 'accepted' || ticket.status == 'in_progress'
                                      ? Icons.video_call
                                      : Icons.pending_actions,
                              color: severityMeta(ticket.severityLevel).fg,
                            ),
                            title: Text('Ticket #${ticket.id} · ${ticket.status}'),
                            subtitle: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const SizedBox(height: 4),
                                Text(ticket.triggerReason),
                                const SizedBox(height: 4),
                                Text('Updated ${_formatDateTime(ticket.acceptedAt ?? ticket.createdAt)}'),
                              ],
                            ),
                            isThreeLine: true,
                            trailing: TextButton(
                              onPressed: () => onOpenConsultation(ticket),
                              child: Text(ticket.status == 'closed' ? 'Review' : 'Open'),
                            ),
                          ),
                        ),
                    ],
                  ),
                );
              },
              loading: () => const SizedBox.shrink(),
              error: (error, _) => ErrorState(message: error.toString(), onRetry: () => ref.invalidate(myConsultationsProvider)),
            ),
            const SizedBox(height: AppSpacing.lg),
            categoriesAsync.when(
              data: (categories) => AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Clinical specialties', style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: AppSpacing.sm),
                    Text(
                      'Use these specialty tags to keep the queue organized and match patient cases quickly.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: AppSpacing.md),
                    Wrap(
                      spacing: AppSpacing.sm,
                      runSpacing: AppSpacing.sm,
                      children: categories.map((category) => StatusPill(label: category.name)).toList(),
                    ),
                  ],
                ),
              ),
              loading: () => const SizedBox.shrink(),
              error: (error, _) => const SizedBox.shrink(),
            ),
          ],
        ),
      ),
    );
  }
}

class DoctorConsultationsScreen extends ConsumerWidget {
  const DoctorConsultationsScreen({
    super.key,
    required this.onOpenConsultation,
  });

  final ValueChanged<ConsultationTicket> onOpenConsultation;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final queueAsync = ref.watch(consultationQueueProvider);
    final consultationsAsync = ref.watch(myConsultationsProvider);

    return Scaffold(
      appBar: const CustomAppBar(title: 'Consultations'),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, AppSpacing.navClearance),
        children: [
          queueAsync.when(
            data: (queue) => _ConsultationSection(
              title: 'Pending Queue',
              tickets: queue,
              onOpenConsultation: onOpenConsultation,
              emptyText: 'No pending cases.',
              allowAccept: true,
            ),
            loading: () => const LoadingState(message: 'Loading queue...'),
            error: (error, _) => ErrorState(message: error.toString(), onRetry: () => ref.invalidate(consultationQueueProvider)),
          ),
          const SizedBox(height: 16),
          consultationsAsync.when(
            data: (consultations) => _ConsultationSection(
              title: 'Assigned Cases',
              tickets: consultations,
              onOpenConsultation: onOpenConsultation,
              emptyText: 'No assigned consultations.',
              allowAccept: false,
            ),
            loading: () => const SizedBox.shrink(),
            error: (error, _) => ErrorState(message: error.toString(), onRetry: () => ref.invalidate(myConsultationsProvider)),
          ),
        ],
      ),
    );
  }
}

class _ConsultationSection extends StatelessWidget {
  const _ConsultationSection({
    required this.title,
    required this.tickets,
    required this.onOpenConsultation,
    required this.emptyText,
    required this.allowAccept,
  });

  final String title;
  final List<ConsultationTicket> tickets;
  final ValueChanged<ConsultationTicket> onOpenConsultation;
  final String emptyText;
  final bool allowAccept;

  static String _waitLabel(DateTime createdAt) {
    final minutes = DateTime.now().difference(createdAt).inMinutes;
    if (minutes < 60) return 'Wait: ${minutes}m';
    return 'Wait: ${(minutes / 60).floor()}h ${minutes % 60}m';
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: AppSpacing.md),
        if (tickets.isEmpty)
          AppCard(
            child: Text(emptyText, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.grey500)),
          )
        else
          for (var i = 0; i < tickets.length; i++) ...[
            AppCard(
              enableBlur: false,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'ID: ${tickets[i].id}',
                              style: AppFonts.mono(
                                Theme.of(context).textTheme.labelSmall!.copyWith(
                                      color: Theme.of(context).colorScheme.primary,
                                      letterSpacing: 1.0,
                                    ),
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              tickets[i].triggerReason,
                              style: Theme.of(context).textTheme.bodyMedium,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: AppSpacing.sm),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppColors.glassWell,
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: AppColors.frostEdge),
                        ),
                        child: Text(
                          _waitLabel(tickets[i].createdAt),
                          style: AppFonts.mono(
                            Theme.of(context).textTheme.labelSmall!.copyWith(color: AppColors.grey500),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.md),
                  PrimaryButton(
                    label: allowAccept ? 'Accept Consult' : 'Open',
                    onPressed: () => onOpenConsultation(tickets[i]),
                  ),
                ],
              ),
            ),
            if (i != tickets.length - 1) const SizedBox(height: AppSpacing.md),
          ],
      ],
    );
  }
}

class _ActionPill extends StatelessWidget {
  const _ActionPill({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;
    return ActionChip(
      avatar: Icon(icon, size: 18, color: primary),
      label: Text(label),
      onPressed: onTap,
      backgroundColor: primary.withValues(alpha: 0.08),
      side: BorderSide(color: primary.withValues(alpha: 0.15)),
    );
  }
}
