from typing import Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.config import ALLOWED_ROLES, ALLOWED_SKILLS


class ParticipantModel(BaseModel):
    version: str
    name: str
    email: EmailStr
    primary_roles: List[str] = Field(..., min_length=1)
    self_rated_skills: Dict[str, int]
    availability_hours: int = Field(..., ge=0, le=40)
    motivation_text: str = Field(..., min_length=40)

    @model_validator(mode="before")
    def validate_model(cls, values):
        # Validate primary_roles
        roles = values.get("primary_roles", [])
        for role in roles:
            if role not in ALLOWED_ROLES:
                raise ValueError(f"Role '{role}' is not an allowed role.")

        # Validate self_rated_skills
        skills = values.get("self_rated_skills", {})
        for skill, rating in skills.items():
            if skill not in ALLOWED_SKILLS:
                raise ValueError(f"Skill '{skill}' is not an allowed skill.")
            if not 0 <= rating <= 5:
                raise ValueError(
                    f"Rating for skill '{skill}' must be between 0 and 5."
                )
        return values


class ProblemModel(BaseModel):
    version: str
    title: str
    raw_prompt: str
    estimated_team_size: int = Field(..., ge=2, le=10)
    preferred_roles: Dict[str, float]
    tech_constraints: Optional[List[str]] = Field(None)

    @model_validator(mode="before")
    def validate_model(cls, values):
        roles = values.get("preferred_roles", {})
        # Validate preferred_roles
        for role, weight in roles.items():
            if role not in ALLOWED_ROLES:
                raise ValueError(
                    f"Role '{role}' in preferred_roles is not an allowed role."
                )
            if not 0.0 <= weight <= 1.0:
                raise ValueError(
                    f"Weight for role '{role}' must be between 0.0 and 1.0."
                )

        if sum(roles.values()) > 1.00001:  # allow for float precision issues
            raise ValueError("Sum of preferred_roles weights cannot exceed 1.0")
        return values 