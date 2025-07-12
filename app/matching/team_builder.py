from typing import Any, Dict, List
import math
from app.matching.kmedoids import k_medoids_clustering, assign_to_medoids
from app.matching.pairwise import participant_pair_cost


def build_provisional_teams(
    prelim_teams: List[List[Dict[str, Any]]], 
    desired_team_size: int = 4,
    max_iter: int = 100,
    random_seed: int = 42
) -> List[List[Dict[str, Any]]]:
    """
    Build provisional teams from preliminary clusters using k-medoids clustering.
    
    Args:
        prelim_teams: List of preliminary team clusters (each containing participant dicts)
        desired_team_size: Target size for each final team
        max_iter: Maximum iterations for k-medoids optimization
        random_seed: Random seed for reproducible results
        
    Returns:
        List of provisional teams, each containing exactly desired_team_size members
    """
    provisional_teams = []
    
    for cluster_idx, cluster in enumerate(prelim_teams):
        if not cluster:
            continue
            
        # Calculate how many teams we need from this cluster
        k = math.ceil(len(cluster) / desired_team_size)
        
        if k == 1:
            # Single team - just take the first desired_team_size members
            team = cluster[:desired_team_size]
            provisional_teams.append(team)
        else:
            # Multiple teams - use k-medoids clustering
            teams = _cluster_into_teams(cluster, k, desired_team_size, max_iter, random_seed)
            provisional_teams.extend(teams)
    
    return provisional_teams


def _cluster_into_teams(
    participants: List[Dict[str, Any]], 
    k: int, 
    desired_team_size: int,
    max_iter: int,
    random_seed: int
) -> List[List[Dict[str, Any]]]:
    """
    Cluster participants into k teams using k-medoids, then assign remaining to nearest medoid.
    """
    if len(participants) <= desired_team_size:
        return [participants]
    
    # Step 1: Find k medoids
    medoid_indices = k_medoids_clustering(
        participants, 
        k=k, 
        max_iter=max_iter, 
        random_seed=random_seed
    )
    
    # Step 2: Assign all participants to nearest medoid
    clusters = assign_to_medoids(participants, medoid_indices)
    
    # Step 3: Convert index-based clusters to participant-based teams
    teams = []
    for cluster_indices in clusters:
        team = [participants[i] for i in cluster_indices]
        teams.append(team)
    
    # Step 4: Balance team sizes to match desired_team_size
    balanced_teams = _balance_team_sizes(teams, desired_team_size)
    
    return balanced_teams


def _balance_team_sizes(
    teams: List[List[Dict[str, Any]]], 
    desired_team_size: int
) -> List[List[Dict[str, Any]]]:
    """
    Balance team sizes by moving participants between teams to reach desired_team_size.
    """
    if not teams:
        return []
    
    # Calculate total participants
    total_participants = sum(len(team) for team in teams)
    
    # If we have fewer participants than one team, return as single team
    if total_participants <= desired_team_size:
        all_participants = []
        for team in teams:
            all_participants.extend(team)
        return [all_participants]
    
    # Calculate how many complete teams we can form
    num_complete_teams = total_participants // desired_team_size
    remainder = total_participants % desired_team_size
    
    # If remainder is too small, merge into existing teams
    if remainder > 0 and remainder < desired_team_size // 2:
        num_complete_teams = max(1, num_complete_teams)
    else:
        num_complete_teams = max(1, num_complete_teams + (1 if remainder > 0 else 0))
    
    # Flatten all participants
    all_participants = []
    for team in teams:
        all_participants.extend(team)
    
    # Redistribute into balanced teams
    balanced_teams = []
    participants_per_team = len(all_participants) // num_complete_teams
    extra_participants = len(all_participants) % num_complete_teams
    
    start_idx = 0
    for i in range(num_complete_teams):
        # Some teams get one extra participant
        team_size = participants_per_team + (1 if i < extra_participants else 0)
        team = all_participants[start_idx:start_idx + team_size]
        balanced_teams.append(team)
        start_idx += team_size
    
    return balanced_teams


