import asyncio
import logging
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

import openai
from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)

logger = logging.getLogger(__name__)

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.warning("OPENAI_API_KEY not found. OpenAI features will be disabled.")
    aclient = None
else:
    aclient = AsyncOpenAI(api_key=api_key)


async def get_completion(prompt: str, model: str = "gpt-4-turbo") -> str:
    """
    Generates a completion using the OpenAI API.
    """
    if not aclient:
        logger.warning("OpenAI client not initialized. Returning empty string.")
        return ""

    try:
        response = await aclient.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("OpenAI response content is None.")
        return content
    except Exception as e:
        logger.error(f"An unexpected error occurred with OpenAI: {e}")
        raise 


async def get_gpt_analysis(motivation_text: str) -> dict:
    """
    Analyzes participant motivation text using GPT to extract structured traits.
    """
    if not aclient:
        logger.warning("OpenAI client not initialized. Returning empty analysis.")
        return {}

    try:
        response = await aclient.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": """You are a participant analyst. Extract structured traits from the motivation text.

Return a JSON object with these fields:
- leadership_potential: float (0.0-1.0) - likelihood of taking leadership roles
- collaboration_style: string - "independent", "collaborative", "supportive"
- technical_curiosity: float (0.0-1.0) - interest in learning new technologies
- problem_solving_approach: string - "analytical", "creative", "systematic"
- communication_preference: string - "direct", "detailed", "visual"
- ambiguity_tolerance: float (0.0-1.0) - comfort with unclear requirements
- innovation_drive: float (0.0-1.0) - desire to create novel solutions
- team_contribution_style: string - "mentor", "implementer", "researcher", "coordinator"

Analyze the motivation text and return valid JSON only."""
                },
                {
                    "role": "user",
                    "content": motivation_text
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Error getting GPT analysis: {e}")
        return {}


async def get_embedding(text: str) -> List[float]:
    """
    Generates an embedding for the given text using OpenAI's embedding model.
    """
    if not aclient:
        logger.warning("OpenAI client not initialized. Returning empty embedding.")
        return []

    try:
        response = await aclient.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error getting embedding: {e}")
        return []


async def get_problem_analysis(raw_prompt: str) -> dict:
    """
    Performs a three-pass analysis on a raw problem description to extract
    structured data.
    """
    if not aclient:
        logger.warning("OpenAI client not initialized. Returning empty analysis.")
        return {}
        
    try:
        response = await aclient.chat.completions.create(
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


async def get_problem_score(raw_prompt: str, additional_context: Optional[Dict[str, Any]] = None) -> float:
    """
    Analyzes a problem and returns a single numerical score representing its
    overall complexity, clarity, and challenge level.
    """
    if not aclient:
        logger.warning("OpenAI client not initialized. Returning default score.")
        return 0.5

    try:
        context = additional_context or {}
        full_context = f"""
Analyze the following problem to generate a holistic score based on its content.

Problem Title: {context.get('title', 'N/A')}
Category: {context.get('category', 'N/A')}
Difficulty Level: {context.get('difficulty_level', 'N/A')}
Description: {raw_prompt}
"""

        system_prompt = """
You are an expert project evaluator for a coding competition. Your task is to provide a single numerical score from 0.00 to 1.00 that represents the problem's overall "matchability" and challenge.

Consider these factors in your score:
- **Clarity (Clarity breeds good matches):** How well-defined is the problem? Is the goal clear? (Higher clarity = higher score)
- **Challenge (Good problems are challenging):** Does it seem appropriately challenging for a competition? (Trivial or impossible problems = lower score)
- **Scope (Well-scoped problems are better):** Is the scope realistic for a small team in a limited time? (Well-scoped = higher score)

