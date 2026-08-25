import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/app_providers.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common_widgets.dart';
import '../../widgets/prescription_card.dart';
import '../chat/chat_screen.dart';

class PrescriptionsScreen extends ConsumerWidget {
  const PrescriptionsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final prescriptionsAsync = ref.watch(myPrescriptionsProvider);

    return Scaffold(
      appBar: const CustomAppBar(title: 'My Prescriptions'),
      body: prescriptionsAsync.when(
        data: (prescriptions) {
          if (prescriptions.isEmpty) {
            return EmptyState(
              title: 'No prescriptions yet',
              message: 'Prescriptions a doctor issues during a consultation will show up here.',
              icon: Icons.medication_outlined,
              actionLabel: 'Start a health chat',
              onAction: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const ChatScreen()),
                );
              },
            );
          }
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(myPrescriptionsProvider),
            child: ListView.builder(
              padding: const EdgeInsets.all(AppSpacing.lg),
              itemCount: prescriptions.length,
              itemBuilder: (context, index) => Padding(
                padding: const EdgeInsets.only(bottom: AppSpacing.md),
                child: PrescriptionCard(prescription: prescriptions[index]),
              ),
            ),
          );
        },
        loading: () => const LoadingState(message: 'Loading your prescriptions...'),
        error: (e, _) => ErrorState(
          message: e.toString(),
          onRetry: () => ref.invalidate(myPrescriptionsProvider),
        ),
      ),
    );
  }
}
