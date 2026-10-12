import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:local_auth/local_auth.dart';

/// Outcome of probing the device for OS authentication capability
/// (parent plan Section 14.2: biometric unlock with passcode fallback "as
/// the OS allows", honest handling when nothing is enrolled).
enum BiometricAvailability {
  /// Biometrics are enrolled; the OS prompt may also offer its passcode
  /// fallback (Section 14.2).
  available,

  /// The device supports OS authentication but nothing is enrolled yet —
  /// the user must enroll (fingerprint/face) or set a device passcode.
  /// The gate shows enrollment guidance and does NOT bypass (Section 14.2
  /// honest states; MT-5.5-06 routes to the enrollment screen).
  enrollmentRequired,

  /// The device cannot perform OS authentication at all — documented
  /// limitation for store-level policy (MT-5.5-04 out-of-scope note); the
  /// lock view says so plainly instead of pretending.
  unsupported,

  /// The probe itself failed; the lock view offers a retry.
  unknown,
}

/// Abstraction over `local_auth` so the gate is unit-testable without
/// platform channels.
abstract class BiometricAuthenticator {
  /// Probes enrolled capability.
  Future<BiometricAvailability> availability();

  /// Runs the OS authentication prompt. [reason] is the user-facing purpose
  /// string. Passcode fallback is offered where the OS allows it
  /// (Section 14.2). Returns true only on OS-reported success.
  Future<bool> authenticate({required String reason});
}

/// Production implementation backed by the `local_auth` plugin.
class LocalBiometricAuthenticator implements BiometricAuthenticator {
  LocalBiometricAuthenticator([LocalAuthentication? localAuthentication])
      : _local = localAuthentication ?? LocalAuthentication();

  final LocalAuthentication _local;

  @override
  Future<BiometricAvailability> availability() async {
    try {
      final bool supported = await _local.isDeviceSupported();
      if (!supported) {
        return BiometricAvailability.unsupported;
      }
      final bool canCheck = await _local.canCheckBiometrics;
      if (canCheck) {
        final List<BiometricType> enrolled =
            await _local.getAvailableBiometrics();
        if (enrolled.isNotEmpty) {
          return BiometricAvailability.available;
        }
      }
      // Supported hardware, but nothing enrolled: the OS may still offer a
      // device passcode when we prompt, which is the Section 14.2 fallback —
      // honest enrollment guidance is shown alongside that prompt.
      return BiometricAvailability.enrollmentRequired;
    } catch (_) {
      // Probe failure is reported honestly, never treated as "unlocked".
      return BiometricAvailability.unknown;
    }
  }

  @override
  Future<bool> authenticate({required String reason}) async {
    try {
      return await _local.authenticate(
        localizedReason: reason,
        // biometricOnly: false = the OS may offer its passcode fallback
        // (Section 14.2: "Fallback to device passcode as the OS allows").
        biometricOnly: false,
        // sticky-auth equivalent in local_auth 3.x: survive backgrounding
        // during the prompt instead of failing it.
        persistAcrossBackgrounding: true,
      );
    } catch (_) {
      // A failed prompt is a failed unlock — never a bypass.
      return false;
    }
  }
}

/// Riverpod provider for the authenticator; tests override with a fake.
final Provider<BiometricAuthenticator> biometricAuthProvider =
    Provider<BiometricAuthenticator>(
  (Ref ref) => LocalBiometricAuthenticator(),
);
