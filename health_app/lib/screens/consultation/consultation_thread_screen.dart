import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../../models/models.dart';
import '../../providers/app_providers.dart';
import '../../services/api_client.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common_widgets.dart';

class ConsultationThreadScreen extends ConsumerStatefulWidget {
  const ConsultationThreadScreen({
    super.key,
    required this.ticket,
  });

  final ConsultationTicket ticket;

  @override
  ConsumerState<ConsultationThreadScreen> createState() => _ConsultationThreadScreenState();
}

class _ConsultationThreadScreenState extends ConsumerState<ConsultationThreadScreen> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<ConsultationMessageItem> _messages = [];

  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  bool _loadingHistory = true;
  bool _sending = false;
  // Set only when the socket drops *after* history has already loaded, so
  // the banner below never has to replace/hide the message list — that's
  // reserved for _error, the initial-history-fetch failure.
  bool _connectionLost = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadHistoryAndConnect();
  }

  @override
  void dispose() {
    _subscription?.cancel();
    _channel?.sink.close();
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadHistoryAndConnect() async {
    setState(() {
      _loadingHistory = true;
      _error = null;
    });

    try {
      final history = await ApiClient.getConsultationMessages(widget.ticket.id);
      if (!mounted) return;
      setState(() {
        _messages
          ..clear()
          ..addAll(history);
        _loadingHistory = false;
      });
      _connect();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loadingHistory = false;
        _error = e.toString();
      });
    }
  }

  void _connect() {
    final token = ApiClient.accessToken;
    if (token == null || token.isEmpty) {
      return;
    }

    // Close out any previous connection first — reconnecting without this
    // could leave the old socket alive alongside the new one, delivering
    // duplicate messages and leaking the old connection.
    _subscription?.cancel();
    _subscription = null;
    _channel?.sink.close();
    _channel = null;

    setState(() {
      _connectionLost = false;
    });

    try {
      _channel = ApiClient.consultationChannel(widget.ticket.id);
      _subscription = _channel?.stream.listen(
        (event) {
          final raw = event is String ? event : event.toString();
          final data = jsonDecode(raw) as Map<String, dynamic>;
          if (data['type'] != 'message') {
            return;
          }

          final incoming = ConsultationMessageItem.fromJson(data);
          if (!mounted) return;
          setState(() {
            _messages.add(incoming);
            _connectionLost = false;
          });
          _scrollToBottom();
        },
        onError: (Object error) {
          if (!mounted) return;
          setState(() {
            _connectionLost = true;
          });
        },
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _connectionLost = true;
      });
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) {
        return;
      }
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    });
  }

  Future<void> _sendMessage() async {
    if (_messageController.text.trim().isEmpty || _sending) {
      return;
    }

    final channel = _channel;
    if (channel == null) {
      // Not connected — sending would silently no-op via the null-aware
      // call below with no feedback. Tell the user instead of losing the
      // message with no trace.
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Not connected — try reconnecting first.')),
      );
      return;
    }

    final text = _messageController.text.trim();
    _messageController.clear();

    setState(() {
      _sending = true;
    });

    try {
      channel.sink.add(jsonEncode({'message': text}));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not send message: $e')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _sending = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final currentUser = authState.user;

    return Scaffold(
      appBar: CustomAppBar(title: 'Consultation #${widget.ticket.id}'),
      body: Column(
        children: [
          // Connection-lost banner sits ABOVE the history and never replaces
          // it — only shown once history has successfully loaded at least
          // once, so the list underneath is always still there.
          if (_connectionLost && !_loadingHistory && _error == null)
            _ConnectionLostBanner(onRetry: _connect),
          Expanded(
            child: _loadingHistory
                ? const LoadingState(message: 'Loading consultation...')
                : _error != null
                    ? ErrorState(
                        message: _error!,
                        onRetry: _loadHistoryAndConnect,
                      )
                    : _messages.isEmpty
                        ? const EmptyState(
                            title: 'No consultation messages yet',
                            message: 'Use the chat below to start the conversation.',
                            icon: Icons.chat_bubble_outline,
                          )
                        : ListView.builder(
                            controller: _scrollController,
                            padding: const EdgeInsets.all(AppSpacing.lg),
                            itemCount: _messages.length,
                            itemBuilder: (context, index) {
                              final item = _messages[index];
                              final isMine = currentUser != null && item.senderUserId == currentUser.id;
                              return _MessageBubble(item: item, isMine: isMine);
                            },
                          ),
          ),
          _Composer(
            controller: _messageController,
            sending: _sending,
            onSend: _sendMessage,
          ),
        ],
      ),
    );
  }
}

