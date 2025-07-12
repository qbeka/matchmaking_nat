import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.utils.validate import validate_participant, validate_problem

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    with open(FIXTURE_DIR / name) as f:
        return json.load(f)


def test_validate_valid_participant():
    payload = load_fixture("valid_participant_1.json")
    assert validate_participant(payload) is not None


def test_validate_invalid_participant():
    payload = load_fixture("invalid_participant_1.json")
    with pytest.raises(HTTPException) as exc_info:
        validate_participant(payload)
    assert exc_info.value.status_code == 422


def test_validate_valid_problem():
    payload = load_fixture("valid_problem_1.json")
    assert validate_problem(payload) is not None


def test_validate_invalid_problem():
    payload = load_fixture("invalid_problem_1.json")
    with pytest.raises(HTTPException) as exc_info:
        validate_problem(payload)
    assert exc_info.value.status_code == 422 