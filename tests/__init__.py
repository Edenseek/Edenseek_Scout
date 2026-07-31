"""Test-package bootstrap — the FIRST code that runs when the test suite is imported.

Forces the Scout runtime safety boundary into TEST mode *before* any Scout application module is
imported (and before ``scout.py`` runs ``load_dotenv()``), so no test can create a real S3 client
or reach production resources — regardless of what ``.env`` or ``~/.aws`` provides on the machine.

This is the tooling-enforced boundary that replaces the previous convention ("remember to inject a
fake client"), after a full-suite run on a workstation with live credentials wrote to production.
See ``docs/phases/geometry-correctness/PRODUCTION_WRITE_INCIDENT.md``.
"""
import os

# Primary guard: the S3 client factories refuse a real client in this mode.
os.environ["SCOUT_RUNTIME_MODE"] = "test"
os.environ.pop("SCOUT_ALLOW_REAL_S3", None)  # never honor an opt-in inside the suite

# Defense-in-depth: plant bogus credentials + bucket names. load_dotenv(override=False) will NOT
# overwrite values already present, so even if a guard were bypassed there is nothing real to reach.
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test-blocked")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test-blocked")
os.environ.setdefault("AWS_SESSION_TOKEN", "test-blocked")
for _bucket_env in ("SCOUT_APPROVED_S3_BUCKET", "SCOUT_REPO_S3_BUCKET"):
    os.environ.setdefault(_bucket_env, "nonexistent-test-bucket")
