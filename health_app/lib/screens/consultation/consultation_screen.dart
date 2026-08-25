import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/models.dart';
import '../../providers/app_providers.dart';
import '../../services/api_client.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common_widgets.dart';
import '../../widgets/prescription_card.dart';
import '../../widgets/status_pill.dart';
import 'consultation_thread_screen.dart';
import 'prescription_form_screen.dart';

class ConsultationScreen extends ConsumerStatefulWidget {
  const ConsultationScreen({
    super.key,
    required this.ticket,
  });

  final ConsultationTicket ticket;

  @override
  ConsumerState<ConsultationScreen> createState() => _ConsultationScreenState();
}

class _ConsultationScreenState extends ConsumerState<ConsultationScreen> {
  final TextEditingController _reviewController = TextEditingController();

  bool _joining = false;
  bool _closing = false;
  bool _rating = false;
  bool _navigating = false;
  int _ratingValue = 5;
  late ConsultationTicket _ticket;

  @override
  void initState() {
    super.initState();
    _ticket = widget.ticket;
  }

  @override
  void dispose() {
    _reviewController.dispose();
    super.dispose();
  }

  // Guards against a double-tap pushing two stacked routes (e.g. on a slow
  // frame, before the first push has settled) — mirrors the _joining/_closing
  // guards below for the accept/close actions.
  Future<void> _pushRoute(Route route) async {
    setState(() => _navigating = true);
    await Navigator.of(context).push(route);
    if (mounted) setState(() => _navigating = false);
  }

