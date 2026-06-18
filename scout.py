from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import os
import json

load_dotenv()

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)
MEMORY_FILE = Path("data/memory.json")

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

    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)

def generate_report():
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

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )

    report = response.output_text

    memory["report_count"] += 1
    memory["last_report"] = timestamp

    save_memory(memory)

    filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.md")
    filepath = REPORTS_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

    return str(filepath)