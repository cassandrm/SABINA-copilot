"""
Loads and caches all validation schemas from the schemas/ directory.
File names (without .json extension) become the schema labels.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMAS_DIR = Path(__file__).parent / "schemas"

_registry: dict[str, dict] = {}


def _load_all() -> None:
    if not SCHEMAS_DIR.is_dir():
        logger.warning(f"Schemas directory not found: {SCHEMAS_DIR}")
        return
    for path in SCHEMAS_DIR.glob("*.json"):
        label = path.stem
        try:
            with path.open(encoding="utf-8") as f:
                _registry[label] = json.load(f)
            logger.info(f"Loaded schema: {label}")
        except Exception as exc:
            logger.error(f"Failed to load schema '{label}': {exc}")


def get_schema(label: str) -> dict | None:
    return _registry.get(label)


def list_schemas() -> list[str]:
    return sorted(_registry.keys())


def reload() -> None:
    _registry.clear()
    _load_all()


# Load on import
_load_all()
