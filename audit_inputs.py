"""Read-only loading and validation of Phase 1 dataset audit inputs.

Scout never writes to these files (Charter §4). This module only opens them for
reading and validates the observed contract documented in
``docs/architecture/DATASET_INPUT_CONTRACT.md``.
"""
from pathlib import Path
import json

DATASET_FILE = "approved_dataset.json"
LLM_OUTPUTS_FILE = "approved_llm_outputs.json"
PACKETS_FILE = "retrieval_evidence_packets.json"

DATASET_KEY = "approved_dataset"
LLM_OUTPUTS_KEY = "llm_enrichment_outputs"
PACKETS_KEY = "retrieval_evidence_packets"


class AuditInputError(Exception):
    """Raised when a required input file is missing or violates the contract."""


def _read_json(path):
    if not path.exists() or not path.is_file():
        raise AuditInputError(f"Required input file not found: {path}")
    # Read-only access; Scout never writes to canonical inputs (Charter §4).
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise AuditInputError(f"Invalid JSON in {path.name}: {e}") from e


def _require_list(obj, key, source):
    if not isinstance(obj, dict) or key not in obj:
        raise AuditInputError(f"{source}: expected top-level key '{key}'")
    value = obj[key]
    if not isinstance(value, list):
        raise AuditInputError(f"{source}: '{key}' must be a list")
    return value


def _derive_dataset_id(input_dir):
    parts = input_dir.resolve().parts
    if len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}"
    return input_dir.name


def load_inputs(input_dir):
    """Load and validate the three Phase 1 input files from ``input_dir``.

    Returns a dict with the artifact population (``llm_outputs``), the approved
    subset (``approved_artifacts``), the evidence ``packets``, and a derived
    ``dataset_id``. Raises ``AuditInputError`` on a missing file or contract
    violation. Performs no writes.
    """
    input_dir = Path(input_dir)

    dataset_raw = _read_json(input_dir / DATASET_FILE)
    llm_raw = _read_json(input_dir / LLM_OUTPUTS_FILE)
    packets_raw = _read_json(input_dir / PACKETS_FILE)

    approved = _require_list(dataset_raw, DATASET_KEY, DATASET_FILE)
    outputs = _require_list(llm_raw, LLM_OUTPUTS_KEY, LLM_OUTPUTS_FILE)
    packets = _require_list(packets_raw, PACKETS_KEY, PACKETS_FILE)

    return {
        "dataset_id": _derive_dataset_id(input_dir),
        "input_dir": str(input_dir),
        "approved_artifacts": approved,
        "llm_outputs": outputs,
        "packets": packets,
    }
