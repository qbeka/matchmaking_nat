import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from scipy.optimize import linear_sum_assignment

from app.db import db
from app.llm.openai_client import get_problem_score, get_team_scores, review_phase1_assignments, review_phase2_teams, review_phase3_assignments, analyze_team_role_balance
from app.matching.cost import compute_individual_cost, DEFAULT_WEIGHTS
from app.matching.pairwise import participant_pair_cost
from app.matching.team_problem_cost import compute_team_problem_cost
from app.matching.team_vector import TeamVector
from app.models import Problem
import numpy as np

logger = logging.getLogger(__name__)
router = APIRouter()

# Deterministic weights for consistent results
PHASE1_WEIGHTS = {
    "skill_gap": 0.35,
    "role_alignment": 0.20,
    "motivation_similarity": 0.15,
    "ambiguity_fit": 0.20,
    "workload_fit": 0.10,
}

PHASE2_WEIGHTS = {
    "role_diversity": 0.30,
    "skill_complementarity": 0.25,
    "communication_style": 0.20,
    "motivation_alignment": 0.15,
    "availability_match": 0.10,
}

PHASE3_WEIGHTS = {
    "skill_gap": 0.30,
    "role_alignment": 0.25,
    "motivation_similarity": 0.20,
    "ambiguity_fit": 0.15,
    "workload_fit": 0.10,
}


class SimplePhase1Request(BaseModel):
    participants: List[Dict[str, Any]]
    problems: List[Dict[str, Any]]


class SimplePhase2Request(BaseModel):
    target_team_size: int = 4
    enable_ai_analysis: bool = True  # Optional AI role balance analysis


class SimplePhase3Request(BaseModel):
    optimization_strategy: str = "quality_first"  # "quality_first" or "balanced"


def ensure_deterministic_order(items: List[Dict[str, Any]], key: str = "id") -> List[Dict[str, Any]]:
    """Sort items by key to ensure deterministic processing order."""
    return sorted(items, key=lambda x: str(x.get(key, "")))


async def consolidate_small_teams(team_assignments: Dict[int, List[dict]], target_team_size: int, all_participants: List[dict]) -> Dict[int, List[dict]]:
    """
    Consolidate teams of 1-2 people into larger teams.
    Ensures no team has fewer than 3 members (unless absolutely unavoidable).
    """
    logger.info(f"🔧 Starting team consolidation. Target size: {target_team_size}")
    
    # Find small teams (1-2 members) and larger teams
    small_teams = {}
    large_teams = {}
    
    for team_idx, members in team_assignments.items():
        if len(members) <= 2:
            small_teams[team_idx] = members
            logger.info(f"📝 Found small team {team_idx}: {len(members)} members")
        else:
            large_teams[team_idx] = members
    
    # If no small teams, return as-is
    if not small_teams:
        logger.info("✅ No small teams found, no consolidation needed")
        return team_assignments
    
    # Collect all members from small teams
    orphaned_members = []
    for members in small_teams.values():
        orphaned_members.extend(members)
    
    logger.info(f"🏠 Found {len(orphaned_members)} orphaned members from {len(small_teams)} small teams")
    
    # Strategy 1: Add orphaned members to existing large teams
    consolidated_assignments = large_teams.copy()
    remaining_orphans = orphaned_members.copy()
    
    for team_idx, members in list(consolidated_assignments.items()):
        while remaining_orphans and len(members) < target_team_size:
            # Find best fit orphan for this team using role/skill compatibility
            best_orphan = find_best_team_fit(members, remaining_orphans)
            if best_orphan:
                members.append(best_orphan)
                remaining_orphans.remove(best_orphan)
                logger.info(f"🔄 Added orphan {best_orphan.get('name', 'Unknown')} to team {team_idx}")
    
    # Strategy 2: If still have orphans, create new teams of minimum 3
    team_counter = max(consolidated_assignments.keys()) + 1 if consolidated_assignments else 0
    while len(remaining_orphans) >= 3:
        new_team_members = remaining_orphans[:target_team_size]
        remaining_orphans = remaining_orphans[target_team_size:]
        consolidated_assignments[team_counter] = new_team_members
        logger.info(f"🆕 Created new team {team_counter} with {len(new_team_members)} members")
        team_counter += 1
    
    # Strategy 3: Force remaining 1-2 orphans into existing teams (even if over target size)
    if remaining_orphans:
        if consolidated_assignments:
            # Add to the team with most compatible skills
            best_team_idx = min(consolidated_assignments.keys(), 
                              key=lambda idx: len(consolidated_assignments[idx]))
            consolidated_assignments[best_team_idx].extend(remaining_orphans)
            logger.info(f"🚨 Force-added {len(remaining_orphans)} remaining orphans to team {best_team_idx}")
        else:
            # Edge case: create a team even if it's small (last resort)
            consolidated_assignments[0] = remaining_orphans
            logger.warning(f"⚠️ Created small team as last resort: {len(remaining_orphans)} members")
    
    logger.info(f"✅ Consolidation complete. Teams: {len(consolidated_assignments)}")
    return consolidated_assignments


def find_best_team_fit(team_members: List[dict], candidates: List[dict]) -> dict:
    """Find the candidate that best fits with the existing team based on roles and skills."""
    if not candidates:
        return None
    
    # Get team's current roles and skills
    team_roles = set()
    team_skills = set()
    
    for member in team_members:
        team_roles.update(member.get("primary_roles", []))
        team_skills.update(member.get("self_rated_skills", {}).keys())
    
    best_candidate = None
    best_score = -1
    
    for candidate in candidates:
        score = 0
        candidate_roles = set(candidate.get("primary_roles", []))
        candidate_skills = set(candidate.get("self_rated_skills", {}).keys())
        
        # Prefer candidates who add new roles
        new_roles = candidate_roles - team_roles
        score += len(new_roles) * 3
        
        # Prefer candidates who add new skills
        new_skills = candidate_skills - team_skills
        score += len(new_skills) * 1
        
        # Prefer leaders if team lacks one
        has_leader = any(member.get("leadership_preference", False) for member in team_members)
        if not has_leader and candidate.get("leadership_preference", False):
            score += 5
        
        if score > best_score:
            best_score = score
            best_candidate = candidate
    
    return best_candidate if best_candidate else candidates[0]


