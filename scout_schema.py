"""Tiny dependency-free JSON-Schema validator + loader (reporting Increment 4).

The versioned JSON Schemas under ``schemas/`` are the canonical machine-readable contracts that the
UI and the intelligence consumers share. This validates a document against the subset of JSON Schema
those contracts use — ``type`` (incl. lists + null), ``required``, ``properties``, ``items``,
``enum``, ``oneOf``/``anyOf`` — with zero third-party dependencies (the runtime only ships
fastapi + uvicorn). It is used by the compatibility tests and, optionally, to self-check projections.
"""
import json
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"

_TYPES = {
    "object": dict, "array": (list, tuple), "string": str, "boolean": bool,
    "number": (int, float), "integer": int, "null": type(None),
}


class SchemaError(Exception):
    """Raised with the list of validation errors when a document does not conform."""


def load_schema(name):
    path = SCHEMA_DIR / (name if name.endswith(".json") else f"{name}.schema.json")
    if not path.is_file():
        raise SchemaError(f"unknown schema: {name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _type_ok(value, t):
    if isinstance(t, list):
        return any(_type_ok(value, x) for x in t)
    py = _TYPES.get(t)
    if py is None:
        return True
    if t == "integer" and isinstance(value, bool):
        return False              # bool is not an integer here
    if t == "number" and isinstance(value, bool):
        return False
    return isinstance(value, py)


def validate(doc, schema, path="$"):
    """Return a list of human-readable error strings (empty ⇒ valid)."""
    errs = []
    t = schema.get("type")
    if t is not None and not _type_ok(doc, t):
        errs.append(f"{path}: expected type {t}, got {type(doc).__name__}")
        return errs
    if "enum" in schema and doc not in schema["enum"]:
        errs.append(f"{path}: {doc!r} not in enum {schema['enum']}")
    for combiner in ("oneOf", "anyOf"):
        if combiner in schema:
            if not any(not validate(doc, s, path) for s in schema[combiner]):
                errs.append(f"{path}: does not match {combiner}")
    if isinstance(doc, dict):
        for req in schema.get("required", []):
            if req not in doc:
                errs.append(f"{path}: missing required '{req}'")
        props = schema.get("properties", {})
        for key, subschema in props.items():
            if key in doc:
                errs += validate(doc[key], subschema, f"{path}.{key}")
    elif isinstance(doc, (list, tuple)) and "items" in schema:
        for i, item in enumerate(doc):
            errs += validate(item, schema["items"], f"{path}[{i}]")
    return errs


def assert_valid(doc, name):
    """Validate ``doc`` against the named schema; raise ``SchemaError`` with all errors if invalid."""
    errs = validate(doc, load_schema(name))
    if errs:
        raise SchemaError(f"{name} validation failed: " + "; ".join(errs[:12]))
    return True
