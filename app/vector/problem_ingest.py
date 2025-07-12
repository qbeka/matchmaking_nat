import logging
import numpy as np

from app.worker.celery_app import celery_app
from app.llm.openai_client import get_problem_analysis, get_embedding
from app.vector.pinecone_client import pinecone_client
from app.db import db
from app.models import Problem

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
async def parse_problem(self, problem_id: str):
    """
    Parses a problem, extracts structured data, generates an embedding,
    and upserts it into Pinecone.
    """
    try:
        problem_doc = await db.problems.find_one({"_id": problem_id})
        if not problem_doc:
            logger.error(f"Problem with id {problem_id} not found.")
            return

        problem = Problem(**problem_doc)
        
        # Extract structured data and update the problem record
        analysis = await get_problem_analysis(problem.raw_prompt)
        # Here you would update the problem with the extracted fields
        # e.g., problem.required_skills = analysis.get("required_skills", {})
        
        # Generate embedding for the problem description
        embedding = await get_embedding(problem.raw_prompt)
        if embedding:
            problem.problem_embedding = embedding
            
            # Update the problem in MongoDB
            await db.problems.update_one(
                {"_id": problem.id},
                {"$set": {"problem_embedding": embedding}}
            )

            # Upsert into Pinecone
            await pinecone_client.upsert_vectors(
                [(f"problem:{problem.id}", np.array(embedding))]
            )
            logger.info(f"Successfully parsed and upserted problem {problem.id}")
        else:
            logger.error(f"Could not generate embedding for problem {problem.id}")

    except Exception as e:
        logger.error(f"Error parsing problem {problem_id}: {e}")
        self.retry(exc=e) 