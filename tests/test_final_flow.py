import pytest
import numpy as np
from unittest.mock import patch, MagicMock, AsyncMock

from app.matching.build_team_problem_matrix import build_team_problem_matrix
from app.matching.final_hungarian import (
    solve_final_assignment,
    store_final_assignments,
    calculate_assignment_statistics,
    validate_assignment,
)

# Mock data fixtures
@pytest.fixture
def mock_teams():
    # Using MagicMock to simulate the Team model objects
    teams = []
    for i in range(3):
        team = MagicMock()
        team.id = f"team_{i}"
        team.participant_ids = [f"p{i}_1", f"p{i}_2"]
        teams.append(team)
    return teams

@pytest.fixture
def mock_problems():
    # Using MagicMock to simulate the Problem model objects
    problems = []
    for i in range(3):
        problem = MagicMock()
        problem.id = f"problem_{i}"
        problem.required_skills = {"skill1": 4}
        problem.role_preferences = {"role1": 1.0}
        problem.expected_ambiguity = 0.5
        problem.expected_hours_per_week = 20
        problem.problem_embedding = [0.1] * 10
        problems.append(problem)
    return problems

@pytest.fixture
def mock_participants():
    # Using MagicMock to simulate Participant model objects
    participants = []
    for i in range(6):
        p = MagicMock()
        p.id = f"p{i // 2}_{i % 2 + 1}"
        p.computed_skills = {"skill1": MagicMock(posterior=MagicMock(mean=4.0))}
        p.roles = ["role1"]
        p.availability = 25
        p.motivation_embedding = [0.1] * 10
        p.gpt_traits = MagicMock(ambiguity_tolerance=0.5)
        participants.append(p)
    return participants

@pytest.mark.asyncio
@patch("app.matching.build_team_problem_matrix.get_all_final_teams")
@patch("app.matching.build_team_problem_matrix.get_all_problems")
@patch("app.matching.build_team_problem_matrix.get_participants_for_team")
async def test_build_matrix_end_to_end(
    mock_get_participants, mock_get_problems, mock_get_teams,
    mock_teams, mock_problems, mock_participants
):
    mock_get_teams.return_value = mock_teams
    mock_get_problems.return_value = mock_problems
    mock_get_participants.return_value = mock_participants[:2] # Assume 2 participants per team

    cost_matrix, team_map, problem_map = await build_team_problem_matrix()

    assert cost_matrix.shape == (3, 3)
    assert len(team_map) == 3
    assert len(problem_map) == 3
    assert not np.any(cost_matrix == 1e6) # No padding costs

@pytest.mark.asyncio
async def test_solve_assignment():
    cost_matrix = np.array([[1, 4, 5], [2, 3, 6], [7, 8, 9]])
    team_map = {0: "t0", 1: "t1", 2: "t2"}
    problem_map = {0: "p0", 1: "p1", 2: "p2"}

    mapping, total_cost = await solve_final_assignment(cost_matrix, team_map, problem_map)

    assert total_cost == 1 + 3 + 9
    assert mapping == {"p0": "t0", "p1": "t1", "p2": "t2"}

@pytest.mark.asyncio
async def test_uneven_teams_problems():
    cost_matrix = np.array([
        [1, 8, 1e6],
        [2, 3, 1e6]
    ])
    team_map = {0: "t0", 1: "t1"}
    problem_map = {0: "p0", 1: "p1"}

    mapping, total_cost = await solve_final_assignment(cost_matrix, team_map, problem_map)
    assert len(mapping) == 2
    assert "p0" in mapping
    assert "p1" in mapping

@pytest.mark.asyncio
async def test_validation_logic():
    valid_map = {"p0": "t0", "p1": "t1"}
    invalid_map = {"p0": "t0", "p1": "t0"}
    
    res_valid = await validate_assignment(valid_map)
    assert res_valid["is_valid"]
    
    res_invalid = await validate_assignment(invalid_map)
    assert not res_invalid["is_valid"]

@pytest.mark.asyncio
async def test_stats_calculation():
    cost_matrix = np.array([[1, 2], [3, 4]])
    team_map = {0: "t0", 1: "t1"}
    problem_map = {0: "p0", 1: "p1"}
    assignment = {"p0": "t0", "p1": "t1"} # t0->p0 (cost 1), t1->p1 (cost 4)

    stats = await calculate_assignment_statistics(assignment, cost_matrix, team_map, problem_map)
    
    assert stats["mean_cost"] == 2.5
    assert stats["worst_case_cost"] == 4
    assert stats["best_case_cost"] == 1

@pytest.mark.asyncio
@patch("app.matching.final_hungarian.db")
async def test_store_assignments(mock_db):
    mock_db.assignments.insert_one = AsyncMock(return_value=MagicMock(inserted_id="test_id"))
    
    assignment_id = await store_final_assignments({"p0": "t0"}, 5.0)
    
    assert assignment_id == "test_id"
    mock_db.assignments.insert_one.assert_called_once()
    
# Add more tests for edge cases

@pytest.mark.asyncio
async def test_no_teams_or_problems():
    with patch("app.matching.build_team_problem_matrix.get_all_final_teams", return_value=[]), \
         patch("app.matching.build_team_problem_matrix.get_all_problems", return_value=[]):
        
        matrix, t_map, p_map = await build_team_problem_matrix()
        
        assert matrix.size == 0
        assert not t_map
        assert not p_map

@pytest.mark.asyncio
async def test_assignment_with_padding():
    # 2 teams, 3 problems
    cost_matrix = np.array([
        [1, 2, 3],
        [4, 5, 6],
        [1e6, 1e6, 1e6] # Padded row for fake team
    ])
    team_map = {0: "t0", 1: "t1"}
    problem_map = {0: "p0", 1: "p1", 2: "p2"}
    
    mapping, _ = await solve_final_assignment(cost_matrix, team_map, problem_map)
    
    # One problem will be unassigned (matched to the fake team)
    assert len(mapping) == 2
    
@pytest.mark.asyncio
async def test_empty_assignment_stats():
    stats = await calculate_assignment_statistics({}, np.array([]), {}, {})
    assert stats["mean_cost"] == 0
    assert stats["worst_case_cost"] == 0 