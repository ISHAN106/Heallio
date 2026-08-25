import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import '../../models/models.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common_widgets.dart';
import '../../widgets/food_scan_widget.dart';
import '../../providers/app_providers.dart';
import '../../services/api_client.dart';
import '../../widgets/status_pill.dart';

/// Simple static-threshold heuristics for the Recent-entries status pills —
/// not medical advice, just a quick visual cue (matches the disclaimer
/// pattern already used on the body-scan screen).
StatusPillTone _bloodPressureTone(int systolic, int diastolic) {
  if (systolic >= 140 || diastolic >= 90) return StatusPillTone.warning;
  return StatusPillTone.success;
}

StatusPillTone _glucoseTone(double glucose) {
  if (glucose < 70 || glucose > 125) return StatusPillTone.warning;
  return StatusPillTone.success;
}

/// Picks the right recent-entry row for a health record — each logged entry
/// now represents a single metric type (per the Metric Type dropdown), so
/// this checks blood pressure and glucose first, falling back to the
/// original combined steps/heart-rate/calories row for older records.
Widget _healthRecentRow(HealthData d, Color primary, bool reversed) {
  final time = _formatTime(d.recordedAt);

  if (d.systolicBp != null && d.diastolicBp != null) {
    return _RecentMetricRow(
      icon: Icons.monitor_heart_outlined,
      iconColor: primary,
      label: 'Blood pressure',
      value: '${d.systolicBp}/${d.diastolicBp}',
      unit: 'mmHg',
      time: time,
      reversed: reversed,
      statusLabel: _bloodPressureTone(d.systolicBp!, d.diastolicBp!) == StatusPillTone.warning ? 'HIGH' : 'NORMAL',
      statusTone: _bloodPressureTone(d.systolicBp!, d.diastolicBp!),
    );
  }

  if (d.bloodGlucose != null) {
    return _RecentMetricRow(
      icon: Icons.water_drop_outlined,
      iconColor: primary,
      label: 'Blood glucose',
      value: d.bloodGlucose!.toStringAsFixed(0),
      unit: 'mg/dL',
      time: time,
      reversed: reversed,
      statusLabel: _glucoseTone(d.bloodGlucose!) == StatusPillTone.warning ? 'OUT OF RANGE' : 'NORMAL',
      statusTone: _glucoseTone(d.bloodGlucose!),
    );
  }

  return _RecentMetricRow(
    icon: Icons.directions_walk,
    iconColor: primary,
    label: 'Steps logged',
    value: '${d.steps ?? 0}',
    unit: 'steps',
    subtitle: 'HR ${d.heartRate?.toInt() ?? 0} BPM · ${d.caloriesBurned?.toInt() ?? 0} kcal',
    time: time,
    reversed: reversed,
  );
}

Color _pillColor(StatusPillTone tone) {
  switch (tone) {
    case StatusPillTone.success:
      return AppColors.successFg;
    case StatusPillTone.warning:
      return AppColors.warningFg;
    case StatusPillTone.error:
      return AppColors.errorFg;
    case StatusPillTone.info:
      return AppColors.infoFg;
    case StatusPillTone.neutral:
      return AppColors.grey400;
  }
}

String _formatTime(DateTime dateTime) {
  final hour = dateTime.hour.toString().padLeft(2, '0');
  final minute = dateTime.minute.toString().padLeft(2, '0');
  return '$hour:$minute';
}

class HealthTrackingScreen extends ConsumerStatefulWidget {
  const HealthTrackingScreen({super.key});

  @override
  ConsumerState<HealthTrackingScreen> createState() => _HealthTrackingScreenState();
}

class _HealthTrackingScreenState extends ConsumerState<HealthTrackingScreen> {
  int _selectedTab = 0;

