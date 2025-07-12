from typing import Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field, model_validator
from datetime import datetime
from app.config import ALLOWED_ROLES, ALLOWED_SKILLS

class Participant(BaseModel):
    version: str
    id: str = Field(..., alias="_id")
    name: str
    email: EmailStr
    primary_roles: List[str]
    self_rated_skills: Dict[str, int]
    availability_hours: int
    motivation_text: str
    computed_skills: Dict[str, "Posterior"] = {}
    motivation_embedding: Optional[List[float]] = None
    gpt_traits: Optional["GptTraits"] = None

    @model_validator(mode="before")
    def validate_model(cls, values):
        # Validation logic here
        return values

class Problem(BaseModel):
    version: str
    id: str = Field(..., alias="_id")
    title: str
    raw_prompt: str
    estimated_team_size: int
    preferred_roles: Dict[str, float]
    tech_constraints: Optional[List[str]] = None
    problem_embedding: Optional[List[float]] = None
    required_skills: Dict[str, float] = {}
    role_preferences: Dict[str, float] = {}
    expected_ambiguity: float = 0.5
    expected_hours_per_week: int = 20

class Posterior(BaseModel):
    mean: float
    std_dev: float
    alpha: float
    beta: float

class GptTraits(BaseModel):
    ambiguity_tolerance: float
    communication_style: float
    motivation_style: str

class Team(BaseModel):
    id: str = Field(..., alias="_id")
    team_id_str: str
    participant_ids: List[str]
    metrics: Dict[str, float]

class Assignment(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    assignments: Dict[str, str]
    total_cost: float
    created_at: datetime = Field(default_factory=datetime.utcnow) 