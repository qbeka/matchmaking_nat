import json
from pathlib import Path
from typing import Any, Dict

import jsonschema
from fastapi import HTTPException
from jsonschema import Draft7Validator
from pydantic import ValidationError as PydanticValidationError

from app.models import Participant, Problem

SCHEMA_DIR = Path(__file__).parent.parent / "schema"
PARTICIPANT_SCHEMA_PATH = SCHEMA_DIR / "participant_form.schema.json"
PROBLEM_SCHEMA_PATH = SCHEMA_DIR / "problem_form.schema.json"

with open(PARTICIPANT_SCHEMA_PATH) as f:
    participant_schema = json.load(f)
    Draft7Validator.check_schema(participant_schema)
    participant_validator = Draft7Validator(participant_schema)

with open(PROBLEM_SCHEMA_PATH) as f:
    problem_schema = json.load(f)
    Draft7Validator.check_schema(problem_schema)
    problem_validator = Draft7Validator(problem_schema)


def _format_jsonschema_errors(errors):
    error_details = []
    for error in sorted(errors, key=str):
        error_details.append(
            {
                "loc": list(error.path),
                "msg": error.message,
                "type": error.validator,
            }
        )
    return error_details


def validate_participant(data: Dict[str, Any]) -> Participant:
    try:
        jsonschema.validate(instance=data, schema=participant_schema)
        return Participant(**data)
    except (jsonschema.exceptions.ValidationError, PydanticValidationError) as e:
        raise HTTPException(status_code=422, detail=str(e))


def validate_problem(data: Dict[str, Any]) -> Problem:
    try:
        jsonschema.validate(instance=data, schema=problem_schema)
        return Problem(**data)
    except (jsonschema.exceptions.ValidationError, PydanticValidationError) as e:
        raise HTTPException(status_code=422, detail=str(e)) 