import pytest
import numpy as np
from app.matching.cost import (
    calculate_skill_gap_cost,
    calculate_role_alignment_cost,
    calculate_motivation_similarity_cost,
    calculate_ambiguity_fit_cost,
    calculate_workload_fit_cost,
)

# Mock data
PARTICIPANT_SKILLS = {"Python": 0.8, "JavaScript": 0.6}
PROBLEM_SKILLS = {"Python": 0.9, "SQL": 0.7}
PARTICIPANT_ROLES = {"backend_dev": 1.0, "data_scientist": 1.0} # Assuming weights for role alignment
PROBLEM_ROLES = {"backend_dev": 0.6, "frontend_dev": 0.4}
P_EMBEDDING = np.array([0.1, 0.2, 0.3])
Q_EMBEDDING = np.array([0.4, 0.5, 0.6])
P_TOLERANCE = 0.7
Q_AMBIGUITY = 0.4
P_AVAILABILITY = 30
Q_HOURS = 32

def test_skill_gap_cost():
    # Python gap: 0.9 - 0.8 = 0.1
    # SQL gap: 0.7 - 0.0 = 0.7
    # Mean gap: (0.1 + 0.7) / 2 = 0.4
    cost = calculate_skill_gap_cost(PARTICIPANT_SKILLS, PROBLEM_SKILLS)
    assert cost == pytest.approx(0.4, abs=1e-6)

def test_role_alignment_cost():
    # Alignment: backend_dev (0.6 * 1.0) + data_scientist (0.0 * 1.0) = 0.6
    # Cost (1 - alignment): 1.0 - 0.6 = 0.4
    cost = calculate_role_alignment_cost(PARTICIPANT_ROLES, PROBLEM_ROLES)
    assert cost == pytest.approx(0.4, abs=1e-6)

def test_motivation_similarity_cost():
    # Cosine distance between [0.1, 0.2, 0.3] and [0.4, 0.5, 0.6] is approx 0.025
    cost = calculate_motivation_similarity_cost(P_EMBEDDING, Q_EMBEDDING)
    assert cost == pytest.approx(0.02537, abs=1e-4)

def test_ambiguity_fit_cost():
    # Mismatch: |0.7 - 0.4| = 0.3
    cost = calculate_ambiguity_fit_cost(P_TOLERANCE, Q_AMBIGUITY)
    assert cost == pytest.approx(0.3, abs=1e-6)

def test_workload_fit_cost():
    # Required: 32h, Available: 30h. Mismatch: (32-30)/40 = 0.05
    cost = calculate_workload_fit_cost(P_AVAILABILITY, Q_HOURS)
    assert cost == pytest.approx(0.05, abs=1e-6)
