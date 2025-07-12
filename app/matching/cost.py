from typing import Any, Dict, Optional

import numpy as np
from scipy.spatial.distance import cosine

# Default weights for the cost function terms
DEFAULT_WEIGHTS = {
    "skill_gap": 0.35,
    "role_alignment": 0.20,
    "motivation_similarity": 0.15,
    "ambiguity_fit": 0.20,
    "workload_fit": 0.10,
}


def calculate_skill_gap_cost(participant_skills: Dict[str, float], problem_skills: Dict[str, float]) -> float:
    """Lower is better."""
    gaps = []
    for skill, required_level in problem_skills.items():
        participant_level = participant_skills.get(skill, 0.0)
        gaps.append(max(0, required_level - participant_level))
    return np.mean(gaps) if gaps else 0.0

def calculate_role_alignment_cost(participant_roles: Dict[str, float], problem_roles: Dict[str, float]) -> float:
    """Lower is better. Cost is 1 - alignment."""
    # Assuming participant_roles is a weight map {role: weight}, not a list
    alignment = sum(problem_roles.get(role, 0.0) * weight for role, weight in participant_roles.items())
    return 1.0 - alignment

def calculate_motivation_similarity_cost(participant_embedding: np.ndarray, problem_embedding: np.ndarray) -> float:
    """Lower is better. Cost is cosine distance."""
    if participant_embedding is None or problem_embedding is None:
        return 1.0
    return cosine(participant_embedding, problem_embedding)

def calculate_ambiguity_fit_cost(participant_tolerance: float, problem_ambiguity: float) -> float:
    """Lower is better."""
    return abs(participant_tolerance - problem_ambiguity)

def calculate_workload_fit_cost(participant_availability: int, problem_hours: int) -> float:
    """Lower is better."""
    return max(0, problem_hours - participant_availability) / 40.0 