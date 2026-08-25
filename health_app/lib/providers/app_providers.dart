import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/models.dart';
import '../services/api_client.dart';

// API Client provider
final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient();
});

// Auth providers
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier();
});

class AuthState {
  final bool isLoading;
  final User? user;
  final String? error;
  final bool isAuthenticated;
  final bool isInitializing;

  AuthState({
    this.isLoading = false,
    this.user,
    this.error,
    this.isAuthenticated = false,
    this.isInitializing = false,
  });

  AuthState copyWith({
    bool? isLoading,
    User? user,
    String? error,
    bool? isAuthenticated,
    bool? isInitializing,
  }) {
    return AuthState(
      isLoading: isLoading ?? this.isLoading,
      user: user ?? this.user,
      error: error,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      isInitializing: isInitializing ?? this.isInitializing,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier() : super(AuthState(isInitializing: true)) {
    // A dead session (refresh token rejected) should route back to the auth
    // screen instead of leaving the app stuck on an authenticated shell
    // where every request silently 401s.
    ApiClient.onSessionExpired = () {
      state = AuthState();
    };
    _restore();
  }

  // Rehydrate auth state from a session persisted across app restarts.
  Future<void> _restore() async {
    if (!ApiClient.isAuthenticated()) {
      state = AuthState();
      return;
    }
    try {
      final user = await ApiClient.getCurrentUser();
      state = AuthState(user: user, isAuthenticated: true);
    } catch (_) {
      // Stale/expired token — drop it and fall back to the auth screen.
      await ApiClient.logout();
      state = AuthState();
    }
  }

  void clearError() {
    if (state.error != null) {
      state = state.copyWith(error: null);
    }
  }

  Future<void> signup({
    required String email,
    required String username,
    required String password,
    String role = 'user',
  }) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final response = await ApiClient.signup(
        email: email,
        username: username,
        password: password,
        role: role,
      );
      state = state.copyWith(
        isLoading: false,
        user: response.user,
        isAuthenticated: true,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString().replaceFirst('Exception: ', ''),
        isAuthenticated: false,
      );
    }
  }

  Future<void> login({
    required String email,
    required String password,
    String role = 'user',
  }) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final response = await ApiClient.login(
        email: email,
        password: password,
        role: role,
      );
      state = state.copyWith(
        isLoading: false,
        user: response.user,
        isAuthenticated: true,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString().replaceFirst('Exception: ', ''),
        isAuthenticated: false,
      );
    }
  }

  Future<void> logout() async {
    state = state.copyWith(isLoading: true);
    try {
      await ApiClient.logout();
      state = AuthState();
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString().replaceFirst('Exception: ', ''),
      );
    }
  }

  Future<void> getCurrentUser() async {
    try {
      final user = await ApiClient.getCurrentUser();
      state = state.copyWith(user: user, isAuthenticated: true);
    } catch (e) {
      state = state.copyWith(error: e.toString().replaceFirst('Exception: ', ''));
    }
  }
}

// User provider. Reuses the user already fetched by AuthNotifier (on
// restore/login/signup) instead of firing a second /users/me request the
// instant a screen watches this provider.
final userProvider = FutureProvider<User>((ref) async {
  final existing = ref.watch(authProvider).user;
  if (existing != null) return existing;
  return await ApiClient.getCurrentUser();
});

// Chat providers
final chatMessagesProvider = FutureProvider<List<ChatMessage>>((ref) async {
  return await ApiClient.getChatHistory();
});

final sendMessageProvider = FutureProvider.family<ChatMessage, String>((ref, message) async {
  return await ApiClient.sendMessage(message);
});

// Health data providers
final healthDataProvider = FutureProvider.family<List<HealthData>, int>((ref, days) async {
  return await ApiClient.getHealthData(days: days);
});

final recentHealthProvider = FutureProvider<List<HealthData>>((ref) async {
  return await ApiClient.getHealthData(days: 7);
});

// Diet data providers
final dietDataProvider = FutureProvider.family<List<DietData>, int>((ref, days) async {
  return await ApiClient.getDietData(days: days);
});

final recentDietProvider = FutureProvider<List<DietData>>((ref) async {
  return await ApiClient.getDietData(days: 7);
});

// Sleep data providers
final sleepDataProvider = FutureProvider.family<List<SleepData>, int>((ref, days) async {
  return await ApiClient.getSleepData(days: days);
});

final recentSleepProvider = FutureProvider<List<SleepData>>((ref) async {
  return await ApiClient.getSleepData(days: 7);
});

// Insights provider
final insightsProvider = FutureProvider<List<Insight>>((ref) async {
  return await ApiClient.getInsights();
});

final doctorCategoriesProvider = FutureProvider<List<DoctorCategory>>((ref) async {
  return await ApiClient.getDoctorCategories();
});

final availableDoctorsProvider = FutureProvider.family<List<DoctorProfile>, String?>((ref, categoryName) async {
  return await ApiClient.getAvailableDoctors(categoryName: categoryName);
});

final myConsultationsProvider = FutureProvider<List<ConsultationTicket>>((ref) async {
  return await ApiClient.getMyConsultations();
});

final consultationQueueProvider = FutureProvider<List<ConsultationTicket>>((ref) async {
  return await ApiClient.getConsultationQueue();
});

final consultationMessagesProvider =
    FutureProvider.family<List<ConsultationMessageItem>, String>((ref, ticketId) async {
  return await ApiClient.getConsultationMessages(ticketId);
});

final ticketPrescriptionsProvider =
    FutureProvider.family<List<Prescription>, String>((ref, ticketId) async {
  return await ApiClient.getTicketPrescriptions(ticketId);
});

final myPrescriptionsProvider = FutureProvider<List<Prescription>>((ref) async {
  return await ApiClient.getMyPrescriptions();
});

final myDoctorProfileProvider = FutureProvider<DoctorProfile>((ref) async {
  return await ApiClient.getMyDoctorProfile();
});

final connectedSessionsProvider = FutureProvider<List<UserSession>>((ref) async {
  return await ApiClient.getConnectedSessions();
});

// Consent provider
final consentProvider = FutureProvider<UserConsent>((ref) async {
  return await ApiClient.getConsent();
});

final grantConsentProvider = FutureProvider<UserConsent>((ref) async {
  return await ApiClient.grantConsent();
});

// Navigation provider
final currentTabProvider = StateProvider<int>((ref) => 0);
