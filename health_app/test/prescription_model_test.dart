import 'package:flutter_test/flutter_test.dart';
import 'package:health_app/models/models.dart';

void main() {
  group('Prescription.fromJson', () {
    test('parses items, notes, and follow-up date', () {
      final prescription = Prescription.fromJson({
        'id': 1,
        'ticket_id': 7,
        'doctor_id': 3,
        'user_id': 9,
        'notes': 'Rest and hydrate',
        'follow_up_date': '2026-07-20',
        'status': 'active',
        'supersedes_id': null,
        'created_at': '2026-07-09T00:00:00.000Z',
        'items': [
          {
            'id': 1,
            'medication_name': 'Paracetamol',
            'dosage': '500mg',
            'frequency': 'twice daily',
            'duration': '3 days',
            'instructions': null,
          }
        ],
      });

      expect(prescription.id, '1');
      expect(prescription.status, 'active');
      expect(prescription.notes, 'Rest and hydrate');
      expect(prescription.followUpDate, DateTime.parse('2026-07-20'));
      expect(prescription.items.length, 1);
      expect(prescription.items.first.medicationName, 'Paracetamol');
      expect(prescription.items.first.dosage, '500mg');
    });

    test('parses a superseded prescription with no items', () {
      final prescription = Prescription.fromJson({
        'id': 2,
        'ticket_id': 7,
        'doctor_id': 3,
        'user_id': 9,
        'notes': null,
        'follow_up_date': null,
        'status': 'superseded',
        'supersedes_id': null,
        'created_at': '2026-07-09T00:00:00.000Z',
        'items': [],
      });

      expect(prescription.status, 'superseded');
      expect(prescription.followUpDate, isNull);
      expect(prescription.items, isEmpty);
    });
  });
}
