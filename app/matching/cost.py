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


def compute_individual_cost(
    participant: Dict[str, Any],
    problem: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Computes the cost between a single participant and a single problem.
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    cost_terms = {
        "skill_gap": _skill_gap(participant, problem),
        "role_alignment": _role_alignment(participant, problem),
        "motivation_similarity": _motivation_similarity(participant, problem),
        "ambiguity_fit": _ambiguity_mismatch(participant, problem),
        "workload_fit": _workload_mismatch(participant, problem),
    }

    total_cost = sum(weights[term] * value for term, value in cost_terms.items())
    return total_cost


def _skill_gap(participant: Dict[str, Any], problem: Dict[str, Any]) -> float:
    """Lower is better."""
    participant_skills = participant.get("enriched_skills", {})
    required_skills = problem.get("required_skills", {})
    gaps = []
    for skill, required_level in required_skills.items():
        participant_level = participant_skills.get(skill, {}).get("mean", 0.0)
        gaps.append(max(0, required_level - participant_level))
    return np.mean(gaps) if gaps else 0.0


def _role_alignment(participant: Dict[str, Any], problem: Dict[str, Any]) -> float:
    """Lower is better. Cost is 1 - alignment."""
    participant_roles = participant.get("primary_roles", [])
    problem_roles = problem.get("preferred_roles", {})
    alignment = sum(problem_roles.get(role, 0.0) for role in participant_roles)
    return 1.0 - alignment


def _motivation_similarity(
    participant: Dict[str, Any], problem: Dict[str, Any]
) -> float:
    """Lower is better. Cost is 1 - similarity."""
    p_embedding = participant.get("motivation_embedding")
    q_embedding = problem.get("prompt_embedding")
    if p_embedding is None or q_embedding is None:
        return 1.0  # Max penalty if embeddings are missing
    return cosine(p_embedding, q_embedding)


def _ambiguity_mismatch(
    participant: Dict[str, Any], problem: Dict[str, Any]
) -> float:
    """Lower is better."""
    p_tolerance = participant.get("ambiguity_tolerance", 0.5)
    q_ambiguity = problem.get("ambiguity", 0.5)
    return abs(p_tolerance - q_ambiguity)


def _workload_mismatch(
    participant: Dict[str, Any], problem: Dict[str, Any]
) -> float:
    """Lower is better."""
    p_availability = participant.get("availability_hours", 0)
    q_complexity = problem.get("complexity", 0.5)
    required_hours = q_complexity * 40
    return max(0, required_hours - p_availability) / 40.0 