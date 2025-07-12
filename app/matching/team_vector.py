import numpy as np
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

from app.models import Participant, Team

class TeamVector(BaseModel):
    """
    A vectorized representation of a team's aggregated attributes.
    """
    team_id: str
    avg_skill_levels: Dict[str, float]
    role_weights: Dict[str, float]
    min_availability: int
    avg_motivation_embedding: Optional[List[float]] = None
    avg_communication_style: float
    avg_ambiguity_tolerance: float
    avg_confidence_score: float

async def build_team_vector(team: Team, participants: List[Participant]) -> TeamVector:
    """
    Aggregates participant data into a single team vector.
    """
    num_participants = len(participants)
    
    # 1. Average Skill Levels
    skill_sums = {}
    for p in participants:
        for skill, level in p.computed_skills.items():
            skill_sums[skill] = skill_sums.get(skill, 0) + level.posterior.mean
    avg_skills = {skill: total / num_participants for skill, total in skill_sums.items()}

    # 2. Role Weights
    role_counts = {}
    for p in participants:
        for role in p.roles:
            role_counts[role] = role_counts.get(role, 0) + 1
    role_weights = {role: count / num_participants for role, count in role_counts.items()}
    
    # 3. Minimum Availability
    min_availability = min(p.availability for p in participants)

    # 4. Average Motivation Embedding
    motivation_embeddings = [p.motivation_embedding for p in participants if p.motivation_embedding]
    avg_motivation_embedding = None
    if motivation_embeddings:
        avg_motivation_embedding = np.mean(motivation_embeddings, axis=0).tolist()

    # 5. Communication Style (using availability as proxy)
    avg_comm_style = np.mean([p.availability / 40.0 for p in participants]) # Normalized

    # 6. Ambiguity Tolerance
    avg_ambiguity_tolerance = np.mean([p.gpt_traits.ambiguity_tolerance for p in participants])
    
    # 7. Confidence Score
    avg_confidence = np.mean([p.computed_skills[skill].posterior.mean for p in participants for skill in p.computed_skills]) / 5.0 # Normalized

    return TeamVector(
        team_id=str(team.id),
        avg_skill_levels=avg_skills,
        role_weights=role_weights,
        min_availability=min_availability,
        avg_motivation_embedding=avg_motivation_embedding,
        avg_communication_style=avg_comm_style,
        avg_ambiguity_tolerance=avg_ambiguity_tolerance,
        avg_confidence_score=avg_confidence,
    ) 