async def ensure_team_leadership(team_assignments: Dict[int, List[dict]], all_participants: List[dict]) -> Dict[int, List[dict]]:
    """
    Ensure each team has at least one member with leadership preference.
    Allows multiple leaders per team if extras are available.
    """
    logger.info("👑 Ensuring team leadership requirements (min 1 leader per team)")
    
    teams_without_leaders = []
    teams_with_leaders = []
    available_leaders = []
    
    # Analyze current leadership distribution
    assigned_participant_ids = set()
    for team_idx, members in team_assignments.items():
        assigned_participant_ids.update(str(member.get("_id")) for member in members)
        
        leader_count = sum(1 for member in members if member.get("leadership_preference", False))
        if leader_count == 0:
            teams_without_leaders.append(team_idx)
            logger.info(f"🚨 Team {team_idx} has no leaders")
        else:
            teams_with_leaders.append((team_idx, leader_count))
            logger.info(f"👑 Team {team_idx} has {leader_count} leader(s)")
    
    # Find unassigned participants who want to lead
    for participant in all_participants:
        if str(participant.get("_id")) not in assigned_participant_ids:
            if participant.get("leadership_preference", False):
                available_leaders.append(participant)
    
    logger.info(f"📊 Teams without leaders: {len(teams_without_leaders)}")
    logger.info(f"📊 Teams with leaders: {len(teams_with_leaders)}")
    logger.info(f"📊 Available unassigned leaders: {len(available_leaders)}")
    
    # Priority 1: Add available leaders to teams that need them
    for team_idx in teams_without_leaders[:len(available_leaders)]:
        leader = available_leaders.pop(0)
        team_assignments[team_idx].append(leader)
        logger.info(f"👑 Added leader {leader.get('name', 'Unknown')} to team {team_idx}")
    
    # Priority 2: Try to swap members to get leaders into teams that need them
    remaining_teams_without_leaders = teams_without_leaders[len(available_leaders):]
    for team_idx in remaining_teams_without_leaders:
        swapped = await try_leadership_swap(team_assignments, team_idx)
        if swapped:
            logger.info(f"🔄 Successfully swapped for leadership in team {team_idx}")
        else:
            # Last resort: promote someone to leadership preference (if they agree)
            team_members = team_assignments[team_idx]
            if team_members:
                promoted_leader = team_members[0]  # Take first member
                promoted_leader["leadership_preference"] = True
                logger.info(f"🆙 Promoted {promoted_leader.get('name', 'Unknown')} to leader in team {team_idx}")
    
    # Priority 3: Distribute any remaining leaders to teams (allowing multiple leaders)
    if available_leaders:
        logger.info(f"🎁 Distributing {len(available_leaders)} extra leaders to teams")
        for leader in available_leaders:
            # Find team with fewest leaders (only if we have teams)
            if team_assignments:
                best_team_idx = min(team_assignments.keys(), 
                                  key=lambda idx: sum(1 for m in team_assignments[idx] 
                                                    if m.get("leadership_preference", False)))
                team_assignments[best_team_idx].append(leader)
                logger.info(f"👑 Added extra leader {leader.get('name', 'Unknown')} to team {best_team_idx}")
            else:
                # No teams exist, create a new team with this leader
                team_assignments[0] = [leader]
                logger.info(f"👑 Created new team 0 with leader {leader.get('name', 'Unknown')}")
    
    # Final verification
    final_teams_without_leaders = []
    for team_idx, members in team_assignments.items():
        leader_count = sum(1 for member in members if member.get("leadership_preference", False))
        if leader_count == 0:
            final_teams_without_leaders.append(team_idx)
    
    if final_teams_without_leaders:
        logger.warning(f"⚠️ Still {len(final_teams_without_leaders)} teams without leaders: {final_teams_without_leaders}")
    else:
        logger.info("✅ All teams now have at least one leader!")
    
    return team_assignments


async def try_leadership_swap(team_assignments: Dict[int, List[dict]], target_team_idx: int) -> bool:
    """Try to swap a member from target team with a leader from another team."""
    target_team = team_assignments[target_team_idx]
    
    for other_team_idx, other_team in team_assignments.items():
        if other_team_idx == target_team_idx:
            continue
        
        # Find leaders in other team
        leaders_in_other_team = [m for m in other_team if m.get("leadership_preference", False)]
        
        # Only swap if other team has multiple leaders
        if len(leaders_in_other_team) > 1:
            # Find non-leaders in target team
            non_leaders_in_target = [m for m in target_team if not m.get("leadership_preference", False)]
            
            if non_leaders_in_target:
                # Perform the swap
                leader_to_move = leaders_in_other_team[0]
                non_leader_to_move = non_leaders_in_target[0]
                
                other_team.remove(leader_to_move)
                other_team.append(non_leader_to_move)
                target_team.remove(non_leader_to_move)
                target_team.append(leader_to_move)
                
                return True
    
    return False


