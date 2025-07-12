from typing import Any, Dict, List, Optional
import numpy as np
from scipy.optimize import linear_sum_assignment
from app.matching.pairwise import participant_pair_cost
from app.config import ALLOWED_ROLES


def solve_team_slots(
    teams: List[List[Dict[str, Any]]], 
    available_participants: List[Dict[str, Any]],
    target_team_size: int = 4,
    role_coverage_threshold: float = 0.6
) -> List[List[Dict[str, Any]]]:
    """
    Fill team slots using linear assignment while enforcing role coverage constraints.
    
    Args:
        teams: List of existing teams (may be incomplete)
        available_participants: Pool of participants to assign to slots
        target_team_size: Target size for each team
        role_coverage_threshold: Minimum role coverage required (0-1)
        
    Returns:
        List of completed teams with filled slots
    """
    completed_teams = []
    
    # Build set of all participants already assigned to teams
    already_assigned = set()
    for team in teams:
        for member in team:
            already_assigned.add(member.get("_id"))
    
    # Create pool of truly available participants (not already in teams)
    remaining_participants = [
        p for p in available_participants 
        if p.get("_id") not in already_assigned
    ]
    
    for team in teams:
        if len(team) >= target_team_size:
            # Team is already complete
            completed_teams.append(team)
            continue
        
        # Calculate how many slots to fill
        slots_needed = target_team_size - len(team)
        
        if slots_needed <= 0:
            completed_teams.append(team)
            continue
        
        # Find best participants to fill slots
        filled_team = _fill_team_slots(
            team, 
            remaining_participants, 
            slots_needed,
            role_coverage_threshold
        )
        
        completed_teams.append(filled_team)
        
        # Remove assigned participants from remaining pool
        assigned_ids = set(p.get("_id") for p in filled_team[len(team):])
        remaining_participants = [
            p for p in remaining_participants 
            if p.get("_id") not in assigned_ids
        ]
    
    return completed_teams


def _fill_team_slots(
    existing_team: List[Dict[str, Any]], 
    candidate_pool: List[Dict[str, Any]], 
    slots_needed: int,
    role_coverage_threshold: float
) -> List[Dict[str, Any]]:
    """
    Fill slots in a team using linear assignment optimization.
    """
    if not candidate_pool or slots_needed <= 0:
        return existing_team
    
    # Limit candidates to available pool size
    slots_to_fill = min(slots_needed, len(candidate_pool))
    
    if slots_to_fill == 1:
        # Simple case: find best single candidate
        best_candidate = _find_best_single_candidate(existing_team, candidate_pool)
        if best_candidate:
            return existing_team + [best_candidate]
        return existing_team
    
    # Build cost matrix for assignment
    cost_matrix = _build_slot_cost_matrix(existing_team, candidate_pool, slots_to_fill)
    
    # Solve assignment problem
    row_indices, col_indices = linear_sum_assignment(cost_matrix)
    
    # Extract assigned participants
    assigned_participants = [candidate_pool[col_idx] for col_idx in col_indices]
    
    # Check role coverage constraint
    new_team = existing_team + assigned_participants
    if not _meets_role_coverage(new_team, role_coverage_threshold):
        # Try to improve role coverage
        improved_team = _improve_role_coverage(
            existing_team, 
            candidate_pool, 
            slots_to_fill, 
            role_coverage_threshold
        )
        if improved_team:
            return improved_team
    
    return new_team


def _build_slot_cost_matrix(
    existing_team: List[Dict[str, Any]], 
    candidates: List[Dict[str, Any]], 
    slots_to_fill: int
) -> np.ndarray:
    """
    Build cost matrix for slot assignment problem.
    """
    num_candidates = len(candidates)
    
    # Create square matrix (pad with high cost if needed)
    matrix_size = max(slots_to_fill, num_candidates)
    cost_matrix = np.full((matrix_size, matrix_size), 1e6)  # High cost for padding
    
    # Fill actual costs
    for slot_idx in range(slots_to_fill):
        for candidate_idx, candidate in enumerate(candidates):
            cost = _calculate_slot_assignment_cost(existing_team, candidate)
            cost_matrix[slot_idx, candidate_idx] = cost
    
    return cost_matrix


