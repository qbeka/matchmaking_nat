import logging
from typing import Any, Dict
import redis
from datetime import datetime

from celery.exceptions import Reject
from pydantic import ValidationError

from app.scoring.bayes import SkillPosterior
from app.utils.validate import validate_participant
from app.worker.celery_app import celery_app
from app.matching.build_matrix import build_individual_problem_matrix
from app.matching.hungarian_capacity import solve_hungarian_capacity
from app.matching.team_builder import build_provisional_teams
from app.matching.slot_solver import solve_team_slots, calculate_team_coverage_metrics
from app.db import db
from app.llm.openai_client import get_gpt_analysis, get_embedding
from app.vector.pinecone_client import pinecone_client

logger = logging.getLogger(__name__)
redis_client = redis.Redis(host='localhost', port=6379, db=0)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
async def score_participant(self, participant_payload: Dict[str, Any]):
    try:
        participant = validate_participant(participant_payload)
    except ValidationError as e:
        logger.error(f"Validation failed for participant: {e}")
        raise Reject(e, requeue=False)

    enriched_skills = {}
    for skill_name, self_rating in participant.self_rated_skills.items():
        try:
            posterior = SkillPosterior()
            posterior.update_from_self_rating(self_rating)
            # In the future, other evidence sources will be added here.
            enriched_skills[skill_name] = {
                "mean": posterior.mean,
                "std_dev": posterior.std_dev,
                "alpha": posterior.alpha,
                "beta": posterior.beta,
            }
        except Exception as e:
            logger.error(
                f"Error scoring skill '{skill_name}' for participant: {e}"
            )
            # Decide if this should be a retryable error.
            # For now, we will log and continue.

    # Placeholder for where the full enriched record will be written to MongoDB.
    enriched_participant = participant.dict()
    enriched_participant["enriched_skills"] = enriched_skills
    
    # Get GPT analysis and embedding
    gpt_analysis = await get_gpt_analysis(participant.motivation_text)
    enriched_participant["gpt_traits"] = gpt_analysis
    
    motivation_embedding = await get_embedding(participant.motivation_text)
    enriched_participant["motivation_embedding"] = motivation_embedding
    
    # Upsert to Pinecone
    await pinecone_client.upsert_vectors([(str(participant.id), np.array(motivation_embedding))])
    
    logger.info(
        f"Successfully scored participant {participant.email}"
    )
    # In the future, this will return the MongoDB document ID.
    return enriched_participant


@celery_app.task(bind=True)
async def run_stage_one(self):
    """
    Builds the individual-problem cost matrix, runs the Hungarian capacity
    solver, and stores the preliminary clusters in MongoDB.
    """
    redis_pubsub = redis_client.pubsub()

    def post_message(message: str):
        logger.info(message)
        redis_client.publish("match_progress", message)

    try:
        post_message("Starting Stage 1: Building cost matrix...")
        cost_matrix, p_map, s_map = await build_individual_problem_matrix()
        if cost_matrix.size == 0:
            post_message("No participants or problems to match. Aborting.")
            return {"status": "aborted", "reason": "No data"}

        post_message("Cost matrix built. Running Hungarian solver...")
        assignments, total_cost = solve_hungarian_capacity(cost_matrix, p_map, s_map)

        post_message(f"Solver finished. Total cost: {total_cost}. Storing results...")
        
        await db.prelim_teams.delete_many({})
        await db.prelim_teams.insert_one({
            "assignments": assignments,
            "total_cost": total_cost,
            "created_at": datetime.utcnow(),
        })

        post_message("Stage 1 complete.")
        return {"status": "complete", "total_cost": total_cost, "assignments": assignments}

    except Exception as e:
        post_message(f"An error occurred during Stage 1: {e}")
        logger.error(f"Stage 1 failed: {e}", exc_info=True)
        raise
    finally:
        redis_pubsub.close()


