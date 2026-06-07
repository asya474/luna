"""JSON Schema validation helper."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

from api.exceptions import QiwiSchemaError

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"


class SchemaValidator:
    """Load and validate API request payloads and responses against documented schemas."""

    def __init__(self, schemas_dir: Path = SCHEMAS_DIR) -> None:
        self.schemas_dir = schemas_dir
        self._cache: dict[str, dict[str, Any]] = {}

    def load(self, schema_name: str) -> dict[str, Any]:
        if schema_name not in self._cache:
            path = self.schemas_dir / schema_name
            with path.open(encoding="utf-8") as handle:
                self._cache[schema_name] = json.load(handle)
        return self._cache[schema_name]

    def validate(self, payload: Any, schema_name: str) -> None:
        """Validate payload against schema (alias for response validation)."""
        self.validate_response(payload, schema_name)

    def validate_request(self, payload: Any, schema_name: str) -> None:
        """Validate outgoing request payload or parameters before send."""
        self._validate(payload, schema_name, context="Request")

    def validate_response(self, payload: Any, schema_name: str) -> None:
        """Validate incoming response body after receive."""
        self._validate(payload, schema_name, context="Response")

    def _validate(self, payload: Any, schema_name: str, *, context: str) -> None:
        schema = self.load(schema_name)
        validator = Draft7Validator(schema)
        errors = sorted(validator.iter_errors(payload), key=lambda err: err.path)
        if errors:
            messages = [f"{list(err.path)}: {err.message}" for err in errors]
            raise QiwiSchemaError(
                f"{context} does not match schema '{schema_name}'",
                errors=messages,
            )
