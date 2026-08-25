import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../models/models.dart';
import '../../services/api_client.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common_widgets.dart';
import '../../widgets/status_pill.dart';

/// Dashed glass picker well — approximates a dotted border with a
/// [CustomPainter] since no dotted-border package is available in
/// pubspec.yaml, per docs/stitch_design_prompt.md Section 8 (Body Scan).
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
  });

  final bool hasImage;
  final String? fileName;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;
    return GestureDetector(
      onTap: onTap,
      child: SizedBox(
        height: 240,
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
                    width: 64,
                    height: 64,
                    decoration: BoxDecoration(
                      color: primary.withValues(alpha: hasImage ? 0.22 : 0.12),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(hasImage ? Icons.check_circle : Icons.add_a_photo, color: primary, size: 30),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  Text(
                    hasImage ? 'Photo selected' : 'Tap to select image',
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

class BodyScanScreen extends StatefulWidget {
  const BodyScanScreen({super.key});

  @override
  State<BodyScanScreen> createState() => _BodyScanScreenState();
}

class _BodyScanScreenState extends State<BodyScanScreen> {
  final _picker = ImagePicker();
  final _bodyPartController = TextEditingController();

  XFile? _selectedImage;
  BodyScanResult? _result;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _bodyPartController.dispose();
    super.dispose();
  }

  Future<void> _pickImage() async {
    final image = await _picker.pickImage(
      source: ImageSource.gallery,
      imageQuality: 90,
      maxWidth: 1280,
      maxHeight: 1280,
    );

    if (image != null) {
      setState(() {
        _selectedImage = image;
        _result = null;
        _error = null;
      });
    }
  }

  Future<void> _analyze() async {
    if (_selectedImage == null) {
      setState(() => _error = 'Please choose an image first.');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
      _result = null;
    });

    try {
      final result = await ApiClient.analyzeBodyImage(
        imageFile: _selectedImage!,
        bodyPart: _bodyPartController.text,
      );
      setState(() => _result = result);
    } catch (e) {
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
      });
    } finally {
      setState(() => _loading = false);
    }
  }

  void _showDetails(BuildContext context) {
    final result = _result!;
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) => Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: AppCard(
          raised: true,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(result.mostLikelyCondition, style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: AppSpacing.sm),
              Text(result.summary, style: Theme.of(context).textTheme.bodyMedium),
              const SizedBox(height: AppSpacing.md),
              Text(result.recommendation, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.grey500)),
              const SizedBox(height: AppSpacing.md),
              Text(result.disclaimer, style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.grey500)),
            ],
          ),
        ),
      ),
    );
  }

  StatusPillTone _urgencyTone(String urgency) {
    final value = urgency.toLowerCase();
    if (value == 'moderate' || value == 'high') return StatusPillTone.error;
    if (value == 'review') return StatusPillTone.warning;
    return StatusPillTone.info;
  }

  @override
  Widget build(BuildContext context) {
    final primary = Theme.of(context).colorScheme.primary;
    return Scaffold(
      appBar: const CustomAppBar(title: 'Body Scan'),
      body: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.md, AppSpacing.lg, AppSpacing.navClearance),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Body Scan', style: Theme.of(context).textTheme.displaySmall),
            const SizedBox(height: AppSpacing.sm),
            Text(
              'Upload a photo of a skin or body concern for an instant AI-powered preliminary assessment. This is not a diagnosis.',
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: AppColors.grey500),
            ),
            const SizedBox(height: AppSpacing.xl),
            _GlassPickerWell(
              hasImage: _selectedImage != null,
              fileName: _selectedImage?.name,
              onTap: _pickImage,
            ),
            const SizedBox(height: AppSpacing.lg),
            CustomTextField(
              label: 'Body Part (optional)',
              hint: 'e.g. arm, leg, neck, hand',
              controller: _bodyPartController,
              prefixIcon: Icon(Icons.accessibility_new, color: primary),
            ),
            const SizedBox(height: AppSpacing.lg),
            PrimaryButton(
              label: 'Analyze Image',
              leadingIcon: Icons.document_scanner_outlined,
              isLoading: _loading,
              onPressed: _analyze,
            ),
            const SizedBox(height: AppSpacing.md),
            SecondaryButton(
              label: 'Choose from Library',
              onPressed: _pickImage,
            ),
            if (_error != null) ...[
              const SizedBox(height: AppSpacing.lg),
              ErrorState(
                message: _error!,
                onRetry: _analyze,
              ),
            ],
            if (_result != null) ...[
              const SizedBox(height: AppSpacing.xxl),
              Text('Recent Analysis', style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: AppSpacing.md),
              AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          flex: 2,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'CONDITION',
                                style: Theme.of(context)
                                    .textTheme
                                    .labelSmall
                                    ?.copyWith(color: AppColors.grey400, letterSpacing: 0.8),
                              ),
                              const SizedBox(height: 6),
                              Text(_result!.mostLikelyCondition, style: Theme.of(context).textTheme.headlineMedium),
                              if ((_result!.bodyPart ?? '').trim().isNotEmpty) ...[
                                const SizedBox(height: 4),
                                Text(
                                  '(${_result!.bodyPart})',
                                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.grey500),
                                ),
                              ],
                            ],
                          ),
                        ),
                        Expanded(
                          child: Align(
                            alignment: Alignment.topRight,
                            child: StatusPill(
                              label: _result!.urgencyLevel.toUpperCase(),
                              tone: _urgencyTone(_result!.urgencyLevel),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    const Divider(height: 1, color: AppColors.frostEdge),
                    const SizedBox(height: AppSpacing.lg),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Confidence Match',
                                style: Theme.of(context).textTheme.labelMedium?.copyWith(color: AppColors.grey500),
                              ),
                              const SizedBox(height: 6),
                              Row(
                                crossAxisAlignment: CrossAxisAlignment.baseline,
                                textBaseline: TextBaseline.alphabetic,
                                children: [
                                  Text(
                                    (_result!.confidence * 100).toStringAsFixed(1),
                                    style: AppFonts.mono(Theme.of(context).textTheme.displaySmall!),
                                  ),
                                  const SizedBox(width: 4),
                                  Text('%', style: TextStyle(color: primary, fontSize: 16, fontWeight: FontWeight.w600)),
                                ],
                              ),
                            ],
                          ),
                        ),
                        SizedBox(
                          width: 96,
                          height: 40,
                          child: OutlinedButton(
                            onPressed: () => _showDetails(context),
                            style: OutlinedButton.styleFrom(
                              side: const BorderSide(color: AppColors.frostEdgeTop),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                            ),
                            child: const Text('Details'),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    Text(_result!.summary, style: Theme.of(context).textTheme.bodyMedium),
                    const SizedBox(height: AppSpacing.sm),
                    Text(
                      _result!.recommendation,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.grey500),
                    ),
                  ],
                ),
              ),
              if (_result!.predictions.isNotEmpty) ...[
                const SizedBox(height: AppSpacing.xl),
                Text('Top Predictions', style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: AppSpacing.md),
                for (var i = 0; i < _result!.predictions.length; i++) ...[
                  _PredictionRow(prediction: _result!.predictions[i]),
                  if (i != _result!.predictions.length - 1) const SizedBox(height: AppSpacing.sm),
                ],
              ],
              const SizedBox(height: AppSpacing.xl),
              AppCard(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.info_outline, color: AppColors.grey400, size: 20),
                    const SizedBox(width: AppSpacing.md),
                    Expanded(
                      child: Text(
                        _result!.disclaimer,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.grey500),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Repeated prediction row — `AppCard(enableBlur: false)` per the perf note.
class _PredictionRow extends StatelessWidget {
  const _PredictionRow({required this.prediction});

  final ScanPrediction prediction;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      enableBlur: false,
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.md),
      child: Row(
        children: [
          Expanded(
            child: Text(prediction.label, style: Theme.of(context).textTheme.bodyMedium),
          ),
          Text(
            '${(prediction.confidence * 100).toStringAsFixed(1)}%',
            style: AppFonts.mono(
              Theme.of(context).textTheme.labelLarge!.copyWith(color: AppColors.grey500),
            ),
          ),
        ],
      ),
    );
  }
}