@celery_app.task(bind=True)
async def run_stage_two(self):
    """
    Build final teams from preliminary clusters using internal team formation.
    """
    redis_pubsub = redis_client.pubsub()

    def post_message(message: str):
        logger.info(message)
        redis_client.publish("match_progress", message)

    try:
        post_message("Starting Stage 2: Building final teams...")
        
        # Get preliminary teams from stage 1
        prelim_result = await db.prelim_teams.find_one(sort=[("created_at", -1)])
        if not prelim_result:
            post_message("No preliminary teams found. Run Stage 1 first.")
            return {"status": "error", "reason": "No preliminary teams found"}
        
        # Extract assignments and convert to team clusters
        assignments = prelim_result.get("assignments", [])
        if not assignments:
            post_message("No assignments found in preliminary teams.")
            return {"status": "error", "reason": "No assignments found"}
        
        post_message("Converting assignments to team clusters...")
        
        # Group participants by problem assignment
        problem_clusters = {}
        for assignment in assignments:
            participant_id = assignment.get("participant_id")
            problem_id = assignment.get("problem_id")
            
            if problem_id not in problem_clusters:
                problem_clusters[problem_id] = []
            
            # Fetch participant data
            participant = await db.participants.find_one({"_id": participant_id})
            if participant:
                problem_clusters[problem_id].append(participant)
        
        # Convert to list of clusters
        prelim_teams = list(problem_clusters.values())
        
        post_message(f"Found {len(prelim_teams)} preliminary clusters. Building provisional teams...")
        
        # Build provisional teams using k-medoids clustering
        provisional_teams = build_provisional_teams(
            prelim_teams=prelim_teams,
            desired_team_size=4,
            max_iter=100,
            random_seed=42
        )
        
        post_message(f"Built {len(provisional_teams)} provisional teams. Optimizing with slot solver...")
        
        # Get all participants for slot filling
        all_participants = []
        async for participant in db.participants.find({}):
            all_participants.append(participant)
        
        # Solve final team slots
        final_teams = solve_team_slots(
            teams=provisional_teams,
            available_participants=all_participants,
            target_team_size=4,
            role_coverage_threshold=0.6
        )
        
        post_message("Calculating team metrics...")
        
        # Calculate metrics for each team
        team_documents = []
        for i, team in enumerate(final_teams):
            metrics = calculate_team_coverage_metrics(team)
            
            team_doc = {
                "team_id": f"team_{i+1}",
                "members": [
                    {
                        "participant_id": str(member.get("_id")),
                        "name": member.get("name"),
                        "email": member.get("email"),
                        "primary_roles": member.get("primary_roles", []),
                        "availability_hours": member.get("availability_hours", 0)
                    }
                    for member in team
                ],
                "team_size": len(team),
                "skills_covered": metrics["skill_coverage"],
                "diversity_score": metrics["diversity_score"],
                "confidence_score": metrics["confidence_score"],
                "role_balance_flag": metrics["role_balance_flag"],
                "role_coverage": metrics["role_coverage"],
                "created_at": datetime.utcnow()
            }
            team_documents.append(team_doc)
        
        # Store final teams in MongoDB
        await db.final_teams.delete_many({})
        if team_documents:
            await db.final_teams.insert_many(team_documents)
        
        # Publish progress update
        summary = {
            "total_teams": len(final_teams),
            "avg_team_size": sum(len(team) for team in final_teams) / max(1, len(final_teams)),
            "avg_coverage": sum(doc["skills_covered"] for doc in team_documents) / max(1, len(team_documents)),
            "avg_diversity": sum(doc["diversity_score"] for doc in team_documents) / max(1, len(team_documents)),
            "teams_with_good_coverage": sum(1 for doc in team_documents if doc["skills_covered"] >= 0.6)
        }
        
        post_message(f"Stage 2 complete. Created {summary['total_teams']} teams with avg coverage {summary['avg_coverage']:.2f}")
        
        return {
            "status": "complete", 
            "summary": summary,
            "teams": team_documents
        }

    except Exception as e:
        post_message(f"An error occurred during Stage 2: {e}")
        logger.error(f"Stage 2 failed: {e}", exc_info=True)
        raise
    finally:
        redis_pubsub.close()