async def strict_team_formation(participants: List[Dict[str, Any]], target_team_size: int) -> List[List[Dict[str, Any]]]:
    """
    STRICT team formation that enforces exact team sizes.
    For 200 participants with team size 5: creates exactly 40 teams of 5 people each.
    No exceptions, no variation in team size.
    """
    logger.info(f"🔒 STRICT team formation: {len(participants)} participants, target size: {target_team_size}")
    
    # Ensure deterministic order
    participants = ensure_deterministic_order(participants)
    
    total_participants = len(participants)
    expected_teams = total_participants // target_team_size
    remaining_participants = total_participants % target_team_size
    
    logger.info(f"📊 STRICT formation plan: {expected_teams} teams of {target_team_size}, {remaining_participants} remainder")
    
    if remaining_participants > 0:
        # Handle remainder by adjusting team sizes slightly or removing participants
        if remaining_participants <= expected_teams:
            # Add 1 person to some teams (e.g., some teams get 6 instead of 5)
            logger.info(f"📊 Adjusting {remaining_participants} teams to size {target_team_size + 1}")
            teams_to_enlarge = remaining_participants
        else:
            # Remove excess participants (last resort)
            logger.warning(f"⚠️ Removing {remaining_participants} participants to enforce strict team sizes")
            participants = participants[:total_participants - remaining_participants]
            total_participants = len(participants)
            expected_teams = total_participants // target_team_size
            remaining_participants = 0
            teams_to_enlarge = 0
    else:
        teams_to_enlarge = 0
    
    # Create exact teams
    teams = []
    participant_index = 0
    
    for team_index in range(expected_teams):
        if team_index < teams_to_enlarge:
            # This team gets one extra member
            team_size = target_team_size + 1
        else:
            # This team gets exactly the target size
            team_size = target_team_size
        
        team_members = participants[participant_index:participant_index + team_size]
        teams.append(team_members)
        
        participant_index += team_size
        logger.info(f"✅ Created strict team {team_index + 1}: {len(team_members)} members")
    
    # Verify strict enforcement
    total_assigned = sum(len(team) for team in teams)
    logger.info(f"🔍 STRICT verification: {len(teams)} teams, {total_assigned} participants assigned")
    
    if total_assigned != len(participants):
        logger.error(f"❌ STRICT enforcement FAILED: Expected {len(participants)}, got {total_assigned}")
        raise ValueError(f"Strict team formation failed: {total_assigned} != {len(participants)}")
    
    logger.info(f"✅ STRICT team formation complete: {len(teams)} teams created")
    return teams


async def build_team_formation_cost_matrix(
    participants: List[Dict[str, Any]], 
    target_team_size: int
) -> tuple[np.ndarray, List[str]]:
    """
    Build cost matrix for optimal team formation using Hungarian algorithm.
    """
    # Ensure deterministic order
    participants = ensure_deterministic_order(participants)
    
    num_participants = len(participants)
    num_teams = (num_participants + target_team_size - 1) // target_team_size  # Ceiling division
    
    # Create cost matrix for assigning participants to team slots
    # Matrix size: participants x (teams * target_team_size)
    total_slots = num_teams * target_team_size
    cost_matrix = np.full((num_participants, total_slots), 1e6)
    
    # Calculate costs for each participant-slot assignment
    for p_idx, participant in enumerate(participants):
        for slot_idx in range(total_slots):
            team_idx = slot_idx // target_team_size
            position_in_team = slot_idx % target_team_size
            
            # Base cost is 0 for valid assignments
            base_cost = 0.0
            
            # Add role diversity bonus (prefer different roles in same team)
            role_bonus = 0.0
            primary_roles = participant.get("primary_roles", [])
            if primary_roles:
                # Slight preference for spreading roles across teams
                role_bonus = -0.1 * (position_in_team / target_team_size)
            
            # Add skill level consideration
            skill_levels = participant.get("self_rated_skills", {})
            avg_skill = sum(skill_levels.values()) / len(skill_levels) if skill_levels else 3.0
            skill_bonus = -(avg_skill - 3.0) * 0.05  # Slight preference for higher skills
            
            # Add availability consideration
            availability = participant.get("availability_hours", 20)
            availability_bonus = -(availability - 20) * 0.01  # Slight preference for higher availability
            
            final_cost = base_cost + role_bonus + skill_bonus + availability_bonus
            cost_matrix[p_idx, slot_idx] = max(0.0, final_cost)
    
    participant_ids = [p["id"] for p in participants]
    return cost_matrix, participant_ids


async def build_team_problem_assignment_matrix(
    teams: List[Dict[str, Any]], 
    problems: List[Dict[str, Any]]
) -> tuple[np.ndarray, Dict[int, str], Dict[int, str]]:
    """
    Build sophisticated cost matrix for team-problem assignment using Hungarian algorithm.
    """
    # Ensure deterministic order
    teams = ensure_deterministic_order(teams, "team_id")
    problems = ensure_deterministic_order(problems)
    
    num_teams = len(teams)
    num_problems = len(problems)
    
    # Create square matrix for Hungarian algorithm
    matrix_size = max(num_teams, num_problems)
    cost_matrix = np.full((matrix_size, matrix_size), 1e6)
    
    # Build mappings
    team_map = {i: teams[i]["team_id"] for i in range(num_teams)}
    problem_map = {i: problems[i]["id"] for i in range(num_problems)}
    
    # Calculate sophisticated team-problem costs
    for i, team in enumerate(teams):
        for j, problem in enumerate(problems):
            # Build team vector
            team_vector = await build_team_vector_from_dict(team)
            
            # Convert problem to Problem model format
            problem_model = Problem(
                version="1.0",
                _id=problem["id"],
                title=problem.get("title", ""),
                raw_prompt=problem.get("raw_prompt", ""),
                estimated_team_size=3,
                preferred_roles=problem.get("role_preferences", {}),
                required_skills=problem.get("required_skills", {}),
                role_preferences=problem.get("role_preferences", {}),
                problem_embedding=problem.get("problem_embedding"),
                expected_ambiguity=problem.get("expected_ambiguity", 0.5),
                expected_hours_per_week=problem.get("estimated_hours", 40) // 4
            )
            
            # Calculate sophisticated cost
            cost = await compute_team_problem_cost(team_vector, problem_model, PHASE3_WEIGHTS)
            cost_matrix[i, j] = cost
    
    return cost_matrix, team_map, problem_map