def _calculate_slot_assignment_cost(
    existing_team: List[Dict[str, Any]], 
    candidate: Dict[str, Any]
) -> float:
    """
    Calculate the cost of assigning a candidate to a team slot.
    """
    if not existing_team:
        return 0.0  # No cost for first team member
    
    # Calculate average pairwise cost with existing team members
    total_cost = 0.0
    for team_member in existing_team:
        total_cost += participant_pair_cost(candidate, team_member)
    
    avg_cost = total_cost / len(existing_team)
    
    # Add role diversity bonus
    role_bonus = _calculate_role_diversity_bonus(existing_team, candidate)
    
    # Add skill complementarity bonus
    skill_bonus = _calculate_skill_complementarity_bonus(existing_team, candidate)
    
    # Final cost (lower is better)
    final_cost = avg_cost - 0.1 * role_bonus - 0.1 * skill_bonus
    
    return max(0.0, final_cost)


def _calculate_role_diversity_bonus(
    existing_team: List[Dict[str, Any]], 
    candidate: Dict[str, Any]
) -> float:
    """
    Calculate bonus for role diversity contribution.
    """
    existing_roles = set()
    for member in existing_team:
        existing_roles.update(member.get("primary_roles", []))
    
    candidate_roles = set(candidate.get("primary_roles", []))
    new_roles = candidate_roles - existing_roles
    
    # Bonus proportional to number of new roles added
    return len(new_roles) / max(1, len(candidate_roles))


def _calculate_skill_complementarity_bonus(
    existing_team: List[Dict[str, Any]], 
    candidate: Dict[str, Any]
) -> float:
    """
    Calculate bonus for skill complementarity.
    """
    existing_skills = set()
    for member in existing_team:
        existing_skills.update(member.get("enriched_skills", {}).keys())
    
    candidate_skills = set(candidate.get("enriched_skills", {}).keys())
    new_skills = candidate_skills - existing_skills
    
    # Bonus proportional to number of new skills added
    return len(new_skills) / max(1, len(candidate_skills))