@celery_app.task(bind=True)
async def run_stage_three(self):
    """
    Execute final team-to-problem assignment using Hungarian algorithm.
    """
    redis_pubsub = redis_client.pubsub()

    def post_message(message: str):
        logger.info(message)
        redis_client.publish("match_progress", message)

    try:
        post_message("Starting Stage 3: Building team-problem matrix...")
        
        # Import here to avoid circular imports
        from app.matching.build_team_problem_matrix import build_team_problem_matrix, validate_matrix_inputs
        from app.matching.final_hungarian import (
            solve_final_assignment, store_final_assignments, 
            calculate_assignment_statistics, validate_assignment
        )
        
        # Validate inputs
        validation = await validate_matrix_inputs()
        if not validation["can_build_matrix"]:
            post_message(f"Cannot build matrix: {validation['team_count']} teams, {validation['problem_count']} problems")
            return {"status": "error", "reason": "Insufficient data for matrix building"}
        
        post_message(f"Building matrix with {validation['team_count']} teams and {validation['problem_count']} problems...")
        
        # Build team-problem cost matrix
        cost_matrix, team_map, problem_map = await build_team_problem_matrix()
        
        if cost_matrix.size == 0:
            post_message("Empty cost matrix generated. Aborting.")
            return {"status": "error", "reason": "Empty cost matrix"}
        
        post_message("Matrix built. Running Hungarian algorithm...")
        
        # Solve assignment problem
        assignment_mapping, total_cost = await solve_final_assignment(
            cost_matrix, team_map, problem_map
        )
        
        if not assignment_mapping:
            post_message("No valid assignments found.")
            return {"status": "error", "reason": "No valid assignments"}
        
        post_message(f"Assignment complete. Total cost: {total_cost:.4f}")
        
        # Validate assignment
        validation_results = await validate_assignment(assignment_mapping)
        if not validation_results["is_valid"]:
            post_message(f"Assignment validation failed: {validation_results}")
            return {"status": "error", "reason": "Invalid assignment", "validation": validation_results}
        
        # Calculate statistics
        stats = await calculate_assignment_statistics(
            assignment_mapping, cost_matrix, team_map, problem_map
        )
        
        post_message("Storing final assignments...")
        
        # Store results in MongoDB
        assignment_id = await store_final_assignments(assignment_mapping, total_cost)
        
        # Publish final statistics
        final_stats = {
            "assignment_count": len(assignment_mapping),
            "total_cost": total_cost,
            "mean_cost": stats["mean_cost"],
            "worst_case_cost": stats["worst_case_cost"],
            "best_case_cost": stats["best_case_cost"],
            "assignment_efficiency": stats["assignment_efficiency"]
        }
        
        post_message(f"Stage 3 complete. Assigned {final_stats['assignment_count']} teams. Mean cost: {final_stats['mean_cost']:.4f}")
        
        # Publish Redis event with statistics
        redis_client.publish("assignment_complete", str({
            "mean_skill_gap": final_stats["mean_cost"] * 0.35,  # Approximate skill gap component
            "mean_role_gap": final_stats["mean_cost"] * 0.20,   # Approximate role gap component
            "worst_case_cost": final_stats["worst_case_cost"],
            "assignment_efficiency": final_stats["assignment_efficiency"],
            "total_assignments": final_stats["assignment_count"]
        }))
        
        return {
            "status": "complete",
            "assignment_id": assignment_id,
            "statistics": final_stats,
            "assignments": assignment_mapping
        }

    except Exception as e:
        post_message(f"An error occurred during Stage 3: {e}")
        logger.error(f"Stage 3 failed: {e}", exc_info=True)
        raise
    finally:
        redis_pubsub.close()
