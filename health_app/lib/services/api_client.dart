import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:image_picker/image_picker.dart';
import 'package:image/image.dart' as img;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../models/models.dart';
import '../config/app_config.dart';

class ApiClient {
  static late String baseUrl;
  static String? _accessToken;
  static String? _refreshToken;

  static const _kAccessKey = 'access_token';
  static const _kRefreshKey = 'refresh_token';

  // Every network call is bounded so a dead/slow backend can't hang the UI.
  static const Duration _timeout = Duration(seconds: 20);

  static String? get accessToken => _accessToken;

  /// Extracts a safe, human-readable message from an error response instead
  /// of showing the raw body verbatim — a raw body can be a FastAPI
  /// validation error's internal structure, which isn't meant for end users.
  static String _errorMessage(http.Response response, String fallback) {
    try {
      final data = jsonDecode(response.body);
      final detail = data is Map<String, dynamic> ? data['detail'] : null;
      if (detail is String && detail.trim().isNotEmpty) return detail;
    } catch (_) {
      // Not JSON, or no usable `detail` — fall through to the generic message.
    }
    return fallback;
  }

  // Set by AuthNotifier so a dead session (refresh failed) routes the app
  // back to the auth screen instead of leaving it stuck on an authenticated
  // shell where every request silently fails.
  static void Function()? onSessionExpired;

  // Concurrent 401s (e.g. several providers firing requests at once) must
  // share one refresh call, not each independently hit /users/refresh —
  // the second-in would otherwise be using a token the first already
  // rotated out.
  static Future<void>? _refreshInFlight;

  // Initialize API client with proper base URL
  static void initialize() {
    baseUrl = AppConfig.apiBaseUrl;
  }

  // Load persisted tokens into memory. Returns true if a session was restored.
  static Future<bool> restoreSession() async {
    final prefs = await SharedPreferences.getInstance();
    _accessToken = prefs.getString(_kAccessKey);
    _refreshToken = prefs.getString(_kRefreshKey);
    return _accessToken != null && _accessToken!.isNotEmpty;
  }

  static Future<void> _persistTokens() async {
    final prefs = await SharedPreferences.getInstance();
    if (_accessToken != null) await prefs.setString(_kAccessKey, _accessToken!);
    if (_refreshToken != null) await prefs.setString(_kRefreshKey, _refreshToken!);
  }

