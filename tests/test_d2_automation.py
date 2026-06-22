import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apscheduler.schedulers.background import BackgroundScheduler  # noqa: E402
import dataset_auditor  # noqa: E402
import scheduler as sched_mod  # noqa: E402
import scout_audit  # noqa: E402

_AUDIT_ENV = ("SCOUT_AUDIT_ENABLED", "SCOUT_LEGACY_JOB_ENABLED",
              "SCOUT_AUDIT_HOUR", "SCOUT_AUDIT_MINUTE", "SCOUT_AUDIT_TZ")


class _EnvMixin:
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in _AUDIT_ENV}
        self._orig_run = dataset_auditor.run_dataset_audit

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        dataset_auditor.run_dataset_audit = self._orig_run

    def _ids(self):
        sched = BackgroundScheduler()
        sched_mod.register_jobs(sched)
        return [j.id for j in sched.get_jobs()]


class TestSchedulerRegistration(_EnvMixin, unittest.TestCase):
    def test_audit_job_registered_when_enabled(self):
        os.environ["SCOUT_AUDIT_ENABLED"] = "true"
        os.environ["SCOUT_LEGACY_JOB_ENABLED"] = "false"
        ids = self._ids()
        self.assertIn("scheduled_audit", ids)
        self.assertNotIn("scheduled_scout", ids)

    def test_audit_job_absent_when_disabled(self):
        os.environ["SCOUT_AUDIT_ENABLED"] = "false"
        self.assertNotIn("scheduled_audit", self._ids())

    def test_legacy_job_only_when_enabled(self):
        os.environ["SCOUT_AUDIT_ENABLED"] = "false"
        os.environ["SCOUT_LEGACY_JOB_ENABLED"] = "true"
        ids = self._ids()
        self.assertIn("scheduled_scout", ids)

    def test_audit_cron_reads_env(self):
        os.environ["SCOUT_AUDIT_ENABLED"] = "true"
        os.environ["SCOUT_AUDIT_HOUR"] = "6"
        os.environ["SCOUT_AUDIT_TZ"] = "UTC"
        cron = sched_mod._audit_cron()
        self.assertEqual(cron["hour"], 6)
        self.assertEqual(cron["timezone"], "UTC")


class TestScheduledAudit(_EnvMixin, unittest.TestCase):
    def test_calls_run_dataset_audit(self):
        calls = []
        dataset_auditor.run_dataset_audit = lambda: calls.append(1) or {"quality_score": 1, "reports": {}}
        sched_mod.scheduled_audit()
        self.assertEqual(len(calls), 1)

    def test_failure_is_caught_not_raised(self):
        def boom():
            raise RuntimeError("audit failed")
        dataset_auditor.run_dataset_audit = boom
        # Must not raise — scheduler stays alive.
        sched_mod.scheduled_audit()


class TestCLI(_EnvMixin, unittest.TestCase):
    def test_cli_success_returns_zero(self):
        dataset_auditor.run_dataset_audit = lambda: {"quality_score": 53, "reports": {"digest": "x"}}
        self.assertEqual(scout_audit.main(), 0)

    def test_cli_failure_returns_one(self):
        def boom():
            raise RuntimeError("nope")
        dataset_auditor.run_dataset_audit = boom
        self.assertEqual(scout_audit.main(), 1)


if __name__ == "__main__":
    unittest.main()