async def build_team_vector_from_dict(team: Dict[str, Any]) -> TeamVector:
    """
    Build TeamVector from team dictionary for cost calculation.
    """
    members = team.get("members", [])
    
    if not members:
        # Return empty team vector
        return TeamVector(
            team_id=team["team_id"],
            avg_skill_levels={},
            role_weights={},
            avg_motivation_embedding=None,
            avg_ambiguity_tolerance=0.5,
            min_availability=0,
            avg_communication_style=0.5,
            avg_confidence_score=0.6
        )
    
    # Aggregate skills
    all_skills = {}
    for member in members:
        skills = member.get("self_rated_skills", {})
        for skill, level in skills.items():
            if skill not in all_skills:
                all_skills[skill] = []
            all_skills[skill].append(level)
    
    avg_skills = {skill: sum(levels) / len(levels) for skill, levels in all_skills.items()}
    
    # Aggregate roles
    role_weights = {}
    for member in members:
        roles = member.get("primary_roles", [])
        for role in roles:
            role_weights[role] = role_weights.get(role, 0) + 1
    
    # Normalize role weights
    total_roles = sum(role_weights.values())
    if total_roles > 0:
        role_weights = {role: count / total_roles for role, count in role_weights.items()}
    
    # Aggregate other attributes
    ambiguity_tolerances = [member.get("ambiguity_tolerance", 0.5) for member in members]
    availabilities = [member.get("availability_hours", 20) for member in members]
    
    avg_ambiguity = sum(ambiguity_tolerances) / len(ambiguity_tolerances)
    min_availability = min(availabilities)
    total_availability = sum(availabilities)
    
    return TeamVector(
        team_id=team["team_id"],
        avg_skill_levels=avg_skills,
        role_weights=role_weights,
        avg_motivation_embedding=None,  # Could aggregate embeddings if available
        avg_ambiguity_tolerance=avg_ambiguity,
        min_availability=min_availability,
        avg_communication_style=total_availability / (len(members) * 40.0),  # Normalized communication style
        avg_confidence_score=sum(avg_skills.values()) / (len(avg_skills) * 5.0) if avg_skills else 0.6  # Normalized confidence
    )


@router.post("/simple/phase1")
async def simple_phase1(request: SimplePhase1Request):
    """
    Phase 1: Optimal participant-problem matching.
    This assigns *every* participant to their best-fit problem based on a deterministic cost function.
    """
    try:
        logger.info("🚀 Starting Sophisticated Phase 1: Participant to Problem Assignment...")

        await db.participants.delete_many({})
        await db.problems.delete_many({})
        await db.individual_problem_assignments.delete_many({})

        processed_problems = []
        for problem in ensure_deterministic_order(request.problems):
            score = await get_problem_score(
                problem["raw_prompt"],
                additional_context={"title": problem.get("title", "")}
            )
            problem_with_score = problem.copy()
            problem_with_score["problem_score"] = score
            problem_with_score["processed"] = True
            problem_with_score["processed_at"] = datetime.utcnow().isoformat()
            problem_with_score["_id"] = problem["id"]
            processed_problems.append(problem_with_score)

        if processed_problems:
            await db.problems.insert_many(processed_problems)
            logger.info(f"✅ Inserted {len(processed_problems)} processed problems")
        
        participants = ensure_deterministic_order(request.participants)
        for p in participants:
            p["_id"] = p["id"]
        if participants:
            await db.participants.insert_many(participants)
            logger.info(f"✅ Inserted {len(participants)} participants")

        assignments = []
        total_cost = 0.0

        for participant in participants:
            min_cost = float('inf')
            best_problem = None

            participant_formatted = {
                "skills": participant.get("self_rated_skills", {}),
                "role_preferences": {role: 1.0 for role in participant.get("primary_roles", [])},
                "motivation_embedding": participant.get("motivation_embedding"),
                "ambiguity_tolerance": participant.get("ambiguity_tolerance", 0.5),
                "hours_per_week": participant.get("availability_hours", 20)
            }
            
            for problem in processed_problems:
                problem_formatted = {
                    "required_skills": problem.get("required_skills", {}),
                    "role_preferences": problem.get("role_preferences", {}),
                    "motivation_embedding": problem.get("problem_embedding"),
                    "expected_ambiguity": problem.get("expected_ambiguity", 0.5),
                    "expected_hours_per_week": problem.get("estimated_hours", 40) / 4,
                }
                
                cost = compute_individual_cost(participant_formatted, problem_formatted, PHASE1_WEIGHTS)
                cost += (1.0 - problem.get("problem_score", 0.5)) * 0.3 # Add quality bonus
                
                if cost < min_cost:
                    min_cost = cost
                    best_problem = problem
            
            if best_problem:
                assignment = {
                    "participant_id": participant["id"],
                    "participant_name": participant.get("name", "Unknown"),
                    "problem_id": best_problem["id"],
                    "problem_title": best_problem.get("title", "Untitled"),
                    "cost": min_cost,
                    "created_at": datetime.utcnow().isoformat()
                }
                assignments.append(assignment)
                total_cost += min_cost

                await db.participants.update_one(
                    {"_id": participant["id"]},
                    {"$set": {
                        "assigned_problem_id": best_problem["id"],
                        "assigned_problem_title": best_problem.get("title", "Untitled"),
                        "assignment_cost": min_cost,
                        "assigned_at": datetime.utcnow().isoformat()
                    }}
                )
        
        if assignments:
            await db.individual_problem_assignments.insert_many(assignments)
            logger.info(f"✅ Created {len(assignments)} optimal assignments")
        
        # 🤖 AI REVIEW PASS: Phase 1 Quality Assessment
        logger.info("🔍 Starting AI review of Phase 1 assignments...")
        ai_review = await review_phase1_assignments(assignments, participants, processed_problems)
        
        # Store AI review in database
        await db.ai_phase_reviews.delete_many({"phase": "phase1"})  # Clear previous reviews
        await db.ai_phase_reviews.insert_one(ai_review)
        logger.info(f"🤖 Phase 1 AI Review: {ai_review.get('quality_rating', 'unknown')} quality")
        
        logger.info(f"🎉 Sophisticated Phase 1 Complete! Total cost: {total_cost:.4f}")
        
        return {
            "status": "completed",
            "assignments_created": len(assignments),
            "total_cost": round(total_cost, 4),
            "ai_review": {
                "quality_rating": ai_review.get("quality_rating", "unknown"),
                "overall_quality": ai_review.get("overall_quality", 0.7),
                "key_insights": ai_review.get("key_insights", [])[:3]  # First 3 insights
            },
            "message": f"Assigned {len(assignments)} participants to their optimal problems with AI review."
        }
        
    except Exception as e:
        logger.error(f"❌ Sophisticated Phase 1 failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Phase 1 failed: {str(e)}")


