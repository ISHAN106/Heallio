import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/models.dart';
import '../../services/api_client.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common_widgets.dart';
import '../../providers/app_providers.dart';
import '../consultation/consultation_screen.dart';

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({
    super.key,
    this.initialMessage,
  });

  final String? initialMessage;

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  late TextEditingController _messageController;
  late ScrollController _scrollController;
  bool? _hasConsent;
  bool _isSending = false;
  ConsultationSuggestion? _activeSuggestion;
  bool _suggestionDismissed = false;
  bool _creatingConsultation = false;

  @override
  void initState() {
    super.initState();
    _messageController = TextEditingController();
    _scrollController = ScrollController();
    if (widget.initialMessage != null && widget.initialMessage!.trim().isNotEmpty) {
      _messageController.text = widget.initialMessage!.trim();
    }
    _checkConsent();
  }

  @override
  void didUpdateWidget(covariant ChatScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    final nextMessage = widget.initialMessage?.trim();
    if (nextMessage != null && nextMessage.isNotEmpty && nextMessage != oldWidget.initialMessage?.trim()) {
      _messageController.text = nextMessage;
      _messageController.selection = TextSelection.collapsed(offset: nextMessage.length);
    }
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _checkConsent() async {
    try {
      final consent = await ref.read(consentProvider.future);
      if (!mounted) return;
      setState(() => _hasConsent = consent.consentGiven);
    } catch (e) {
      if (!mounted) return;
      setState(() => _hasConsent = false);
    }
  }

  void _grantConsent() async {
    try {
      await ref.read(grantConsentProvider.future);
      if (!mounted) return;
      setState(() => _hasConsent = true);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Consent granted! You can now use the chat.')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: ${e.toString()}')),
      );
    }
  }

  void _sendMessage() async {
    if (_messageController.text.trim().isEmpty || _isSending) return;

    final message = _messageController.text.trim();
    _messageController.clear();

    setState(() {
      _isSending = true;
      _activeSuggestion = null;
      _suggestionDismissed = false;
    });

    try {
      final sentMessage = await ref.read(sendMessageProvider(message).future);
      if (mounted) {
        setState(() {
          _activeSuggestion = sentMessage.consultationSuggestion;
        });
      }
      if (sentMessage.escalated && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'A doctor consultation has been opened${sentMessage.consultationTicketId != null ? ' (#${sentMessage.consultationTicketId})' : ''}.',
            ),
          ),
        );
      }
      ref.invalidate(chatMessagesProvider);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: ${e.toString()}')),
      );
    } finally {
      if (mounted) {
        setState(() => _isSending = false);
      }
    }

    // Scroll to bottom
    Future.delayed(const Duration(milliseconds: 100), () {
      if (!_scrollController.hasClients) return;
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    });
  }

  Future<void> _acceptConsultationSuggestion(ConsultationSuggestion suggestion) async {
    setState(() => _creatingConsultation = true);
    try {
      final ticket = await ApiClient.createManualConsultation(
        reason: suggestion.reason,
        categoryName: suggestion.categoryName,
      );
      ref.invalidate(myConsultationsProvider);
      if (!mounted) return;
      setState(() => _activeSuggestion = null);
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => ConsultationScreen(ticket: ticket),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not start a consultation: $e')),
      );
    } finally {
      if (mounted) {
        setState(() => _creatingConsultation = false);
      }
    }
  }

  void _dismissConsultationSuggestion() {
    setState(() => _suggestionDismissed = true);
  }

  void _sendStarterPrompt(String prompt) {
    _messageController.text = prompt;
    _sendMessage();
  }

  @override
  Widget build(BuildContext context) {
    ref.watch(consentProvider);
    final chatAsync = ref.watch(chatMessagesProvider);
    final primary = Theme.of(context).colorScheme.primary;

    return Scaffold(
      appBar: const CustomAppBar(title: 'Health Assistant'),
      body: Column(
        children: [
          // Consent banner
          if (_hasConsent == false) _ConsentBanner(onGrant: _grantConsent),
          // Persistent clinical disclaimer (heallio_ai.html) — distinct from
          // the one-time consent gate above; shown for the life of the chat.
          if (_hasConsent == true) const _ClinicalDisclaimerBanner(),

          // Chat messages
          Expanded(
            child: chatAsync.when(
              data: (messages) {
                final sortedMessages = [...messages]
                  ..sort((a, b) => a.timestamp.compareTo(b.timestamp));

                if (messages.isEmpty && _hasConsent != true) {
                  return EmptyState(
                    title: 'Chat with Health Assistant',
                    message: 'Grant consent to start chatting about your health',
                    icon: Icons.chat_outlined,
                  );
                }

                if (messages.isEmpty) {
                  return EmptyState(
                    title: 'No messages yet',
                    message: 'Start a conversation with your AI health assistant',
                    icon: Icons.chat_outlined,
                  );
                }

                final itemCount = sortedMessages.length + (_isSending ? 1 : 0);

                return ListView.separated(
                  controller: _scrollController,
                  padding: const EdgeInsets.all(AppSpacing.lg),
                  itemCount: itemCount,
                  separatorBuilder: (_, _) => const SizedBox(height: AppSpacing.lg),
                  itemBuilder: (context, index) {
                    if (index >= sortedMessages.length) {
                      return const _TypingBubble();
                    }

                    final message = sortedMessages[index];
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // User message
                        Align(
                          alignment: Alignment.centerRight,
                          child: ConstrainedBox(
                            constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.82),
                            child: _ChatBubble(
                              color: primary.withValues(alpha: 0.18),
                              child: Text(
                                message.message,
                                style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.grey900),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        // AI response
                        Align(
                          alignment: Alignment.centerLeft,
                          child: ConstrainedBox(
                            constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.85),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const _AiAvatar(),
                                const SizedBox(width: AppSpacing.sm),
                                Flexible(
                                  child: _ChatBubble(
                              color: AppColors.glassPanel,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(
                                    message.response,
                                    style: Theme.of(context).textTheme.bodyMedium,
                                  ),
                                  if (message.suggestedActions != null &&
                                      message.suggestedActions!.isNotEmpty) ...[
                                    const SizedBox(height: AppSpacing.md),
                                    Wrap(
                                      spacing: AppSpacing.sm,
                                      runSpacing: AppSpacing.sm,
                                      children: message.suggestedActions!
                                          .map(
                                            (action) => ActionChip(
                                              label: Text(action),
                                              backgroundColor: primary.withValues(alpha: 0.08),
                                              side: BorderSide(color: primary.withValues(alpha: 0.25)),
                                              labelStyle:
                                                  Theme.of(context).textTheme.labelMedium?.copyWith(color: primary),
                                              onPressed: () {
                                                _messageController.text = action;
                                                _sendMessage();
                                              },
                                            ),
                                          )
                                          .toList(),
                                    ),
                                  ],
                                  if (message.metricsImplicated != null) ...[
                                    const SizedBox(height: AppSpacing.md),
                                    _MetricsImplicatedCard(context: message.metricsImplicated!),
                                  ],
                                ],
                              ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        if (index == sortedMessages.length - 1 &&
                            _activeSuggestion != null &&
                            !_suggestionDismissed) ...[
                          const SizedBox(height: AppSpacing.md),
                          Align(
                            alignment: Alignment.centerLeft,
                            child: ConstrainedBox(
                              constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.85),
                              child: AppCard(
                                raised: true,
                                enableBlur: false,
                                padding: const EdgeInsets.all(AppSpacing.lg),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Row(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Icon(Icons.medical_services_outlined, color: primary, size: 18),
                                        const SizedBox(width: AppSpacing.sm),
                                        Expanded(
                                          child: Text(
                                            'This sounds like something worth discussing with a doctor.',
                                            style: Theme.of(context).textTheme.bodyMedium,
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: AppSpacing.md),
                                    Row(
                                      children: [
                                        Expanded(
                                          child: PrimaryButton(
                                            label: 'Consult a doctor',
                                            isLoading: _creatingConsultation,
                                            onPressed: () => _acceptConsultationSuggestion(_activeSuggestion!),
                                          ),
                                        ),
                                        const SizedBox(width: AppSpacing.sm),
                                        GhostButton(
                                          label: 'Not now',
                                          isEnabled: !_creatingConsultation,
                                          onPressed: _dismissConsultationSuggestion,
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ],
                      ],
                    );
                  },
                );
              },
              loading: () => const LoadingState(message: 'Loading chat...'),
              error: (error, _) => ErrorState(
                message: error.toString(),
                onRetry: () => ref.refresh(chatMessagesProvider),
              ),
            ),
          ),

          // Starter-prompt chips — a persistent entry point above the
          // composer, per the mockup, so a new conversation doesn't require
          // typing from scratch.
          if (_hasConsent == true)
            Padding(
              padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, AppSpacing.sm),
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    for (final prompt in const [
                      'Explain my vitals',
                      'Daily summary',
                      'Sleep tips',
                    ])
                      Padding(
                        padding: const EdgeInsets.only(right: AppSpacing.sm),
                        child: ActionChip(
                          label: Text(prompt),
                          backgroundColor: primary.withValues(alpha: 0.08),
                          side: BorderSide(color: primary.withValues(alpha: 0.25)),
                          labelStyle: Theme.of(context).textTheme.labelMedium?.copyWith(color: primary),
                          onPressed: _isSending ? null : () => _sendStarterPrompt(prompt),
                        ),
                      ),
                  ],
                ),
              ),
            ),

          // Composer bar
          if (_hasConsent == true)
            Padding(
              padding: const EdgeInsets.fromLTRB(AppSpacing.lg, 0, AppSpacing.lg, AppSpacing.navClearance),
              child: AppCard(
                raised: true,
                padding: const EdgeInsets.all(AppSpacing.sm),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    IconButton(
                      icon: const Icon(Icons.add),
                      color: AppColors.grey400,
                      tooltip: 'Attach',
                      onPressed: () {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Attachments are coming soon.')),
                        );
                      },
                    ),
                    Expanded(
                      child: TextField(
                        controller: _messageController,
                        minLines: 1,
                        maxLines: 5,
                        style: Theme.of(context).textTheme.bodyLarge,
                        decoration: InputDecoration(
                          hintText: 'Ask about your health data...',
                          filled: true,
                          fillColor: Colors.black.withValues(alpha: 0.18),
                          contentPadding:
                              const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.md),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(16),
                            borderSide: BorderSide.none,
                          ),
                          enabledBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(16),
                            borderSide: BorderSide.none,
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(16),
                            borderSide: BorderSide(color: primary, width: 1.5),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    _SendButton(isSending: _isSending, onPressed: _isSending ? null : _sendMessage),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// Warning-toned glass consent banner — the single "consent banner variant"
/// called for in Section 8. The banner tint communicates the semantic state
/// (Caution Amber); the CTA stays the app's one Signal Blue [PrimaryButton]
/// per the "max one accent per screen" rule.
/// Real recent-health averages implicated in a risk-flagged reply — the same
/// sleep/calorie context the backend's risk evaluator already computed
/// (see app/services/escalation.py::evaluate_chat_risk), not fabricated
/// vitals. Only rendered when the backend actually returns it.
class _MetricsImplicatedCard extends StatelessWidget {
  const _MetricsImplicatedCard({required this.context});

  final ChatMetricsContext context;

  @override
  Widget build(BuildContext buildContext) {
    final chips = <String>[
      if (context.avgSleepHours != null) 'Sleep avg: ${context.avgSleepHours!.toStringAsFixed(1)}h',
      if (context.avgCalories != null) 'Calories avg: ${context.avgCalories!.toStringAsFixed(0)}',
    ];
    if (chips.isEmpty) return const SizedBox.shrink();

    return AppCard(
      enableBlur: false,
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'METRICS IMPLICATED',
            style: Theme.of(buildContext).textTheme.labelSmall?.copyWith(color: AppColors.grey400, letterSpacing: 0.8),
          ),
          const SizedBox(height: AppSpacing.sm),
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            children: chips
                .map(
                  (chip) => Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: AppColors.glassWell,
                      borderRadius: BorderRadius.circular(999),
                      border: Border.all(color: AppColors.frostEdge),
                    ),
                    child: Text(chip, style: AppFonts.mono(Theme.of(buildContext).textTheme.labelSmall!)),
                  ),
                )
                .toList(),
          ),
        ],
      ),
    );
  }
}

/// Small circular avatar shown next to each AI reply (heallio_ai.html).
class _AiAvatar extends StatelessWidget {
  const _AiAvatar();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 32,
      height: 32,
      decoration: BoxDecoration(
        color: AppColors.surfaceRaised,
        shape: BoxShape.circle,
        border: Border.all(color: AppColors.frostEdge),
      ),
      child: const Icon(Icons.psychology_outlined, color: AppColors.grey400, size: 18),
    );
  }
}

/// Persistent clinical-disclaimer banner (heallio_ai.html) — separate from
/// the one-time privacy-consent gate, shown for the life of the chat once
/// consent is granted.
class _ClinicalDisclaimerBanner extends StatelessWidget {
  const _ClinicalDisclaimerBanner();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.lg),
      color: AppColors.errorBg.withValues(alpha: 0.5),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.info_outline, color: AppColors.errorFg, size: 20),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: RichText(
              text: TextSpan(
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.grey600),
                children: [
                  TextSpan(
                    text: 'Clinical Disclaimer\n',
                    style: Theme.of(context).textTheme.labelMedium?.copyWith(color: AppColors.grey900),
                  ),
                  const TextSpan(
                    text: 'AI insights are for information only. Always consult a healthcare professional for medical advice.',
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ConsentBanner extends StatelessWidget {
  const _ConsentBanner({required this.onGrant});

  final VoidCallback onGrant;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: const BoxDecoration(
        color: AppColors.warningBg,
        border: Border(bottom: BorderSide(color: Color(0x4DFBBF24))),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.info_outline, color: AppColors.warningFg, size: 20),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Text(
                  'Grant consent to start chatting with your AI health assistant.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: AppColors.warningFg),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          PrimaryButton(label: 'Grant Consent', onPressed: onGrant),
        ],
      ),
    );
  }
}

/// Lightweight glass container mirroring [AppCard]'s frost-edge visual
/// language (24px→20px radius, hairline border, resting shadow) but with a
/// caller-supplied fill so user bubbles can be accent-tinted while AI
/// bubbles stay neutral — something the shared [AppCard] can't do since its
/// fill is fixed to the two glassPanel/glassRaised tokens. Deliberately
/// never wraps in `BackdropFilter`: this is the highest-frequency repeated
/// surface in the app (WebSocket/stream-driven chat list), so it follows
/// the `enableBlur: false` perf rule by construction.
class _ChatBubble extends StatelessWidget {
  const _ChatBubble({required this.child, required this.color});

  final Widget child;
  final Color color;

  @override
  Widget build(BuildContext context) {
    // Uniform border — a per-side color (brighter top edge) can't be
    // combined with borderRadius (Flutter's Border.paint throws). See
    // AppCard's doc comment in common_widgets.dart.
    return Stack(
      children: [
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: AppColors.frostEdge, width: 1),
            boxShadow: AppShadows.resting,
          ),
          child: child,
        ),
        Positioned(
          top: 1,
          left: 14,
          right: 14,
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
    );
  }
}

/// Three-dot shimmer inside a glass bubble — the spec's prescribed AI
/// "typing" state (Section 6: Motion & Interaction).
class _TypingBubble extends StatefulWidget {
  const _TypingBubble();

  @override
  State<_TypingBubble> createState() => _TypingBubbleState();
}

class _TypingBubbleState extends State<_TypingBubble> with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1200),
  )..repeat();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: _ChatBubble(
        color: AppColors.glassPanel,
        child: AnimatedBuilder(
          animation: _controller,
          builder: (context, _) {
            return Row(
              mainAxisSize: MainAxisSize.min,
              children: List.generate(3, (i) {
                final phase = (_controller.value + (i * 0.2)) % 1.0;
                final opacity = (0.3 + 0.7 * (1 - (phase - 0.5).abs() * 2)).clamp(0.3, 1.0);
                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 2),
                  child: Opacity(
                    opacity: opacity,
                    child: Container(
                      width: 6,
                      height: 6,
                      decoration: const BoxDecoration(color: AppColors.grey400, shape: BoxShape.circle),
                    ),
                  ),
                );
              }),
            );
          },
        ),
      ),
    );
  }
}

class _SendButton extends StatelessWidget {
  const _SendButton({required this.isSending, required this.onPressed});

  final bool isSending;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final primary = theme.colorScheme.primary;
    final onPrimary = theme.elevatedButtonTheme.style?.foregroundColor?.resolve({}) ?? AppColors.white;
    return Material(
      color: primary,
      shape: const CircleBorder(),
      child: InkWell(
        customBorder: const CircleBorder(),
        onTap: onPressed,
        child: SizedBox(
          width: 44,
          height: 44,
          child: Center(
            child: isSending
                ? SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(onPrimary),
                    ),
                  )
                : Icon(Icons.send_rounded, color: onPrimary, size: 20),
          ),
        ),
      ),
    );
  }
}