Based on your expert assessment of these factors, return a SINGLE JSON object with one key, "problem_score", which is a float between 0.00 and 1.00. Your response must only be the JSON object.
"""

        response = await aclient.chat.completions.create(
            model="gpt-4-turbo", # Using a faster model for this focused task
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_context}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        
        result = json.loads(response.choices[0].message.content)
        score = result.get("problem_score", 0.5)

        logger.info(f"Generated score for '{context.get('title')}': {score}")
        return float(score)
        
    except Exception as e:
        logger.error(f"Error getting problem score: {e}")
        return 0.5


async def get_enhanced_problem_analysis(raw_prompt: str, additional_context: Optional[Dict[str, Any]] = None) -> dict:
    """
    Performs a single, comprehensive GPT analysis for natPortal problems.
    This consolidated approach is faster and more efficient than multiple calls.
    """
    if not aclient:
        logger.warning("OpenAI client not initialized. Returning default analysis.")
        return _get_default_problem_analysis()

    try:
        context = additional_context or {}
        full_context = f"""
Problem Title: {context.get('title', 'N/A')}
Category: {context.get('category', 'N/A')}
Difficulty Level: {context.get('difficulty_level', 'N/A')}
Suggested Skills: {', '.join(context.get('suggested_skills', [])) or 'N/A'}
Business Impact: {context.get('business_impact', 'N/A')}
Success Criteria: {context.get('success_criteria', 'N/A')}

Problem Description:
{raw_prompt}
"""

        system_prompt = """
You are an expert project analyst. Analyze the provided problem context and description to extract a comprehensive set of structured data.

Return a SINGLE JSON object with the following exact fields:
- "required_skills": A dictionary of technical skills needed, with proficiency levels from 1.0 to 5.0. Only use these skill keys: python, javascript, typescript, react, fastapi, aws, gcp, azure, docker, kubernetes, sql, nosql, machine_learning, data_analysis.
- "technical_focus_areas": A list of the main technical domains (max 5). Only use these keys: backend, frontend, fullstack, mobile, data_science, devops, cloud, security, ui_ux, api_design.
- "complexity_level": A string representing the technical complexity. Must be one of: "low", "medium", "high", "expert".
- "estimated_hours_per_week": An integer for the expected weekly time commitment (between 5 and 40).
- "role_preferences": A dictionary of ideal team roles and their weights. The weights MUST sum to 1.0. Only use these role keys: frontend, backend, fullstack, data_science, devops, product_manager, designer.
- "expected_ambiguity": A float from 0.0 (very clear requirements) to 1.0 (highly ambiguous).
- "collaboration_style": A string describing the ideal team working style. Must be one of: "structured", "agile", "flexible", "research_oriented".
- "innovation_level": A float from 0.0 (implementation-focused) to 1.0 (highly innovative/research).

Be consistent and fair in your analysis. Similar problems should receive similar analysis. Ensure the `role_preferences` values sum to 1.0.
Return only a valid JSON object.
"""

        response = await aclient.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_context}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        
        analysis = json.loads(response.choices[0].message.content)

        # --- Validation and Normalization ---
        role_prefs = analysis.get("role_preferences", {})
        if role_prefs:
            total_weight = sum(role_prefs.values())
            if total_weight > 0 and abs(total_weight - 1.0) > 0.01:
                analysis["role_preferences"] = {role: weight/total_weight for role, weight in role_prefs.items()}

        analysis["expected_ambiguity"] = max(0.0, min(1.0, analysis.get("expected_ambiguity", 0.5)))
        analysis["innovation_level"] = max(0.0, min(1.0, analysis.get("innovation_level", 0.5)))
        analysis["estimated_hours_per_week"] = max(5, min(40, analysis.get("estimated_hours_per_week", 20)))
        
        logger.info(f"Enhanced problem analysis completed for prompt: {context.get('title')}")
        return analysis
        
    except Exception as e:
        logger.error(f"Error in single-pass enhanced problem analysis: {e}")
        return _get_default_problem_analysis()


def _get_default_problem_analysis() -> dict:
    """
    Provides default problem analysis when GPT analysis fails.
    
    Returns:
        Default analysis structure
    """
    return {
        "required_skills": {
            "python": 3.0,
            "javascript": 2.5,
            "sql": 2.0
        },
        "role_preferences": {
            "fullstack": 0.4,
            "backend": 0.3,
            "frontend": 0.3
        },
        "expected_ambiguity": 0.5,
        "expected_hours_per_week": 20,
        "technical_focus_areas": ["backend", "frontend"],
        "complexity_level": "medium",
        "collaboration_style": "flexible",
        "innovation_level": 0.5,
        "confidence_score": 0.3,
        "consistency_notes": "Default analysis - GPT unavailable",
        "analysis_timestamp": datetime.utcnow().isoformat()
    } 


async def get_team_scores(team_data: dict, problem_data: dict) -> dict:
    """
    Analyzes a team-problem match and provides AI-generated team performance scores.
    
    Args:
        team_data: Dictionary containing team information including members
        problem_data: Dictionary containing problem details and requirements
        
    Returns:
        Dictionary with AI-generated scores for the team
    """
    if not aclient:
        logger.warning("OpenAI client not initialized. Returning default team scores.")
        return _get_default_team_scores()

    try:
        # Build comprehensive team context
        team_context = f"""
