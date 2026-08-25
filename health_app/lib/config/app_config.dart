import 'package:flutter/foundation.dart';

class AppConfig {
  static String get apiBaseUrl {
    const configured = String.fromEnvironment('API_BASE_URL', defaultValue: '');
    if (configured.isNotEmpty) {
      return configured;
    }

    if (kIsWeb) {
      return 'http://localhost:8000';
    }

    // Android emulator reaches the host machine via 10.0.2.2, not 127.0.0.1
    // (which points at the emulator itself).
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8000';
    }

    // Desktop / iOS simulator share the host loopback.
    return 'http://127.0.0.1:8000';
  }
}
