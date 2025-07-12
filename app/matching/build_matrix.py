import asyncio
from typing import Dict, Tuple

import numpy as np

from app.db import db
from app.matching.cost import compute_individual_cost


async def build_individual_problem_matrix() -> Tuple[np.ndarray, Dict[int, str], Dict[int, Tuple[str, int]]]:
    participants_cursor = db.participants.find({}, {"_id": 1})
    problems_cursor = db.problems.find({}, {"_id": 1, "estimated_team_size": 1})

    participants_list = await participants_cursor.to_list(length=None)
    problems_list = await problems_cursor.to_list(length=None)

    participant_ids = [p["_id"] for p in participants_list]
    
    problem_slots = []
    for problem in problems_list:
        for i in range(problem["estimated_team_size"]):
            problem_slots.append((problem["_id"], i))

    if not participant_ids or not problem_slots:
        return np.array([]), {}, {}

    participant_map = {i: pid for i, pid in enumerate(participant_ids)}
    slot_map = {i: slot for i, slot in enumerate(problem_slots)}
    
    num_participants = len(participant_ids)
    num_slots = len(problem_slots)
    
    cost_matrix = np.full((num_participants, num_slots), np.inf)

    # Fetch all data in parallel
    participant_docs = await asyncio.gather(
        *[db.participants.find_one({"_id": pid}) for pid in participant_ids]
    )
    problem_docs_map = {
        p["_id"]: p
        for p in await db.problems.find(
            {"_id": {"$in": [s[0] for s in problem_slots]}}
        ).to_list(length=None)
    }

    for i, p_doc in enumerate(participant_docs):
        for j, (problem_id, _) in enumerate(problem_slots):
            problem_doc = problem_docs_map[problem_id]
            if p_doc and problem_doc:
                cost_matrix[i, j] = compute_individual_cost(p_doc, problem_doc)
            else:
                cost_matrix[i, j] = np.inf # or some other high value

    # Make the matrix square
    size = max(num_participants, num_slots)
    padded_matrix = np.full((size, size), np.max(cost_matrix) * 2 if cost_matrix.size > 0 else 1000)
    padded_matrix[:num_participants, :num_slots] = cost_matrix
    
    return padded_matrix, participant_map, slot_map 