def _find_best_single_candidate(
    existing_team: List[Dict[str, Any]], 
    candidates: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Find the best single candidate to add to a team.
    """
    if not candidates:
        return None
    
    best_candidate = None
    best_cost = float('inf')
    
    for candidate in candidates:
        cost = _calculate_slot_assignment_cost(existing_team, candidate)
        if cost < best_cost:
            best_cost = cost
            best_candidate = candidate
    
    return best_candidate


def _meets_role_coverage(team: List[Dict[str, Any]], threshold: float) -> bool:
    """
    Check if team meets minimum role coverage requirement.
    """
    if not team:
        return False
    
    covered_roles = set()
    for member in team:
        covered_roles.update(member.get("primary_roles", []))
    
    coverage_ratio = len(covered_roles) / len(ALLOWED_ROLES)
    return coverage_ratio >= threshold


def _improve_role_coverage(
    existing_team: List[Dict[str, Any]], 
    candidate_pool: List[Dict[str, Any]], 
    slots_to_fill: int,
    role_coverage_threshold: float
) -> Optional[List[Dict[str, Any]]]:
    """
    Try to improve role coverage by selecting candidates with missing roles.
    """
    existing_roles = set()
    for member in existing_team:
        existing_roles.update(member.get("primary_roles", []))
    
    missing_roles = set(ALLOWED_ROLES) - existing_roles
    
    if not missing_roles:
        return None  # Already have good coverage
    
    # Find candidates that can fill missing roles
    role_filling_candidates = []
    for candidate in candidate_pool:
        candidate_roles = set(candidate.get("primary_roles", []))
        if candidate_roles & missing_roles:  # Has at least one missing role
            role_filling_candidates.append(candidate)
    
    if not role_filling_candidates:
        return None
    
    # Greedily select candidates to maximize role coverage
    selected_candidates = []
    remaining_missing_roles = missing_roles.copy()
    
    for _ in range(min(slots_to_fill, len(role_filling_candidates))):
        best_candidate = None
        best_new_roles = 0
        
        for candidate in role_filling_candidates:
            if candidate in selected_candidates:
                continue
            
            candidate_roles = set(candidate.get("primary_roles", []))
            new_roles_count = len(candidate_roles & remaining_missing_roles)
            
            if new_roles_count > best_new_roles:
                best_new_roles = new_roles_count
                best_candidate = candidate
        
        if best_candidate:
            selected_candidates.append(best_candidate)
            candidate_roles = set(best_candidate.get("primary_roles", []))
            remaining_missing_roles -= candidate_roles
    
    # Fill remaining slots with best available candidates
    remaining_slots = slots_to_fill - len(selected_candidates)
    if remaining_slots > 0:
        available_candidates = [
            c for c in candidate_pool 
            if c not in selected_candidates
        ]
        
        for _ in range(min(remaining_slots, len(available_candidates))):
            best_candidate = _find_best_single_candidate(
                existing_team + selected_candidates, 
                available_candidates
            )
            if best_candidate:
                selected_candidates.append(best_candidate)
                available_candidates.remove(best_candidate)
    
    new_team = existing_team + selected_candidates
    
    # Check if we achieved the coverage threshold
    if _meets_role_coverage(new_team, role_coverage_threshold):
        return new_team
    
    return None


def calculate_team_coverage_metrics(team: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate coverage metrics for a team.
    
    Args:
        team: List of participant dictionaries
        
    Returns:
        Dictionary containing coverage metrics
    """
    if not team:
        return {
            "role_coverage": 0.0,
            "skill_coverage": 0.0,
            "diversity_score": 0.0,
            "confidence_score": 0.0,
            "role_balance_flag": False
        }
    
    # Role coverage
    covered_roles = set()
    for member in team:
        covered_roles.update(member.get("primary_roles", []))
    role_coverage = len(covered_roles) / len(ALLOWED_ROLES)
    
    # Skill coverage (normalized to 0-1 range)
    covered_skills = set()
    for member in team:
        covered_skills.update(member.get("enriched_skills", {}).keys())
    skill_coverage = len(covered_skills) / max(1, len(team))
    skill_coverage_normalized = min(1.0, skill_coverage / 3.0)  # Normalize assuming max ~3 skills per person
    
    # Diversity score (based on role and skill diversity)
    diversity_score = (role_coverage + skill_coverage_normalized) / 2.0
    
    # Confidence score (based on average skill levels)
    total_skill_level = 0.0
    total_skills = 0
    for member in team:
        skills = member.get("enriched_skills", {})
        for skill_data in skills.values():
            total_skill_level += skill_data.get("mean", 0.0)
            total_skills += 1
    
    confidence_score = total_skill_level / max(1, total_skills) / 5.0  # Normalize to 0-1
    
    # Role balance flag (check if team has reasonable role distribution)
    role_counts: Dict[str, int] = {}
    for member in team:
        for role in member.get("primary_roles", []):
            role_counts[role] = role_counts.get(role, 0) + 1
    
    # Team is balanced if no single role dominates too much
    max_role_count = max(role_counts.values()) if role_counts else 0
    role_balance_flag = max_role_count <= len(team) * 0.6  # No role > 60% of team
    
    return {
        "role_coverage": role_coverage,
        "skill_coverage": skill_coverage,
        "diversity_score": diversity_score,
        "confidence_score": confidence_score,
        "role_balance_flag": role_balance_flag
    }
