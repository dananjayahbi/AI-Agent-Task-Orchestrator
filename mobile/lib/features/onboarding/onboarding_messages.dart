import '../../core/api/api_exception.dart';
import '../../orchestrator_mobile.dart';

/// Maps Section 9.2 catalog codes to friendly, non-leaky onboarding copy
/// (MT-5.5-06 acceptance item 2; Section 12.4: no credential echo, no raw
/// server message shown to the user — the catalog code drives the copy).
///
/// One table, one place: screens never inspect codes themselves
/// (Section 20.4 item 5 — only catalog-relevant errors surface).
String friendlyOnboardingMessage(OrchestratorApiException error) {
  switch (error.code) {
    case CodeEnum.AUTH_REQUIRED:
      return 'Username or password is not correct.';
    case CodeEnum.AUTH_FORBIDDEN_PROJECT:
    case CodeEnum.ROLE_NOT_PERMITTED:
      return 'This account cannot set up mobile devices.';
    case CodeEnum.VALIDATION_ERROR:
      return 'The server rejected the request — check the value and try again.';
    case CodeEnum.RATE_LIMITED:
      return 'Too many attempts — wait a moment and try again.';
    case CodeEnum.SERVER_ERROR:
      return 'The server had a problem — try again in a moment.';
    case null:
      return _transportMessage(error);
    default:
      return _transportMessage(error);
  }
}

String _transportMessage(OrchestratorApiException error) {
  if (error.code == null && error.retryable) {
    return 'Could not reach the server — check the address and your connection.';
  }
  if (error.code == null) {
    return 'Something went wrong — try again.';
  }
  // Catalog code with no dedicated friendly line: generic, honest, and
  // still free of raw server text or credentials.
  return 'The server refused the request (${error.codeName}).';
}
