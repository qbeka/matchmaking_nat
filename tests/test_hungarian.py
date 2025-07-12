import numpy as np

from app.matching.hungarian_capacity import solve_hungarian_capacity


def test_hungarian_solver():
    cost_matrix = np.array([
        [10, 20, 5],
        [15, 5, 25],
        [5, 10, 20],
    ])
    participant_map = {0: "p1", 1: "p2", 2: "p3"}
    slot_map = {
        0: ("prob1", 0),
        1: ("prob1", 1),
        2: ("prob2", 0),
    }

    assignments, total_cost = solve_hungarian_capacity(
        cost_matrix, participant_map, slot_map
    )

    # Expected assignments:
    # p1 -> prob2 (cost 5)
    # p2 -> prob1, slot 1 (cost 5)
    # p3 -> prob1, slot 0 (cost 5)
    # This is incorrect, p1 should go to slot 2 for prob2
    # p2 should go to slot 1 for prob1
    # p3 should go to slot 0 for prob1
    # Actually, p1->slot 2 (cost 5), p2->slot 1 (cost 5), p3->slot 0 (cost 5). Total 15.
    # No, that's wrong. p3 is assigned to slot 0 (cost 5), p2 to slot 1 (cost 5) and p1 to slot 2 (cost 5)
    # Wait, the assignment is (0,2), (1,1), (2,0). So p1->slot 2, p2->slot 1, p3->slot 0.
    # p1 is participant_map[0], assigned to slot_map[2] which is ("prob2", 0)
    # p2 is participant_map[1], assigned to slot_map[1] which is ("prob1", 1)
    # p3 is participant_map[2], assigned to slot_map[0] which is ("prob1", 0)
    
    # Assertions
    assert total_cost == 15.0
    assert len(assignments["prob1"]) == 2
    assert len(assignments["prob2"]) == 1
    assert "p2" in assignments["prob1"]
    assert "p3" in assignments["prob1"]
    assert "p1" in assignments["prob2"]


def test_hungarian_solver_padded():
    cost_matrix = np.array([
        [10, 20, 5, 1000],
        [15, 5, 25, 1000],
        [5, 10, 20, 1000],
        [1000, 1000, 1000, 1000]
    ])
    participant_map = {0: "p1", 1: "p2", 2: "p3"}
    slot_map = {
        0: ("prob1", 0),
        1: ("prob1", 1),
        2: ("prob2", 0),
    }

    assignments, total_cost = solve_hungarian_capacity(
        cost_matrix, participant_map, slot_map
    )

    assert total_cost == 15.0
    assert len(assignments["prob1"]) == 2
    assert len(assignments["prob2"]) == 1
