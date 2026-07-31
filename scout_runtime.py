"""Runtime safety boundary between Scout code and real cloud resources.

A single, tooling-enforced gate that decides whether a **real** AWS/S3 client may be created —
so DEVELOPMENT and especially TEST processes cannot accidentally read or (far worse) WRITE the
production Publisher/Scout buckets. This exists because a full test-suite run, executed on a
workstation whose ``.env`` carried live credentials, published an uncertified report to
production: the boundary was a convention (inject a fake client), not something enforced. See
``docs/phases/geometry-correctness/PRODUCTION_WRITE_INCIDENT.md``.

Modes (env ``SCOUT_RUNTIME_MODE``):
  * ``production``  — the deployed agent (Oracle VM). Real clients allowed.
  * ``development`` — a developer/agent workstation. Real clients allowed ONLY with an explicit
                      opt-in ``SCOUT_ALLOW_REAL_S3=1``, so a stray script that loads ``.env``
                      cannot silently touch production.
  * ``test``        — the test harness. Real clients are **always refused**; tests inject fakes.
                      This is the boundary that would have prevented the accidental write.

Default is ``development`` (deny-by-default). The deployed VM MUST set
``SCOUT_RUNTIME_MODE=production``. Leaf module: stdlib only, no Scout imports, no cycle.
"""
import os
import sys

MODE_ENV = "SCOUT_RUNTIME_MODE"
ALLOW_REAL_S3_ENV = "SCOUT_ALLOW_REAL_S3"
PRODUCTION, DEVELOPMENT, TEST = "production", "development", "test"
_VALID = (PRODUCTION, DEVELOPMENT, TEST)
_TRUTHY = ("1", "true", "yes", "on")


class ScoutSafetyError(RuntimeError):
    """Raised when code attempts to create a real cloud client in a context that forbids it
    (test mode, or development mode without an explicit opt-in)."""


def mode():
    """The current runtime mode; unknown/unset values resolve to ``development`` (deny-by-default)."""
    m = (os.getenv(MODE_ENV) or DEVELOPMENT).strip().lower()
    return m if m in _VALID else DEVELOPMENT


def is_test():
    return mode() == TEST


def real_s3_allowed():
    """Whether the current mode permits creating a real S3 client."""
    m = mode()
    if m == PRODUCTION:
        return True
    if m == TEST:
        return False
    return (os.getenv(ALLOW_REAL_S3_ENV, "") or "").strip().lower() in _TRUTHY  # development: opt-in


def _under_test_runner():
    """True when running under a unit-test runner (unittest/pytest imported). Independent of how the
    suite is launched, so the test boundary holds even when the ``tests`` package bootstrap does not
    run (e.g. ``unittest discover -s tests``) or a workstation has left ``SCOUT_ALLOW_REAL_S3`` set.
    The application never imports unittest/pytest, so this is never true in production."""
    return any(m in sys.modules for m in ("unittest", "pytest", "_pytest"))


def guard_real_s3_client():
    """Choke-point called by EVERY real boto3 S3 client factory. Raises ``ScoutSafetyError`` unless
    the current runtime mode permits a real client. A test process can NEVER pass this — tests must
    inject a fake/stub client — regardless of mode or a stray opt-in."""
    if _under_test_runner():
        raise ScoutSafetyError(
            "Refusing to create a real S3 client from a test process (a unit-test runner is loaded). "
            "Tests must inject a fake/stub client.")
    if not real_s3_allowed():
        raise ScoutSafetyError(
            f"Refusing to create a real S3 client in runtime mode={mode()!r}. "
            f"Tests must inject a fake client; a development process must set {ALLOW_REAL_S3_ENV}=1 "
            f"to intentionally reach real resources; the deployed agent must run with "
            f"{MODE_ENV}=production."
        )
