"""CLI entrypoint to run a Scout dataset audit once (Phase D2 automation).

Runs the same execution path as the scheduled job and the `/run-audit` endpoint:
``dataset_auditor.run_dataset_audit()`` — which writes all reports (including the
Daily Digest) and appends an audit-history snapshot. Read-only over canonical
data; no LLM. Suitable for an external systemd timer or cron.

Usage:
    python scout_audit.py
Exit code 0 on success, 1 on failure.
"""
import sys

from logging_config import logger
import dataset_auditor


def main():
    logger.info("scout_audit CLI: starting dataset audit")
    try:
        result = dataset_auditor.run_dataset_audit()
        logger.info(
            f"scout_audit CLI: completed quality_score={result['quality_score']}, "
            f"reports={len(result['reports'])}"
        )
        return 0
    except Exception as e:
        logger.exception(f"scout_audit CLI: failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
