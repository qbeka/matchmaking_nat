from typing import Dict, List, Tuple

import numpy as np
from scipy.optimize import linear_sum_assignment


def solve_hungarian_capacity(
    cost_matrix: np.ndarray,
    participant_map: Dict[int, str],
    slot_map: Dict[int, Tuple[str, int]],
) -> Tuple[Dict[str, List[str]], float]:
    """
    Solves the assignment problem using the Hungarian algorithm for capacity.
    """
    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    assignments: Dict[str, List[str]] = {}
    total_cost = 0.0

    for i, j in zip(row_ind, col_ind):
        # Ignore assignments to padded rows/columns
        if i < len(participant_map) and j < len(slot_map):
            participant_id = participant_map[int(i)]
            problem_id, _ = slot_map[int(j)]
            if problem_id not in assignments:
                assignments[problem_id] = []
            assignments[problem_id].append(participant_id)
            total_cost += cost_matrix[i, j]

    return assignments, total_cost 