/// Inline glass banner (Alert Red tint) shown above the chat history when
/// the socket drops — distinct from [ErrorState], which is reserved for the
/// initial history-fetch failure where there's nothing yet to preserve.
class _ConnectionLostBanner extends StatelessWidget {
  const _ConnectionLostBanner({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      margin: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.lg, AppSpacing.lg, 0),
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.errorBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.error.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.wifi_off, color: AppColors.errorFg, size: 20),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Connection interrupted',
                  style: theme.textTheme.labelLarge?.copyWith(color: AppColors.errorFg),
                ),
                const SizedBox(height: 2),
                Text(
                  'Your message history is safe. Reconnect to keep chatting.',
                  style: theme.textTheme.bodySmall?.copyWith(color: AppColors.errorFg),
                ),
              ],
            ),
          ),
          TextButton(
            onPressed: onRetry,
            style: TextButton.styleFrom(foregroundColor: AppColors.errorFg),
            child: const Text('Reconnect'),
          ),
        ],
      ),
    );
  }
}

/// Repeated per-message in the thread, so blur is disabled per the shared
/// AppCard's perf guidance for densely-repeated list items. Sent messages
/// use the brighter `raised` glass fill to read as "mine" without hardcoding
/// an accent color; the accent only appears on the "You" label and timestamp.
class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.item, required this.isMine});

  final ConsultationMessageItem item;
  final bool isMine;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final primary = theme.colorScheme.primary;

    return Align(
      alignment: isMine ? Alignment.centerRight : Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.only(bottom: AppSpacing.md),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 320),
          child: AppCard(
            enableBlur: false,
            raised: isMine,
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isMine ? 'You' : 'Them',
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: isMine ? primary : AppColors.grey500,
                  ),
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(item.message, style: theme.textTheme.bodyMedium),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  _formatTime(item.createdAt),
                  style: AppFonts.mono(
                    theme.textTheme.labelSmall!.copyWith(color: AppColors.grey500),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  static String _formatTime(DateTime dateTime) {
    final local = dateTime.toLocal();
    final hour24 = local.hour;
    final hour12 = hour24 % 12 == 0 ? 12 : hour24 % 12;
    final minute = local.minute.toString().padLeft(2, '0');
    final period = hour24 >= 12 ? 'PM' : 'AM';
    return '$hour12:$minute $period';
  }
}

/// Sticky glass composer bar with a mono-icon send button, per spec.
class _Composer extends StatelessWidget {
  const _Composer({
    required this.controller,
    required this.sending,
    required this.onSend,
  });

  final TextEditingController controller;
  final bool sending;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: const BoxDecoration(
        color: AppColors.glassPanel,
        border: Border(top: BorderSide(color: AppColors.frostEdge)),
      ),
      child: SafeArea(
        top: false,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: TextField(
                controller: controller,
                decoration: const InputDecoration(hintText: 'Type a message...'),
                textInputAction: TextInputAction.send,
                minLines: 1,
                maxLines: 4,
                onSubmitted: (_) => onSend(),
              ),
            ),
            const SizedBox(width: AppSpacing.md),
            SizedBox(
              height: 52,
              width: 52,
              child: ElevatedButton(
                onPressed: sending ? null : onSend,
                style: ElevatedButton.styleFrom(
                  shape: const CircleBorder(),
                  padding: EdgeInsets.zero,
                ),
                child: sending
                    ? SizedBox(
                        height: 18,
                        width: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Theme.of(context).elevatedButtonTheme.style?.foregroundColor?.resolve({}) ?? AppColors.white,
                        ),
                      )
                    : const Icon(Icons.send_rounded),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
