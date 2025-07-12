import numpy as np
from typing import List, Tuple, Dict
from app.db import db
from app.models import Team, Problem, Participant
from app.matching.team_vector import build_team_vector, TeamVector
from app.matching.team_problem_cost import compute_team_problem_cost
from app.config import STAGE_3_WEIGHTS

async def get_all_final_teams() -> List[Team]:
    return await db.final_teams.find().to_list(length=None)

async def get_all_problems() -> List[Problem]:
    return await db.problems.find().to_list(length=None)

async def get_participants_for_team(team: Team) -> List[Participant]:
    participant_ids = team.participant_ids
    return await db.participants.find({"_id": {"$in": participant_ids}}).to_list(length=None)

async def validate_matrix_inputs() -> dict:
    team_count = await db.final_teams.count_documents({})
    problem_count = await db.problems.count_documents({})
    return {
        "team_count": team_count,
        "problem_count": problem_count,
        "can_build_matrix": team_count > 0 and problem_count > 0,
    }

async def build_team_problem_matrix() -> Tuple[np.ndarray, Dict[int, str], Dict[int, str]]:
    """
    Builds a cost matrix for assigning teams to problems.
    """
    teams = await get_all_final_teams()
    problems = await get_all_problems()

    if not teams or not problems:
        return np.array([]), {}, {}

    team_vectors = []
    for team in teams:
        participants = await get_participants_for_team(team)
        if participants:
            team_vector = await build_team_vector(team, participants)
            team_vectors.append(team_vector)

    num_teams = len(team_vectors)
    num_problems = len(problems)
    
    # Ensure matrix is square for Hungarian algorithm
    matrix_size = max(num_teams, num_problems)
    cost_matrix = np.full((matrix_size, matrix_size), 1e6) # High cost for padding

    team_map = {i: tv.team_id for i, tv in enumerate(team_vectors)}
    problem_map = {i: str(p.id) for i, p in enumerate(problems)}

    for i, team_vector in enumerate(team_vectors):
        for j, problem in enumerate(problems):
            cost = await compute_team_problem_cost(team_vector, problem, STAGE_3_WEIGHTS)
            cost_matrix[i, j] = cost

    return cost_matrix, team_map, problem_map 