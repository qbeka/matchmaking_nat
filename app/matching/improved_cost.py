from typing import Any, Dict, Optional
import numpy as np
from scipy.spatial.distance import cosine

# Improved weights for better balance (sum should equal 1.0)
IMPROVED_WEIGHTS = {
    "skill_match": 0.40,      # Increased focus on skill matching
    "role_alignment": 0.25,   # Balanced role importance  
    "motivation_fit": 0.15,   # Moderate motivation importance
    "ambiguity_fit": 0.10,    # Lower ambiguity weight
    "workload_fit": 0.10,     # Lower workload weight
}

# Skills importance weights (some skills are more critical than others)
SKILL_IMPORTANCE = {
    "python": 1.0,
    "javascript": 1.0, 
    "react": 0.9,
    "typescript": 0.8,
    "sql": 0.9,
    "nosql": 0.7,
    "aws": 0.8,
    "gcp": 0.8,
    "azure": 0.8,
    "docker": 0.7,
    "kubernetes": 0.6,
    "fastapi": 0.7,
    "machine_learning": 0.9,
    "data_analysis": 0.8,
}

def calculate_improved_skill_match_cost(
    participant_skills: Dict[str, float], 
    problem_skills: Dict[str, float]
) -> float:
    """
    Improved skill matching using weighted coverage and competency.
    Returns value between 0-1, where 0 is perfect match.
    """
    if not problem_skills:
        return 0.0
    
    total_weighted_gap = 0.0
    total_weight = 0.0
    coverage_bonus = 0.0
    
    for skill, required_level in problem_skills.items():
        # Get skill importance (default to 0.5 for unknown skills)
        importance = SKILL_IMPORTANCE.get(skill, 0.5)
        participant_level = participant_skills.get(skill, 0.0)
        
        # Calculate skill gap (0 means perfect match, 5 means maximum gap)
        skill_gap = max(0, required_level - participant_level)
        
        # Apply importance weighting
        weighted_gap = skill_gap * importance
        total_weighted_gap += weighted_gap
        total_weight += importance * required_level
        
        # Bonus for having the skill at all (even if not perfect level)
        if participant_level > 0:
            coverage_bonus += importance * 0.1  # 10% bonus per covered skill
    
    # Normalize by total possible weighted gap
    if total_weight > 0:
        normalized_gap = total_weighted_gap / total_weight
        # Apply coverage bonus (reduces cost)
        final_cost = max(0.0, normalized_gap - coverage_bonus)
        return min(1.0, final_cost)
    
    return 0.0

def calculate_improved_role_alignment_cost(
    participant_roles: Dict[str, float], 
    problem_roles: Dict[str, float]
) -> float:
    """
    Improved role alignment using better matching algorithm.
    Returns value between 0-1, where 0 is perfect alignment.
    """
    if not problem_roles or not participant_roles:
        return 0.5  # Neutral cost if no role info
    
    # Calculate role coverage score
    coverage_score = 0.0
    total_required_weight = sum(problem_roles.values())
    
    for role, required_weight in problem_roles.items():
        participant_weight = participant_roles.get(role, 0.0)
        
        # Calculate match quality for this role
        if required_weight > 0:
            match_ratio = min(1.0, participant_weight / required_weight)
            coverage_score += match_ratio * required_weight
    
    # Normalize by total required weight
    if total_required_weight > 0:
        final_alignment = coverage_score / total_required_weight
        return 1.0 - final_alignment  # Convert to cost (lower is better)
    
    return 0.5

def calculate_improved_motivation_fit_cost(
    participant_embedding: np.ndarray, 
    problem_embedding: np.ndarray
) -> float:
    """
    Improved motivation similarity using better distance calculation.
    Returns value between 0-1, where 0 is perfect similarity.
    """
    if participant_embedding is None or problem_embedding is None:
        return 0.3  # Neutral cost instead of maximum penalty
    
    try:
        # Ensure arrays are the same length
        if len(participant_embedding) != len(problem_embedding):
            return 0.5
        
        # Use cosine similarity (1 - cosine_distance)
        similarity = 1.0 - cosine(participant_embedding, problem_embedding)
        
        # Convert similarity to cost (invert and normalize)
        cost = (1.0 - similarity) / 2.0  # Scale to 0-0.5 range
        return max(0.0, min(1.0, cost))
        
    except (ValueError, TypeError, ZeroDivisionError):
        return 0.3

