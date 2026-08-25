// health_app/lib/screens/consultation/prescription_form_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/app_providers.dart';
import '../../services/api_client.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common_widgets.dart';

class _MedicationRow {
  final TextEditingController name = TextEditingController();
  final TextEditingController dosage = TextEditingController();
  final TextEditingController frequency = TextEditingController();
  final TextEditingController duration = TextEditingController();

  void dispose() {
    name.dispose();
    dosage.dispose();
    frequency.dispose();
    duration.dispose();
  }
}

class PrescriptionFormScreen extends ConsumerStatefulWidget {
  const PrescriptionFormScreen({
    super.key,
    required this.ticketId,
    this.supersedesPrescriptionId,
  });

  final String ticketId;
  final String? supersedesPrescriptionId;

  @override
  ConsumerState<PrescriptionFormScreen> createState() => _PrescriptionFormScreenState();
}

class _PrescriptionFormScreenState extends ConsumerState<PrescriptionFormScreen> {
  final List<_MedicationRow> _rows = [_MedicationRow()];
  final TextEditingController _notesController = TextEditingController();
  DateTime? _followUpDate;
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    for (final row in _rows) {
      row.dispose();
    }
    _notesController.dispose();
    super.dispose();
  }

  void _addRow() {
    setState(() => _rows.add(_MedicationRow()));
  }

  void _removeRow(int index) {
    setState(() {
      _rows[index].dispose();
      _rows.removeAt(index);
    });
  }

  Future<void> _pickFollowUpDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked != null) {
      setState(() => _followUpDate = picked);
    }
  }

  Future<void> _submit() async {
    // A row with any field filled in but no name would previously be
    // silently dropped by the old name-only filter — the doctor would see
    // the form "succeed" while that medication vanished. Rows that are
    // entirely blank (the normal trailing empty row) are still ignored.
    final nonEmptyRows = _rows.where((row) =>
        row.name.text.trim().isNotEmpty ||
        row.dosage.text.trim().isNotEmpty ||
        row.frequency.text.trim().isNotEmpty ||
        row.duration.text.trim().isNotEmpty);

    if (nonEmptyRows.any((row) => row.name.text.trim().isEmpty)) {
      setState(() => _error = 'Each medication needs a name — fill it in or remove the row.');
      return;
    }

    final items = nonEmptyRows
        .map((row) => {
              'medication_name': row.name.text.trim(),
              'dosage': row.dosage.text.trim().isEmpty ? null : row.dosage.text.trim(),
              'frequency': row.frequency.text.trim().isEmpty ? null : row.frequency.text.trim(),
              'duration': row.duration.text.trim().isEmpty ? null : row.duration.text.trim(),
            })
        .toList();
    final notes = _notesController.text.trim().isEmpty ? null : _notesController.text.trim();

    if (items.isEmpty && notes == null) {
      setState(() => _error = 'Add at least one medication or a note before submitting.');
      return;
    }

    setState(() {
      _submitting = true;
      _error = null;
    });

    try {
      final followUpDateString = _followUpDate?.toIso8601String().split('T').first;
      if (widget.supersedesPrescriptionId != null) {
        await ApiClient.supersedePrescription(
          widget.supersedesPrescriptionId!,
          items: items,
          notes: notes,
          followUpDate: followUpDateString,
        );
      } else {
        await ApiClient.createPrescription(
          widget.ticketId,
          items: items,
          notes: notes,
          followUpDate: followUpDateString,
        );
      }
      ref.invalidate(ticketPrescriptionsProvider(widget.ticketId));
      ref.invalidate(myPrescriptionsProvider);
      if (!mounted) return;
      Navigator.of(context).pop();
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString());
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isSupersede = widget.supersedesPrescriptionId != null;

    return Scaffold(
      appBar: CustomAppBar(title: isSupersede ? 'Supersede Prescription' : 'New Prescription'),
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.lg),
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  isSupersede
                      ? 'This issues a corrected prescription and marks the previous one as superseded.'
                      : 'Issuing a prescription for consultation #${widget.ticketId}',
                  style: theme.textTheme.bodyMedium?.copyWith(color: AppColors.grey500),
                ),
              ),
              const SizedBox(width: AppSpacing.md),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
                decoration: BoxDecoration(
                  color: AppColors.glassPanel,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppColors.frostEdge),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      'STATUS',
                      style: theme.textTheme.labelSmall?.copyWith(color: AppColors.grey400, letterSpacing: 1.0),
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Container(
                          width: 6,
                          height: 6,
                          decoration: BoxDecoration(color: theme.colorScheme.primary, shape: BoxShape.circle),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          'Draft',
                          style: AppFonts.mono(theme.textTheme.labelSmall!.copyWith(color: theme.colorScheme.primary)),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.xl),

          // -- Medications section -------------------------------------------------
          _SectionHeader(icon: Icons.vaccines_outlined, label: 'Rx Details'),
          const SizedBox(height: AppSpacing.md),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (int i = 0; i < _rows.length; i++) ...[
                  if (i > 0) ...[
                    const SizedBox(height: AppSpacing.lg),
                    const Divider(height: 1, color: AppColors.grey200),
                    const SizedBox(height: AppSpacing.lg),
                  ],
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        flex: 2,
                        child: CustomTextField(
                          label: 'Medication name',
                          hint: 'e.g. Amoxicillin',
                          controller: _rows[i].name,
                        ),
                      ),
                      const SizedBox(width: AppSpacing.sm),
                      Expanded(
                        child: CustomTextField(
                          label: 'Dosage',
                          hint: '500mg',
                          controller: _rows[i].dosage,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.md),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: CustomTextField(
                          label: 'Frequency',
                          hint: '1x daily',
                          controller: _rows[i].frequency,
                        ),
                      ),
                      const SizedBox(width: AppSpacing.sm),
                      Expanded(
                        child: CustomTextField(
                          label: 'Duration',
                          hint: '7 days',
                          controller: _rows[i].duration,
                        ),
                      ),
                    ],
                  ),
                  if (_rows.length > 1) ...[
                    const SizedBox(height: AppSpacing.sm),
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton.icon(
                        onPressed: () => _removeRow(i),
                        style: TextButton.styleFrom(foregroundColor: AppColors.errorFg),
                        icon: const Icon(Icons.close, size: 16),
                        label: const Text('Remove'),
                      ),
                    ),
                  ],
                ],
                const SizedBox(height: AppSpacing.lg),
                SecondaryButton(
                  label: 'Add another medication',
                  icon: Icons.add,
                  onPressed: _addRow,
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.xl),

          // -- Directives section ---------------------------------------------------
          _SectionHeader(icon: Icons.assignment_outlined, label: 'Directives'),
          const SizedBox(height: AppSpacing.md),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'CARE INSTRUCTIONS',
                  style: theme.textTheme.labelSmall?.copyWith(color: AppColors.grey400, letterSpacing: 0.8),
                ),
                const SizedBox(height: AppSpacing.sm),
                TextFormField(
                  controller: _notesController,
                  maxLines: 3,
                  decoration: const InputDecoration(hintText: 'Take with food. Avoid alcohol...'),
                ),
                const SizedBox(height: AppSpacing.lg),
                Text(
                  'FOLLOW-UP EVALUATION',
                  style: theme.textTheme.labelSmall?.copyWith(color: AppColors.grey400, letterSpacing: 0.8),
                ),
                const SizedBox(height: AppSpacing.sm),
                _GlassDateField(
                  value: _followUpDate,
                  onTap: _pickFollowUpDate,
                ),
              ],
            ),
          ),

          if (_error != null) ...[
            const SizedBox(height: AppSpacing.lg),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: AppColors.errorBg,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppColors.error.withValues(alpha: 0.3)),
              ),
              child: Text(_error!, style: theme.textTheme.bodyMedium?.copyWith(color: AppColors.errorFg)),
            ),
          ],

          const SizedBox(height: AppSpacing.xl),
          PrimaryButton(
            label: isSupersede ? 'Authorize Correction' : 'Authorize Prescription',
            onPressed: _submit,
            isLoading: _submitting,
          ),
          const SizedBox(height: AppSpacing.lg),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;
    return Row(
      children: [
        Icon(icon, color: primary, size: 20),
        const SizedBox(width: AppSpacing.sm),
        Text(label, style: Theme.of(context).textTheme.headlineSmall),
      ],
    );
  }
}

/// Follow-up date trigger styled to match [CustomTextField]'s glass-well
/// look — the underlying `showDatePicker` dialog is still the platform
/// picker (unavoidable in Flutter), but the tappable surface itself never
/// reads as a raw/unstyled control.
class _GlassDateField extends StatelessWidget {
  const _GlassDateField({required this.value, required this.onTap});

  final DateTime? value;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: AppColors.glassWell,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppColors.grey200),
        ),
        child: Row(
          children: [
            const Icon(Icons.calendar_month_outlined, size: 18, color: AppColors.grey400),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: Text(
                value == null ? 'No follow-up date set' : _formatDate(value!),
                style: AppFonts.mono(
                  theme.textTheme.bodyMedium!.copyWith(
                    color: value == null ? AppColors.grey400 : AppColors.grey700,
                  ),
                ),
              ),
            ),
            const Icon(Icons.chevron_right, size: 18, color: AppColors.grey400),
          ],
        ),
      ),
    );
  }

  static String _formatDate(DateTime date) {
    final local = date.toLocal();
    const months = [
      'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC',
    ];
    return '${months[local.month - 1]} ${local.day.toString().padLeft(2, '0')}, ${local.year}';
  }
}