TEAM: {team_data.get('team_id', 'Unknown')}
Team Size: {team_data.get('team_size', 0)} members

ASSIGNED PROBLEM: {problem_data.get('title', 'Unknown Problem')}
Problem Description: {problem_data.get('raw_prompt', 'No description')}
Required Skills: {json.dumps(problem_data.get('required_skills', {}), indent=2)}
Role Preferences: {json.dumps(problem_data.get('role_preferences', {}), indent=2)}
Expected Complexity: {problem_data.get('complexity_level', 'medium')}
Expected Weekly Hours: {problem_data.get('estimated_hours_per_week', 20)}

TEAM MEMBERS:
"""
        
        # Add detailed member information
        members = team_data.get('members', [])
        for i, member in enumerate(members, 1):
            team_context += f"""
Member {i}:
- Name: {member.get('name', 'Unknown')}
- Primary Roles: {', '.join(member.get('primary_roles', []))}
- Skills: {json.dumps(member.get('self_rated_skills', {}), indent=2)}
- Experience Level: {member.get('experience_level', 'intermediate')}
- Availability: {member.get('availability_hours', 20)} hours/week
- Communication Style: {member.get('communication_style', 'balanced')}
- Motivation: {member.get('motivation_summary', 'Not provided')}
"""

        system_prompt = """
You are an expert team performance analyst. Analyze the provided team composition and their assigned problem to evaluate how well-suited this team is for the given challenge.

Consider the following factors in your analysis:
1. SKILLS COVERAGE: How well do the team's combined skills match the problem requirements?
2. ROLE COVERAGE: Does the team have the right mix of roles for this problem?
3. ROLE BALANCE: Is there good distribution of roles, or is one role dominating?
4. DIVERSITY SCORE: How diverse is the team in terms of skills, roles, and experience?
5. CONFIDENCE SCORE: How confident should we be that this team can succeed?

Provide realistic and encouraging scores that reflect actual team capabilities. Consider:
- Skill level matches and gaps
- Role complementarity 
- Team size appropriateness
- Experience distribution
- Communication compatibility
- Motivation alignment with problem domain

Return a JSON object with these exact fields:
- "skills_coverage": Float 0.0-1.0 representing how well team skills match problem requirements
- "role_coverage": Float 0.0-1.0 representing completeness of necessary roles
- "role_balance": Float 0.0-1.0 representing balance of role distribution (higher = more balanced)
- "diversity_score": Float 0.0-1.0 representing overall team diversity and complementarity
- "confidence_score": Float 0.0-1.0 representing confidence in team success potential
- "strengths": List of strings highlighting team's main strengths (max 4 items)
- "potential_challenges": List of strings identifying potential challenges (max 3 items)
- "ai_recommendations": String with specific suggestions for maximizing team effectiveness (max 200 words)

