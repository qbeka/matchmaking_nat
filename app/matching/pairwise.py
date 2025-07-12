from typing import Any, Dict

import numpy as np
from scipy.spatial.distance import cosine


def participant_pair_cost(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    """
    Calculates the cost between two participants for internal team formation.
    
    Cost = role_diversity_penalty + skill_overlap_penalty + comm_style_clash - 0.2 * motivation_similarity
    
    Args:
        a: First participant dictionary
        b: Second participant dictionary
        
    Returns:
        Cost value (0-1 range, lower is better for pairing)
    """
    if a.get("_id") == b.get("_id"):
        return 0.0  # Zero cost for same participant
    
    role_diversity_penalty = _role_diversity_penalty(a, b)
    skill_overlap = _skill_overlap_penalty(a, b)
    comm_clash = _communication_style_clash(a, b)
    motivation_sim = _motivation_similarity(a, b)
    
    # Combine terms with balanced weights: penalties minus similarity bonus
    cost = 0.4 * role_diversity_penalty + 0.3 * skill_overlap + 0.3 * comm_clash - 0.2 * motivation_sim
    
    # Clamp to [0, 1] range
    return max(0.0, min(1.0, cost))


def _role_diversity_penalty(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    """
    Calculate penalty for lack of role compatibility.
    Returns 0-1 where 1 is maximum penalty (no role overlap).
    """
    roles_a = set(a.get("primary_roles", []))
    roles_b = set(b.get("primary_roles", []))
    
    if not roles_a or not roles_b:
        return 0.5  # Medium penalty for missing role data
    
    intersection = roles_a & roles_b
    union = roles_a | roles_b
    
    if not union:
        return 0.5
    
    # High penalty for low role overlap (incompatible roles)
    overlap_ratio = len(intersection) / len(union)
    return 1.0 - overlap_ratio  # Invert: penalty for lack of overlap


def _skill_overlap_penalty(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    """
    Calculate penalty for excessive skill overlap.
    Returns 0-1 where 1 is maximum overlap penalty.
    """
    skills_a = a.get("enriched_skills", {})
    skills_b = b.get("enriched_skills", {})
    
    if not skills_a or not skills_b:
        return 0.0
    
    # Get common skills
    common_skills = set(skills_a.keys()) & set(skills_b.keys())
    
    if not common_skills:
        return 0.0
    
    # Calculate overlap based on skill levels
    overlap_scores = []
    for skill in common_skills:
        level_a = skills_a[skill].get("mean", 0.0)
        level_b = skills_b[skill].get("mean", 0.0)
        
        # High overlap when both have high skill levels
        if level_a > 3.0 and level_b > 3.0:
            overlap_scores.append(min(level_a, level_b) / 5.0)
    
    if not overlap_scores:
        return 0.0
    
    # Average overlap penalty, scaled by number of overlapping skills
    avg_overlap = np.mean(overlap_scores)
    skill_coverage = len(common_skills) / max(len(skills_a), len(skills_b))
    
    return avg_overlap * skill_coverage


def _communication_style_clash(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    """
    Calculate communication style clash penalty.
    Returns 0-1 where 1 is maximum clash.
    """
    # Extract communication preferences from availability patterns
    avail_a = a.get("availability_hours", 20)
    avail_b = b.get("availability_hours", 20)
    
    # Simple heuristic: large availability differences suggest different work styles
    max_avail = max(avail_a, avail_b)
    if max_avail == 0:
        return 0.0
    
    availability_clash = abs(avail_a - avail_b) / max_avail
    
    # Additional clash based on motivation text length (proxy for communication style)
    motivation_a = a.get("motivation_text", "")
    motivation_b = b.get("motivation_text", "")
    
    len_a = len(motivation_a)
    len_b = len(motivation_b)
    max_len = max(len_a, len_b)
    
    if max_len == 0:
        text_clash = 0.0
    else:
        text_clash = abs(len_a - len_b) / max_len
    
    # Combine clash indicators
    return (availability_clash + text_clash) / 2.0


def _motivation_similarity(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    """
    Calculate motivation similarity using cosine similarity of embeddings.
    Returns 0-1 where 1 is maximum similarity.
    """
    embedding_a = a.get("motivation_embedding")
    embedding_b = b.get("motivation_embedding")
    
    if embedding_a is None or embedding_b is None:
        return 0.0  # No similarity if embeddings missing
    
    try:
        # Cosine similarity = 1 - cosine distance
        similarity = 1.0 - cosine(embedding_a, embedding_b)
        return max(0.0, similarity)  # Clamp to [0, 1]
    except (ValueError, TypeError):
        return 0.0