def optimize_team_composition(
    teams: List[List[Dict[str, Any]]], 
    max_swaps: int = 10
) -> List[List[Dict[str, Any]]]:
    """
    Optimize team composition by performing beneficial swaps between teams.
    
    Args:
        teams: List of teams to optimize
        max_swaps: Maximum number of swaps to attempt
        
    Returns:
        Optimized teams
    """
    if len(teams) < 2:
        return teams
    
    optimized_teams = [team[:] for team in teams]  # Deep copy
    
    for swap_count in range(max_swaps):
        best_swap = None
        best_improvement = 0.0
        
        # Try swapping participants between all pairs of teams
        for i in range(len(optimized_teams)):
            for j in range(i + 1, len(optimized_teams)):
                team_i = optimized_teams[i]
                team_j = optimized_teams[j]
                
                # Try swapping each participant from team i with each from team j
                for p_i_idx, participant_i in enumerate(team_i):
                    for p_j_idx, participant_j in enumerate(team_j):
                        improvement = _calculate_swap_improvement(
                            team_i, team_j, p_i_idx, p_j_idx
                        )
                        
                        if improvement > best_improvement:
                            best_improvement = improvement
                            best_swap = (i, j, p_i_idx, p_j_idx)
        
        # Perform the best swap if it's beneficial
        if best_swap is not None:
            team_i_idx, team_j_idx, p_i_idx, p_j_idx = best_swap
            
            # Swap the participants
            participant_i = optimized_teams[team_i_idx][p_i_idx]
            participant_j = optimized_teams[team_j_idx][p_j_idx]
            
            optimized_teams[team_i_idx][p_i_idx] = participant_j
            optimized_teams[team_j_idx][p_j_idx] = participant_i
        else:
            # No beneficial swap found, stop optimization
            break
    
    return optimized_teams


def _calculate_swap_improvement(
    team_i: List[Dict[str, Any]], 
    team_j: List[Dict[str, Any]], 
    p_i_idx: int, 
    p_j_idx: int
) -> float:
    """
    Calculate the improvement in total team cost if we swap two participants.
    """
    # Calculate current internal team costs
    current_cost_i = _calculate_team_internal_cost(team_i)
    current_cost_j = _calculate_team_internal_cost(team_j)
    current_total = current_cost_i + current_cost_j
    
    # Create teams after swap
    new_team_i = team_i[:]
    new_team_j = team_j[:]
    new_team_i[p_i_idx] = team_j[p_j_idx]
    new_team_j[p_j_idx] = team_i[p_i_idx]
    
    # Calculate new internal team costs
    new_cost_i = _calculate_team_internal_cost(new_team_i)
    new_cost_j = _calculate_team_internal_cost(new_team_j)
    new_total = new_cost_i + new_cost_j
    
    # Return improvement (positive means beneficial swap)
    return current_total - new_total


def _calculate_team_internal_cost(team: List[Dict[str, Any]]) -> float:
    """
    Calculate the total internal cost of a team (sum of all pairwise costs).
    """
    if len(team) <= 1:
        return 0.0
    
    total_cost = 0.0
    for i in range(len(team)):
        for j in range(i + 1, len(team)):
            total_cost += participant_pair_cost(team[i], team[j])
    
    return total_cost


def calculate_team_metrics(team: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate various metrics for a team.
    
    Args:
        team: List of participant dictionaries
        
    Returns:
        Dictionary containing team metrics
    """
    if not team:
        return {
            "internal_cost": 0.0,
            "avg_pairwise_cost": 0.0,
            "role_diversity": 0.0,
            "skill_coverage": 0.0,
            "availability_variance": 0.0
        }
    
    # Internal cost metrics
    internal_cost = _calculate_team_internal_cost(team)
    num_pairs = len(team) * (len(team) - 1) / 2
    avg_pairwise_cost = internal_cost / max(1, num_pairs)
    
    # Role diversity
    all_roles = set()
    for participant in team:
        all_roles.update(participant.get("primary_roles", []))
    role_diversity = len(all_roles) / max(1, len(team))
    
    # Skill coverage
    all_skills = set()
    for participant in team:
        skills = participant.get("enriched_skills", {})
        all_skills.update(skills.keys())
    skill_coverage = len(all_skills) / max(1, len(team))
    
    # Availability variance
    availabilities = [p.get("availability_hours", 0) for p in team]
    if len(availabilities) > 1:
        mean_availability = sum(availabilities) / len(availabilities)
        variance = sum((a - mean_availability) ** 2 for a in availabilities) / len(availabilities)
        availability_variance = variance ** 0.5  # Standard deviation
    else:
        availability_variance = 0.0
    
    return {
        "internal_cost": internal_cost,
        "avg_pairwise_cost": avg_pairwise_cost,
        "role_diversity": role_diversity,
        "skill_coverage": skill_coverage,
        "availability_variance": availability_variance
    }