  static Future<void> _clearPersistedTokens() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kAccessKey);
    await prefs.remove(_kRefreshKey);
  }

  /// Runs an authenticated request with a timeout and one automatic retry after
  /// refreshing the access token on a 401. The thunk re-reads `_accessToken` on
  /// each invocation, so the retry uses the refreshed token.
  static Future<http.Response> _send(
    Future<http.Response> Function() call,
  ) async {
    var response = await call().timeout(_timeout);
    if (response.statusCode == 401 &&
        _refreshToken != null &&
        _refreshToken!.isNotEmpty) {
      try {
        // Join an in-flight refresh instead of starting a second one.
        _refreshInFlight ??= _refreshAccessToken().whenComplete(() {
          _refreshInFlight = null;
        });
        await _refreshInFlight;
      } catch (_) {
        // The session can't be refreshed — it's dead, not just this one
        // request. Clear it and let the app route back to the auth screen
        // instead of leaving isAuthenticated true while every call 401s.
        _accessToken = null;
        _refreshToken = null;
        await _clearPersistedTokens();
        onSessionExpired?.call();
        return response;
      }
      response = await call().timeout(_timeout);
    }
    return response;
  }

  // Auth endpoints
  static Future<AuthResponse> signup({
    required String email,
    required String username,
    required String password,
    String role = 'user',
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/users/signup'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'name': username,
        'password': password,
        'role': role,
      }),
    ).timeout(_timeout);

    if (response.statusCode == 201) {
      // Backend signup returns user info only; perform login to obtain tokens.
      return login(email: email, password: password, role: role);
    } else {
      throw Exception(_errorMessage(response, 'Signup failed'));
    }
  }

  static Future<AuthResponse> login({
    required String email,
    required String password,
    String role = 'user',
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/users/login'),
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: {
        'username': email,
        'password': password,
        'role': role,
      },
    ).timeout(_timeout);

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      _accessToken = (data['access_token'] ?? '').toString();
      _refreshToken = (data['refresh_token'] ?? '').toString();
      await _persistTokens();

      User user;
      final rawUser = data['user'];
      if (rawUser is Map<String, dynamic>) {
        final fallbackName = (rawUser['email'] ?? 'user').toString().split('@').first;
        final resolvedName = (rawUser['username'] ?? rawUser['name'] ?? '')
                .toString()
                .trim()
                .isNotEmpty
            ? (rawUser['username'] ?? rawUser['name']).toString().trim()
            : fallbackName;
        user = User.fromJson({
          'id': (rawUser['id'] ?? '').toString(),
          'email': rawUser['email'],
          'name': resolvedName,
          'username': resolvedName,
          'role': rawUser['role'] ?? 'user',
          'email_verified': true,
        });
      } else {
        user = await getCurrentUser();
      }

      return AuthResponse(
        user: user,
        accessToken: _accessToken ?? '',
        refreshToken: _refreshToken ?? '',
      );
    } else if (response.statusCode == 423) {
      throw Exception('Account locked due to failed login attempts');
    } else {
      throw Exception(_errorMessage(response, 'Login failed'));
    }
  }

  static Future<void> logout() async {
    try {
      if (_refreshToken != null) {
        await http.post(
          Uri.parse('$baseUrl/users/logout'),
          headers: {
            'Content-Type': 'application/json',
          },
          body: jsonEncode({'refresh_token': _refreshToken}),
        ).timeout(_timeout);
      }
    } catch (_) {
      // Ignore network errors on logout; tokens are cleared below regardless.
    } finally {
      // Always clear local tokens so account switches do not reuse stale auth.
      _accessToken = null;
      _refreshToken = null;
      await _clearPersistedTokens();
    }
  }

  // Refresh only the access token. Kept separate from the public refreshToken()
  // so _send() can call it without recursing through getCurrentUser().
  static Future<void> _refreshAccessToken() async {
    if (_refreshToken == null || _refreshToken!.isEmpty) {
      throw Exception('No refresh token available');
    }

    final response = await http.post(
      Uri.parse('$baseUrl/users/refresh'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'refresh_token': _refreshToken}),
    ).timeout(_timeout);

    if (response.statusCode != 200) {
      throw Exception('Token refresh failed');
    }
    final data = jsonDecode(response.body);
    _accessToken = (data['access_token'] ?? '').toString();
    await _persistTokens();
  }

  static Future<AuthResponse> refreshToken() async {
    await _refreshAccessToken();
    final user = await getCurrentUser();
    return AuthResponse(
      user: user,
      accessToken: _accessToken ?? '',
      refreshToken: _refreshToken ?? '',
    );
  }

  // User endpoints
  static Future<List<UserSession>> getConnectedSessions() async {
    final response = await _send(
      () => http.get(
        Uri.parse('$baseUrl/users/me/sessions'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      ),
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List;
      return data.map((e) => UserSession.fromJson(e as Map<String, dynamic>)).toList();
    }
    throw Exception('Failed to load connected sessions');
  }

  static Future<void> revokeSession(String sessionId) async {
    final response = await _send(
      () => http.delete(
        Uri.parse('$baseUrl/users/me/sessions/$sessionId'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      ),
    );
    if (response.statusCode != 204) {
      throw Exception('Failed to revoke session');
    }
  }

  static Future<User> getCurrentUser() async {
    final response = await _send(
      () => http.get(
        Uri.parse('$baseUrl/users/me'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      ),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final fallbackName = (data['email'] ?? 'user').toString().split('@').first;
      final resolvedName = (data['username'] ?? data['name'] ?? '').toString().trim().isNotEmpty
          ? (data['username'] ?? data['name']).toString().trim()
          : fallbackName;
      return User.fromJson({
        'id': (data['id'] ?? '').toString(),
        'email': data['email'],
        'name': resolvedName,
        'username': resolvedName,
        'role': data['role'] ?? 'user',
        'email_verified': true,
      });
    } else {
      throw Exception('Failed to get current user');
    }
  }

  // Chat endpoints
  static Future<ChatMessage> sendMessage(String message) async {
    final response = await _send(
      () => http.post(
        Uri.parse('$baseUrl/chat/'),
        headers: {
          'Authorization': 'Bearer $_accessToken',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({'message': message}),
      ),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return ChatMessage.fromJson({
        'id': DateTime.now().millisecondsSinceEpoch,
        'user_id': '',
        'message': message,
        'response': data['response'] ?? '',
        'escalated': data['escalated'] ?? false,
        'consultation_ticket_id': data['consultation_ticket_id'],
        'consultation_status': data['consultation_status'],
        'doctor_id': data['doctor_id'],
        'consultation_suggestion': data['consultation_suggestion'],
        'metrics_implicated': data['metrics_implicated'],
        'timestamp': DateTime.now().toIso8601String(),
      });
    } else if (response.statusCode == 403) {
      throw Exception('Please grant consent to use chat');
    } else {
      throw Exception('Chat request failed');
    }
  }

  static Future<List<ChatMessage>> getChatHistory() async {
    final response = await _send(
      () => http.get(
        Uri.parse('$baseUrl/chat/history'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      ),
    );

    if (response.statusCode == 200) {
      final messages = jsonDecode(response.body) as List;
      return messages.map((m) => ChatMessage.fromJson(m)).toList();
    } else {
      throw Exception('Failed to fetch chat history');
    }
  }

  static Future<List<DoctorCategory>> getDoctorCategories() async {
    final response = await http
        .get(Uri.parse('$baseUrl/doctors/categories'))
        .timeout(_timeout);
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List;
      return data.map((item) => DoctorCategory.fromJson(item)).toList();
    }
    throw Exception('Failed to fetch doctor categories');
  }

  static Future<List<DoctorProfile>> getAvailableDoctors({String? categoryName}) async {
    final query = categoryName == null ? '' : '?category_name=${Uri.encodeComponent(categoryName)}';
    final response = await _send(
      () => http.get(
        Uri.parse('$baseUrl/doctors/available$query'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      ),
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List;
      return data.map((item) => DoctorProfile.fromJson(item)).toList();
    }
    throw Exception('Failed to fetch doctors');
  }

  static Future<DoctorProfile> createDoctorProfile({
    required String categoryId,
    required String licenseNumber,
    required int yearsExperience,
    String? bio,
  }) async {
    final response = await _send(
      () => http.post(
        Uri.parse('$baseUrl/doctors/profile'),
        headers: {
          'Authorization': 'Bearer $_accessToken',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'category_id': int.parse(categoryId),
          'license_number': licenseNumber,
          'years_experience': yearsExperience,
          'bio': bio,
          'is_available': true,
        }),
      ),
    );

    if (response.statusCode == 201) {
      return DoctorProfile.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
    }
    throw Exception('Failed to create doctor profile');
  }

  static Future<DoctorProfile> getMyDoctorProfile() async {
    final response = await _send(
      () => http.get(
        Uri.parse('$baseUrl/doctors/me/profile'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      ),
    );
    if (response.statusCode == 200) {
      return DoctorProfile.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
    }
    throw Exception('Doctor profile not found');
  }

  static Future<DoctorProfile> setDoctorAvailability(bool isAvailable) async {
    final response = await _send(
      () => http.patch(
        Uri.parse('$baseUrl/doctors/me/availability?is_available=$isAvailable'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      ),
    );
    if (response.statusCode == 200) {
      final profile = await getMyDoctorProfile();
      return profile;
    }
    throw Exception('Failed to update doctor availability');
  }

  static Future<List<ConsultationTicket>> getMyConsultations() async {
    final response = await _send(
      () => http.get(
        Uri.parse('$baseUrl/consultations/my'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      ),
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List;
      return data.map((item) => ConsultationTicket.fromJson(item)).toList();
    }
    throw Exception('Failed to fetch consultations');
  }

  static Future<List<ConsultationTicket>> getConsultationQueue() async {
    final response = await _send(
      () => http.get(
        Uri.parse('$baseUrl/consultations/queue'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      ),
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List;
      return data.map((item) => ConsultationTicket.fromJson(item)).toList();
    }
    throw Exception('Failed to load consultation queue');
  }

  static Future<List<ConsultationMessageItem>> getConsultationMessages(String ticketId) async {
    final response = await _send(
      () => http.get(
        Uri.parse('$baseUrl/consultations/$ticketId/messages'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      ),
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List;
      return data.map((item) => ConsultationMessageItem.fromJson(item)).toList();
    }
    throw Exception('Failed to fetch consultation messages');
  }

  static Future<ConsultationTicket> createManualConsultation({
    required String reason,
    String? categoryName,
  }) async {
    final response = await _send(
      () => http.post(
        Uri.parse('$baseUrl/consultations/manual'),
        headers: {
          'Authorization': 'Bearer $_accessToken',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'reason': reason,
          'category_name': categoryName,
        }),
      ),
    );
    if (response.statusCode == 200) {
      return ConsultationTicket.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
    }
    throw Exception('Failed to create consultation');
  }

  static Future<ConsultationTicket> acceptConsultation(String ticketId) async {
    final response = await _send(
      () => http.post(
        Uri.parse('$baseUrl/consultations/$ticketId/accept'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      ),
    );
    if (response.statusCode == 200) {
      return ConsultationTicket.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
    }
    throw Exception('Failed to accept consultation');
  }

  static Future<ConsultationTicket> closeConsultation(String ticketId) async {
    final response = await _send(
      () => http.post(
        Uri.parse('$baseUrl/consultations/$ticketId/close'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      ),
    );
    if (response.statusCode == 200) {
      return ConsultationTicket.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
    }
    throw Exception('Failed to close consultation');
  }

  static Future<Map<String, dynamic>> rateDoctor(String ticketId, {required int rating, String? review}) async {
    final response = await _send(
      () => http.post(
        Uri.parse('$baseUrl/consultations/$ticketId/rate'),
        headers: {
          'Authorization': 'Bearer $_accessToken',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'rating': rating,
          'review': review,
        }),
      ),
    );
    if (response.statusCode == 201) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }
    throw Exception('Failed to rate doctor');
  }

  static Future<Prescription> createPrescription(
    String ticketId, {
    required List<Map<String, String?>> items,
    String? notes,
    String? followUpDate,
  }) async {
    final response = await _send(
      () => http.post(
        Uri.parse('$baseUrl/consultations/$ticketId/prescriptions'),
        headers: {
          'Authorization': 'Bearer $_accessToken',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'items': items,
          'notes': notes,
          'follow_up_date': followUpDate,
        }),
      ),
    );
    if (response.statusCode == 201) {
      return Prescription.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
    }
    throw Exception(_errorMessage(response, 'Failed to create prescription'));
  }

  static Future<List<Prescription>> getTicketPrescriptions(String ticketId) async {
    final response = await _send(
      () => http.get(
        Uri.parse('$baseUrl/consultations/$ticketId/prescriptions'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      ),
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List;
      return data.map((item) => Prescription.fromJson(item as Map<String, dynamic>)).toList();
    }
    throw Exception('Failed to load prescriptions for this consultation');
  }

  static Future<List<Prescription>> getMyPrescriptions() async {
    final response = await _send(
      () => http.get(
        Uri.parse('$baseUrl/prescriptions/my'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      ),
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List;
      return data.map((item) => Prescription.fromJson(item as Map<String, dynamic>)).toList();
    }
    throw Exception('Failed to load your prescriptions');
  }

  static Future<Prescription> supersedePrescription(
    String prescriptionId, {
    required List<Map<String, String?>> items,
    String? notes,
    String? followUpDate,
  }) async {
    final response = await _send(
      () => http.post(
        Uri.parse('$baseUrl/prescriptions/$prescriptionId/supersede'),
        headers: {
          'Authorization': 'Bearer $_accessToken',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'items': items,
          'notes': notes,
          'follow_up_date': followUpDate,
        }),
      ),
    );
    if (response.statusCode == 201) {
      return Prescription.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
    }
    throw Exception(_errorMessage(response, 'Failed to supersede prescription'));
  }

  static Future<String> getDoctorReputation(String doctorId) async {
    final response = await _send(
      () => http.get(
        Uri.parse('$baseUrl/doctors/$doctorId/reputation'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      ),
    );
    if (response.statusCode == 200) {
      return response.body;
    }
    throw Exception('Failed to load reputation');
  }

  static Uri consultationWebSocketUri(String ticketId) {
    final httpBase = Uri.parse(baseUrl);
    final wsScheme = httpBase.scheme == 'https' ? 'wss' : 'ws';
    final wsBase = httpBase.replace(scheme: wsScheme);
    return wsBase.replace(path: '/consultations/ws/$ticketId');
  }

  static WebSocketChannel consultationChannel(String ticketId) {
    // Send the JWT via the Sec-WebSocket-Protocol header (["bearer", <token>])
    // so it never lands in URL query strings / server access logs.
    return WebSocketChannel.connect(
      consultationWebSocketUri(ticketId),
      protocols: ['bearer', _accessToken ?? ''],
    );
  }

  // Health endpoints
  static Future<List<HealthData>> getHealthData({int days = 7}) async {
    final response = await _send(
      () => http.get(
        Uri.parse('$baseUrl/health?days=$days'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      ),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List;
      return data.map((h) => HealthData.fromJson(h)).toList();
    } else if (response.statusCode == 404) {
      return [];
    } else {
      throw Exception('Failed to fetch health data');
    }
  }

  static Future<HealthData> recordHealth({
    int? steps,
    double? heartRate,
    double? caloriesBurned,
    int? systolicBp,
    int? diastolicBp,
    double? bloodGlucose,
    DateTime? recordedAt,
  }) async {
    final response = await _send(
      () => http.post(
        Uri.parse('$baseUrl/health/record'),
        headers: {
          'Authorization': 'Bearer $_accessToken',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'steps': steps,
          'heart_rate': heartRate,
          'calories_burned': caloriesBurned,
          'systolic_bp': systolicBp,
          'diastolic_bp': diastolicBp,
          'blood_glucose': bloodGlucose,
          if (recordedAt != null) 'recorded_at': recordedAt.toIso8601String(),
        }),
      ),
    );

    if (response.statusCode == 201) {
      return HealthData.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to record health data');
    }
  }

  // Diet endpoints
  static Future<List<DietData>> getDietData({int days = 7}) async {
    final response = await _send(
      () => http.get(
        Uri.parse('$baseUrl/diet/my-records'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      ),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List;
      return data.map((d) => DietData.fromJson(d)).toList();
    } else {
      throw Exception('Failed to fetch diet data');
    }
  }

  static Future<DietData> recordMeal({
    required String mealType,
    required String description,
    int? calories,
  }) async {
    final response = await _send(
      () => http.post(
        Uri.parse('$baseUrl/diet/log'),
        headers: {
          'Authorization': 'Bearer $_accessToken',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'meal_type': mealType,
          'food': description,
          'calories': calories,
          'notes': '',
        }),
      ),
    );

    if (response.statusCode == 201) {
      return DietData.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to record diet data');
    }
  }

  static Future<Map<String, dynamic>> scanFood({
    required XFile image,
    required String mealType,
    String? hint,
  }) async {
    // Multipart uploads keep a plain timeout; the token is validated up front by
    // the surrounding session, so 401 auto-retry isn't wired here.
    final request = http.MultipartRequest('POST', Uri.parse('$baseUrl/scan/food/analyze'));
    request.headers['Authorization'] = 'Bearer $_accessToken';
    request.fields['meal_type'] = mealType;
    if (hint != null && hint.trim().isNotEmpty) {
      request.fields['hint'] = hint.trim();
    }
    request.files.add(await http.MultipartFile.fromPath('image', image.path));

    final streamed = await request.send().timeout(_timeout);
    final response = await http.Response.fromStream(streamed);

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }

    throw Exception(_errorMessage(response, 'Food scan failed'));
  }

  // Sleep endpoints
  static Future<List<SleepData>> getSleepData({int days = 7}) async {
    final response = await _send(
      () => http.get(
        Uri.parse('$baseUrl/sleep/my-records'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      ),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List;
      return data.map((s) => SleepData.fromJson(s)).toList();
    } else {
      throw Exception('Failed to fetch sleep data');
    }
  }

  static Future<SleepData> recordSleep({
    required Duration duration,
    required String quality,
    int? remCycles,
  }) async {
    final now = DateTime.now().toUtc();
    final start = now.subtract(duration);

    final response = await _send(
      () => http.post(
        Uri.parse('$baseUrl/sleep/log'),
        headers: {
          'Authorization': 'Bearer $_accessToken',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'sleep_start': start.toIso8601String(),
          'sleep_end': now.toIso8601String(),
          'quality': quality,
          'rem_cycles': remCycles,
        }),
      ),
    );

    if (response.statusCode == 201) {
      return SleepData.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to record sleep data');
    }
  }

  // Insights endpoints
  static Future<List<Insight>> getInsights() async {
    final response = await _send(
      () => http.get(
        Uri.parse('$baseUrl/insights/weekly'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      ),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final now = DateTime.now().toIso8601String();
      return [
        Insight.fromJson({
          'id': 'sleep',
          'category': 'sleep',
          'title': 'Sleep Insight',
          'description': data['sleep']?['message'] ?? '',
          'recommendation': data['overall_suggestion'],
          'status': data['sleep']?['status'],
          'generated_at': now,
        }),
        Insight.fromJson({
          'id': 'diet',
          'category': 'diet',
          'title': 'Diet Insight',
          'description': data['diet']?['message'] ?? '',
          'recommendation': data['overall_suggestion'],
          'status': data['diet']?['status'],
          'generated_at': now,
        }),
        Insight.fromJson({
          'id': 'consistency',
          'category': 'consistency',
          'title': 'Consistency Insight',
          'description': data['consistency']?['message'] ?? '',
          'recommendation': data['overall_suggestion'],
          'status': data['consistency']?['status'],
          'generated_at': now,
        }),
      ];
    } else {
      throw Exception('Failed to fetch insights');
    }
  }

  // Privacy endpoints
  static Future<UserConsent> grantConsent() async {
    final response = await _send(
      () => http.post(
        Uri.parse('$baseUrl/privacy/consent'),
        headers: {
          'Authorization': 'Bearer $_accessToken',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({'consent_given': true}),
      ),
    );

    if (response.statusCode == 200) {
      return UserConsent.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to grant consent');
    }
  }

  static Future<UserConsent> getConsent() async {
    final response = await _send(
      () => http.get(
        Uri.parse('$baseUrl/privacy/consent/me'),
        headers: {'Authorization': 'Bearer $_accessToken'},
      ),
    );

    if (response.statusCode == 200) {
      return UserConsent.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to fetch consent');
    }
  }

  // Scan endpoints
  static Future<BodyScanResult> analyzeBodyImage({
    required XFile imageFile,
    String? bodyPart,
  }) async {
    final originalBytes = await imageFile.readAsBytes();
    final decoded = img.decodeImage(originalBytes);
    if (decoded == null) {
      throw Exception('Unsupported image format. Please use JPG or PNG.');
    }
    final bytes = img.encodeJpg(decoded, quality: 92);

    final request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/scan/analyze'),
    );

    request.headers['Authorization'] = 'Bearer $_accessToken';
    if (bodyPart != null && bodyPart.trim().isNotEmpty) {
      request.fields['body_part'] = bodyPart.trim();
    }

    request.files.add(
      http.MultipartFile.fromBytes(
        'image',
        bytes,
        filename: 'scan_upload.jpg',
      ),
    );

    final streamed = await request.send().timeout(_timeout);
    final response = await http.Response.fromStream(streamed);

    if (response.statusCode == 200) {
      return BodyScanResult.fromJson(jsonDecode(response.body));
    }

    throw Exception(_errorMessage(response, 'Scan failed'));
  }

  // Helper methods
  static String? getAccessToken() => _accessToken;
  static void setAccessToken(String token) => _accessToken = token;
  static void setRefreshToken(String token) => _refreshToken = token;
  static bool isAuthenticated() => _accessToken != null;
}