def calculate_improved_ambiguity_fit_cost(
    participant_tolerance: float, 
    problem_ambiguity: float
) -> float:
    """
    Improved ambiguity fit with better tolerance handling.
    Returns value between 0-1, where 0 is perfect fit.
    """
    # Normalize inputs to 0-1 range if needed
    participant_tolerance = max(0.0, min(1.0, participant_tolerance))
    problem_ambiguity = max(0.0, min(1.0, problem_ambiguity))
    
    # Calculate absolute difference
    diff = abs(participant_tolerance - problem_ambiguity)
    
    # Apply tolerance - small differences should have minimal cost
    if diff <= 0.2:  # 20% tolerance
        return diff * 0.5  # Reduced penalty for small differences
    else:
        return 0.1 + (diff - 0.2) * 1.125  # Progressive penalty for larger differences

def calculate_improved_workload_fit_cost(
    participant_availability: int, 
    problem_hours: int
) -> float:
    """
    Improved workload fit with better availability matching.
    Returns value between 0-1, where 0 is perfect fit.
    """
    if participant_availability <= 0 or problem_hours <= 0:
        return 0.2  # Small penalty for missing data
    
    # Calculate workload ratio
    workload_ratio = problem_hours / participant_availability
    
    if workload_ratio <= 1.0:
        # Participant has enough availability
        # Small cost for underutilization
        return max(0.0, (1.0 - workload_ratio) * 0.2)
    else:
        # Participant doesn't have enough availability
        # Progressive penalty for overload
        overload = workload_ratio - 1.0
        return min(1.0, 0.1 + overload * 0.6)

def compute_improved_individual_cost(
    participant: Dict[str, Any], 
    problem: Dict[str, Any], 
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Compute improved total cost for assigning a participant to a problem.
    Returns value between 0-1, where 0 is perfect match.
    """
    if weights is None:
        weights = IMPROVED_WEIGHTS
    
    # Extract data with better defaults
    participant_skills = participant.get("self_rated_skills", {})
    participant_roles = {}
    
    # Convert role list to weights (assuming equal weight for each role)
    roles = participant.get("primary_roles", [])
    if roles:
        role_weight = 1.0 / len(roles)
        participant_roles = {role: role_weight for role in roles}
    
    participant_embedding = participant.get("motivation_embedding")
    participant_tolerance = participant.get("ambiguity_tolerance", 0.5)
    participant_availability = participant.get("hours_per_week", 20)
    
    problem_skills = problem.get("required_skills", {})
    problem_roles = problem.get("role_preferences", {})
    problem_embedding = problem.get("problem_embedding")
    problem_ambiguity = problem.get("expected_ambiguity", 0.5)
    problem_hours = problem.get("expected_hours_per_week", 20)
    
    # Convert embeddings to numpy arrays if they exist
    if participant_embedding is not None:
        participant_embedding = np.array(participant_embedding)
    if problem_embedding is not None:
        problem_embedding = np.array(problem_embedding)
    
    # Calculate improved individual costs
    skill_cost = calculate_improved_skill_match_cost(participant_skills, problem_skills)
    role_cost = calculate_improved_role_alignment_cost(participant_roles, problem_roles)
    motivation_cost = calculate_improved_motivation_fit_cost(participant_embedding, problem_embedding)
    ambiguity_cost = calculate_improved_ambiguity_fit_cost(participant_tolerance, problem_ambiguity)
    workload_cost = calculate_improved_workload_fit_cost(participant_availability, problem_hours)
    
    # Calculate weighted sum
    total_cost = (
        weights.get("skill_match", 0.4) * skill_cost +
        weights.get("role_alignment", 0.25) * role_cost +
        weights.get("motivation_fit", 0.15) * motivation_cost +
        weights.get("ambiguity_fit", 0.1) * ambiguity_cost +
        weights.get("workload_fit", 0.1) * workload_cost
    )
    
    # Ensure cost is in valid range
    return max(0.0, min(1.0, total_cost))

def calculate_team_synergy_bonus(team_members: list) -> float:
    """
    Calculate team synergy bonus based on complementary skills and roles.
    Returns value between 0-0.2 that reduces total team cost.
    """
    if len(team_members) <= 1:
        return 0.0
    
    # Skill complementarity bonus
    all_skills = set()
    skill_overlap = 0
    total_skills = 0
    
    for member in team_members:
        member_skills = set(member.get("self_rated_skills", {}).keys())
        skill_overlap += len(all_skills.intersection(member_skills))
        all_skills.update(member_skills)
        total_skills += len(member_skills)
    
    # Lower overlap means better complementarity
    if total_skills > 0:
        overlap_ratio = skill_overlap / total_skills
        skill_bonus = max(0.0, 0.1 * (1.0 - overlap_ratio))
    else:
        skill_bonus = 0.0
    
    # Role diversity bonus
    all_roles = set()
    for member in team_members:
        all_roles.update(member.get("primary_roles", []))
    
    role_diversity = len(all_roles) / len(team_members)
    role_bonus = min(0.1, role_diversity * 0.05)
    
    return skill_bonus + role_bonus 