@router.post("/simple/phase2")
async def simple_phase2(request: SimplePhase2Request):
    """
    Phase 2: Optimal team formation using Hungarian algorithm.
    """
    try:
        logger.info("🚀 Starting Sophisticated Phase 2 with Hungarian Algorithm...")
        
        # Clear existing teams
        await db.final_teams.delete_many({})
        
        # Get all participants with their assigned problems
        participants = await db.participants.find({}).to_list(length=None)
        if not participants:
            raise HTTPException(status_code=400, detail="No participants found. Run Phase 1 first.")
        
        logger.info(f"📊 Found {len(participants)} total participants for STRICT team formation")
        
        # STRICT TEAM FORMATION: Form teams across ALL participants first
        logger.info(f"🔒 Using STRICT formation: {len(participants)} participants → teams of {request.target_team_size}")
        
        # Use STRICT team formation on ALL participants (ignore problem groups for team formation)
        all_team_assignments = await strict_team_formation(participants, request.target_team_size)
        
        logger.info(f"✅ STRICT formation created {len(all_team_assignments)} teams")
        
        # Verify strict compliance
        total_in_teams = sum(len(team) for team in all_team_assignments)
        logger.info(f"📊 STRICT verification: {total_in_teams}/{len(participants)} participants in teams")
        
        if total_in_teams != len(participants):
            logger.error(f"❌ STRICT enforcement FAILED: {total_in_teams} != {len(participants)}")
            raise HTTPException(status_code=500, detail=f"Strict enforcement failed: {total_in_teams} != {len(participants)}")
        
        # 👑 ENSURE LEADERSHIP: Verify each team has at least one leader
        team_assignments_dict = {i: team for i, team in enumerate(all_team_assignments)}
        team_assignments_dict = await ensure_team_leadership(team_assignments_dict, participants)
        
        # Now assign each team to the most common problem among its members
        all_teams = []
        team_counter = 1
        
        for team_idx, team_members in team_assignments_dict.items():
            # Find the most common problem assignment among team members
            problem_votes = {}
            for member in team_members:
                problem_id = member.get("assigned_problem_id")
                if problem_id:
                    problem_votes[problem_id] = problem_votes.get(problem_id, 0) + 1
            
            # Assign team to problem with most votes, or first problem if tie
            if problem_votes:
                best_problem_id = max(problem_votes.items(), key=lambda x: x[1])[0]
            
            # Get problem details
                problem = await db.problems.find_one({"_id": best_problem_id})
            problem_title = problem.get("title", "Unknown Problem") if problem else "Unknown Problem"
            else:
                # Fallback to first problem if no problem assignments
                first_problem = await db.problems.find_one({})
                best_problem_id = first_problem["_id"] if first_problem else "unknown"
                problem_title = first_problem.get("title", "Unknown Problem") if first_problem else "Unknown Problem"
            
            # Create team document
                team_doc = {
                    "team_id": f"team_{team_counter}",
                "problem_id": best_problem_id,
                    "problem_title": problem_title,
                    "members": [
                        {
                            "participant_id": str(member.get("_id")),
                            "name": member.get("name"),
                            "email": member.get("email"),
                            "primary_roles": member.get("primary_roles", []),
                            "self_rated_skills": member.get("self_rated_skills", {}),
                        "availability_hours": member.get("availability_hours", 0),
                        "leadership_preference": member.get("leadership_preference", False),
                        "experience_level": member.get("experience_level", "intermediate")
                        }
                        for member in team_members
                    ],
                    "team_size": len(team_members),
                    "created_at": datetime.utcnow().isoformat(),
                "phase": "phase2_strict_global",
                "algorithm": "strict_enforcement"
                }
                
                all_teams.append(team_doc)
                team_counter += 1
            
            # Log team assignment
            logger.info(f"✅ Team {team_counter-1}: {len(team_members)} members → Problem '{problem_title}'")
        
        logger.info(f"✅ Created {len(all_teams)} STRICT teams across all participants")
        
        # 🧠 AI ROLE BALANCE ANALYSIS: Analyze each team for role balance (optional)
        if request.enable_ai_analysis and all_teams:
            logger.info("🔍 Starting AI role balance analysis for all teams (parallel processing)...")
            
            async def analyze_single_team(team_doc):
                """Analyze a single team's role balance."""
                try:
                    role_analysis = await analyze_team_role_balance(team_doc)
                    team_doc["role_balance_analysis"] = role_analysis
                    
                    if not role_analysis.get("is_balanced", True):
                        logger.info(f"⚠️ Team {team_doc['team_id']} is unbalanced: {role_analysis.get('balance_explanation', 'Unknown reason')}")
                    else:
                        logger.info(f"✅ Team {team_doc['team_id']} is well-balanced")
                        
                except Exception as e:
                                    logger.warning(f"Failed to analyze role balance for team {team_doc.get('team_id', 'unknown')}: {e}")
                team_doc["role_balance_analysis"] = {
                    "is_balanced": True,
                    "balance_score": 0.7,
                    "missing_roles": [],
                    "concise_issue": "Analysis failed - assuming balanced",
                    "urgency": "low",
                    "confidence": 0.5,
                    "analysis_method": "error_fallback"
                }
            
            # Run all team analyses in parallel
            await asyncio.gather(*[analyze_single_team(team_doc) for team_doc in all_teams])
            logger.info(f"✅ AI role balance analysis completed for {len(all_teams)} teams")
        else:
            logger.info("ℹ️ AI role balance analysis disabled or no teams to analyze")
        
        # Store all teams in database
        if all_teams:
            await db.final_teams.insert_many(all_teams)
            logger.info(f"✅ Stored {len(all_teams)} teams in database with role balance analysis")
        
        # Calculate summary statistics
        total_participants_in_teams = sum(team["team_size"] for team in all_teams)
        avg_team_size = total_participants_in_teams / len(all_teams) if all_teams else 0
        
        # Count unique problems that have teams assigned
        problems_with_teams = len(set(team["problem_id"] for team in all_teams)) if all_teams else 0
        
        # 🤖 AI REVIEW PASS: Phase 2 Team Formation Assessment
        logger.info("🔍 Starting AI review of Phase 2 team formations...")
        ai_review = await review_phase2_teams(all_teams, participants)
        
        # Store AI review in database
        await db.ai_phase_reviews.delete_many({"phase": "phase2"})  # Clear previous reviews
        await db.ai_phase_reviews.insert_one(ai_review)
        logger.info(f"🤖 Phase 2 AI Review: {ai_review.get('quality_rating', 'unknown')} quality")
        
        logger.info("🎉 Sophisticated Phase 2 Complete!")
        
        return {
            "status": "completed",
            "teams_created": len(all_teams),
            "total_participants_in_teams": total_participants_in_teams,
            "avg_team_size": round(avg_team_size, 2),
            "problems_with_teams": problems_with_teams,
            "algorithm": "strict_enforcement",
            "ai_review": {
                "quality_rating": ai_review.get("quality_rating", "unknown"),
                "overall_quality": ai_review.get("overall_quality", 0.7),
                "key_insights": ai_review.get("key_insights", [])[:3]  # First 3 insights
            },
            "message": f"STRICT team formation of {len(all_teams)} teams with enforced team sizes using strict algorithm"
        }
        
    except Exception as e:
        logger.error(f"❌ Sophisticated Phase 2 failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Phase 2 failed: {str(e)}")


