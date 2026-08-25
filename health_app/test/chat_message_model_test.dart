import 'package:flutter_test/flutter_test.dart';
import 'package:health_app/models/models.dart';

void main() {
  group('ChatMessage.fromJson consultation_suggestion', () {
    test('parses a present consultation_suggestion', () {
      final message = ChatMessage.fromJson({
        'id': 1,
        'user_id': '1',
        'message': 'hi',
        'response': 'hello',
        'escalated': false,
        'consultation_suggestion': {
          'category_name': 'Mental Health',
          'severity_level': 'medium',
          'reason': 'Risk detected from chatbot conversation and recent health context.',
        },
        'timestamp': '2026-07-20T00:00:00.000Z',
      });

      expect(message.consultationSuggestion, isNotNull);
      expect(message.consultationSuggestion!.categoryName, 'Mental Health');
      expect(message.consultationSuggestion!.severityLevel, 'medium');
      expect(
        message.consultationSuggestion!.reason,
        'Risk detected from chatbot conversation and recent health context.',
      );
    });

    test('leaves consultation_suggestion null when absent', () {
      final message = ChatMessage.fromJson({
        'id': 1,
        'user_id': '1',
        'message': 'hi',
        'response': 'hello',
        'escalated': false,
        'timestamp': '2026-07-20T00:00:00.000Z',
      });

      expect(message.consultationSuggestion, isNull);
    });
  });
}
