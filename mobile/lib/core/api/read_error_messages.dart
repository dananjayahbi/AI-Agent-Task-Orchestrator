import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../api/api_exception.dart';

/// Maps Section 9.2 catalog codes to friendly, non-leaky copy for the
/// read-oriented screens (dashboard MT-5.6-01, selector MT-5.6-02, board
/// MT-5.6-03; Section 12.4: no raw server message shown to the user — the
/// catalog code drives the copy).
///
/// One table, one place: screens never inspect codes themselves
/// (Section 20.4 item 5 — only catalog-relevant errors surface). Onboarding
/// keeps its own copy (different flows, different guidance) in
/// `features/onboarding/onboarding_messages.dart`.
String friendlyReadErrorMessage(OrchestratorApiException error) {
  switch (error.code) {
    case CodeEnum.AUTH_REQUIRED:
      return 'Your session has expired — unlock to sign in again.';
    case CodeEnum.AUTH_FORBIDDEN_PROJECT:
    case CodeEnum.ROLE_NOT_PERMITTED:
      return 'This account cannot view that project.';
    case CodeEnum.VALIDATION_ERROR:
      return 'The server rejected the request — try again.';
    case CodeEnum.RATE_LIMITED:
      return 'Too many requests — wait a moment and try again.';
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
    return 'Could not reach the server — check your connection.';
  }
  if (error.code == null) {
    return 'Something went wrong — try again.';
  }
  // Catalog code with no dedicated friendly line: generic, honest, and
  // still free of raw server text or credentials.
  return 'The server refused the request (${error.codeName}).';
}
