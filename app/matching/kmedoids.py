from typing import Any, Dict, List, Callable
import numpy as np
from app.matching.pairwise import participant_pair_cost


def k_medoids_clustering(
    participants: List[Dict[str, Any]], 
    k: int,
    max_iter: int = 100,
    cost_function: Callable[[Dict[str, Any], Dict[str, Any]], float] = participant_pair_cost,
    random_seed: int = 42
) -> List[int]:
    """
    Perform k-medoids clustering using PAM (Partitioning Around Medoids) algorithm.
    
    Args:
        participants: List of participant dictionaries
        k: Number of clusters/medoids
        max_iter: Maximum number of iterations for optimization
        cost_function: Function to calculate cost between two participants
        random_seed: Random seed for reproducible results
        
    Returns:
        List of medoid indices (indices into participants list)
    """
    if k >= len(participants):
        return list(range(len(participants)))
    
    np.random.seed(random_seed)
    
    # Step 1: PAM initialization - select k initial medoids
    medoids = _pam_initialization(participants, k, cost_function)
    
    # Step 2: Iterative improvement
    for iteration in range(max_iter):
        # Try to swap each medoid with each non-medoid
        improved = False
        
        for i, medoid_idx in enumerate(medoids):
            best_swap = None
            best_cost_reduction = 0.0
            
            for candidate_idx in range(len(participants)):
                if candidate_idx in medoids:
                    continue
                
                # Calculate cost reduction if we swap medoid with candidate
                cost_reduction = _calculate_swap_cost_reduction(
                    participants, medoids, medoid_idx, candidate_idx, cost_function
                )
                
                if cost_reduction > best_cost_reduction:
                    best_cost_reduction = cost_reduction
                    best_swap = candidate_idx
            
            # Perform the best swap if it improves the solution
            if best_swap is not None:
                medoids[i] = best_swap
                improved = True
        
        # If no improvement, converged
        if not improved:
            break
    
    return medoids


def _pam_initialization(
    participants: List[Dict[str, Any]], 
    k: int, 
    cost_function: Callable[[Dict[str, Any], Dict[str, Any]], float]
) -> List[int]:
    """
    PAM initialization: greedily select k medoids that minimize total cost.
    """
    if k == 1:
        # For k=1, select the participant with minimum average cost to all others
        best_medoid = 0
        best_avg_cost = float('inf')
        
        for i in range(len(participants)):
            total_cost = sum(
                cost_function(participants[i], participants[j])
                for j in range(len(participants))
                if i != j
            )
            avg_cost = total_cost / max(1, len(participants) - 1)
            
            if avg_cost < best_avg_cost:
                best_avg_cost = avg_cost
                best_medoid = i
        
        return [best_medoid]
    
    # For k > 1, use greedy selection
    medoids = []
    
    # Select first medoid (same as k=1 case)
    first_medoid = 0
    best_avg_cost = float('inf')
    
    for i in range(len(participants)):
        total_cost = sum(
            cost_function(participants[i], participants[j])
            for j in range(len(participants))
            if i != j
        )
        avg_cost = total_cost / max(1, len(participants) - 1)
        
        if avg_cost < best_avg_cost:
            best_avg_cost = avg_cost
            first_medoid = i
    
    medoids.append(first_medoid)
    
    # Select remaining medoids greedily
    for _ in range(k - 1):
        best_candidate = None
        best_cost_reduction = 0.0
        
        for candidate_idx in range(len(participants)):
            if candidate_idx in medoids:
                continue
            
            # Calculate how much total cost would be reduced by adding this candidate
            cost_reduction = _calculate_addition_cost_reduction(
                participants, medoids, candidate_idx, cost_function
            )
            
            if cost_reduction > best_cost_reduction:
                best_cost_reduction = cost_reduction
                best_candidate = candidate_idx
        
        if best_candidate is not None:
            medoids.append(best_candidate)
        else:
            # Fallback: add a random non-medoid
            available = [i for i in range(len(participants)) if i not in medoids]
            if available:
                medoids.append(np.random.choice(available))
    
    return medoids


def _calculate_addition_cost_reduction(
    participants: List[Dict[str, Any]], 
    current_medoids: List[int], 
    candidate_idx: int,
    cost_function: Callable[[Dict[str, Any], Dict[str, Any]], float]
) -> float:
    """
    Calculate how much total cost would be reduced by adding a new medoid.
    """
    total_reduction = 0.0
    
    for i in range(len(participants)):
        if i == candidate_idx or i in current_medoids:
            continue
        
        # Current minimum cost to existing medoids
        current_min_cost = min(
            cost_function(participants[i], participants[medoid_idx])
            for medoid_idx in current_medoids
        ) if current_medoids else float('inf')
        
        # Cost to new candidate
        candidate_cost = cost_function(participants[i], participants[candidate_idx])
        
        # Reduction if candidate becomes the closest medoid
        if candidate_cost < current_min_cost:
            total_reduction += current_min_cost - candidate_cost
    
    return total_reduction


def _calculate_swap_cost_reduction(
    participants: List[Dict[str, Any]], 
    medoids: List[int], 
    old_medoid_idx: int, 
    new_medoid_idx: int,
    cost_function: Callable[[Dict[str, Any], Dict[str, Any]], float]
) -> float:
    """
    Calculate how much total cost would be reduced by swapping medoids.
    """
    total_cost_change = 0.0
    
    for i in range(len(participants)):
        if i in medoids or i == new_medoid_idx:
            continue
        
        # Current assignment cost (minimum cost to any current medoid)
        current_costs = [
            cost_function(participants[i], participants[medoid_idx])
            for medoid_idx in medoids
        ]
        current_min_cost = min(current_costs)
        
        # New assignment cost after swap
        new_medoids = [new_medoid_idx if m == old_medoid_idx else m for m in medoids]
        new_costs = [
            cost_function(participants[i], participants[medoid_idx])
            for medoid_idx in new_medoids
        ]
        new_min_cost = min(new_costs)
        
        # Cost change for this participant
        total_cost_change += current_min_cost - new_min_cost
    
    return total_cost_change


def assign_to_medoids(
    participants: List[Dict[str, Any]], 
    medoids: List[int],
    cost_function: Callable[[Dict[str, Any], Dict[str, Any]], float] = participant_pair_cost
) -> List[List[int]]:
    """
    Assign each participant to the nearest medoid.
    
    Args:
        participants: List of participant dictionaries
        medoids: List of medoid indices
        cost_function: Function to calculate cost between participants
        
    Returns:
        List of clusters, where each cluster is a list of participant indices
    """
    if not medoids:
        return []
    
    clusters: List[List[int]] = [[] for _ in medoids]
    
    for i, participant in enumerate(participants):
        if i in medoids:
            # Medoids assign to themselves
            medoid_position = medoids.index(i)
            clusters[medoid_position].append(i)
        else:
            # Find nearest medoid
            min_cost = float('inf')
            best_medoid_idx = 0
            
            for j, medoid_idx in enumerate(medoids):
                cost = cost_function(participant, participants[medoid_idx])
                if cost < min_cost:
                    min_cost = cost
                    best_medoid_idx = j
            
            clusters[best_medoid_idx].append(i)
    
    return clusters