  static const _tabLabels = ['Health', 'Food Scan', 'Sleep'];

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;
    return Scaffold(
      appBar: const CustomAppBar(title: 'Tracking'),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.lg, AppSpacing.lg, AppSpacing.sm),
            child: _GlassSegmentedTabs(
              labels: _tabLabels,
              selectedIndex: _selectedTab,
              accent: primary,
              onChanged: (index) => setState(() => _selectedTab = index),
            ),
          ),
          Expanded(
            child: IndexedStack(
              index: _selectedTab,
              children: [
                HealthTab(
                  onTabChange: (tab) => setState(() => _selectedTab = tab),
                ),
                DietTab(
                  onTabChange: (tab) => setState(() => _selectedTab = tab),
                ),
                SleepTab(
                  onTabChange: (tab) => setState(() => _selectedTab = tab),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Segmented glass pill tab bar — one frosted pill housing the three tabs,
/// active tab tinted with the current mode's accent plus a small underglow
/// bar, per docs/stitch_design_prompt.md Section 8 (Health Tracking screen).
class _GlassSegmentedTabs extends StatelessWidget {
  const _GlassSegmentedTabs({
    required this.labels,
    required this.selectedIndex,
    required this.accent,
    required this.onChanged,
  });

  final List<String> labels;
  final int selectedIndex;
  final Color accent;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(999),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
        // Uniform border — a per-side color (brighter top edge) can't be
        // combined with borderRadius (Flutter's Border.paint throws). See
        // AppCard's doc comment in lib/widgets/common_widgets.dart.
        child: Container(
          padding: const EdgeInsets.all(6),
          decoration: BoxDecoration(
            color: AppColors.glassPanel,
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: AppColors.frostEdge, width: 1),
          ),
          child: Row(
            children: [
              for (var i = 0; i < labels.length; i++)
                Expanded(
                  child: GestureDetector(
                    onTap: () => onChanged(i),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 200),
                      curve: Curves.easeOut,
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      decoration: BoxDecoration(
                        color: i == selectedIndex ? accent.withValues(alpha: 0.2) : Colors.transparent,
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            labels[i].toUpperCase(),
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                  color: i == selectedIndex ? accent : AppColors.grey400,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: 1.0,
                                ),
                          ),
                          const SizedBox(height: 4),
                          AnimatedContainer(
                            duration: const Duration(milliseconds: 200),
                            width: i == selectedIndex ? 14 : 0,
                            height: 3,
                            decoration: BoxDecoration(
                              color: accent,
                              borderRadius: BorderRadius.circular(2),
                              boxShadow: i == selectedIndex
                                  ? [BoxShadow(color: accent.withValues(alpha: 0.6), blurRadius: 6, spreadRadius: 1)]
                                  : null,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

/// A single glass "recent entry" row, laid out as a wide main tile (icon,
/// label, mono value) plus a narrow side tile (mono time) — alternating
/// left/right per the zig-zag layout rule in Section 5. Uses
/// `AppCard(enableBlur: false)` per the perf note: this row repeats inside a
/// potentially long, frequently-invalidated list.
class _RecentMetricRow extends StatelessWidget {
  const _RecentMetricRow({
    required this.icon,
    required this.iconColor,
    required this.label,
    required this.value,
    this.unit,
    this.subtitle,
    required this.time,
    this.reversed = false,
    this.statusLabel,
    this.statusTone = StatusPillTone.neutral,
  });

  final IconData icon;
  final Color iconColor;
  final String label;
  final String value;
  final String? unit;
  final String? subtitle;
  final String time;
  final bool reversed;
  final String? statusLabel;
  final StatusPillTone statusTone;

  @override
  Widget build(BuildContext context) {
    final mainTile = AppCard(
      enableBlur: false,
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(color: iconColor.withValues(alpha: 0.16), shape: BoxShape.circle),
                child: Icon(icon, size: 16, color: iconColor),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Text(
                  label,
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(color: AppColors.grey500),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Flexible(
                child: Text(
                  value,
                  style: AppFonts.mono(Theme.of(context).textTheme.displaySmall!),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (unit != null) ...[
                const SizedBox(width: 4),
                Text(unit!, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.grey500)),
              ],
            ],
          ),
          if (subtitle != null) ...[
            const SizedBox(height: 4),
            Text(
              subtitle!,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.grey500),
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ],
      ),
    );

    final sideTile = AppCard(
      enableBlur: false,
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Stack(
        children: [
          if (statusLabel != null)
            Positioned(
              top: 0,
              right: 0,
              child: Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(color: _pillColor(statusTone), shape: BoxShape.circle),
              ),
            ),
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                time,
                style: AppFonts.mono(Theme.of(context).textTheme.labelSmall!.copyWith(color: AppColors.grey400)),
              ),
              if (statusLabel != null) ...[
                const SizedBox(height: 6),
                StatusPill(label: statusLabel!, tone: statusTone),
              ],
            ],
          ),
        ],
      ),
    );

    return Row(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: reversed
          ? [
              Expanded(child: sideTile),
              const SizedBox(width: AppSpacing.md),
              Expanded(flex: 2, child: mainTile),
            ]
          : [
              Expanded(flex: 2, child: mainTile),
              const SizedBox(width: AppSpacing.md),
              Expanded(child: sideTile),
            ],
    );
  }
}

/// Glass-well time picker field, matching CustomTextField's label/well style
/// (tracking.html's Time input).
class _TimeField extends StatelessWidget {
  const _TimeField({required this.time, required this.onTap});

  final TimeOfDay time;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'TIME',
          style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.grey400, letterSpacing: 0.8),
        ),
        const SizedBox(height: AppSpacing.sm),
        InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(14),
          child: Container(
            height: 52,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            decoration: BoxDecoration(
              color: AppColors.glassWell,
              borderRadius: BorderRadius.circular(14),
            ),
            alignment: Alignment.centerLeft,
            child: Row(
              children: [
                const Icon(Icons.schedule, color: AppColors.grey400, size: 18),
                const SizedBox(width: AppSpacing.sm),
                Text(time.format(context), style: AppFonts.mono(Theme.of(context).textTheme.bodyLarge!)),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class HealthTab extends ConsumerStatefulWidget {
  final Function(int) onTabChange;

  const HealthTab({super.key, required this.onTabChange});

  @override
  ConsumerState<HealthTab> createState() => _HealthTabState();
}

enum _MetricType {
  heartRate('Heart Rate (BPM)', Icons.favorite),
  bloodPressure('Blood Pressure', Icons.monitor_heart_outlined),
  bloodGlucose('Blood Glucose', Icons.water_drop_outlined),
  steps('Steps', Icons.directions_walk),
  caloriesBurned('Calories Burned', Icons.local_fire_department);

  const _MetricType(this.label, this.icon);
  final String label;
  final IconData icon;
}

class _HealthTabState extends ConsumerState<HealthTab> {
  late TextEditingController _valueController;
  late TextEditingController _secondaryValueController;
  _MetricType _selectedType = _MetricType.heartRate;
  TimeOfDay _selectedTime = TimeOfDay.now();

  @override
  void initState() {
    super.initState();
    _valueController = TextEditingController();
    _secondaryValueController = TextEditingController();
  }

  @override
  void dispose() {
    _valueController.dispose();
    _secondaryValueController.dispose();
    super.dispose();
  }

  DateTime get _recordedAt {
    final now = DateTime.now();
    return DateTime(now.year, now.month, now.day, _selectedTime.hour, _selectedTime.minute);
  }

  Future<void> _pickTime() async {
    final picked = await showTimePicker(context: context, initialTime: _selectedTime);
    if (picked != null) setState(() => _selectedTime = picked);
  }

  void _logHealth() async {
    try {
      switch (_selectedType) {
        case _MetricType.heartRate:
          await ApiClient.recordHealth(heartRate: double.tryParse(_valueController.text), recordedAt: _recordedAt);
        case _MetricType.steps:
          await ApiClient.recordHealth(steps: int.tryParse(_valueController.text), recordedAt: _recordedAt);
        case _MetricType.caloriesBurned:
          await ApiClient.recordHealth(caloriesBurned: double.tryParse(_valueController.text), recordedAt: _recordedAt);
        case _MetricType.bloodPressure:
          await ApiClient.recordHealth(
            systolicBp: int.tryParse(_valueController.text),
            diastolicBp: int.tryParse(_secondaryValueController.text),
            recordedAt: _recordedAt,
          );
        case _MetricType.bloodGlucose:
          await ApiClient.recordHealth(bloodGlucose: double.tryParse(_valueController.text), recordedAt: _recordedAt);
      }

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Health data logged successfully')),
      );

      _valueController.clear();
      _secondaryValueController.clear();
      setState(() => _selectedTime = TimeOfDay.now());

      ref.invalidate(recentHealthProvider);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: ${e.toString()}')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.md, AppSpacing.lg, AppSpacing.navClearance),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Log Entry', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: AppSpacing.lg),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'METRIC TYPE',
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.grey400, letterSpacing: 0.8),
                ),
                const SizedBox(height: AppSpacing.sm),
                DropdownButtonFormField<_MetricType>(
                  initialValue: _selectedType,
                  dropdownColor: AppColors.glassRaised,
                  borderRadius: BorderRadius.circular(14),
                  icon: const Icon(Icons.expand_more, color: AppColors.grey400),
                  items: _MetricType.values
                      .map((type) => DropdownMenuItem(
                            value: type,
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(type.icon, size: 18, color: primary),
                                const SizedBox(width: AppSpacing.sm),
                                Text(type.label),
                              ],
                            ),
                          ))
                      .toList(),
                  onChanged: (value) {
                    setState(() {
                      _selectedType = value ?? _MetricType.heartRate;
                      _valueController.clear();
                      _secondaryValueController.clear();
                    });
                  },
                ),
                const SizedBox(height: AppSpacing.lg),
                if (_selectedType == _MetricType.bloodPressure)
                  Row(
                    children: [
                      Expanded(
                        child: CustomTextField(
                          label: 'Systolic',
                          hint: '120',
                          controller: _valueController,
                          keyboardType: TextInputType.number,
                          prefixIcon: Icon(_selectedType.icon, color: primary),
                        ),
                      ),
                      const SizedBox(width: AppSpacing.lg),
                      Expanded(
                        child: CustomTextField(
                          label: 'Diastolic',
                          hint: '80',
                          controller: _secondaryValueController,
                          keyboardType: TextInputType.number,
                        ),
                      ),
                    ],
                  )
                else
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: CustomTextField(
                          label: 'Value',
                          hint: '00',
                          controller: _valueController,
                          keyboardType: TextInputType.number,
                          prefixIcon: Icon(_selectedType.icon, color: primary),
                        ),
                      ),
                      const SizedBox(width: AppSpacing.lg),
                      Expanded(
                        child: _TimeField(time: _selectedTime, onTap: _pickTime),
                      ),
                    ],
                  ),
                if (_selectedType == _MetricType.bloodPressure) ...[
                  const SizedBox(height: AppSpacing.lg),
                  _TimeField(time: _selectedTime, onTap: _pickTime),
                ],
                const SizedBox(height: AppSpacing.xl),
                PrimaryButton(label: 'Save Metric', leadingIcon: Icons.add, onPressed: _logHealth),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.xxl),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text('Recent', style: Theme.of(context).textTheme.headlineSmall),
              Text(
                'TODAY',
                style: AppFonts.mono(
                  Theme.of(context).textTheme.labelSmall!.copyWith(color: primary, letterSpacing: 1.2),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Consumer(
            builder: (context, ref, _) {
              final recentAsync = ref.watch(recentHealthProvider);
              return recentAsync.when(
                data: (data) {
                  if (data.isEmpty) {
                    return EmptyState(
                      title: 'No data yet',
                      message: 'Start logging your health metrics',
                      icon: Icons.health_and_safety,
                    );
                  }
                  return Column(
                    children: [
                      for (var i = 0; i < data.length; i++) ...[
                        _healthRecentRow(data[i], primary, i.isOdd),
                        if (i != data.length - 1) const SizedBox(height: AppSpacing.md),
                      ],
                    ],
                  );
                },
                loading: () => const LoadingState(),
                error: (error, _) => ErrorState(
                  message: error.toString(),
                  onRetry: () => ref.invalidate(recentHealthProvider),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}

class DietTab extends ConsumerStatefulWidget {
  final Function(int) onTabChange;

  const DietTab({super.key, required this.onTabChange});

  @override
  ConsumerState<DietTab> createState() => _DietTabState();
}

class _DietTabState extends ConsumerState<DietTab> {
  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.md, AppSpacing.lg, AppSpacing.navClearance),
      child: FoodScanWidget(
        title: 'Scan Food',
        subtitle: 'Capture a meal photo and get estimated amount, contents, calories, and nutrients.',
        scanFood: _scanFood,
      ),
    );
  }

  static Future<FoodScanResult> _scanFood(
    XFile image,
    String mealType,
    String? hint,
  ) async {
    final response = await ApiClient.scanFood(
      image: image,
      mealType: mealType,
      hint: hint,
    );
    return FoodScanResult.fromJson(response);
  }
}

class SleepTab extends ConsumerStatefulWidget {
  final Function(int) onTabChange;

  const SleepTab({super.key, required this.onTabChange});

  @override
  ConsumerState<SleepTab> createState() => _SleepTabState();
}

class _SleepTabState extends ConsumerState<SleepTab> {
  late TextEditingController _hoursController;
  late TextEditingController _minutesController;
  String _selectedQuality = 'good';

  @override
  void initState() {
    super.initState();
    _hoursController = TextEditingController();
    _minutesController = TextEditingController();
  }

  @override
  void dispose() {
    _hoursController.dispose();
    _minutesController.dispose();
    super.dispose();
  }

  void _logSleep() async {
    try {
      final hours = int.tryParse(_hoursController.text) ?? 0;
      final minutes = int.tryParse(_minutesController.text) ?? 0;
      final duration = Duration(hours: hours, minutes: minutes);

      await ApiClient.recordSleep(
            duration: duration,
            quality: _selectedQuality,
          );

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Sleep logged successfully')),
      );

      _hoursController.clear();
      _minutesController.clear();
      ref.invalidate(recentSleepProvider);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: ${e.toString()}')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.md, AppSpacing.lg, AppSpacing.navClearance),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Log Sleep', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: AppSpacing.lg),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: CustomTextField(
                        label: 'Hours',
                        hint: '8',
                        controller: _hoursController,
                        keyboardType: TextInputType.number,
                        prefixIcon: Icon(Icons.bedtime_outlined, color: primary),
                      ),
                    ),
                    const SizedBox(width: AppSpacing.lg),
                    Expanded(
                      child: CustomTextField(
                        label: 'Minutes',
                        hint: '0',
                        controller: _minutesController,
                        keyboardType: TextInputType.number,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.lg),
                Text(
                  'SLEEP QUALITY',
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.grey400, letterSpacing: 0.8),
                ),
                const SizedBox(height: AppSpacing.sm),
                DropdownButtonFormField<String>(
                  initialValue: _selectedQuality,
                  dropdownColor: AppColors.glassRaised,
                  borderRadius: BorderRadius.circular(14),
                  icon: const Icon(Icons.expand_more, color: AppColors.grey400),
                  items: ['poor', 'fair', 'good', 'excellent']
                      .map((quality) => DropdownMenuItem(
                            value: quality,
                            child: Text(quality.toUpperCase()),
                          ))
                      .toList(),
                  onChanged: (value) {
                    setState(() => _selectedQuality = value ?? 'good');
                  },
                ),
                const SizedBox(height: AppSpacing.xl),
                PrimaryButton(label: 'Log Sleep', onPressed: _logSleep),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.xxl),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text('Sleep History', style: Theme.of(context).textTheme.headlineSmall),
              Text(
                'RECENT',
                style: AppFonts.mono(
                  Theme.of(context).textTheme.labelSmall!.copyWith(color: primary, letterSpacing: 1.2),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Consumer(
            builder: (context, ref, _) {
              final recentAsync = ref.watch(recentSleepProvider);
              return recentAsync.when(
                data: (data) {
                  if (data.isEmpty) {
                    return EmptyState(
                      title: 'No sleep logged',
                      message: 'Start logging your sleep',
                      icon: Icons.bedtime,
                    );
                  }
                  return Column(
                    children: [
                      for (var i = 0; i < data.length; i++) ...[
                        _RecentMetricRow(
                          icon: Icons.bedtime,
                          iconColor: primary,
                          label: 'Sleep logged',
                          value: '${data[i].duration.inHours}h ${data[i].duration.inMinutes % 60}m',
                          subtitle: 'Quality: ${data[i].quality}',
                          time: _formatTime(data[i].recordedAt),
                          reversed: i.isOdd,
                        ),
                        if (i != data.length - 1) const SizedBox(height: AppSpacing.md),
                      ],
                    ],
                  );
                },
                loading: () => const LoadingState(),
                error: (error, _) => ErrorState(
                  message: error.toString(),
                  onRetry: () => ref.invalidate(recentSleepProvider),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}
