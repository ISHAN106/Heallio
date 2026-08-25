/// The backend serializes timestamps via Python's `datetime.utcnow()`, which
/// has no timezone designator (no trailing `Z`/offset). `DateTime.parse`
/// treats a designator-less string as *local* time, so without this, every
/// backend timestamp displayed here is silently off by the device's UTC
/// offset. Append `Z` only when the string doesn't already carry a
/// designator, then parse as UTC.
///
/// Date-only values (e.g. `follow_up_date`, a Python `date` serialized as
/// "YYYY-MM-DD" with no time component) are left untouched — appending `Z`
/// to a bare date is not valid ISO-8601 and DateTime.parse throws on it, and
/// there's no time-of-day for a UTC offset to shift in the first place.
DateTime parseUtc(String value) {
  final hasTimeComponent = value.contains('T') || value.contains(' ');
  if (!hasTimeComponent) return DateTime.parse(value);
  final hasDesignator = value.endsWith('Z') || RegExp(r'[+-]\d\d:?\d\d$').hasMatch(value);
  return DateTime.parse(hasDesignator ? value : '${value}Z');
}

/// Non-throwing counterpart to [parseUtc], for callers that fall back to a
/// default instead of erroring on a missing/malformed timestamp.
DateTime? tryParseUtc(String value) {
  try {
    return parseUtc(value);
  } catch (_) {
    return null;
  }
}

class UserSession {
  final String id;
  final String? deviceLabel;
  final String? ipAddress;
  final DateTime createdAt;
  final DateTime? lastSeenAt;
  final bool isCurrent;

  UserSession({
    required this.id,
    this.deviceLabel,
    this.ipAddress,
    required this.createdAt,
    this.lastSeenAt,
    required this.isCurrent,
  });

  factory UserSession.fromJson(Map<String, dynamic> json) {
    return UserSession(
      id: (json['id'] ?? '').toString(),
      deviceLabel: json['device_label']?.toString(),
      ipAddress: json['ip_address']?.toString(),
      createdAt: parseUtc((json['created_at'] ?? DateTime.now().toIso8601String()).toString()),
      lastSeenAt: json['last_seen_at'] != null ? parseUtc(json['last_seen_at'].toString()) : null,
      isCurrent: json['is_current'] == true,
    );
  }
}

class User {
  final String id;
  final String email;
  final String username;
  final String role;
  final bool emailVerified;
  final String? profileImage;
  final DateTime createdAt;
  final DateTime updatedAt;

