import asyncio
import logging
import os
import json

import openai
from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)

logger = logging.getLogger(__name__)

# It's recommended to set the API key in the environment.
# For local development, you can use a .env file.
# For production, this should be managed by the deployment environment.
openai.api_key = os.getenv("OPENAI_API_KEY")

aclient = AsyncOpenAI()


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
async def get_completion(prompt: str, model: str = "gpt-4-turbo") -> str:
    """
    Generates a completion using the OpenAI API with retry logic.
    """
    if not openai.api_key:
        logger.warning("OPENAI_API_KEY is not set. Returning empty string.")
        return ""

    try:
        response = await asyncio.wait_for(
            aclient.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            ),
            timeout=10,
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("OpenAI response content is None.")
        return content

    except asyncio.TimeoutError:
        logger.error("OpenAI request timed out.")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred with OpenAI: {e}")
        raise 

async def get_problem_analysis(raw_prompt: str) -> dict:
    """
    Performs a three-pass analysis on a raw problem description to extract
    structured data.
    """
    # This is a placeholder for the described three-pass GPT extraction.
    # A real implementation would be more sophisticated.
    try:
        response = await openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a problem analyst. Extract the required skills, role preferences (as a normalized JSON object), and expected ambiguity (as a float from 0 to 1) from the following problem description."
                },
                {
                    "role": "user",
                    "content": raw_prompt
                }
            ],
            response_format={"type": "json_object"}
        )
        # In a real scenario, you would parse this more carefully
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Error getting problem analysis: {e}")
        return {} 