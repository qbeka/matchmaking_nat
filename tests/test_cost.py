import pytest

from app.matching.cost import compute_individual_cost

# Mock data for a participant and a problem
PARTICIPANT = {
    "enriched_skills": {
        "Python": {"mean": 0.8},
        "JavaScript": {"mean": 0.6},
    },
    "primary_roles": ["backend_dev", "data_scientist"],
    "motivation_embedding": [0.1, 0.2, 0.3],
    "ambiguity_tolerance": 0.7,
    "availability_hours": 30,
}

PROBLEM = {
    "required_skills": {"Python": 0.9, "SQL": 0.7},
    "preferred_roles": {"backend_dev": 0.6, "frontend_dev": 0.4},
    "prompt_embedding": [0.4, 0.5, 0.6],
    "ambiguity": 0.4,
    "complexity": 0.8,  # requires 0.8 * 40 = 32 hours
}


def test_skill_gap():
    cost = compute_individual_cost(PARTICIPANT, PROBLEM, weights={
        "skill_gap": 1.0, "role_alignment": 0.0, "motivation_similarity": 0.0,
        "ambiguity_fit": 0.0, "workload_fit": 0.0
    })
    # Python gap: 0.9 - 0.8 = 0.1
    # SQL gap: 0.7 - 0.0 = 0.7
    # Mean gap: (0.1 + 0.7) / 2 = 0.4
    assert cost == pytest.approx(0.4, abs=1e-6)


def test_role_alignment():
    cost = compute_individual_cost(PARTICIPANT, PROBLEM, weights={
        "skill_gap": 0.0, "role_alignment": 1.0, "motivation_similarity": 0.0,
        "ambiguity_fit": 0.0, "workload_fit": 0.0
    })
    # Alignment: backend_dev (0.6) + data_scientist (0.0) = 0.6
    # Cost (1 - alignment): 1.0 - 0.6 = 0.4
    assert cost == pytest.approx(0.4, abs=1e-6)


def test_motivation_similarity():
    cost = compute_individual_cost(PARTICIPANT, PROBLEM, weights={
        "skill_gap": 0.0, "role_alignment": 0.0, "motivation_similarity": 1.0,
        "ambiguity_fit": 0.0, "workload_fit": 0.0
    })
    # Cosine distance between [0.1, 0.2, 0.3] and [0.4, 0.5, 0.6] is approx 0.025
    assert cost == pytest.approx(0.02537, abs=1e-4)


def test_ambiguity_fit():
    cost = compute_individual_cost(PARTICIPANT, PROBLEM, weights={
        "skill_gap": 0.0, "role_alignment": 0.0, "motivation_similarity": 0.0,
        "ambiguity_fit": 1.0, "workload_fit": 0.0
    })
    # Mismatch: |0.7 - 0.4| = 0.3
    assert cost == pytest.approx(0.3, abs=1e-6)


def test_workload_fit():
    cost = compute_individual_cost(PARTICIPANT, PROBLEM, weights={
        "skill_gap": 0.0, "role_alignment": 0.0, "motivation_similarity": 0.0,
        "ambiguity_fit": 0.0, "workload_fit": 1.0
    })
    # Required: 32h, Available: 30h. Mismatch: (32-30)/40 = 0.05
    assert cost == pytest.approx(0.05, abs=1e-6)


def test_total_cost():
    total_cost = compute_individual_cost(PARTICIPANT, PROBLEM)
    expected = (
        0.35 * 0.4  # skill_gap
        + 0.20 * 0.4  # role_alignment
        + 0.15 * 0.02537  # motivation_similarity
        + 0.20 * 0.3  # ambiguity_fit
        + 0.10 * 0.05  # workload_fit
    )
    assert total_cost == pytest.approx(expected, abs=1e-6)