  User({
    required this.id,
    required this.email,
    required this.username,
    required this.role,
    required this.emailVerified,
    this.profileImage,
    required this.createdAt,
    required this.updatedAt,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    final rawId = json['id'];
    final parsedId = rawId == null ? '' : rawId.toString();
    final now = DateTime.now();

    return User(
      id: parsedId,
      email: (json['email'] ?? '').toString(),
      username: (json['username'] ?? json['name'] ?? 'User').toString(),
      role: (json['role'] ?? 'user').toString(),
      emailVerified: json['email_verified'] ?? false,
      profileImage: json['profile_image'],
      createdAt: json['created_at'] != null ? parseUtc(json['created_at']) : now,
      updatedAt: json['updated_at'] != null ? parseUtc(json['updated_at']) : now,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'username': username,
      'role': role,
      'email_verified': emailVerified,
      'profile_image': profileImage,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }
}

class AuthResponse {
  final User user;
  final String accessToken;
  final String refreshToken;

  AuthResponse({
    required this.user,
    required this.accessToken,
    required this.refreshToken,
  });

  factory AuthResponse.fromJson(Map<String, dynamic> json) {
    return AuthResponse(
      user: User.fromJson((json['user'] ?? const <String, dynamic>{}) as Map<String, dynamic>),
      accessToken: (json['access_token'] ?? '').toString(),
      refreshToken: (json['refresh_token'] ?? '').toString(),
    );
  }
}

class ChatMessage {
  final String id;
  final String userId;
  final String message;
  final String response;
  final String? sentiment;
  final List<String>? suggestedActions;
  final bool escalated;
  final String? consultationTicketId;
  final String? consultationStatus;
  final String? doctorId;
  final ConsultationSuggestion? consultationSuggestion;
  final ChatMetricsContext? metricsImplicated;
  final DateTime timestamp;

  ChatMessage({
    required this.id,
    required this.userId,
    required this.message,
    required this.response,
    this.sentiment,
    this.suggestedActions,
    this.escalated = false,
    this.consultationTicketId,
    this.consultationStatus,
    this.doctorId,
    this.consultationSuggestion,
    this.metricsImplicated,
    required this.timestamp,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: (json['id'] ?? '').toString(),
      userId: (json['user_id'] ?? '').toString(),
      message: (json['message'] ?? '').toString(),
      response: (json['response'] ?? '').toString(),
      sentiment: json['sentiment'],
      suggestedActions: List<String>.from(json['suggested_actions'] ?? []),
      escalated: json['escalated'] == true,
      consultationTicketId: json['consultation_ticket_id']?.toString(),
      consultationStatus: json['consultation_status']?.toString(),
      doctorId: json['doctor_id']?.toString(),
      consultationSuggestion: json['consultation_suggestion'] != null
          ? ConsultationSuggestion.fromJson(json['consultation_suggestion'] as Map<String, dynamic>)
          : null,
      metricsImplicated: json['metrics_implicated'] != null
          ? ChatMetricsContext.fromJson(json['metrics_implicated'] as Map<String, dynamic>)
          : null,
      timestamp: parseUtc((json['timestamp'] ?? json['recorded_at'] ?? DateTime.now().toIso8601String()).toString()),
    );
  }
}

/// Real recent-health context implicated in a risk-flagged chat reply —
/// sourced from the same sleep/calorie averages the backend already
/// evaluates the message against (see app/services/escalation.py).
class ChatMetricsContext {
  final double? avgSleepHours;
  final double? avgCalories;
  final int? sleepDaysTracked;
  final int? dietDaysTracked;

  ChatMetricsContext({
    this.avgSleepHours,
    this.avgCalories,
    this.sleepDaysTracked,
    this.dietDaysTracked,
  });

  factory ChatMetricsContext.fromJson(Map<String, dynamic> json) {
    return ChatMetricsContext(
      avgSleepHours: (json['avg_sleep_hours'] as num?)?.toDouble(),
      avgCalories: (json['avg_calories'] as num?)?.toDouble(),
      sleepDaysTracked: (json['sleep_days_tracked'] as num?)?.toInt(),
      dietDaysTracked: (json['diet_days_tracked'] as num?)?.toInt(),
    );
  }
}

class ConsultationSuggestion {
  final String categoryName;
  final String severityLevel;
  final String reason;

  ConsultationSuggestion({
    required this.categoryName,
    required this.severityLevel,
    required this.reason,
  });

  factory ConsultationSuggestion.fromJson(Map<String, dynamic> json) {
    return ConsultationSuggestion(
      categoryName: (json['category_name'] ?? '').toString(),
      severityLevel: (json['severity_level'] ?? '').toString(),
      reason: (json['reason'] ?? '').toString(),
    );
  }
}

class DoctorCategory {
  final String id;
  final String name;
  final String? description;

  DoctorCategory({
    required this.id,
    required this.name,
    this.description,
  });

  factory DoctorCategory.fromJson(Map<String, dynamic> json) {
    return DoctorCategory(
      id: (json['id'] ?? '').toString(),
      name: (json['name'] ?? '').toString(),
      description: json['description']?.toString(),
    );
  }
}

class DoctorProfile {
  final String id;
  final String userId;
  final String doctorName;
  final String categoryId;
  final String categoryName;
  final String licenseNumber;
  final int yearsExperience;
  final String? bio;
  final bool isAvailable;
  final double averageRating;
  final int totalRatings;
  final int totalConsultations;
  final double? avgResponseSeconds;
  final int activeCases;
  final int prescriptionsIssued;

  DoctorProfile({
    required this.id,
    required this.userId,
    required this.doctorName,
    required this.categoryId,
    required this.categoryName,
    required this.licenseNumber,
    required this.yearsExperience,
    required this.bio,
    required this.isAvailable,
    required this.averageRating,
    required this.totalRatings,
    required this.totalConsultations,
    this.avgResponseSeconds,
    this.activeCases = 0,
    this.prescriptionsIssued = 0,
  });

  factory DoctorProfile.fromJson(Map<String, dynamic> json) {
    return DoctorProfile(
      id: (json['id'] ?? '').toString(),
      userId: (json['user_id'] ?? '').toString(),
      doctorName: (json['doctor_name'] ?? '').toString(),
      categoryId: (json['category_id'] ?? '').toString(),
      categoryName: (json['category_name'] ?? '').toString(),
      licenseNumber: (json['license_number'] ?? '').toString(),
      yearsExperience: (json['years_experience'] as num?)?.toInt() ?? 0,
      bio: json['bio']?.toString(),
      isAvailable: json['is_available'] == true,
      averageRating: (json['average_rating'] as num?)?.toDouble() ?? 0,
      totalRatings: (json['total_ratings'] as num?)?.toInt() ?? 0,
      totalConsultations: (json['total_consultations'] as num?)?.toInt() ?? 0,
      activeCases: (json['active_cases'] as num?)?.toInt() ?? 0,
      prescriptionsIssued: (json['prescriptions_issued'] as num?)?.toInt() ?? 0,
      avgResponseSeconds: (json['avg_response_seconds'] as num?)?.toDouble(),
    );
  }
}

class ConsultationTicket {
  final String id;
  final String userId;
  final String? doctorId;
  final String triggerSource;
  final String triggerReason;
  final int severityScore;
  final String severityLevel;
  final String status;
  final DateTime createdAt;
  final DateTime? acceptedAt;
  final DateTime? closedAt;

  ConsultationTicket({
    required this.id,
    required this.userId,
    required this.doctorId,
    required this.triggerSource,
    required this.triggerReason,
    required this.severityScore,
    required this.severityLevel,
    required this.status,
    required this.createdAt,
    required this.acceptedAt,
    required this.closedAt,
  });

  factory ConsultationTicket.fromJson(Map<String, dynamic> json) {
    return ConsultationTicket(
      id: (json['id'] ?? '').toString(),
      userId: (json['user_id'] ?? '').toString(),
      doctorId: json['doctor_id']?.toString(),
      triggerSource: (json['trigger_source'] ?? '').toString(),
      triggerReason: (json['trigger_reason'] ?? '').toString(),
      severityScore: (json['severity_score'] as num?)?.toInt() ?? 0,
      severityLevel: (json['severity_level'] ?? '').toString(),
      status: (json['status'] ?? '').toString(),
      createdAt: parseUtc((json['created_at'] ?? DateTime.now().toIso8601String()).toString()),
      acceptedAt: json['accepted_at'] != null ? parseUtc(json['accepted_at'].toString()) : null,
      closedAt: json['closed_at'] != null ? parseUtc(json['closed_at'].toString()) : null,
    );
  }
}

class ConsultationMessageItem {
  final String id;
  final String ticketId;
  final String senderUserId;
  final String message;
  final DateTime createdAt;

  ConsultationMessageItem({
    required this.id,
    required this.ticketId,
    required this.senderUserId,
    required this.message,
    required this.createdAt,
  });

  factory ConsultationMessageItem.fromJson(Map<String, dynamic> json) {
    return ConsultationMessageItem(
      id: (json['id'] ?? '').toString(),
      ticketId: (json['ticket_id'] ?? '').toString(),
      senderUserId: (json['sender_user_id'] ?? '').toString(),
      message: (json['message'] ?? '').toString(),
      createdAt: parseUtc((json['created_at'] ?? DateTime.now().toIso8601String()).toString()),
    );
  }
}

class PrescriptionItem {
  final String id;
  final String medicationName;
  final String? dosage;
  final String? frequency;
  final String? duration;
  final String? instructions;

  PrescriptionItem({
    required this.id,
    required this.medicationName,
    required this.dosage,
    required this.frequency,
    required this.duration,
    required this.instructions,
  });

  factory PrescriptionItem.fromJson(Map<String, dynamic> json) {
    return PrescriptionItem(
      id: (json['id'] ?? '').toString(),
      medicationName: (json['medication_name'] ?? '').toString(),
      dosage: json['dosage']?.toString(),
      frequency: json['frequency']?.toString(),
      duration: json['duration']?.toString(),
      instructions: json['instructions']?.toString(),
    );
  }
}

class Prescription {
  final String id;
  final String ticketId;
  final String doctorId;
  final String userId;
  final String? notes;
  final DateTime? followUpDate;
  final String status;
  final String? supersedesId;
  final DateTime createdAt;
  final List<PrescriptionItem> items;
  final String? doctorName;

  Prescription({
    required this.id,
    required this.ticketId,
    required this.doctorId,
    required this.userId,
    required this.notes,
    required this.followUpDate,
    required this.status,
    required this.supersedesId,
    required this.createdAt,
    required this.items,
    this.doctorName,
  });

  bool get isActive => status == 'active';

  factory Prescription.fromJson(Map<String, dynamic> json) {
    return Prescription(
      id: (json['id'] ?? '').toString(),
      ticketId: (json['ticket_id'] ?? '').toString(),
      doctorId: (json['doctor_id'] ?? '').toString(),
      userId: (json['user_id'] ?? '').toString(),
      notes: json['notes']?.toString(),
      followUpDate: json['follow_up_date'] != null ? parseUtc(json['follow_up_date'].toString()) : null,
      status: (json['status'] ?? '').toString(),
      supersedesId: json['supersedes_id']?.toString(),
      createdAt: parseUtc((json['created_at'] ?? DateTime.now().toIso8601String()).toString()),
      items: ((json['items'] as List?) ?? const [])
          .map((item) => PrescriptionItem.fromJson(item as Map<String, dynamic>))
          .toList(),
      doctorName: json['doctor_name']?.toString(),
    );
  }
}

class HealthData {
  final String id;
  final String userId;
  final int? steps;
  final double? heartRate;
  final double? caloriesBurned;
  final int? systolicBp;
  final int? diastolicBp;
  final double? bloodGlucose;
  final Uri? imageUrl;
  final DateTime recordedAt;

  HealthData({
    required this.id,
    required this.userId,
    this.steps,
    this.heartRate,
    this.caloriesBurned,
    this.systolicBp,
    this.diastolicBp,
    this.bloodGlucose,
    this.imageUrl,
    required this.recordedAt,
  });

  factory HealthData.fromJson(Map<String, dynamic> json) {
    return HealthData(
      id: (json['id'] ?? '').toString(),
      userId: (json['user_id'] ?? '').toString(),
      steps: (json['steps'] as num?)?.toInt(),
      heartRate: (json['heart_rate'] as num?)?.toDouble(),
      caloriesBurned: (json['calories_burned'] as num?)?.toDouble(),
      systolicBp: (json['systolic_bp'] as num?)?.toInt(),
      diastolicBp: (json['diastolic_bp'] as num?)?.toInt(),
      bloodGlucose: (json['blood_glucose'] as num?)?.toDouble(),
      imageUrl: json['image_url'] != null ? Uri.parse(json['image_url']) : null,
      recordedAt: parseUtc((json['recorded_at'] ?? json['created_at'] ?? DateTime.now().toIso8601String()).toString()),
    );
  }
}

class DietData {
  final String id;
  final String userId;
  final String mealType; // breakfast, lunch, dinner, snack
  final String description;
  final int? calories;
  final List<String>? nutrients;
  final DateTime recordedAt;

  DietData({
    required this.id,
    required this.userId,
    required this.mealType,
    required this.description,
    this.calories,
    this.nutrients,
    required this.recordedAt,
  });

  factory DietData.fromJson(Map<String, dynamic> json) {
    return DietData(
      id: (json['id'] ?? '').toString(),
      userId: (json['user_id'] ?? '').toString(),
      mealType: (json['meal_type'] ?? '').toString(),
      description: (json['description'] ?? json['food'] ?? '').toString(),
      calories: (json['calories'] as num?)?.toInt(),
      nutrients: List<String>.from(json['nutrients'] ?? []),
      recordedAt: parseUtc((json['recorded_at'] ?? json['created_at'] ?? DateTime.now().toIso8601String()).toString()),
    );
  }
}

class SleepData {
  final String id;
  final String userId;
  final Duration duration;
  final String quality; // poor, fair, good, excellent
  final int? remCycles;
  final DateTime recordedAt;

  SleepData({
    required this.id,
    required this.userId,
    required this.duration,
    required this.quality,
    this.remCycles,
    required this.recordedAt,
  });

  factory SleepData.fromJson(Map<String, dynamic> json) {
    final start = json['sleep_start'] != null ? parseUtc(json['sleep_start'].toString()) : null;
    final end = json['sleep_end'] != null ? parseUtc(json['sleep_end'].toString()) : null;
    final inferredDuration = (start != null && end != null) ? end.difference(start) : null;

    return SleepData(
      id: (json['id'] ?? '').toString(),
      userId: (json['user_id'] ?? '').toString(),
      duration: inferredDuration ?? Duration(hours: json['duration_hours'] ?? 0, minutes: json['duration_minutes'] ?? 0),
      quality: (json['quality'] ?? 'average').toString(),
      remCycles: (json['rem_cycles'] as num?)?.toInt(),
      recordedAt: parseUtc((json['recorded_at'] ?? json['created_at'] ?? DateTime.now().toIso8601String()).toString()),
    );
  }
}

class Insight {
  final String id;
  final String userId;
  final String category; // health, diet, sleep, exercise
  final String title;
  final String description;
  final String? recommendation;
  final String? status; // poor | average | good, from the backend's weekly-insights scoring
  final DateTime generatedAt;

  Insight({
    required this.id,
    required this.userId,
    required this.category,
    required this.title,
    required this.description,
    this.recommendation,
    this.status,
    required this.generatedAt,
  });

  factory Insight.fromJson(Map<String, dynamic> json) {
    return Insight(
      id: (json['id'] ?? '').toString(),
      userId: (json['user_id'] ?? '').toString(),
      category: (json['category'] ?? 'general').toString(),
      title: (json['title'] ?? '').toString(),
      description: (json['description'] ?? json['message'] ?? '').toString(),
      recommendation: json['recommendation']?.toString(),
      status: json['status']?.toString(),
      generatedAt: parseUtc((json['generated_at'] ?? DateTime.now().toIso8601String()).toString()),
    );
  }
}

class UserConsent {
  final String id;
  final String userId;
  final bool consentGiven;
  final String consentVersion;
  final DateTime? updatedAt;
  final DateTime? grantedAt;
  final DateTime? revokedAt;

  UserConsent({
    required this.id,
    required this.userId,
    required this.consentGiven,
    this.consentVersion = 'v1',
    this.updatedAt,
    this.grantedAt,
    this.revokedAt,
  });

  factory UserConsent.fromJson(Map<String, dynamic> json) {
    return UserConsent(
      id: (json['id'] ?? '').toString(),
      userId: (json['user_id'] ?? '').toString(),
      consentGiven: json['consent_given'] == true,
      consentVersion: (json['consent_version'] ?? 'v1').toString(),
      updatedAt: json['updated_at'] != null
          ? parseUtc(json['updated_at'].toString())
          : null,
      grantedAt: json['granted_at'] != null
          ? parseUtc(json['granted_at'].toString())
          : null,
      revokedAt: json['revoked_at'] != null
          ? parseUtc(json['revoked_at'].toString())
          : null,
    );
  }
}

class ScanPrediction {
  final String label;
  final double confidence;

  ScanPrediction({
    required this.label,
    required this.confidence,
  });

  factory ScanPrediction.fromJson(Map<String, dynamic> json) {
    return ScanPrediction(
      label: (json['label'] ?? '').toString(),
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
    );
  }
}

class BodyScanResult {
  final String mostLikelyCondition;
  final double confidence;
  final List<ScanPrediction> predictions;
  final String urgencyLevel;
  final String summary;
  final String recommendation;
  final String disclaimer;
  final String? bodyPart;

  BodyScanResult({
    required this.mostLikelyCondition,
    required this.confidence,
    required this.predictions,
    required this.urgencyLevel,
    required this.summary,
    required this.recommendation,
    required this.disclaimer,
    this.bodyPart,
  });

  factory BodyScanResult.fromJson(Map<String, dynamic> json) {
    final rawPredictions = (json['predictions'] as List?) ?? const [];
    return BodyScanResult(
      mostLikelyCondition: (json['most_likely_condition'] ?? '').toString(),
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
      predictions: rawPredictions
          .map((item) => ScanPrediction.fromJson(item as Map<String, dynamic>))
          .toList(),
      urgencyLevel: (json['urgency_level'] ?? '').toString(),
      summary: (json['summary'] ?? '').toString(),
      recommendation: (json['recommendation'] ?? '').toString(),
      disclaimer: (json['disclaimer'] ?? '').toString(),
      bodyPart: json['body_part']?.toString(),
    );
  }
}
