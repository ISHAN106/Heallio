import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../models/models.dart';
import '../theme/app_theme.dart';
import 'common_widgets.dart';
import 'status_pill.dart';

class FoodScanResult {
  final String mealType;
  final String foodName;
  final String amount;
  final String servingSize;
  final double confidence;
  final int calories;
  final int carbs;
  final int protein;
  final int fat;
  final int fiber;
  final int sugar;
  final Map<String, String> micronutrients;
  final List<String> contents;
  final String notes;
  final DateTime scannedAt;
  final String? modelVersion;
  final double? trainingAccuracy;
  final List<Map<String, dynamic>> predictions;

  const FoodScanResult({
    required this.mealType,
    required this.foodName,
    required this.amount,
    required this.servingSize,
    required this.confidence,
    required this.calories,
    required this.carbs,
    required this.protein,
    required this.fat,
    required this.fiber,
    required this.sugar,
    required this.micronutrients,
    required this.contents,
    required this.notes,
    required this.scannedAt,
    this.modelVersion,
    this.trainingAccuracy,
    this.predictions = const [],
  });

  factory FoodScanResult.fromJson(Map<String, dynamic> json) {
    final micronutrients = <String, String>{};
    final rawMicronutrients = json['micronutrients'];
    if (rawMicronutrients is List) {
      for (final item in rawMicronutrients) {
        if (item is Map<String, dynamic>) {
          final name = item['name']?.toString().trim() ?? '';
          final amount = item['amount']?.toString().trim() ?? '';
          if (name.isNotEmpty) {
            micronutrients[name] = amount;
          }
        }
      }
    } else if (rawMicronutrients is Map<String, dynamic>) {
      rawMicronutrients.forEach((key, value) {
        micronutrients[key.toString()] = value.toString();
      });
    }

    final predictions = <Map<String, dynamic>>[];
    final rawPredictions = json['predictions'];
    if (rawPredictions is List) {
      for (final item in rawPredictions) {
        if (item is Map<String, dynamic>) {
          predictions.add(item);
        }
      }
    }

    return FoodScanResult(
      mealType: (json['meal_type'] ?? 'breakfast').toString(),
      foodName: (json['predicted_food'] ?? json['food_name'] ?? '').toString(),
      amount: (json['amount'] ?? '').toString(),
      servingSize: (json['serving_size'] ?? '').toString(),
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
      calories: (json['calories'] as num?)?.toInt() ?? 0,
      carbs: (json['carbs'] as num?)?.toInt() ?? 0,
      protein: (json['protein'] as num?)?.toInt() ?? 0,
      fat: (json['fat'] as num?)?.toInt() ?? 0,
      fiber: (json['fiber'] as num?)?.toInt() ?? 0,
      sugar: (json['sugar'] as num?)?.toInt() ?? 0,
      micronutrients: micronutrients,
      contents: (json['contents'] as List<dynamic>? ?? []).map((item) => item.toString()).toList(),
      notes: (json['notes'] ?? '').toString(),
      scannedAt: tryParseUtc((json['scanned_at'] ?? '').toString()) ?? DateTime.now(),
      modelVersion: json['model_version']?.toString(),
      trainingAccuracy: (json['training_accuracy'] as num?)?.toDouble(),
      predictions: predictions,
    );
  }
}

/// Dashed glass picker well — approximates a dotted border with a
/// [CustomPainter] since no dotted-border package is available in
/// pubspec.yaml, per docs/stitch_design_prompt.md Section 8 (Body Scan /
/// image-picker screens).
class _DashedRRectPainter extends CustomPainter {
  const _DashedRRectPainter({required this.color});

  static const double radius = 24;
  static const double dashWidth = 8;
  static const double gapWidth = 6;

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Rect.fromLTWH(1, 1, size.width - 2, size.height - 2);
    final rrect = RRect.fromRectAndRadius(rect, const Radius.circular(radius));
    final path = Path()..addRRect(rrect);
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;