  Future<void> _acceptConsultation() async {
    setState(() {
      _joining = true;
    });
    try {
      final accepted = await ApiClient.acceptConsultation(_ticket.id);
      if (!mounted) return;
      setState(() {
        _ticket = accepted;
      });
      ref.invalidate(myConsultationsProvider);
      ref.invalidate(consultationQueueProvider);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not accept consultation: $e')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _joining = false;
        });
      }
    }
  }

  Future<void> _closeConsultation() async {
    setState(() {
      _closing = true;
    });
    try {
      final closed = await ApiClient.closeConsultation(_ticket.id);
      if (!mounted) return;
      setState(() {
        _ticket = closed;
      });
      ref.invalidate(myConsultationsProvider);
      ref.invalidate(consultationQueueProvider);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not close consultation: $e')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _closing = false;
        });
      }
    }
  }

  Future<void> _rateDoctor() async {
    setState(() {
      _rating = true;
    });
    try {
      await ApiClient.rateDoctor(
        _ticket.id,
        rating: _ratingValue,
        review: _reviewController.text.trim().isEmpty ? null : _reviewController.text.trim(),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Thanks for your feedback.')),
      );
      ref.invalidate(myConsultationsProvider);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not submit rating: $e')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _rating = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    // Reads the ambient Theme rather than a hardcoded accent — this screen is
    // pushed from both patient (chat_screen.dart) and doctor
    // (doctor_navigation_screen.dart) navigation stacks, and `Theme.of` always
    // resolves to whichever ThemeData (Signal Blue vs Clinical Gold) is active
    // in the root MaterialApp for the logged-in user's role. No branching on
    // `isDoctor` is needed here to pick a color.
    final primary = theme.colorScheme.primary;
    final authState = ref.watch(authProvider);
    final currentUser = authState.user;
    final isDoctor = currentUser?.role == 'doctor';
    final canAccept = isDoctor && _ticket.status == 'pending';
    final canClose = _ticket.status != 'closed' && (isDoctor || _ticket.status == 'in_progress' || _ticket.status == 'accepted');
    final canAddPrescription = isDoctor && _ticket.doctorId == currentUser?.id && (_ticket.status == 'accepted' || _ticket.status == 'in_progress');
    final severity = severityMeta(_ticket.severityLevel);

    return Scaffold(
      appBar: CustomAppBar(
        title: 'Consultation #${_ticket.id}',
        actions: [
          if (canAccept)
            TextButton(
              onPressed: _joining ? null : _acceptConsultation,
              child: _joining
                  ? const SizedBox(
                      height: 16,
                      width: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Accept'),
            ),
          if (canClose)
            TextButton(
              onPressed: _closing ? null : _closeConsultation,
              child: _closing
                  ? const SizedBox(
                      height: 16,
                      width: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Close'),
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.lg),
        children: [
          // Severity banner — semantic glass tint keyed off severityLevel.
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(AppSpacing.lg),
            decoration: BoxDecoration(
              color: severity.bg,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: severity.fg.withValues(alpha: 0.25)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(severity.icon, color: severity.fg, size: 20),
                    const SizedBox(width: AppSpacing.sm),
                    Text(
                      '${_ticket.severityLevel.toUpperCase()} SEVERITY',
                      style: AppFonts.mono(
                        theme.textTheme.labelLarge!.copyWith(color: severity.fg, letterSpacing: 1),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.sm),
                Text(_ticket.triggerReason, style: theme.textTheme.bodyMedium),
                const SizedBox(height: AppSpacing.md),
                Wrap(
                  spacing: AppSpacing.sm,
                  runSpacing: AppSpacing.sm,
                  children: [
                    StatusPill(label: _ticket.status.toUpperCase(), tone: StatusPillTone.info),
                    StatusPill(label: _ticket.triggerSource.toUpperCase(), tone: StatusPillTone.neutral),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.xl),

          // Primary action — Open Chat. The single solid-primary CTA on this
          // screen; "Add Prescription" below is demoted to glass-secondary
          // per the spec's "never two solid primaries side by side" rule.
          PrimaryButton(
            label: 'Open Chat',
            isEnabled: !_navigating,
            onPressed: () {
              _pushRoute(
                MaterialPageRoute(
                  builder: (_) => ConsultationThreadScreen(ticket: _ticket),
                ),
              );
            },
          ),

          if (canAddPrescription) ...[
            const SizedBox(height: AppSpacing.md),
            SecondaryButton(
              label: 'Add Prescription',
              icon: Icons.medication_outlined,
              isEnabled: !_navigating,
              onPressed: () {
                _pushRoute(
                  MaterialPageRoute(
                    builder: (_) => PrescriptionFormScreen(ticketId: _ticket.id),
                  ),
                );
              },
            ),
          ],

          const SizedBox(height: AppSpacing.xl),

          Consumer(
            builder: (context, ref, _) {
              final prescriptionsAsync = ref.watch(ticketPrescriptionsProvider(_ticket.id));
              return prescriptionsAsync.when(
                data: (prescriptions) {
                  if (prescriptions.isEmpty) return const SizedBox.shrink();
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Prescriptions', style: theme.textTheme.headlineSmall),
                      const SizedBox(height: AppSpacing.md),
                      ...prescriptions.map(
                        (prescription) => Padding(
                          padding: const EdgeInsets.only(bottom: AppSpacing.md),
                          child: PrescriptionCard(
                            prescription: prescription,
                            onSupersede: isDoctor && _ticket.doctorId == currentUser?.id && !_navigating
                                ? () {
                                    _pushRoute(
                                      MaterialPageRoute(
                                        builder: (_) => PrescriptionFormScreen(
                                          ticketId: _ticket.id,
                                          supersedesPrescriptionId: prescription.id,
                                        ),
                                      ),
                                    );
                                  }
                                : null,
                          ),
                        ),
                      ),
                    ],
                  );
                },
                loading: () => const SizedBox.shrink(),
                error: (_, _) => const SizedBox.shrink(),
              );
            },
          ),

          if (_ticket.status == 'closed' && !isDoctor) ...[
            const SizedBox(height: AppSpacing.xl),
            AppCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Rate this doctor', style: theme.textTheme.headlineSmall),
                  const SizedBox(height: AppSpacing.lg),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: List.generate(5, (index) {
                      final star = index + 1;
                      return Column(
                        children: [
                          IconButton(
                            icon: Icon(
                              star <= _ratingValue ? Icons.star : Icons.star_border,
                              color: primary,
                            ),
                            onPressed: () => setState(() => _ratingValue = star),
                          ),
                          Text(
                            '$star',
                            style: AppFonts.mono(
                              theme.textTheme.labelSmall!.copyWith(color: AppColors.grey500),
                            ),
                          ),
                        ],
                      );
                    }),
                  ),
                  Center(
                    child: Text(
                      '$_ratingValue / 5',
                      style: AppFonts.mono(theme.textTheme.titleMedium!.copyWith(color: primary)),
                    ),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  TextField(
                    controller: _reviewController,
                    decoration: const InputDecoration(hintText: 'Optional review'),
                    maxLines: 2,
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  PrimaryButton(
                    label: 'Submit Rating',
                    onPressed: _rateDoctor,
                    isLoading: _rating,
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

