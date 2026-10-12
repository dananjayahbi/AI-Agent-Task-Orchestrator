"""Business services for the accounts app (Section 9.1).

Views stay thin: everything that mints, hashes, revokes or extends credentials
lives here, independently testable and reusable by later work packages (the
bridge-facing issuance of MT-1.2-03 and device registration of MT-1.2-04 call
the same primitives).
"""

from __future__ import annotations