Be realistic but encouraging. Teams should typically score in the 0.4-0.9 range unless there are major issues.
"""

        response = await aclient.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": team_context}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        
        scores = json.loads(response.choices[0].message.content)
        
        # Validate and normalize scores
        required_fields = ["skills_coverage", "role_coverage", "role_balance", "diversity_score", "confidence_score"]
        for field in required_fields:
            if field not in scores:
                scores[field] = 0.6  # Default reasonable score
            else:
                # Ensure scores are in valid range
                scores[field] = max(0.0, min(1.0, float(scores[field])))
        
        # Ensure lists exist
        if "strengths" not in scores:
            scores["strengths"] = ["Team assembled for this problem"]
        if "potential_challenges" not in scores:
            scores["potential_challenges"] = ["Standard project challenges"]
        if "ai_recommendations" not in scores:
            scores["ai_recommendations"] = "Focus on leveraging each member's strengths and maintaining good communication."
        
        # Add metadata
        scores["analysis_timestamp"] = datetime.utcnow().isoformat()
        scores["analysis_method"] = "ai_generated"
        scores["team_id"] = team_data.get('team_id')
        scores["problem_id"] = problem_data.get('id')
        
        logger.info(f"Generated AI scores for {team_data.get('team_id')}: diversity={scores['diversity_score']:.2f}, confidence={scores['confidence_score']:.2f}")
        return scores
        
    except Exception as e:
        logger.error(f"Error getting team scores: {e}")
        return _get_default_team_scores()


def _get_default_team_scores() -> dict:
    """Return default team scores when AI analysis is unavailable."""
    return {
        "skills_coverage": 0.6,
        "role_coverage": 0.6,
        "role_balance": 0.7,
        "diversity_score": 0.6,
        "confidence_score": 0.6,
        "strengths": ["Team has been assembled for this problem"],
        "potential_challenges": ["Standard project coordination challenges"],
        "ai_recommendations": "Focus on clear communication and leveraging individual strengths.",
        "analysis_timestamp": datetime.utcnow().isoformat(),
        "analysis_method": "default_fallback",
        "team_id": None,
        "problem_id": None
    }


async def review_phase1_assignments(assignments: List[dict], participants: List[dict], problems: List[dict]) -> dict:
    """
    AI review of Phase 1 participant-problem assignments.
    Provides quality assessment and suggestions for improvements.
    """
    if not aclient:
        logger.warning("OpenAI client not initialized. Returning default Phase 1 review.")
        return _get_default_phase_review("phase1")

    try:
        # Build context for AI review
        assignment_context = f"""
PHASE 1 REVIEW: Participant-Problem Assignments
Total Participants: {len(participants)}
Total Problems: {len(problems)}
Total Assignments: {len(assignments)}

ASSIGNMENT SUMMARY:
"""
        
        # Group assignments by problem
        problem_assignments = {}
        for assignment in assignments:
            problem_id = assignment.get("problem_id")
            if problem_id not in problem_assignments:
                problem_assignments[problem_id] = []
            problem_assignments[problem_id].append(assignment)
        
        # Add detailed assignment analysis
        for problem_id, problem_assignments_list in problem_assignments.items():
            problem = next((p for p in problems if p.get("id") == problem_id), None)
            problem_title = problem.get("title", "Unknown") if problem else "Unknown"
            
            assignment_context += f"""
Problem: {problem_title} (ID: {problem_id})
- Participants assigned: {len(problem_assignments_list)}
- Required skills: {problem.get('required_skills', {}) if problem else 'Unknown'}
- Assignment costs: {[round(a.get('cost', 0), 3) for a in problem_assignments_list]}
"""

        system_prompt = """
You are an expert matching algorithm auditor. Review the Phase 1 participant-problem assignments and provide quality assessment.

Analyze the assignments for:
1. SKILL ALIGNMENT: Do participants have skills matching their assigned problems?
2. LOAD DISTRIBUTION: Are participants distributed evenly across problems?
3. COST EFFICIENCY: Are assignment costs reasonable (lower is better)?
4. QUALITY CONCERNS: Any participants severely mismatched to their problems?

