from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from logging_config import logger
import os
import json
import time
import threading

load_dotenv()

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)
MEMORY_FILE = Path("data/memory.json")
memory_lock = threading.Lock()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def load_memory():

    if not MEMORY_FILE.exists():
        return {
            "report_count": 0,
            "themes": [],
            "opportunities": [],
            "risks": [],
            "last_report": None
        }

    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_memory(memory):
    MEMORY_FILE.parent.mkdir(exist_ok=True)

    temp_file = MEMORY_FILE.with_suffix(".json.tmp")

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)
        f.flush()
        os.fsync(f.fileno())

    os.replace(temp_file, MEMORY_FILE)

def _default_dataset_track():
    """Seed for the edenseek_dataset memory track (PROJECT_MEMORY_SCHEMA.md §2.2-2.3)."""
    return {
        "active_milestone": None,
        "next_action": None,
        "last_verified_commit": None,
        "quality_score": None,
        "last_audit": None,
        "audited_artifact_count": 0,
        "scores": {
            "metadata_completeness": None,
            "character_consistency": None,
            "dialogue_completeness": None,
            "retrieval_readiness": None,
        },
        "weak_artifacts": {
            "total_flagged": 0,
            "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        },
        "latest_reports": {},
        "audit_history": [],
        "open_questions": [],
        "themes": [],
        "opportunities": [],
        "risks": [],
    }


def update_dataset_memory(summary):
    """Persist a Phase 1 audit summary to the edenseek_dataset track only.

    Additive and idempotent: seeds the track if absent, writes the defined audit
    fields, and leaves all other memory untouched. Atomic + lock-guarded.
    """
    with memory_lock:
        memory = load_memory()
        projects = memory.setdefault("projects", {})
        track = projects.get("edenseek_dataset") or _default_dataset_track()

        track["quality_score"] = summary["quality_score"]
        track["last_audit"] = summary["last_audit"]
        track["audited_artifact_count"] = summary["artifact_count"]
        track["scores"] = summary["scores"]
        track["weak_artifacts"] = summary["weak_artifacts_summary"]
        track["latest_reports"] = summary["latest_reports"]

        projects["edenseek_dataset"] = track
        save_memory(memory)
        logger.info("edenseek_dataset memory track updated")


MAX_AUDIT_HISTORY = 30


def record_audit_history(snapshot):
    """Append an audit snapshot to the edenseek_dataset history (append-only).

    Capped at MAX_AUDIT_HISTORY (oldest dropped), chronological (newest last).
    Atomic + lock-guarded. Returns the resulting history list.
    """
    with memory_lock:
        memory = load_memory()
        projects = memory.setdefault("projects", {})
        track = projects.get("edenseek_dataset") or _default_dataset_track()

        history = track.get("audit_history") or []
        history.append(snapshot)
        if len(history) > MAX_AUDIT_HISTORY:
            history = history[-MAX_AUDIT_HISTORY:]
        track["audit_history"] = history

        projects["edenseek_dataset"] = track
        save_memory(memory)
        logger.info(f"edenseek_dataset audit history recorded ({len(history)} snapshots)")
        return history


def call_openai_with_retries(prompt, max_attempts=3, timeout=60):
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"OpenAI request attempt {attempt} starting")

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                timeout=timeout,
            )

            logger.info(f"OpenAI request attempt {attempt} completed")
            return response

        except Exception as e:
            last_error = e
            logger.exception(f"OpenAI request attempt {attempt} failed: {e}")

            if attempt < max_attempts:
                sleep_seconds = 2 ** attempt
                logger.info(f"Retrying OpenAI request in {sleep_seconds} seconds")
                time.sleep(sleep_seconds)

    raise last_error

def generate_report():
    logger.info("Scout report generation started")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    memory = load_memory()

    prompt = f"""
You are Edenseek Scout, an always-on AI research agent.

Generate a concise strategic report for Derek Uskert and Edenseek Publishing.

Context:
- Edenseek is building AI-enabled publishing tools.
- Phrasmos involves symbolic image tagging and metadata.
- Caelaris is a comic publishing project.
- The long-term goal is AI-assisted comic navigation and creator tools.

Report time:
{timestamp}

Memory:
{json.dumps(memory, indent=2)}

Include:
1. Scout status
2. What you are watching
3. Why it matters
4. One recommended action today
5. One longer-term opportunity
6. One risk to monitor

Keep it under 700 words.
"""

    try:
        logger.info("OpenAI request starting")

        response = call_openai_with_retries(prompt)

        report = response.choices[0].message.content

        with memory_lock:
            memory = load_memory()
            memory["report_count"] += 1
            memory["last_report"] = timestamp

            save_memory(memory)
            logger.info("Memory updated")

        filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.md")
        filepath = REPORTS_DIR / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)

        logger.info(f"Report saved: {filepath}")
        logger.info("Scout report generation completed")

        return str(filepath)

    except Exception as e:
        logger.exception(f"Scout report generation failed: {e}")
        raise
