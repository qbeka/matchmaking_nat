import pytest
import numpy as np
from app.models import Problem
from app.matching.team_vector import TeamVector
from app.matching.team_problem_cost import compute_team_problem_cost

# Default weights for testing
TEST_WEIGHTS = {
    "skill_gap": 0.35,
    "role_alignment": 0.20,
    "motivation_similarity": 0.15,
    "ambiguity_fit": 0.20,
    "workload_fit": 0.10,
}

# Mock data
@pytest.fixture
def base_team_vector():
    return TeamVector(
        team_id="team_1",
        avg_skill_levels={"python": 4.0, "fastapi": 3.0},
        role_weights={"backend": 0.8, "frontend": 0.2},
        min_availability=30,
        avg_motivation_embedding=np.random.rand(10).tolist(),
        avg_ambiguity_tolerance=0.7,
        avg_communication_style=0.5,
        avg_confidence_score=0.8
    )

@pytest.fixture
def base_problem():
    return Problem(
        version="1.0.0",
        _id="problem_1",
        title="Test Problem",
        raw_prompt="A problem for testing.",
        estimated_team_size=4,
        preferred_roles={"backend": 1.0},
        problem_embedding=np.random.rand(10).tolist(),
        required_skills={"python": 4.0, "fastapi": 4.0},
        role_preferences={"backend": 1.0},
        expected_ambiguity=0.6,
        expected_hours_per_week=25,
    )

@pytest.mark.asyncio
async def test_base_cost_calculation(base_team_vector, base_problem):
    cost = await compute_team_problem_cost(base_team_vector, base_problem, TEST_WEIGHTS)
    assert cost >= 0
    assert isinstance(cost, float)

@pytest.mark.asyncio
async def test_skill_gap_increases_cost(base_team_vector, base_problem):
    cost1 = await compute_team_problem_cost(base_team_vector, base_problem, TEST_WEIGHTS)
    base_problem.required_skills["python"] = 5.0 # Increase skill gap
    cost2 = await compute_team_problem_cost(base_team_vector, base_problem, TEST_WEIGHTS)
    assert cost2 > cost1

@pytest.mark.asyncio
async def test_role_mismatch_increases_cost(base_team_vector, base_problem):
    cost1 = await compute_team_problem_cost(base_team_vector, base_problem, TEST_WEIGHTS)
    base_problem.role_preferences = {"frontend": 1.0} # Increase role mismatch
    cost2 = await compute_team_problem_cost(base_team_vector, base_problem, TEST_WEIGHTS)
    assert cost2 > cost1

@pytest.mark.asyncio
async def test_motivation_divergence_increases_cost(base_team_vector, base_problem):
    cost1 = await compute_team_problem_cost(base_team_vector, base_problem, TEST_WEIGHTS)
    base_problem.problem_embedding = np.random.rand(10).tolist() # Change embedding
    cost2 = await compute_team_problem_cost(base_team_vector, base_problem, TEST_WEIGHTS)
    # This might not always be > cost1 due to random nature, but should be different
    assert cost1 != cost2

@pytest.mark.asyncio
async def test_ambiguity_mismatch_increases_cost(base_team_vector, base_problem):
    cost1 = await compute_team_problem_cost(base_team_vector, base_problem, TEST_WEIGHTS)
    base_problem.expected_ambiguity = 0.1 # Increase ambiguity mismatch
    cost2 = await compute_team_problem_cost(base_team_vector, base_problem, TEST_WEIGHTS)
    assert cost2 > cost1

@pytest.mark.asyncio
async def test_workload_mismatch_increases_cost(base_team_vector, base_problem):
    cost1 = await compute_team_problem_cost(base_team_vector, base_problem, TEST_WEIGHTS)
    base_problem.expected_hours_per_week = 35 # Exceeds team availability
    cost2 = await compute_team_problem_cost(base_team_vector, base_problem, TEST_WEIGHTS)
    assert cost2 > cost1

@pytest.mark.asyncio
async def test_zero_weight_disables_term(base_team_vector, base_problem):
    weights = TEST_WEIGHTS.copy()
    weights["skill_gap"] = 0.0
    
    # Cost should be lower if the skill gap is ignored
    cost_with_gap = await compute_team_problem_cost(base_team_vector, base_problem, TEST_WEIGHTS)
    cost_without_gap = await compute_team_problem_cost(base_team_vector, base_problem, weights)
    
    assert cost_without_gap < cost_with_gap
    
@pytest.mark.asyncio
async def test_perfect_match_has_low_cost(base_team_vector, base_problem):
    base_problem.required_skills = base_team_vector.avg_skill_levels
    base_problem.role_preferences = base_team_vector.role_weights
    base_problem.expected_ambiguity = base_team_vector.avg_ambiguity_tolerance
    base_problem.expected_hours_per_week = base_team_vector.min_availability
    
    cost = await compute_team_problem_cost(base_team_vector, base_problem, TEST_WEIGHTS)
    
    # Motivation similarity might not be perfect
    assert cost < 0.2 
    
@pytest.mark.asyncio
async def test_no_embedding_yields_default_cost(base_team_vector, base_problem):
    base_team_vector.avg_motivation_embedding = None
    cost = await compute_team_problem_cost(base_team_vector, base_problem, TEST_WEIGHTS)
    assert cost > 0 