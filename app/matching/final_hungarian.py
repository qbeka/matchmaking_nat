from typing import Dict, Tuple, Optional
import numpy as np
from scipy.optimize import linear_sum_assignment
from datetime import datetime, timezone

from app.db import db
from app.models import Assignment

async def solve_final_assignment(
    cost_matrix: np.ndarray,
    team_map: Dict[int, str],
    problem_map: Dict[int, str]
) -> Tuple[Dict[str, str], float]:
    """
    Solves the assignment problem using the Hungarian algorithm.
    """
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    
    total_cost = cost_matrix[row_ind, col_ind].sum()
    
    assignment_mapping = {}
    num_teams = len(team_map)
    num_problems = len(problem_map)

    for r, c in zip(row_ind, col_ind):
        # Only map real teams to real problems
        if r < num_teams and c < num_problems:
            team_id = team_map[r]
            problem_id = problem_map[c]
            assignment_mapping[problem_id] = team_id
            
    return assignment_mapping, float(total_cost)

async def store_final_assignments(
    assignment_mapping: Dict[str, str],
    total_cost: float
) -> str:
    """
    Stores the final assignment map in the 'assignments' collection.
    """
    assignment_doc = Assignment(
        assignments=assignment_mapping,
        total_cost=total_cost,
        created_at=datetime.now(timezone.utc)
    )
    result = await db.assignments.insert_one(assignment_doc.dict(by_alias=True))
    return str(result.inserted_id)

async def calculate_assignment_statistics(
    assignment_mapping: Dict[str, str],
    cost_matrix: np.ndarray,
    team_map: Dict[int, str],
    problem_map: Dict[int, str]
) -> Dict[str, float]:
    """
    Calculates statistics about the assignment quality.
    """
    costs = []
    
    # Reverse maps for quick lookup
    inv_team_map = {v: k for k, v in team_map.items()}
    inv_problem_map = {v: k for k, v in problem_map.items()}

    for problem_id, team_id in assignment_mapping.items():
        team_idx = inv_team_map[team_id]
        problem_idx = inv_problem_map[problem_id]
        costs.append(cost_matrix[team_idx, problem_idx])
    
    if not costs:
        return {
            "mean_cost": 0,
            "worst_case_cost": 0,
            "best_case_cost": 0,
            "assignment_efficiency": 0
        }
        
    mean_cost = np.mean(costs)
    worst_cost = np.max(costs)
    best_cost = np.min(costs)

    # Efficiency: 1 - (mean_cost / theoretical_worst_cost)
    # Theoretical worst is sum of max costs in each row (assigning each team to its worst problem)
    theoretical_worst = np.sum(np.max(cost_matrix, axis=1))
    efficiency = 1 - (np.sum(costs) / theoretical_worst) if theoretical_worst > 0 else 0

    return {
        "mean_cost": float(mean_cost),
        "worst_case_cost": float(worst_cost),
        "best_case_cost": float(best_cost),
        "assignment_efficiency": float(efficiency)
    }

async def get_latest_assignment() -> Optional[Dict]:
    """Retrieves the most recent assignment from the database."""
    latest = await db.assignments.find_one({}, sort=[("created_at", -1)])
    if latest:
        latest["_id"] = str(latest["_id"])
    return latest

async def validate_assignment(assignment_mapping: Dict[str, str]) -> Dict:
    """Validates one-to-one mapping."""
    teams = list(assignment_mapping.values())
    problems = list(assignment_mapping.keys())
    
    is_one_to_one = len(teams) == len(set(teams))
    
    return {
        "is_valid": is_one_to_one,
        "unique_teams_assigned": len(set(teams)),
        "total_assignments": len(teams),
    } 