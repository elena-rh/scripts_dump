#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _is_type(value: Any, t: str) -> bool:
    if t == "object":  return isinstance(value, dict)
    if t == "array":   return isinstance(value, list)
    if t == "string":  return isinstance(value, str)
    if t == "number":  return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "integer": return isinstance(value, int) and not isinstance(value, bool)
    if t == "boolean": return isinstance(value, bool)
    if t == "null":    return value is None
    # Unknown types are treated as pass-through (no-op)
    return True

def _normalize_schema(node: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a schema node:
      - If 'properties' or 'required' exist and 'type' is missing, set type to 'object'.
      - Leaves other fields as-is.
    """
    if "type" not in node and (("properties" in node) or ("required" in node)):
        node = dict(node)
        node["type"] = "object"
    return node

def _safe_load_json(path: Path) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"JSON file not found: {path}") from e
    except PermissionError as e:
        raise PermissionError(f"Insufficient permissions to read: {path}") from e
    except UnicodeDecodeError as e:
        raise UnicodeDecodeError(e.encoding, e.object, e.start, e.end, 
                                 f"Invalid encoding while reading {path}: {e.reason}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path} at line {e.lineno}, col {e.colno}: {e.msg}") from e

# ====================================================================================================

def validate(data: Any, schema: Dict[str, Any], path: str = "$") -> List[str]:
    """
    Minimal JSON validation:
    - type: one of object|array|string|number|integer|boolean|null
    - required: list of property names
    - properties: dict of subschemas
    - items: subschema for array items
    Returns a list of error messages (empty list means valid).
    """

    errors: List[str] = []
    schema = _normalize_schema(schema)

    t = schema.get("type")
    if t and not _is_type(data, t):
        errors.append(f"{path}: expected {t}, got {type(data).__name__}")

    if isinstance(data, dict):
        for key in schema.get("required", []):
            if key not in data:
                errors.append(f"{path}.{key}: is required")
        for key, subschema in schema.get("properties", {}).items():
            if key in data:
                errors.extend(validate(data[key], subschema, f"{path}.{key}"))

    if isinstance(data, list) and "items" in schema:
        for i, item in enumerate(data):
            errors.extend(validate(item, schema["items"], f"{path}[{i}]"))

    return errors



def load_json(file_path: Path, schema_inline: Optional[str] = None) -> Any:
    """
    Load JSON from file; if schema_inline is provided, validate using a minimal validator.
    Raises errors if file_path is not an existing file or a valid json file.
    Raises ValueError on validation errors.
    """

    data = _safe_load_json(file_path)

    if schema_inline is not None:
        schema = json.loads(schema_inline)
        errs = validate(data, schema)
        if errs:
            raise ValueError("Validation errors:\n" + "\n".join(f"- {e}" for e in errs))
        
    return data
