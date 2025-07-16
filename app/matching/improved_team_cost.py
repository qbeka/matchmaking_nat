from typing import Dict, List
import numpy as np

from app.models import Problem
from app.matching.improved_cost import (
    calculate_improved_skill_match_cost,
    calculate_improved_role_alignment_cost,
    calculate_improved_motivation_fit_cost,
    calculate_improved_ambiguity_fit_cost,
    calculate_improved_workload_fit_cost,
    calculate_team_synergy_bonus,
    IMPROVED_WEIGHTS
)

class ImprovedTeamVector:
    """Improved team aggregation with better statistical methods."""
    
    def __init__(self, team_id: str, members: List[Dict]):
        self.team_id = team_id
        self.members = members
        self.size = len(members)
        
        # Calculate aggregated team properties
        self._calculate_team_properties()
    
    def _calculate_team_properties(self):
        """Calculate improved team aggregation properties."""
        if not self.members:
            self._set_empty_defaults()
            return
        
        # 1. Skill aggregation using weighted coverage approach
        self.skill_coverage = self._calculate_skill_coverage()
        self.skill_strength = self._calculate_skill_strength()
        
        # 2. Role coverage and balance
        self.role_coverage = self._calculate_role_coverage()
        self.role_weights = self._calculate_role_weights()
        
        # 3. Availability (use minimum as bottleneck, but consider distribution)
        availabilities = [m.get("hours_per_week", 20) for m in self.members]
        self.min_availability = min(availabilities)
        self.avg_availability = sum(availabilities) / len(availabilities)
        
        # 4. Motivation embedding (using median for robustness)
        self.motivation_embedding = self._calculate_robust_motivation_embedding()
        
        # 5. Ambiguity tolerance (using team consensus approach)
        self.ambiguity_tolerance = self._calculate_team_ambiguity_tolerance()
        
        # 6. Team synergy factor
        self.synergy_bonus = calculate_team_synergy_bonus(self.members)
    
    def _set_empty_defaults(self):
        """Set default values for empty teams."""
        self.skill_coverage = {}
        self.skill_strength = {}
        self.role_coverage = {}
        self.role_weights = {}
        self.min_availability = 0
        self.avg_availability = 0
        self.motivation_embedding = None
        self.ambiguity_tolerance = 0.5
        self.synergy_bonus = 0.0
    
    def _calculate_skill_coverage(self) -> Dict[str, float]:
        """Calculate what skills the team covers and how well."""
        skill_coverage = {}
        
        for member in self.members:
            member_skills = member.get("self_rated_skills", {})
            for skill, level in member_skills.items():
                if skill not in skill_coverage:
                    skill_coverage[skill] = level
                else:
                    # Use max level available in team for each skill
                    skill_coverage[skill] = max(skill_coverage[skill], level)
        
        return skill_coverage
    
    def _calculate_skill_strength(self) -> Dict[str, float]:
        """Calculate average skill strength for skills the team has."""
        skill_totals = {}
        skill_counts = {}
        
        for member in self.members:
            member_skills = member.get("self_rated_skills", {})
            for skill, level in member_skills.items():
                if skill not in skill_totals:
                    skill_totals[skill] = 0
                    skill_counts[skill] = 0
                skill_totals[skill] += level
                skill_counts[skill] += 1
        
        return {
            skill: skill_totals[skill] / skill_counts[skill]
            for skill in skill_totals
        }
    
    def _calculate_role_coverage(self) -> Dict[str, int]:
        """Calculate role coverage in the team."""
        role_counts = {}
        
        for member in self.members:
            member_roles = member.get("primary_roles", [])
            for role in member_roles:
                role_counts[role] = role_counts.get(role, 0) + 1
        
        return role_counts
    
    def _calculate_role_weights(self) -> Dict[str, float]:
        """Calculate normalized role weights."""
        role_counts = self._calculate_role_coverage()
        total_role_assignments = sum(role_counts.values())
        
        if total_role_assignments == 0:
            return {}
        
        return {
            role: count / total_role_assignments
            for role, count in role_counts.items()
        }
    
    def _calculate_robust_motivation_embedding(self):
        """Calculate robust team motivation embedding using median approach."""
        embeddings = []
        for member in self.members:
            embedding = member.get("motivation_embedding")
            if embedding is not None:
                embeddings.append(np.array(embedding))
        
        if not embeddings:
            return None
        
        # Use median for robustness against outliers
        stacked_embeddings = np.stack(embeddings)
        return np.median(stacked_embeddings, axis=0)
    
    def _calculate_team_ambiguity_tolerance(self) -> float:
        """Calculate team's collective ambiguity tolerance."""
        tolerances = [
            member.get("ambiguity_tolerance", 0.5) 
            for member in self.members
        ]
        
        # Use median for team consensus (more robust than mean)
        tolerances_array = np.array(tolerances)
        return float(np.median(tolerances_array))

