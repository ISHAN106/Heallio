# Heallio App - Flutter UI

A professional, feature-rich Flutter mobile application for tracking health metrics and interacting with an AI health assistant. The app provides a clean, intuitive interface for managing daily health data, receiving personalized insights, and getting AI-powered health recommendations.

## Features

### 🔐 Authentication
- **Signup Screen** - Create new accounts with email validation
- **Login Screen** - Secure sign-in with token management
- **Password Management** - Secure password hashing and reset
- **Session Management** - Automatic token refresh and logout

### 📊 Dashboard
- **Welcome Section** - Personalized greeting and daily summary
- **Quick Actions** - Fast access to chat and health logging
- **Weekly Stats** - Visual overview of health metrics
- **AI Insights Card** - Quick link to health recommendations

### 💬 AI Chat
- **Health Assistant** - Ask questions about health and wellness
- **Consent Management** - Privacy-first consent gating
- **Chat History** - View previous conversations
- **Suggested Actions** - Quick reply suggestions

### 📈 Health Tracking
**Health Tab:**
- Log steps, heart rate, and calories burned
- View recent health records
- Track physical activity

**Diet Tab:**
- Log meals (breakfast, lunch, dinner, snacks)
- Track calorie intake
- Record nutritional data

**Sleep Tab:**
- Log sleep duration and quality
- Track sleep patterns
- View sleep history

### 💡 AI Insights
- Personalized health recommendations
- Trend analysis of your health data
- Category-based insights (health, diet, sleep, exercise)
- Actionable recommendations

### 👤 Profile & Settings
- **Profile Information** - View and edit user details
- **Account Settings** - Password, privacy, security
- **Preferences** - Notifications, data sync, theme
- **Support** - Help, FAQ, about

## Project Structure

```
lib/
├── main.dart                           # App entry point
├── theme/
│   └── app_theme.dart                 # Design system, colors, typography
├── models/
│   └── models.dart                    # Data models (User, ChatMessage, HealthData, etc.)
├── services/
│   └── api_client.dart                # Backend API integration
├── providers/
│   └── app_providers.dart             # State management (Riverpod)
├── widgets/
│   └── common_widgets.dart            # Reusable UI components
├── screens/
│   ├── auth/
│   │   ├── login_screen.dart
│   │   └── signup_screen.dart
│   ├── home/
│   │   └── home_screen.dart
│   ├── chat/
│   │   └── chat_screen.dart
│   ├── health/
│   │   └── health_tracking_screen.dart
│   ├── insights/
│   │   └── insights_screen.dart
│   └── profile/
│       └── profile_screen.dart
```

## Design System

### Colors
- **Primary:** Emerald Green (#10B981)
- **Secondary:** Blue (#3B82F6)
- **Accent:** Amber (#F59E0B)
- **Error:** Red (#EF4444)
- **Neutral:** Professional grayscale palette

### Typography
- **Display:** Large, bold headings
- **Title:** Section headers and important text
- **Body:** Main content and descriptions
- **Label:** Small, secondary text

### Components
- **PrimaryButton** - Call-to-action buttons
- **CustomTextField** - Form inputs with validation
- **HealthCard** - Health metric display cards
- **StatCard** - Statistics with values and units
- **CustomAppBar** - Consistent app bar
- **LoadingState** - Loading indicators
- **ErrorState** - Error messages with retry
- **EmptyState** - Empty list states

## Setup & Installation

### Prerequisites
- Flutter SDK (^3.11.3)
- Dart SDK (included with Flutter)
- Android SDK / iOS SDK
- Backend API running (see backend README)

### Installation Steps

1. **Clone the project:**
   ```bash
   cd health_app
   ```

2. **Get dependencies:**
   ```bash
   flutter pub get
   ```

3. **Update API endpoint:**
   Edit `lib/services/api_client.dart` and update `baseUrl`:
   ```dart
   static const String baseUrl = 'http://your-backend-url:8000';
   ```

4. **Run the app:**
   ```bash
   # Run on all available devices/emulators
   flutter run

   # Or specify a device
   flutter run -d android
   flutter run -d ios
   ```

## Dependencies

### Key Packages
- **flutter_riverpod** - State management
- **http** - HTTP client for API calls
- **shared_preferences** - Local storage

### Version Info
- **Flutter:** ^3.11.3
- **Dart:** ^3.11.3

## API Integration

The app communicates with a FastAPI backend. Key endpoints:

### Authentication
- `POST /users/signup` - Create account
- `POST /users/login` - Login
- `POST /users/refresh` - Refresh token
- `POST /users/logout` - Logout
- `GET /users/me` - Get current user

### Health Tracking
- `GET /health` - Get health data
- `POST /health/record` - Log health data
- `GET /diet` - Get diet data
- `POST /diet/record` - Log meals
- `GET /sleep` - Get sleep data
- `POST /sleep/record` - Log sleep

### Chat & AI
- `POST /chat` - Send message to AI
- `GET /chat/history` - Get chat history

### Insights & Privacy
- `GET /insights` - Get health insights
- `POST /privacy/consent` - Grant consent
- `GET /privacy/consent/me` - Get consent status

## State Management

The app uses **Riverpod** for state management:

### Providers
- `authProvider` - Authentication state
- `userProvider` - Current user data
- `chatMessagesProvider` - Chat messages
- `recentHealthProvider` - Recent health data
- `recentDietProvider` - Recent diet data
- `recentSleepProvider` - Recent sleep data
- `insightsProvider` - Health insights
- `consentProvider` - Privacy consent

## Error Handling

The app includes comprehensive error handling:
- Network error messages
- Form validation
- Empty state messages
- Loading indicators
- Retry mechanisms

## Security Features

- ✅ JWT token-based authentication
- ✅ Secure token storage
- ✅ Automatic token refresh
- ✅ Encrypted password transmission
- ✅ Privacy consent enforcement
- ✅ Secure logout

## Performance Optimizations

- Lazy loading of screens
- Cached API responses
- Optimized rebuilds with Riverpod
- Efficient image loading
- Minimal widget rebuild

## Building for Production

### Android APK
```bash
flutter build apk --release
```

### iOS IPA
```bash
flutter build ios --release
```

### Web
```bash
flutter build web --release
```

## Testing

The app includes test-ready architecture:
- Mockable API client
- Separable state management
- Reusable components
- Type-safe models

To run tests:
```bash
flutter test
```

## Troubleshooting

### Common Issues

**API connection errors:**
- Ensure backend is running
- Check baseUrl in api_client.dart
- Verify firewall settings

**State not updating:**
- Ensure using Riverpod providers correctly
- Check ref.watch/ref.read usage
- Verify provider invalidation

**Build errors:**
- Run `flutter clean`
- Run `flutter pub get`
- Check Flutter version: `flutter --version`

## Future Enhancements

- 📱 Wearable device integration
- 🎯 Goal tracking and reminders
- 📊 Advanced analytics dashboard
- 🔔 Push notifications
- 🌍 Offline mode with sync
- 🎨 Dark mode support
- 🗣️ Multi-language support

## Support

For issues or questions:
1. Check the backend README for API documentation
2. Review Riverpod documentation: https://riverpod.dev
3. Check Flutter documentation: https://flutter.dev

## License

This project is part of the Heallio application.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss proposed changes.
