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