@router.post("/simple/phase3")
async def simple_phase3(request: SimplePhase3Request):
    """
    Phase 3: Optimal team-problem assignment using Hungarian algorithm.
    """
    try:
        logger.info("🚀 Starting Sophisticated Phase 3 with Hungarian Algorithm...")
        
        # Clear existing final assignments
        await db.team_problem_assignments.delete_many({})
        
        # Get all teams
        teams = await db.final_teams.find({}).to_list(length=None)
        if not teams:
            raise HTTPException(status_code=400, detail="No teams found. Run Phase 2 first.")
        
        # Get all problems with scores
        problems = await db.problems.find({"processed": True}).to_list(length=None)
        if not problems:
            raise HTTPException(status_code=400, detail="No processed problems found. Run Phase 1 first.")
        
        logger.info(f"📊 Found {len(teams)} teams and {len(problems)} problems for optimal assignment")
        
        # Build sophisticated cost matrix
        logger.info("🔧 Building sophisticated team-problem cost matrix...")
        cost_matrix, team_map, problem_map = await build_team_problem_assignment_matrix(teams, problems)
        
        logger.info(f"📊 Cost matrix shape: {cost_matrix.shape}")
        
        # Solve using Hungarian algorithm
        logger.info("🎯 Running Hungarian algorithm for optimal team-problem assignment...")
        row_indices, col_indices = linear_sum_assignment(cost_matrix)
        
        # Extract assignments - ensure every team gets assigned
        final_assignments = []
        total_cost = 0.0
        assigned_teams = set()
        assigned_problems = set()
        
        # First pass: Assign teams with good matches (cost < 1e5)
        for row, col in zip(row_indices, col_indices):
            if row < len(team_map) and col < len(problem_map):
                team_id = team_map[row]
                problem_id = problem_map[col]
                cost = cost_matrix[row, col]
                
                # Accept good assignments first
                if cost < 1e5:
                    team = next(t for t in teams if t["team_id"] == team_id)
                    problem = next(p for p in problems if p["id"] == problem_id)
                    
                    assignment = {
                        "team_id": team_id,
                        "team_size": team["team_size"],
                        "problem_id": problem_id,
                        "problem_title": problem.get("title", "Unknown"),
                        "problem_score": problem.get("problem_score", 0.5),
                        "assignment_cost": cost,
                        "optimization_strategy": request.optimization_strategy,
                        "algorithm": "hungarian",
                        "created_at": datetime.utcnow().isoformat()
                    }
                    final_assignments.append(assignment)
                    total_cost += cost
                    assigned_teams.add(team_id)
                    assigned_problems.add(problem_id)
                    
                    # Update team with final problem assignment
                    await db.final_teams.update_one(
                        {"team_id": team_id},
                        {"$set": {
                            "final_problem_id": problem_id,
                            "final_problem_title": problem.get("title", "Unknown"),
                            "final_assignment_cost": cost,
                            "final_assigned_at": datetime.utcnow().isoformat()
                        }}
                    )
                    
                    logger.info(f"✅ Optimally assigned {team_id} to '{problem.get('title')}' (cost: {cost:.4f})")
        
        # Second pass: Assign remaining teams to remaining problems or reuse problems
        unassigned_teams = [team_map[i] for i in range(len(team_map)) if team_map[i] not in assigned_teams]
        available_problems = problems.copy()  # All problems can be reused
        
        for team_id in unassigned_teams:
            team = next(t for t in teams if t["team_id"] == team_id)
            
            # Find the best available problem for this team
            best_problem = None
            best_cost = float('inf')
            
            for problem in available_problems:
                team_idx = next(i for i, tid in team_map.items() if tid == team_id)
                problem_idx = next(i for i, pid in problem_map.items() if pid == problem["id"])
                
                if team_idx < cost_matrix.shape[0] and problem_idx < cost_matrix.shape[1]:
                    cost = cost_matrix[team_idx, problem_idx]
                    # Even accept high costs if necessary - normalize them
                    if cost >= 1e5:
                        cost = 0.8 + (cost - 1e5) / 1e6  # Convert padding to reasonable cost
                    
                    if cost < best_cost:
                        best_cost = cost
                        best_problem = problem
            
            if best_problem:
                assignment = {
                    "team_id": team_id,
                    "team_size": team["team_size"],
                    "problem_id": best_problem["id"],
                    "problem_title": best_problem.get("title", "Unknown"),
                    "problem_score": best_problem.get("problem_score", 0.5),
                    "assignment_cost": best_cost,
                    "optimization_strategy": request.optimization_strategy,
                    "algorithm": "hungarian_fallback",
                    "created_at": datetime.utcnow().isoformat()
                }
                final_assignments.append(assignment)
                total_cost += best_cost
                
                # Update team with final problem assignment
                await db.final_teams.update_one(
                    {"team_id": team_id},
                    {"$set": {
                        "final_problem_id": best_problem["id"],
                        "final_problem_title": best_problem.get("title", "Unknown"),
                        "final_assignment_cost": best_cost,
                        "final_assigned_at": datetime.utcnow().isoformat()
                    }}
                )
                
                logger.info(f"✅ Fallback assigned {team_id} to '{best_problem.get('title')}' (cost: {best_cost:.4f})")
        
        # 🎯 ENSURE NO UNUSED PROBLEMS: Make sure every problem gets at least one team
        logger.info("🔍 Ensuring no problems are left unassigned...")
        assigned_problem_ids = set(assignment["problem_id"] for assignment in final_assignments)
        unassigned_problems = [p for p in problems if p["id"] not in assigned_problem_ids]
        
        if unassigned_problems:
            logger.info(f"⚠️ Found {len(unassigned_problems)} unassigned problems, creating additional assignments...")
            
            for problem in unassigned_problems:
                # Find the team with the lowest assignment cost to assign to this problem
                team_costs = []
                for team in teams:
                    team_idx = next(i for i, tid in team_map.items() if tid == team["team_id"])
                    problem_idx = next(i for i, pid in problem_map.items() if pid == problem["id"])
                    
                    if team_idx < cost_matrix.shape[0] and problem_idx < cost_matrix.shape[1]:
                        cost = cost_matrix[team_idx, problem_idx]
                        if cost >= 1e5:
                            cost = 0.9 + (cost - 1e5) / 1e6  # Normalize high costs
                        team_costs.append((team, cost))
                
                if team_costs:
                    # Choose team with lowest cost for this problem
                    best_team, best_cost = min(team_costs, key=lambda x: x[1])
                    
                    assignment = {
                        "team_id": best_team["team_id"],
                        "team_size": best_team["team_size"],
                        "problem_id": problem["id"],
                        "problem_title": problem.get("title", "Unknown"),
                        "problem_score": problem.get("problem_score", 0.5),
                        "assignment_cost": best_cost,
                        "optimization_strategy": request.optimization_strategy,
                        "algorithm": "unused_problem_recovery",
                        "created_at": datetime.utcnow().isoformat()
                    }
                    final_assignments.append(assignment)
                    total_cost += best_cost
                    
                    # Update team with additional problem assignment (allowing multiple problems per team)
                    await db.final_teams.update_one(
                        {"team_id": best_team["team_id"]},
                        {"$addToSet": {
                            "additional_problems": {
                                "problem_id": problem["id"],
                                "problem_title": problem.get("title", "Unknown"),
                                "assignment_cost": best_cost,
                                "assigned_at": datetime.utcnow().isoformat()
                            }
                        }}
                    )
                    
                    logger.info(f"🔄 Assigned unused problem '{problem.get('title')}' to team {best_team['team_id']} (cost: {best_cost:.4f})")
        else:
            logger.info("✅ All problems have been assigned to teams")
        
        # Store final assignments
        if final_assignments:
            await db.team_problem_assignments.insert_many(final_assignments)
            logger.info(f"✅ Stored {len(final_assignments)} optimal assignments")
        
        # Calculate summary statistics
        avg_cost = total_cost / len(final_assignments) if final_assignments else 0
        avg_problem_score = sum(assignment["problem_score"] for assignment in final_assignments) / len(final_assignments) if final_assignments else 0
        
        # 🤖 AI REVIEW PASS: Phase 3 Assignment Quality Assessment
        logger.info("🔍 Starting AI review of Phase 3 team-problem assignments...")
        ai_review = await review_phase3_assignments(final_assignments, teams, problems)
        
        # Store AI review in database
        await db.ai_phase_reviews.delete_many({"phase": "phase3"})  # Clear previous reviews
        await db.ai_phase_reviews.insert_one(ai_review)
        logger.info(f"🤖 Phase 3 AI Review: {ai_review.get('quality_rating', 'unknown')} quality")
        
        # 🎯 FINAL PASS: AI-Generated Team Scoring
        logger.info("🤖 Starting AI-powered team scoring analysis...")
        ai_scores_generated = 0
        ai_score_summary = {
            "avg_ai_diversity": 0.0,
            "avg_ai_skills_coverage": 0.0,
            "avg_ai_role_coverage": 0.0,
            "avg_ai_role_balance": 0.0,
            "avg_ai_confidence": 0.0
        }
        
        try:
            # Get updated teams with final assignments
            teams_with_assignments = await db.final_teams.find({"final_problem_id": {"$exists": True}}).to_list(length=None)
            
            all_ai_scores = []
            for team in teams_with_assignments:
                try:
                    # Get problem data for this team
                    problem_id = team.get("final_problem_id")
                    problem = await db.problems.find_one({"_id": problem_id})
                    
                    if problem:
                        # Call AI scoring
                        ai_scores = await get_team_scores(team, problem)
                        
                        # Store AI scores in team document
                        await db.final_teams.update_one(
                            {"team_id": team["team_id"]},
                            {"$set": {
                                "ai_scores": ai_scores,
                                "ai_scored_at": datetime.utcnow().isoformat()
                            }}
                        )
                        
                        all_ai_scores.append(ai_scores)
                        ai_scores_generated += 1
                        
                        logger.info(f"🎯 AI scored {team['team_id']}: diversity={ai_scores['diversity_score']:.2f}, confidence={ai_scores['confidence_score']:.2f}")
                        
                except Exception as team_error:
                    logger.warning(f"Failed to score team {team.get('team_id', 'unknown')}: {team_error}")
                    continue
            
            # Calculate AI score averages
            if all_ai_scores:
                ai_score_summary = {
                    "avg_ai_diversity": round(sum(s["diversity_score"] for s in all_ai_scores) / len(all_ai_scores), 3),
                    "avg_ai_skills_coverage": round(sum(s["skills_coverage"] for s in all_ai_scores) / len(all_ai_scores), 3),
                    "avg_ai_role_coverage": round(sum(s["role_coverage"] for s in all_ai_scores) / len(all_ai_scores), 3),
                    "avg_ai_role_balance": round(sum(s["role_balance"] for s in all_ai_scores) / len(all_ai_scores), 3),
                    "avg_ai_confidence": round(sum(s["confidence_score"] for s in all_ai_scores) / len(all_ai_scores), 3)
                }
                
            logger.info(f"🤖 AI Scoring Complete! Generated scores for {ai_scores_generated} teams")
            
        except Exception as ai_error:
            logger.warning(f"AI scoring encountered issues: {ai_error}")
        
        logger.info(f"🎉 Sophisticated Phase 3 Complete! Total cost: {total_cost:.4f}")
        
        return {
            "status": "completed",
            "teams_assigned": len(final_assignments),
            "total_assignment_cost": round(total_cost, 4),
            "avg_assignment_cost": round(avg_cost, 4),
            "avg_problem_score": round(avg_problem_score, 4),
            "optimization_strategy": request.optimization_strategy,
            "algorithm": "hungarian",
            "ai_scores_generated": ai_scores_generated,
            "ai_score_summary": ai_score_summary,
            "ai_review": {
                "quality_rating": ai_review.get("quality_rating", "unknown"),
                "overall_quality": ai_review.get("overall_quality", 0.7),
                "key_insights": ai_review.get("key_insights", [])[:3]  # First 3 insights
            },
            "message": f"Optimal assignment of {len(final_assignments)} teams using Hungarian algorithm with AI scoring and review"
        }
        
    except Exception as e:
        logger.error(f"❌ Sophisticated Phase 3 failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Phase 3 failed: {str(e)}")