async def compute_improved_team_problem_cost(
    team_members: List[Dict],
    problem: Problem,
    weights: Dict[str, float] = None
) -> float:
    """
    Calculate improved cost between a team and a problem.
    Returns value between 0-1, where 0 is perfect match.
    """
    if weights is None:
        weights = IMPROVED_WEIGHTS
    
    # Create improved team vector
    team_vector = ImprovedTeamVector("temp", team_members)
    
    # Extract problem properties
    problem_skills = problem.required_skills or {}
    problem_roles = problem.role_preferences or {}
    problem_embedding = problem.problem_embedding
    problem_ambiguity = problem.expected_ambiguity or 0.5
    problem_hours = problem.expected_hours_per_week or 20
    
    # 1. Improved Skill Match Cost
    skill_cost = calculate_improved_skill_match_cost(
        team_vector.skill_coverage,
        problem_skills
    )
    
    # Apply skill strength bonus (teams with higher average skills get bonus)
    if problem_skills and team_vector.skill_strength:
        avg_team_skill = np.mean([
            team_vector.skill_strength.get(skill, 0) 
            for skill in problem_skills.keys()
        ])
        skill_strength_bonus = min(0.1, avg_team_skill / 50.0)  # Max 10% bonus
        skill_cost = max(0.0, skill_cost - skill_strength_bonus)
    
    # 2. Improved Role Alignment Cost
    role_cost = calculate_improved_role_alignment_cost(
        team_vector.role_weights,
        problem_roles
    )
    
    # 3. Improved Motivation Fit Cost
    motivation_cost = calculate_improved_motivation_fit_cost(
        team_vector.motivation_embedding,
        np.array(problem_embedding) if problem_embedding else None
    )
    
    # 4. Improved Ambiguity Fit Cost
    ambiguity_cost = calculate_improved_ambiguity_fit_cost(
        team_vector.ambiguity_tolerance,
        problem_ambiguity
    )
    
    # 5. Improved Workload Fit Cost (use minimum availability as constraint)
    workload_cost = calculate_improved_workload_fit_cost(
        team_vector.min_availability,
        problem_hours
    )
    
    # Apply team size efficiency bonus/penalty
    size_factor = _calculate_team_size_efficiency(team_vector.size, problem)
    
    # Calculate base cost
    base_cost = (
        weights.get("skill_match", 0.4) * skill_cost +
        weights.get("role_alignment", 0.25) * role_cost +
        weights.get("motivation_fit", 0.15) * motivation_cost +
        weights.get("ambiguity_fit", 0.1) * ambiguity_cost +
        weights.get("workload_fit", 0.1) * workload_cost
    )
    
    # Apply bonuses and penalties
    final_cost = base_cost * size_factor - team_vector.synergy_bonus
    
    # Ensure cost is in valid range
    return max(0.0, min(1.0, final_cost))

def _calculate_team_size_efficiency(team_size: int, problem: Problem) -> float:
    """
    Calculate team size efficiency factor.
    Returns multiplier between 0.8-1.2 based on team size appropriateness.
    """
    # Get ideal team size for problem (default to 3)
    ideal_size = getattr(problem, 'ideal_team_size', 3)
    
    if team_size == ideal_size:
        return 0.9  # 10% bonus for perfect size
    elif abs(team_size - ideal_size) == 1:
        return 0.95  # 5% bonus for close to ideal
    elif team_size < ideal_size:
        # Penalty for undersized teams
        deficit = ideal_size - team_size
        return 1.0 + min(0.2, deficit * 0.1)  # Max 20% penalty
    else:
        # Penalty for oversized teams
        excess = team_size - ideal_size
        return 1.0 + min(0.15, excess * 0.05)  # Max 15% penalty

def calculate_improved_team_metrics(team_members: List[Dict]) -> Dict[str, float]:
    """
    Calculate improved team metrics for display in dashboard.
    """
    if not team_members:
        return {
            "diversity_score": 0.0,
            "skills_covered": 0.0,
            "role_coverage": 0.0,
            "role_balance_flag": False,
            "confidence_score": 0.0,
            "synergy_score": 0.0
        }
    
    team_vector = ImprovedTeamVector("temp", team_members)
    
    # Skills coverage (percentage of important skills covered)
    from app.matching.improved_cost import SKILL_IMPORTANCE
    important_skills = set(SKILL_IMPORTANCE.keys())
    covered_skills = set(team_vector.skill_coverage.keys())
    skills_covered = len(covered_skills.intersection(important_skills)) / len(important_skills)
    
    # Role coverage
    all_roles = {"fullstack", "frontend", "backend", "data_science", "devops"}
    covered_roles = set(team_vector.role_coverage.keys())
    role_coverage = len(covered_roles) / len(all_roles)
    
    # Diversity score (weighted combination of role and skill diversity)
    diversity_score = 0.6 * role_coverage + 0.4 * skills_covered
    
    # Role balance (check if any role dominates too much)
    if team_vector.role_coverage:
        max_role_count = max(team_vector.role_coverage.values())
        role_balance_flag = max_role_count <= max(2, len(team_members) * 0.6)
    else:
        role_balance_flag = False
    
    # Confidence score (average skill level)
    if team_vector.skill_strength:
        avg_skill_level = np.mean(list(team_vector.skill_strength.values()))
        confidence_score = min(1.0, avg_skill_level / 5.0)  # Normalize to 0-1
    else:
        confidence_score = 0.0
    
    return {
        "diversity_score": diversity_score,
        "skills_covered": skills_covered,
        "role_coverage": role_coverage,
        "role_balance_flag": role_balance_flag,
        "confidence_score": confidence_score,
        "synergy_score": team_vector.synergy_bonus * 5  # Scale for display
    } 