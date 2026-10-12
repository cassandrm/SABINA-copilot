import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

import schema_registry
from di_transformer import transform_document_intelligence
from validator_service import ValidatorService

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="JSON Validation Service",
    description="Validates JSON data against named schemas.",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ValidateRequest(BaseModel):
    schema_label: str
    data: dict[str, Any]
    transform_di: bool = False  # set True when data is raw Document Intelligence output


class FieldResult(BaseModel):
    field: str | None
    label_field: str | None
    value: Any
    rule_description: str | None
    failed_check: str | None = None


class ValidateResponse(BaseModel):
    schema_label: str
    is_valid: bool
    valid_fields: list[dict[str, Any]]
    error_fields: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/schemas", summary="List available schema labels")
def list_schemas() -> list[str]:
    return schema_registry.list_schemas()


@app.post("/reload-schemas", summary="Reload schemas from disk")
def reload_schemas() -> dict[str, Any]:
    schema_registry.reload()
    labels = schema_registry.list_schemas()
    return {"reloaded": labels}


@app.post("/validate", response_model=ValidateResponse, summary="Validate data against a schema")
def validate(request: ValidateRequest) -> ValidateResponse:
    schema = schema_registry.get_schema(request.schema_label)
    if schema is None:
        available = schema_registry.list_schemas()
        raise HTTPException(
            status_code=404,
            detail=f"Schema '{request.schema_label}' not found. Available: {available}",
        )

    data = request.data
    if request.transform_di:
        data = transform_document_intelligence(data)

    service = ValidatorService(schema)
    result = service.validate(data)

    return ValidateResponse(
        schema_label=request.schema_label,
        is_valid=result["is_valid"],
        valid_fields=result["valid_fields"],
        error_fields=result["error_fields"],
    )