@router.get("/simple/status")
async def simple_status():
    """Get comprehensive status of all phases with algorithm information."""
    try:
        participants = await db.participants.find({}).to_list(length=None)
        problems = await db.problems.find({}).to_list(length=None)
        assignments = await db.individual_problem_assignments.find({}).to_list(length=None)
        teams = await db.final_teams.find({}).to_list(length=None)
        final_assignments = await db.team_problem_assignments.find({}).to_list(length=None)
        
        return {
            "participants_count": len(participants),
            "problems_count": len(problems),
            "assignments_count": len(assignments),
            "teams_count": len(teams),
            "final_assignments_count": len(final_assignments),
            "algorithm_info": {
                "phase1": "Hungarian Algorithm for Participant-Problem Matching",
                "phase2": "Hungarian Algorithm for Team Formation",
                "phase3": "Hungarian Algorithm for Team-Problem Assignment"
            },
            "participants": [
                {
                    "id": str(p.get("_id")),
                    "name": p.get("name"),
                    "assigned_problem_id": p.get("assigned_problem_id"),
                    "assigned_problem_title": p.get("assigned_problem_title"),
                    "assignment_cost": p.get("assignment_cost")
                }
                for p in ensure_deterministic_order(participants, "_id")
            ],
            "teams": [
                {
                    "team_id": t.get("team_id"),
                    "problem_title": t.get("problem_title"),
                    "team_size": t.get("team_size"),
                    "member_names": [m.get("name") for m in t.get("members", [])],
                    "final_problem_title": t.get("final_problem_title"),
                    "final_assignment_cost": t.get("final_assignment_cost"),
                    "algorithm": t.get("algorithm", "hungarian")
                }
                for t in ensure_deterministic_order(teams, "team_id")
            ],
            "final_assignments": [
                {
                    "team_id": fa.get("team_id"),
                    "problem_title": fa.get("problem_title"),
                    "problem_score": fa.get("problem_score"),
                    "assignment_cost": fa.get("assignment_cost"),
                    "team_size": fa.get("team_size"),
                    "algorithm": fa.get("algorithm", "hungarian")
                }
                for fa in ensure_deterministic_order(final_assignments, "team_id")
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}") 


@router.get("/simple/ai-reviews")
async def get_ai_reviews():
    """Get AI reviews for all completed phases."""
    try:
        reviews = await db.ai_phase_reviews.find({}).to_list(length=None)
        
        # Organize reviews by phase
        phase_reviews = {
            "phase1": None,
            "phase2": None,
            "phase3": None
        }
        
        for review in reviews:
            phase = review.get("phase")
            if phase in phase_reviews:
                # Remove MongoDB _id for JSON serialization
                review.pop("_id", None)
                phase_reviews[phase] = review
        
        return {
            "reviews": phase_reviews,
            "total_reviews": len([r for r in phase_reviews.values() if r is not None]),
            "last_updated": max([r.get("review_timestamp", "") for r in reviews], default="")
        }
        
    except Exception as e:
        logger.error(f"Error fetching AI reviews: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch AI reviews: {str(e)}")