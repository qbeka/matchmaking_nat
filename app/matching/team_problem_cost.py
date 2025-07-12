from typing import Dict
import numpy as np

from app.models import Problem
from app.matching.team_vector import TeamVector
from app.matching.cost import (
    calculate_skill_gap_cost,
    calculate_role_alignment_cost,
    calculate_motivation_similarity_cost,
    calculate_ambiguity_fit_cost,
    calculate_workload_fit_cost,
)

async def compute_team_problem_cost(
    team_vector: TeamVector,
    problem: Problem,
    weights: Dict[str, float],
) -> float:
    """
    Calculates the cost between a team and a problem using a weighted formula.
    """
    # 1. Skill Gap
    skill_gap = calculate_skill_gap_cost(
        participant_skills=team_vector.avg_skill_levels,
        problem_skills=problem.required_skills,
    )

    # 2. Role Alignment
    role_alignment = calculate_role_alignment_cost(
        participant_roles=team_vector.role_weights,
        problem_roles=problem.role_preferences,
    )

    # 3. Motivation Similarity
    motivation_similarity = 1.0  # Default if no embeddings
    if team_vector.avg_motivation_embedding and problem.problem_embedding:
        motivation_similarity = calculate_motivation_similarity_cost(
            participant_embedding=np.array(team_vector.avg_motivation_embedding),
            problem_embedding=np.array(problem.problem_embedding),
        )

    # 4. Ambiguity Fit
    ambiguity_fit = calculate_ambiguity_fit_cost(
        participant_tolerance=team_vector.avg_ambiguity_tolerance,
        problem_ambiguity=problem.expected_ambiguity,
    )

    # 5. Workload Fit
    workload_fit = calculate_workload_fit_cost(
        participant_availability=team_vector.min_availability,
        problem_hours=problem.expected_hours_per_week,
    )

    total_cost = (
        weights["skill_gap"] * skill_gap +
        weights["role_alignment"] * role_alignment +
        weights["motivation_similarity"] * motivation_similarity +
        weights["ambiguity_fit"] * ambiguity_fit +
        weights["workload_fit"] * workload_fit
    )
    
    return total_cost 