Return a JSON object with:
- "overall_quality": Float 0.0-1.0 representing overall assignment quality
- "quality_rating": String ("excellent", "good", "fair", "poor")
- "key_insights": List of 3-5 main observations about the assignments
- "improvement_suggestions": List of specific suggestions for better assignments
- "problematic_assignments": List of assignment IDs or descriptions that seem poor
- "strengths": List of what's working well in these assignments
- "confidence": Float 0.0-1.0 how confident you are in this assessment

Be constructive and specific. Focus on actionable improvements.
"""

        response = await aclient.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": assignment_context}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        
        review = json.loads(response.choices[0].message.content)
        
        # Add metadata
        review["phase"] = "phase1"
        review["review_timestamp"] = datetime.utcnow().isoformat()
        review["assignments_reviewed"] = len(assignments)
        review["participants_count"] = len(participants)
        review["problems_count"] = len(problems)
        
        logger.info(f"Phase 1 AI Review: {review.get('quality_rating', 'unknown')} quality ({review.get('overall_quality', 0):.2f})")
        return review
        
    except Exception as e:
        logger.error(f"Error in Phase 1 AI review: {e}")
        return _get_default_phase_review("phase1")


async def review_phase2_teams(teams: List[dict], participants: List[dict]) -> dict:
    """
    AI review of Phase 2 team formations.
    Provides quality assessment and suggestions for team improvements.
    """
    if not aclient:
        logger.warning("OpenAI client not initialized. Returning default Phase 2 review.")
        return _get_default_phase_review("phase2")

    try:
        # Build context for AI review
        team_context = f"""
PHASE 2 REVIEW: Team Formation Analysis
Total Teams: {len(teams)}
Total Participants in Teams: {sum(team.get('team_size', 0) for team in teams)}

TEAM COMPOSITION ANALYSIS:
"""
        
        # Analyze each team
        for i, team in enumerate(teams[:10]):  # Limit to first 10 teams for context length
            members = team.get("members", [])
            team_context += f"""
Team {team.get('team_id', f'team_{i+1}')}:
- Size: {len(members)} members
- Roles: {[m.get('primary_roles', []) for m in members]}
- Skills: {[list(m.get('self_rated_skills', {}).keys()) for m in members]}
- Experience: {[m.get('experience_level', 'unknown') for m in members]}
"""

        if len(teams) > 10:
            team_context += f"\n... and {len(teams) - 10} more teams with similar analysis needed."

        system_prompt = """
You are an expert team composition analyst. Review the Phase 2 team formations and assess their quality.

Analyze the teams for:
1. ROLE BALANCE: Do teams have appropriate role distributions?
2. SKILL DIVERSITY: Are complementary skills represented in each team?
3. TEAM SIZE: Are team sizes appropriate (typically 3-5 members)?
4. EXPERIENCE MIX: Do teams have good experience level distribution?
5. COLLABORATION POTENTIAL: Will these team compositions work well together?

Return a JSON object with:
- "overall_quality": Float 0.0-1.0 representing overall team formation quality
- "quality_rating": String ("excellent", "good", "fair", "poor")
- "key_insights": List of main observations about team formations
- "improvement_suggestions": List of specific suggestions for better team formations
- "problematic_teams": List of team IDs that seem poorly formed
- "strengths": List of what's working well in team formations
- "recommended_changes": List of specific team member swaps or adjustments
- "confidence": Float 0.0-1.0 confidence in this assessment

