import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'theme/app_theme.dart';
import 'screens/auth/auth_choice_screen.dart';
import 'screens/auth/patient_auth_screen.dart';
import 'screens/auth/doctor_auth_screen.dart';
import 'screens/home/home_screen.dart';
import 'screens/chat/chat_screen.dart';
import 'screens/health/health_tracking_screen.dart';
import 'screens/scan/body_scan_screen.dart';
import 'screens/insights/insights_screen.dart';
import 'screens/profile/profile_screen.dart';
import 'screens/doctor/doctor_navigation_screen.dart';
import 'providers/app_providers.dart';
import 'services/api_client.dart';
import 'widgets/glass_bottom_nav.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Initialize API client with platform-specific configuration
  ApiClient.initialize();
  // Restore any persisted session so tokens survive app restarts.
  await ApiClient.restoreSession();
  runApp(const ProviderScope(child: MyApp()));
}

class MyApp extends ConsumerWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final isDoctor = authState.user?.role == 'doctor';

    return MaterialApp(
      title: 'Heallio',
      debugShowCheckedModeBanner: false,
      theme: isDoctor ? AppTheme.doctorTheme : AppTheme.lightTheme,
      home: const AuthWrapper(),
    );
  }
}

class AuthWrapper extends ConsumerWidget {
  const AuthWrapper({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);

    if (authState.isInitializing) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    if (authState.isAuthenticated) {
      final role = authState.user?.role ?? 'user';
      if (role == 'doctor') {
        return const DoctorNavigationScreen();
      }
      return const MainNavigationScreen();
    } else {
      return const AuthNavigationScreen();
    }
  }
}

class AuthNavigationScreen extends ConsumerStatefulWidget {
  const AuthNavigationScreen({super.key});

  @override
  ConsumerState<AuthNavigationScreen> createState() =>
      _AuthNavigationScreenState();
}

class _AuthNavigationScreenState extends ConsumerState<AuthNavigationScreen> {
  AuthRoute _authRoute = AuthRoute.intro;

  void _showIntro() {
    ref.read(authProvider.notifier).clearError();
    setState(() {
      _authRoute = AuthRoute.intro;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 420),
                switchInCurve: Curves.easeOutCubic,
                switchOutCurve: Curves.easeInCubic,
                transitionBuilder: (child, animation) {
                  final curvedAnimation = CurvedAnimation(
                    parent: animation,
                    curve: Curves.easeOut,
                  );
                  final offsetAnimation = Tween<Offset>(
                    begin: const Offset(0.08, 0),
                    end: Offset.zero,
                  ).animate(curvedAnimation);

                  return FadeTransition(
                    opacity: curvedAnimation,
                    child: SlideTransition(
                      position: offsetAnimation,
                      child: child,
                    ),
                  );
                },
                layoutBuilder: (currentChild, previousChildren) {
                  return Stack(
                    children: [
                      ...previousChildren,
                      currentChild ?? const SizedBox.shrink(),
                    ],
                  );
                },
                child: switch (_authRoute) {
                  AuthRoute.intro => AuthChoiceScreen(
                      key: const ValueKey('auth-intro'),
                      onPatientTap: () {
                        ref.read(authProvider.notifier).clearError();
                        setState(() => _authRoute = AuthRoute.patient);
                      },
                      onDoctorTap: () {
                        ref.read(authProvider.notifier).clearError();
                        setState(() => _authRoute = AuthRoute.doctor);
                      },
                    ),
                  AuthRoute.patient => PatientAuthScreen(
                      key: const ValueKey('patient-auth'),
                      onBackToIntroTap: _showIntro,
                    ),
                  AuthRoute.doctor => DoctorAuthScreen(
                      key: const ValueKey('doctor-auth'),
                      onBackToIntroTap: _showIntro,
                    ),
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class MainNavigationScreen extends ConsumerStatefulWidget {
  const MainNavigationScreen({super.key});

  @override
  ConsumerState<MainNavigationScreen> createState() =>
      _MainNavigationScreenState();
}

class _MainNavigationScreenState extends ConsumerState<MainNavigationScreen> {
  int _selectedIndex = 0;
  String? _chatDraft;

  static const _navItems = [
    GlassNavItem(icon: Icons.home_outlined, activeIcon: Icons.home, label: 'Home'),
    GlassNavItem(icon: Icons.chat_outlined, activeIcon: Icons.chat, label: 'Chat'),
    GlassNavItem(icon: Icons.favorite_outline, activeIcon: Icons.favorite, label: 'Health'),
    GlassNavItem(icon: Icons.camera_alt_outlined, activeIcon: Icons.camera_alt, label: 'Scan'),
    GlassNavItem(icon: Icons.lightbulb_outline, activeIcon: Icons.lightbulb, label: 'Insights'),
    GlassNavItem(icon: Icons.person_outline, activeIcon: Icons.person, label: 'Profile'),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBody: true,
      body: IndexedStack(
        index: _selectedIndex,
        children: [
          // Home
          HomeScreen(
            onNavigateChat: () => setState(() => _selectedIndex = 1),
            onNavigateChatWithPrompt: (prompt) {
              setState(() {
                _chatDraft = prompt;
                _selectedIndex = 1;
              });
            },
            onNavigateHealth: () => setState(() => _selectedIndex = 2),
            onNavigateInsights: () => setState(() => _selectedIndex = 4),
            onNavigateProfile: () => setState(() => _selectedIndex = 5),
          ),
          // Chat
          ChatScreen(initialMessage: _chatDraft),
          // Health Tracking
          const HealthTrackingScreen(),
          // Body Scan
          const BodyScanScreen(),
          // Insights
          const InsightsScreen(),
          // Profile
          ProfileScreen(
            onLogout: () {
              // Navigate back to auth screen is handled by AuthWrapper
            },
          ),
        ],
      ),
      bottomNavigationBar: GlassBottomNav(
        items: _navItems,
        currentIndex: _selectedIndex,
        onTap: (index) => setState(() => _selectedIndex = index),
      ),
    );
  }
}

enum AuthRoute { intro, patient, doctor }