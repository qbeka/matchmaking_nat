import asyncio

import redis.asyncio as redis
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.worker.tasks import run_stage_one, run_stage_two, run_stage_three
from app.db import db
from app.vector.pinecone_client import pinecone_client

router = APIRouter()


@router.get("/similarity/{participant_id}")
async def get_similar_problems(participant_id: str):
    """
    Returns the top 10 most similar problems for a given participant.
    """
    participant = await db.participants.find_one({"_id": participant_id})
    if not participant or "motivation_embedding" not in participant:
        raise HTTPException(status_code=404, detail="Participant or embedding not found")

    embedding = participant["motivation_embedding"]
    
    try:
        matches = await pinecone_client.query(
            top_k=10,
            vector=embedding
        )
        problem_ids = [match['id'] for match in matches if match['id'].startswith("problem:")]
        return {"participant_id": participant_id, "similar_problems": problem_ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match/stage1")
async def start_stage_one_matching():
    task = run_stage_one.delay()
    return {"task_id": task.id, "status": "started"}


@router.get("/match/stage1/status")
async def get_stage_one_status():
    async def event_stream():
        pubsub = redis.Redis(host="localhost", port=6379, db=0).pubsub()
        await pubsub.subscribe("match_progress")
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                yield f"data: {message['data'].decode('utf-8')}\n\n"
            await asyncio.sleep(0.1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/match/phase2")
async def start_phase_two_matching():
    """Start phase 2 matching (internal team formation)."""
    # TODO: Add check to ensure phase 1 is complete
    task = run_stage_two.delay()
    return {"task_id": task.id, "status": "started"}


@router.get("/match/phase2/status")
async def get_phase_two_status():
    """Get real-time status of phase 2 matching with team summaries."""
    async def event_stream():
        pubsub = redis.Redis(host="localhost", port=6379, db=0).pubsub()
        await pubsub.subscribe("match_progress")
        
        # Also send current team summaries if available
        try:
            async for team_doc in db.final_teams.find({}):
                team_summary = {
                    "team_id": team_doc.get("team_id"),
                    "team_size": team_doc.get("team_size", 0),
                    "skills_covered": team_doc.get("skills_covered", 0.0),
                    "diversity_score": team_doc.get("diversity_score", 0.0),
                    "confidence_score": team_doc.get("confidence_score", 0.0),
                    "role_balance_flag": team_doc.get("role_balance_flag", False)
                }
                yield f"data: TEAM_SUMMARY:{team_summary}\n\n"
        except Exception as e:
            yield f"data: ERROR: Failed to fetch team summaries: {e}\n\n"
        
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                yield f"data: {message['data'].decode('utf-8')}\n\n"
            await asyncio.sleep(0.1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/match/phase3")
async def start_phase_three_matching():
    """Start phase 3 matching (final team-to-problem assignment)."""
    # Check if phase 2 is complete
    team_count = await db.final_teams.count_documents({})
    if team_count == 0:
        return {"error": "Phase 2 must be completed first. No final teams found."}
    
    problem_count = await db.problems.count_documents({})
    if problem_count == 0:
        return {"error": "No problems found in database."}
    
    task = run_stage_three.delay()
    return {"task_id": task.id, "status": "started", "phase": "team_to_problem_assignment"}


@router.get("/match/phase3/status")
async def get_phase_three_status():
    """Get real-time status of phase 3 matching with final assignment results."""
    async def event_stream():
        pubsub = redis.Redis(host="localhost", port=6379, db=0).pubsub()
        await pubsub.subscribe("match_progress")
        await pubsub.subscribe("assignment_complete")
        
        # Send current assignment if available
        from app.db import db
        from app.matching.final_hungarian import get_latest_assignment
        
        try:
            latest_assignment = await get_latest_assignment()
            if latest_assignment:
                # Convert ObjectId to str for JSON serialization
                latest_assignment['_id'] = str(latest_assignment['_id'])
                yield f"data: LATEST_ASSIGNMENT:{latest_assignment}\n\n"
        except Exception as e:
            yield f"data: ERROR: Failed to fetch latest assignment: {e}\n\n"
        
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                channel = message['channel'].decode('utf-8')
                data = message['data'].decode('utf-8')
                
                if channel == "assignment_complete":
                    yield f"data: ASSIGNMENT_STATS:{data}\n\n"
                else:
                    yield f"data: {data}\n\n"
            await asyncio.sleep(0.1)

    return StreamingResponse(event_stream(), media_type="text/event-stream") 