    for (final metric in path.computeMetrics()) {
      var distance = 0.0;
      while (distance < metric.length) {
        final next = (distance + dashWidth).clamp(0.0, metric.length);
        canvas.drawPath(metric.extractPath(distance, next), paint);
        distance = next + gapWidth;
      }
    }
  }

  @override
  bool shouldRepaint(covariant _DashedRRectPainter oldDelegate) => oldDelegate.color != color;
}

class _GlassPickerWell extends StatelessWidget {
  const _GlassPickerWell({
    required this.hasImage,
    required this.fileName,
    required this.onTap,
    required this.icon,
    required this.label,
  });

  final bool hasImage;
  final String? fileName;
  final VoidCallback onTap;
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;
    return GestureDetector(
      onTap: onTap,
      child: SizedBox(
        height: 200,
        width: double.infinity,
        child: CustomPaint(
          painter: const _DashedRRectPainter(color: AppColors.frostEdgeTop),
          child: Container(
            decoration: BoxDecoration(
              color: AppColors.glassWell,
              borderRadius: BorderRadius.circular(24),
            ),
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 56,
                    height: 56,
                    decoration: BoxDecoration(
                      color: primary.withValues(alpha: hasImage ? 0.22 : 0.12),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(hasImage ? Icons.check_circle : icon, color: primary, size: 26),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  Text(
                    hasImage ? 'Photo selected' : label,
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    hasImage ? (fileName ?? '') : 'JPG, PNG, HEIC',
                    style: AppFonts.mono(
                      Theme.of(context).textTheme.labelSmall!.copyWith(color: AppColors.grey400),
                    ),
                    overflow: TextOverflow.ellipsis,
                    maxLines: 1,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class FoodScanWidget extends StatefulWidget {
  const FoodScanWidget({
    super.key,
    this.title = 'Food Scan',
    this.subtitle = 'Scan a food photo to estimate portion, ingredients, and nutrition.',
    required this.scanFood,
    this.onSaveScan,
  });

  final String title;
  final String subtitle;
  final Future<FoodScanResult> Function(XFile image, String mealType, String? hint) scanFood;
  final Future<void> Function(FoodScanResult result)? onSaveScan;

  @override
  State<FoodScanWidget> createState() => _FoodScanWidgetState();
}

class _FoodScanWidgetState extends State<FoodScanWidget> {
  final ImagePicker _picker = ImagePicker();
  final TextEditingController _hintController = TextEditingController();

  XFile? _selectedImage;
  FoodScanResult? _result;
  bool _scanning = false;
  bool _saving = false;
  String? _error;
  String _mealType = 'breakfast';
  final List<FoodScanResult> _history = [];

  @override
  void dispose() {
    _hintController.dispose();
    super.dispose();
  }

  Future<void> _pickImage(ImageSource source) async {
    final image = await _picker.pickImage(
      source: source,
      imageQuality: 90,
      maxWidth: 1280,
      maxHeight: 1280,
    );

    if (image == null) return;

    setState(() {
      _selectedImage = image;
      _result = null;
      _error = null;
    });
  }

  Future<void> _scanFood() async {
    if (_selectedImage == null) {
      setState(() => _error = 'Please choose a food photo first.');
      return;
    }

    setState(() {
      _scanning = true;
      _error = null;
      _result = null;
    });

    try {
      final result = await widget.scanFood(_selectedImage!, _mealType, _hintController.text.trim());
      setState(() {
        _result = result;
        _history.insert(0, result);
      });
    } catch (e) {
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
      });
    } finally {
      if (mounted) {
        setState(() => _scanning = false);
      }
    }
  }

  Future<void> _saveScan() async {
    if (_result == null || widget.onSaveScan == null) return;

    setState(() => _saving = true);
    try {
      await widget.onSaveScan!(_result!);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Food scan saved')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Save failed: ${e.toString()}')),
      );
    } finally {
      if (mounted) {
        setState(() => _saving = false);
      }
    }
  }

  StatusPillTone _confidenceTone(double confidence) {
    if (confidence >= 0.8) return StatusPillTone.success;
    if (confidence >= 0.6) return StatusPillTone.warning;
    return StatusPillTone.error;
  }

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;

    return LayoutBuilder(
      builder: (context, constraints) {
        final tileWidth = (constraints.maxWidth - 12) / 2;

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(widget.title, style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: AppSpacing.sm),
            Text(
              widget.subtitle,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.grey500),
            ),
            const SizedBox(height: AppSpacing.lg),
            _GlassPickerWell(
              hasImage: _selectedImage != null,
              fileName: _selectedImage?.name,
              icon: Icons.add_a_photo,
              label: 'Tap to select a meal photo',
              onTap: () => _pickImage(ImageSource.gallery),
            ),
            const SizedBox(height: AppSpacing.md),
            Row(
              children: [
                Expanded(
                  child: SecondaryButton(
                    label: 'Gallery',
                    icon: Icons.photo_library_outlined,
                    onPressed: () => _pickImage(ImageSource.gallery),
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: SecondaryButton(
                    label: 'Camera',
                    icon: Icons.photo_camera_outlined,
                    onPressed: () => _pickImage(ImageSource.camera),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.lg),
            CustomTextField(
              label: 'Food hint (optional)',
              hint: 'e.g. pizza, salad, rice bowl',
              controller: _hintController,
              prefixIcon: Icon(Icons.search, color: primary),
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(
              'MEAL TYPE',
              style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.grey400, letterSpacing: 0.8),
            ),
            const SizedBox(height: AppSpacing.sm),
            DropdownButtonFormField<String>(
              initialValue: _mealType,
              dropdownColor: AppColors.glassRaised,
              borderRadius: BorderRadius.circular(14),
              icon: const Icon(Icons.expand_more, color: AppColors.grey400),
              items: const [
                DropdownMenuItem(value: 'breakfast', child: Text('Breakfast')),
                DropdownMenuItem(value: 'lunch', child: Text('Lunch')),
                DropdownMenuItem(value: 'dinner', child: Text('Dinner')),
                DropdownMenuItem(value: 'snack', child: Text('Snack')),
              ],
              onChanged: (value) {
                setState(() {
                  _mealType = value ?? 'breakfast';
                });
              },
            ),
            const SizedBox(height: AppSpacing.xl),
            PrimaryButton(
              label: _scanning ? 'Scanning...' : 'Scan Food',
              isLoading: _scanning,
              onPressed: _scanFood,
            ),
            if (_error != null) ...[
              const SizedBox(height: AppSpacing.lg),
              ErrorState(
                message: _error!,
                onRetry: _scanFood,
              ),
            ],
            if (_result != null) ...[
              const SizedBox(height: AppSpacing.xl),
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: primary.withValues(alpha: 0.14),
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: Icon(Icons.restaurant, color: primary),
                        ),
                        const SizedBox(width: AppSpacing.md),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(_result!.foodName, style: Theme.of(context).textTheme.headlineSmall),
                              const SizedBox(height: 4),
                              Text(
                                '${_result!.amount} · ${_result!.servingSize}',
                                style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.grey500),
                              ),
                            ],
                          ),
                        ),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(
                              '${(_result!.confidence * 100).toStringAsFixed(0)}%',
                              style: AppFonts.mono(Theme.of(context).textTheme.titleLarge!),
                            ),
                            const SizedBox(height: 4),
                            StatusPill(
                              label: 'MATCH',
                              tone: _confidenceTone(_result!.confidence),
                            ),
                          ],
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    Text('Contents', style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: AppSpacing.sm),
                    Wrap(
                      spacing: AppSpacing.sm,
                      runSpacing: AppSpacing.sm,
                      children:
                          _result!.contents.map((content) => StatusPill(label: content, tone: StatusPillTone.neutral)).toList(),
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    Text('Nutrition Facts', style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: AppSpacing.md),
                    Wrap(
                      spacing: AppSpacing.md,
                      runSpacing: AppSpacing.md,
                      children: [
                        SizedBox(width: tileWidth, child: StatCard(label: 'Calories', value: '${_result!.calories}', unit: 'kcal')),
                        SizedBox(width: tileWidth, child: StatCard(label: 'Carbs', value: '${_result!.carbs}', unit: 'g')),
                        SizedBox(width: tileWidth, child: StatCard(label: 'Protein', value: '${_result!.protein}', unit: 'g')),
                        SizedBox(width: tileWidth, child: StatCard(label: 'Fat', value: '${_result!.fat}', unit: 'g')),
                        SizedBox(width: tileWidth, child: StatCard(label: 'Fiber', value: '${_result!.fiber}', unit: 'g')),
                        SizedBox(width: tileWidth, child: StatCard(label: 'Sugar', value: '${_result!.sugar}', unit: 'g')),
                      ],
                    ),
                    if (_result!.micronutrients.isNotEmpty) ...[
                      const SizedBox(height: AppSpacing.lg),
                      Text('Micronutrients', style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: AppSpacing.sm),
                      Wrap(
                        spacing: AppSpacing.sm,
                        runSpacing: AppSpacing.sm,
                        children: _result!.micronutrients.entries
                            .map((entry) => StatusPill(label: '${entry.key}: ${entry.value}', tone: StatusPillTone.info))
                            .toList(),
                      ),
                    ],
                    if (_result!.notes.trim().isNotEmpty) ...[
                      const SizedBox(height: AppSpacing.lg),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(AppSpacing.md),
                        decoration: BoxDecoration(
                          color: AppColors.glassWell,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: AppColors.frostEdge),
                        ),
                        child: Text(_result!.notes, style: Theme.of(context).textTheme.bodySmall),
                      ),
                    ],
                    const SizedBox(height: AppSpacing.md),
                    Text(
                      'Scanned at ${_formatTime(_result!.scannedAt)}',
                      style: AppFonts.mono(
                        Theme.of(context).textTheme.labelSmall!.copyWith(color: AppColors.grey500),
                      ),
                    ),
                    if (_result!.modelVersion != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        'Model ${_result!.modelVersion}${_result!.trainingAccuracy == null ? '' : ' · ${(_result!.trainingAccuracy! * 100).toStringAsFixed(1)}% train accuracy'}',
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(color: AppColors.grey500),
                      ),
                    ],
                    if (widget.onSaveScan != null) ...[
                      const SizedBox(height: AppSpacing.lg),
                      PrimaryButton(
                        label: _saving ? 'Saving...' : 'Save Scan',
                        isLoading: _saving,
                        onPressed: _saveScan,
                      ),
                    ],
                  ],
                ),
              ),
            ],
            if (_history.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.xxl),
              Text('Recent Scans', style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: AppSpacing.md),
              for (var i = 0; i < _history.take(5).length; i++) ...[
                _RecentScanRow(result: _history[i]),
                if (i != _history.take(5).length - 1) const SizedBox(height: AppSpacing.sm),
              ],
            ],
          ],
        );
      },
    );
  }
}

String _formatTime(DateTime dateTime) {
  final hour = dateTime.hour.toString().padLeft(2, '0');
  final minute = dateTime.minute.toString().padLeft(2, '0');
  return '$hour:$minute';
}

/// Repeated history row — `AppCard(enableBlur: false)` per the perf note:
/// this list can grow as scans accumulate.
class _RecentScanRow extends StatelessWidget {
  const _RecentScanRow({required this.result});

  final FoodScanResult result;

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;
    return AppCard(
      enableBlur: false,
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(color: primary.withValues(alpha: 0.14), shape: BoxShape.circle),
            child: Icon(Icons.restaurant, size: 18, color: primary),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(result.foodName, style: Theme.of(context).textTheme.titleSmall, overflow: TextOverflow.ellipsis),
                const SizedBox(height: 2),
                Text(
                  '${result.amount} · ${result.calories} kcal',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.grey500),
                ),
              ],
            ),
          ),
          Text(
            '${(result.confidence * 100).toStringAsFixed(0)}%',
            style: AppFonts.mono(
              Theme.of(context).textTheme.labelLarge!.copyWith(color: primary, fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
    );
  }
}