Focus on actionable team composition improvements.
"""

        response = await aclient.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": team_context}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        
        review = json.loads(response.choices[0].message.content)
        
        # Add metadata
        review["phase"] = "phase2"
        review["review_timestamp"] = datetime.utcnow().isoformat()
        review["teams_reviewed"] = len(teams)
        review["avg_team_size"] = sum(team.get('team_size', 0) for team in teams) / len(teams) if teams else 0
        
        logger.info(f"Phase 2 AI Review: {review.get('quality_rating', 'unknown')} quality ({review.get('overall_quality', 0):.2f})")
        return review
        
    except Exception as e:
        logger.error(f"Error in Phase 2 AI review: {e}")
        return _get_default_phase_review("phase2")


async def review_phase3_assignments(final_assignments: List[dict], teams: List[dict], problems: List[dict]) -> dict:
    """
    AI review of Phase 3 team-problem assignments.
    Provides quality assessment and suggestions for assignment improvements.
    """
    if not aclient:
        logger.warning("OpenAI client not initialized. Returning default Phase 3 review.")
        return _get_default_phase_review("phase3")

    try:
        # Build context for AI review
        assignment_context = f"""
PHASE 3 REVIEW: Team-Problem Assignment Analysis
Total Teams: {len(teams)}
Total Problems: {len(problems)}
Total Final Assignments: {len(final_assignments)}

ASSIGNMENT ANALYSIS:
"""
        
        # Analyze assignments
        for assignment in final_assignments[:15]:  # Limit for context length
            team_id = assignment.get("team_id")
            problem_id = assignment.get("problem_id")
            cost = assignment.get("assignment_cost", 0)
            
            team = next((t for t in teams if t.get("team_id") == team_id), None)
            problem = next((p for p in problems if p.get("id") == problem_id), None)
            
            assignment_context += f"""
Assignment: {team_id} → {problem.get('title', 'Unknown') if problem else 'Unknown'}
- Team size: {team.get('team_size', 'unknown') if team else 'unknown'}
- Assignment cost: {cost:.3f}
- Problem complexity: {problem.get('complexity_level', 'unknown') if problem else 'unknown'}
- Required skills match: {problem.get('required_skills', {}) if problem else 'unknown'}
"""

        system_prompt = """
You are an expert project assignment analyst. Review the Phase 3 team-problem assignments and assess their strategic quality.

Analyze the assignments for:
1. CAPABILITY MATCH: Do teams have the right skills for their assigned problems?
2. COMPLEXITY ALIGNMENT: Are team sizes appropriate for problem complexity?
3. RESOURCE OPTIMIZATION: Are high-capability teams assigned to high-value problems?
4. ASSIGNMENT COSTS: Are costs reasonable and well-distributed?
5. STRATEGIC FIT: Do these assignments maximize overall success potential?

Return a JSON object with:
- "overall_quality": Float 0.0-1.0 representing overall assignment strategy quality
- "quality_rating": String ("excellent", "good", "fair", "poor")
- "key_insights": List of strategic observations about the assignments
- "improvement_suggestions": List of specific suggestions for better strategic assignments
- "problematic_assignments": List of team-problem pairs that seem mismatched
- "strengths": List of what's working well strategically
- "recommended_swaps": List of specific team-problem assignment changes
- "success_predictions": List of assignments most/least likely to succeed
- "confidence": Float 0.0-1.0 confidence in this assessment

Focus on strategic improvements and success optimization.
"""

        response = await aclient.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": assignment_context}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        
        review = json.loads(response.choices[0].message.content)
        
        # Add metadata
        review["phase"] = "phase3"
        review["review_timestamp"] = datetime.utcnow().isoformat()
        review["assignments_reviewed"] = len(final_assignments)
        review["total_assignment_cost"] = sum(a.get("assignment_cost", 0) for a in final_assignments)
        review["avg_assignment_cost"] = review["total_assignment_cost"] / len(final_assignments) if final_assignments else 0
        
        logger.info(f"Phase 3 AI Review: {review.get('quality_rating', 'unknown')} quality ({review.get('overall_quality', 0):.2f})")
        return review
        
    except Exception as e:
        logger.error(f"Error in Phase 3 AI review: {e}")
        return _get_default_phase_review("phase3")


def _get_default_phase_review(phase: str) -> dict:
    """Return default phase review when AI analysis is unavailable."""
    return {
        "overall_quality": 0.7,
        "quality_rating": "good",
        "key_insights": [f"Phase {phase} completed successfully", "AI review unavailable"],
        "improvement_suggestions": ["No specific suggestions available - AI unavailable"],
        "problematic_assignments": [],
        "strengths": [f"Phase {phase} algorithm executed"],
        "confidence": 0.5,
        "phase": phase,
        "review_timestamp": datetime.utcnow().isoformat(),
        "analysis_method": "default_fallback"
    }


async def analyze_team_role_balance(team_data: dict) -> dict:
    """
    Analyze a team's role balance and provide recommendations for improvement.
    Identifies unbalanced teams and suggests what roles to add.
    """
    if not aclient:
        logger.warning("OpenAI client not initialized. Returning default role balance analysis.")
        return _get_default_role_balance_analysis()

    try:
        # Build team context for analysis
        team_context = f"""
