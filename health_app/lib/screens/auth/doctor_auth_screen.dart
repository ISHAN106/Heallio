import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/app_providers.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common_widgets.dart';

class DoctorAuthScreen extends ConsumerStatefulWidget {
  const DoctorAuthScreen({
    super.key,
    required this.onBackToIntroTap,
  });

  final VoidCallback onBackToIntroTap;

  @override
  ConsumerState<DoctorAuthScreen> createState() => _DoctorAuthScreenState();
}

class _DoctorAuthScreenState extends ConsumerState<DoctorAuthScreen> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _emailController;
  late TextEditingController _nameController;
  late TextEditingController _passwordController;
  late TextEditingController _confirmPasswordController;
  bool _isLoginMode = true;
  bool _agreeToTerms = false;
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;

  @override
  void initState() {
    super.initState();
    _emailController = TextEditingController();
    _nameController = TextEditingController();
    _passwordController = TextEditingController();
    _confirmPasswordController = TextEditingController();
  }

  @override
  void dispose() {
    _emailController.dispose();
    _nameController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    if (!_isLoginMode && !_agreeToTerms) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please confirm you are an authorized doctor')),
      );
      return;
    }

    if (_isLoginMode) {
      await ref.read(authProvider.notifier).login(
            email: _emailController.text,
            password: _passwordController.text,
            role: 'doctor',
          );
    } else {
      await ref.read(authProvider.notifier).signup(
            email: _emailController.text,
            username: _nameController.text,
            password: _passwordController.text,
            role: 'doctor',
          );
    }

    final authState = ref.read(authProvider);
    if (authState.isAuthenticated && authState.user?.role == 'doctor') {
      return;
    }

    if (authState.isAuthenticated && authState.user?.role != 'doctor') {
      ref.read(authProvider.notifier).clearError();
      await ref.read(authProvider.notifier).logout();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('This portal is only for doctor accounts')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);

    // Pre-auth, MyApp always renders AppTheme.lightTheme (blue) — see
    // main.dart: `authState.user?.role == 'doctor' ? doctorTheme :
    // lightTheme`, and `authState.user` is null until login succeeds, so
    // Theme.of(context) cannot know this is the doctor path yet. This
    // screen is definitionally gold-mode regardless, so it wraps itself in
    // a local doctorTheme override: every shared component below
    // (PrimaryButton, CustomTextField's focus ring, GhostButton, Checkbox)
    // reads Theme.of(context) internally and will now correctly resolve to
    // Clinical Gold instead of Signal Blue, without touching main.dart's
    // role-based theme selection or any provider/business logic.
    return Theme(
      data: AppTheme.doctorTheme,
      child: Scaffold(
        body: SafeArea(
          child: SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextButton.icon(
                    onPressed: widget.onBackToIntroTap,
                    icon: const Icon(Icons.arrow_back),
                    label: const Text('Back to choices'),
                  ),
                  const SizedBox(height: 12),
                  // Centered header (clinical_access.html).
                  Center(
                    child: Column(
                      children: [
                        Container(
                          width: 80,
                          height: 80,
                          decoration: BoxDecoration(
                            color: AppColors.glassWell,
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(
                              color: AppColors.doctorPrimary.withValues(alpha: 0.35),
                            ),
                          ),
                          child: const Icon(Icons.medical_services, color: AppColors.doctorPrimary, size: 34),
                        ),
                        const SizedBox(height: 18),
                        Text(
                          _isLoginMode ? 'Provider Portal' : 'Doctor Sign Up',
                          style: Theme.of(context).textTheme.displaySmall,
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _isLoginMode
                              ? 'Secure Clinical Access'
                              : 'Create a doctor account to manage consultations and availability.',
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                color: AppColors.doctorPrimary,
                              ),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 28),
                  AppCard(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      children: [
                        Form(
                          key: _formKey,
                          child: Column(
                            children: [
                              if (!_isLoginMode) ...[
                                CustomTextField(
                                  label: 'Doctor Name',
                                  hint: 'Enter your display name',
                                  controller: _nameController,
                                  prefixIcon: const Icon(Icons.badge_outlined),
                                  validator: (value) {
                                    if (value?.isEmpty ?? true) {
                                      return 'Name is required';
                                    }
                                    if (value!.trim().length < 3) {
                                      return 'Name must be at least 3 characters';
                                    }
                                    return null;
                                  },
                                ),
                                const SizedBox(height: 20),
                              ],
                              CustomTextField(
                                label: 'Doctor Email',
                                hint: 'Enter your work email',
                                controller: _emailController,
                                keyboardType: TextInputType.emailAddress,
                                prefixIcon: const Icon(Icons.email_outlined),
                                validator: (value) {
                                  if (value?.isEmpty ?? true) {
                                    return 'Email is required';
                                  }
                                  if (!value!.contains('@')) {
                                    return 'Please enter a valid email';
                                  }
                                  return null;
                                },
                              ),
                              const SizedBox(height: 20),
                              CustomTextField(
                                label: 'Password',
                                hint: 'Enter your password',
                                controller: _passwordController,
                                obscureText: _obscurePassword,
                                prefixIcon: const Icon(Icons.lock_outlined),
                                suffixIcon: IconButton(
                                  icon: Icon(_obscurePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                                  onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                                ),
                                validator: (value) {
                                  if (value?.isEmpty ?? true) {
                                    return 'Password is required';
                                  }
                                  if (value!.length < 8) {
                                    return 'Password must be at least 8 characters';
                                  }
                                  return null;
                                },
                              ),
                              if (!_isLoginMode) ...[
                                const SizedBox(height: 20),
                                CustomTextField(
                                  label: 'Confirm Password',
                                  hint: 'Re-enter your password',
                                  controller: _confirmPasswordController,
                                  obscureText: _obscureConfirmPassword,
                                  prefixIcon: const Icon(Icons.lock_outlined),
                                  suffixIcon: IconButton(
                                    icon: Icon(_obscureConfirmPassword ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                                    onPressed: () => setState(() => _obscureConfirmPassword = !_obscureConfirmPassword),
                                  ),
                                  validator: (value) {
                                    if (value?.isEmpty ?? true) {
                                      return 'Please confirm your password';
                                    }
                                    if (value != _passwordController.text) {
                                      return 'Passwords do not match';
                                    }
                                    return null;
                                  },
                                ),
                              ],
                            ],
                          ),
                        ),
                        if (!_isLoginMode) ...[
                          const SizedBox(height: 20),
                          // Professional-attestation checkbox — the whole
                          // row toggles it, not just the checkbox widget.
                          _AttestationRow(
                            value: _agreeToTerms,
                            onChanged: (value) => setState(() => _agreeToTerms = value),
                          ),
                        ],
                        if (authState.error != null) ...[
                          const SizedBox(height: 20),
                          _ErrorBanner(message: authState.error!),
                        ],
                        const SizedBox(height: 24),
                        PrimaryButton(
                          label: _isLoginMode ? 'Authenticate' : 'Create Doctor Account',
                          trailingIcon: _isLoginMode ? Icons.arrow_forward : null,
                          isLoading: authState.isLoading,
                          onPressed: _submit,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 8),
                  SizedBox(
                    width: double.infinity,
                    child: GhostButton(
                      label: _isLoginMode
                          ? 'Need a doctor account? Sign up'
                          : 'Already have a doctor account? Sign in',
                      onPressed: () {
                        ref.read(authProvider.notifier).clearError();
                        setState(() => _isLoginMode = !_isLoginMode);
                      },
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Professional-attestation checkbox row — the whole row is one tap target,
/// not just the checkbox, per docs/stitch_design_prompt.md's ban on
/// undersized/bare tappable controls.
class _AttestationRow extends StatelessWidget {
  const _AttestationRow({required this.value, required this.onChanged});

  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.glassWell,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => onChanged(!value),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Checkbox(
                value: value,
                onChanged: (v) => onChanged(v ?? false),
                activeColor: AppColors.doctorPrimary,
              ),
              const SizedBox(width: 4),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(top: 14),
                  child: Text(
                    'I attest that I am an authorized medical professional accessing protected health information (PHI) under HIPAA guidelines.',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Inline glass banner (Alert Red tint) per docs/stitch_design_prompt.md
/// Section 4 — errors never render as raw exception text.
class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.errorBg,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.error.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: AppColors.errorFg, size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              message,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.errorFg,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}
