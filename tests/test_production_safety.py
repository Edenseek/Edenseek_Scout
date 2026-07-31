"""CI verification that test code cannot reach production resources.

Asserts the tooling-enforced boundary is active during the suite: the runtime is in TEST mode, the
real S3 client factories REFUSE to construct a client, and the mode gate behaves correctly across
production / development(+opt-in) / test. This is the regression guard for the accidental
production write (an uncertified report published by a full-suite run with live credentials).
"""
import os
import sys
import unittest
from unittest import mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import scout_runtime  # noqa: E402
import audit_s3_source  # noqa: E402
import scout_report_publisher as srp  # noqa: E402


class TestRuntimeBoundary(unittest.TestCase):
    def test_this_process_cannot_reach_real_s3(self):
        # The enforced invariant, independent of how the suite is launched: a test process is
        # never in production mode and never has the development opt-in, so real S3 is refused.
        # (When tests/__init__.py runs — e.g. pytest / `unittest tests.test_x` — mode is 'test';
        # under `discover -s tests` it is the deny-by-default 'development'. Either way: refused.)
        self.assertNotEqual(scout_runtime.mode(), scout_runtime.PRODUCTION)
        self.assertFalse(scout_runtime.real_s3_allowed())

    def test_real_client_factories_refuse_in_test_mode(self):
        # Both choke-point factories must raise rather than construct a real boto3 client.
        with self.assertRaises(scout_runtime.ScoutSafetyError):
            audit_s3_source._s3_client("us-west-2")
        with self.assertRaises(scout_runtime.ScoutSafetyError):
            srp._s3_client("us-west-2")

    def test_public_s3_client_helpers_refuse_in_test_mode(self):
        with self.assertRaises(scout_runtime.ScoutSafetyError):
            audit_s3_source.s3_client()

    def test_mode_gate_matrix(self):
        cases = {
            "production": (True, True),        # (allowed_without_optin, allowed_with_optin)
            "test": (False, False),
            "development": (False, True),
            "": (False, True),                 # unset -> development (deny-by-default)
            "bogus": (False, True),            # unknown -> development
        }
        for m, (no_optin, with_optin) in cases.items():
            with mock.patch.dict(os.environ, {"SCOUT_RUNTIME_MODE": m}, clear=False):
                os.environ.pop("SCOUT_ALLOW_REAL_S3", None)
                self.assertEqual(scout_runtime.real_s3_allowed(), no_optin, f"mode={m!r} no opt-in")
                with mock.patch.dict(os.environ, {"SCOUT_ALLOW_REAL_S3": "1"}, clear=False):
                    self.assertEqual(scout_runtime.real_s3_allowed(), with_optin,
                                     f"mode={m!r} with opt-in")
        # restore is automatic via patch.dict; the suite process still refuses real S3
        # (mode is 'test' under package import, deny-by-default 'development' under `-s tests`).
        self.assertFalse(scout_runtime.real_s3_allowed())


if __name__ == "__main__":
    unittest.main()