TEAM ROLE BALANCE ANALYSIS

Team ID: {team_data.get('team_id', 'Unknown')}
Team Size: {len(team_data.get('members', []))} members
Problem: {team_data.get('problem_title', 'Unknown Problem')}

TEAM COMPOSITION:
"""
        
        # Add member details
        members = team_data.get('members', [])
        role_distribution = {}
        
        for i, member in enumerate(members, 1):
            roles = member.get('primary_roles', [])
            skills = member.get('self_rated_skills', {})
            leadership = member.get('leadership_preference', False)
            experience = member.get('experience_level', 'intermediate')
            
            team_context += f"""
Member {i}: {member.get('name', 'Unknown')}
- Primary Roles: {roles}
- Key Skills: {list(skills.keys())}
- Experience Level: {experience}
- Leadership Preference: {'Yes' if leadership else 'No'}
"""
            
            # Count role distribution
            for role in roles:
                role_distribution[role] = role_distribution.get(role, 0) + 1
        
        team_context += f"""

CURRENT ROLE DISTRIBUTION:
{json.dumps(role_distribution, indent=2)}

Team has leadership: {any(m.get('leadership_preference', False) for m in members)}
"""

        system_prompt = """
You are an expert team composition analyst. Analyze this team's role balance and provide CONCISE recommendations.

Evaluate role distribution: frontend, backend, fullstack, data science, devops, product manager, designer.

Return a JSON object with:
- "is_balanced": Boolean indicating if the team is well-balanced
- "balance_score": Float 0.0-1.0 representing overall balance quality
- "missing_roles": List of 2-3 most critical missing roles only
- "concise_issue": String with ONE short sentence (max 15 words) explaining the main balance problem
- "urgency": String ("low", "medium", "high")
- "confidence": Float 0.0-1.0 confidence in this assessment

IMPORTANT: Keep "concise_issue" very brief. Examples:
- "Too many backend roles, needs frontend and design"
- "Missing technical leadership and product management"
- "Lacks data science and DevOps capabilities"

Focus only on the most critical 2-3 missing roles, not comprehensive lists.
"""

        response = await aclient.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": team_context}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            timeout=30  # 30 second timeout for faster processing
        )
        
        analysis = json.loads(response.choices[0].message.content)
        
        # Add metadata
        analysis["team_id"] = team_data.get('team_id')
        analysis["analysis_timestamp"] = datetime.utcnow().isoformat()
        analysis["analysis_method"] = "ai_generated"
        
        logger.info(f"Team role balance analysis for {team_data.get('team_id')}: {'balanced' if analysis.get('is_balanced', False) else 'unbalanced'}")
        return analysis
        
    except Exception as e:
        logger.error(f"Error in team role balance analysis: {e}")
        return _get_default_role_balance_analysis()


def _get_default_role_balance_analysis() -> dict:
    """Return default role balance analysis when AI is unavailable."""
    return {
        "is_balanced": True,
        "balance_score": 0.7,
        "missing_roles": [],
        "concise_issue": "AI analysis unavailable",
        "urgency": "low",
        "confidence": 0.5,
        "analysis_timestamp": datetime.utcnow().isoformat(),
        "analysis_method": "default_fallback"
    }