"""
API endpoints for powering the admin dashboard.
"""
import logging
import json
import csv
import io
from typing import List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime

from app.db import db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/participants")
async def get_all_participants():
    """Returns a list of all participants with key details."""
    try:
        participants_cursor = db.participants.find({})
        participants = []
        async for p in participants_cursor:
            p["_id"] = str(p["_id"])
            participants.append(p)
        return participants
    except Exception as e:
        logger.error(f"Error fetching participants: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/participants/{participant_id}")
async def get_participant_details(participant_id: str):
    """Returns full details for a specific participant, including their optimal problem assignment."""
    try:
        participant = await db.participants.find_one({"_id": participant_id})
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")
        participant["_id"] = str(participant["_id"])

        # Find the participant's assignment from Phase 1
        assignment = await db.individual_problem_assignments.find_one({"participant_id": participant_id})
        participant["optimal_problem"] = assignment or "Not yet assigned"
        
        return participant
    except Exception as e:
        logger.error(f"Error fetching participant {participant_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/problems/detailed")
async def get_all_problems_detailed():
    """Returns a list of all problems with full details."""
    try:
        problems_cursor = db.problems.find({})
        problems = []
        async for p in problems_cursor:
            p["_id"] = str(p["_id"])
            problems.append(p)
        return problems
    except Exception as e:
        logger.error(f"Error fetching problems: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
        

@router.get("/teams/detailed")
async def get_teams_detailed():
    """Returns a list of all final teams with their members and assigned problem."""
    try:
        teams_cursor = db.final_teams.find({})
        teams_detailed = []
        async for team in teams_cursor:
            team["_id"] = str(team["_id"])
            
            # Get full participant objects for members
            participant_ids = team.get("participant_ids", [])
            existing_members = team.get("members", [])
            
            # If we already have member details, use them
            if existing_members:
                team["members"] = existing_members
            # Otherwise, fetch by participant IDs
            elif participant_ids:
            members = []
                # Try both id and _id fields for participants
                members_cursor = db.participants.find({"$or": [{"id": {"$in": participant_ids}}, {"_id": {"$in": participant_ids}}]})
                async for member in members_cursor:
                    member["_id"] = str(member["_id"])
                    members.append(member)
            team["members"] = members
            else:
                team["members"] = []

            # Get the assigned problem for the team
            team_id = team.get("team_id")
            assigned_problem = team.get("final_problem_title", "Not yet assigned")
            team["assigned_problem"] = assigned_problem

            teams_detailed.append(team)
        return teams_detailed
    except Exception as e:
        logger.error(f"Error fetching detailed teams: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats")
async def get_matching_stats():
    """Returns comprehensive matching statistics and algorithm performance metrics."""
    try:
        # Get basic counts
        participants_count = await db.participants.count_documents({})
        problems_count = await db.problems.count_documents({})
        teams_count = await db.final_teams.count_documents({})
        assignments_count = await db.individual_problem_assignments.count_documents({})
        final_assignments_count = await db.team_problem_assignments.count_documents({})
        
        # Phase 1 stats
        phase1_stats = None
        if assignments_count > 0:
            assignments = await db.individual_problem_assignments.find({}).to_list(length=None)
            total_cost = sum(a.get("cost", a.get("assignment_cost", 0)) for a in assignments)
            phase1_stats = {
                "total_participants": participants_count,
                "total_problems": problems_count,
                "total_assignments": assignments_count,
                "avg_assignment_cost": total_cost / assignments_count if assignments_count > 0 else 0,
                "algorithm": "hungarian"
            }
        
        # Phase 2 stats
        phase2_stats = None
        if teams_count > 0:
            teams = await db.final_teams.find({}).to_list(length=None)
            # Check both participant_ids and members fields for team size calculation
            total_participants_in_teams = 0
            for t in teams:
                if "participant_ids" in t:
                    total_participants_in_teams += len(t.get("participant_ids", []))
                elif "members" in t:
                    total_participants_in_teams += len(t.get("members", []))
                else:
                    total_participants_in_teams += t.get("team_size", 0)
            
            avg_team_size = total_participants_in_teams / teams_count if teams_count > 0 else 0
            
            # Calculate average metrics
            diversity_scores = [t.get("metrics", {}).get("diversity_score", 0) for t in teams]
            skills_coverage = [t.get("metrics", {}).get("skills_covered", 0) for t in teams]
            
            phase2_stats = {
                "total_teams": teams_count,
                "avg_team_size": avg_team_size,
                "total_participants_in_teams": total_participants_in_teams,
                "avg_diversity_score": sum(diversity_scores) / len(diversity_scores) if diversity_scores else 0,
                "avg_skills_coverage": sum(skills_coverage) / len(skills_coverage) if skills_coverage else 0,
                "algorithm": "hungarian"
            }
        
        # Phase 3 stats
        phase3_stats = None
        if final_assignments_count > 0:
            final_assignments = await db.team_problem_assignments.find({}).to_list(length=None)
            total_cost = sum(fa.get("assignment_cost", 0) for fa in final_assignments)
            problem_scores = [fa.get("problem_score", 0) for fa in final_assignments]
            
            phase3_stats = {
                "teams_assigned": final_assignments_count,
                "total_assignment_cost": total_cost,
                "avg_assignment_cost": total_cost / final_assignments_count if final_assignments_count > 0 else 0,
                "avg_problem_score": sum(problem_scores) / len(problem_scores) if problem_scores else 0,
                "algorithm": "hungarian"
            }
        
        return {
            "phase1_stats": phase1_stats,
            "phase2_stats": phase2_stats,
            "phase3_stats": phase3_stats,
            "overall_stats": {
                "participants_count": participants_count,
                "problems_count": problems_count,
                "teams_count": teams_count,
                "assignments_count": assignments_count,
                "final_assignments_count": final_assignments_count,
                "completion_rate": (assignments_count / participants_count * 100) if participants_count > 0 else 0,
                "team_formation_rate": (teams_count * 100) if teams_count > 0 else 0
            }
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/start-matching")
async def start_matching():
    """Start a new matching process (placeholder for now)."""
    try:
        # This would typically trigger the matching algorithm
        # For now, return the current status
        return {
            "status": "started",
            "message": "Matching process initiated",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error starting matching: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/export")
async def export_results(format: str = "json"):
    """Export matching results in JSON or CSV format."""
    try:
        if format.lower() == "csv":
            return await export_csv()
        else:
            return await export_json()
    except Exception as e:
        logger.error(f"Error exporting results: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def export_json():
    """Export comprehensive results as JSON with detailed participant information."""
    try:
        # Get all data
        participants = await db.participants.find({}).to_list(length=None)
        problems = await db.problems.find({}).to_list(length=None)
        teams = await db.final_teams.find({}).to_list(length=None)
        assignments = await db.individual_problem_assignments.find({}).to_list(length=None)
        final_assignments = await db.team_problem_assignments.find({}).to_list(length=None)
        
        # Convert ObjectIds to strings
        for item in participants + problems + teams + assignments + final_assignments:
            if "_id" in item:
                item["_id"] = str(item["_id"])
        
        # Create participant lookup for quick access
        participant_lookup = {str(p.get("_id", p.get("id", ""))): p for p in participants}
        problem_lookup = {str(p.get("_id", p.get("id", ""))): p for p in problems}
        
        # Enhance teams with detailed member information
        enhanced_teams = []
        for team in teams:
            enhanced_team = team.copy()
            
            # Get detailed member information
            detailed_members = []
            member_ids = team.get("participant_ids", [])
            existing_members = team.get("members", [])
            
            # Use existing members if available, otherwise lookup by participant_ids
            if existing_members:
                for member in existing_members:
                    participant_id = str(member.get("participant_id", member.get("_id", "")))
                    full_participant = participant_lookup.get(participant_id, {})
                    
                    detailed_member = {
                        "participant_id": participant_id,
                        "name": member.get("name") or full_participant.get("name", "Unknown"),
                        "email": member.get("email") or full_participant.get("email", "unknown@example.com"),
                        "primary_roles": member.get("primary_roles") or full_participant.get("primary_roles", []),
                        "self_rated_skills": member.get("self_rated_skills") or full_participant.get("self_rated_skills", {}),
                        "availability_hours": member.get("availability_hours") or full_participant.get("availability_hours", 0),
                        "experience_level": full_participant.get("experience_level", "intermediate"),
                        "motivation_text": full_participant.get("motivation_text", ""),
                        "team_preferences": full_participant.get("team_preferences", []),
                        "challenge_preferences": full_participant.get("challenge_preferences", [])
                    }
                    detailed_members.append(detailed_member)
            else:
                # Lookup by participant_ids
                for member_id in member_ids:
                    participant = participant_lookup.get(str(member_id), {})
                    if participant:
                        detailed_member = {
                            "participant_id": str(member_id),
                            "name": participant.get("name", "Unknown"),
                            "email": participant.get("email", "unknown@example.com"),
                            "primary_roles": participant.get("primary_roles", []),
                            "self_rated_skills": participant.get("self_rated_skills", {}),
                            "availability_hours": participant.get("availability_hours", 0),
                            "experience_level": participant.get("experience_level", "intermediate"),
                            "motivation_text": participant.get("motivation_text", ""),
                            "team_preferences": participant.get("team_preferences", []),
                            "challenge_preferences": participant.get("challenge_preferences", [])
                        }
                        detailed_members.append(detailed_member)
            
            enhanced_team["detailed_members"] = detailed_members
            enhanced_team["member_count"] = len(detailed_members)
            
            # Add problem details if assigned
            problem_id = team.get("final_problem_id") or team.get("problem_id")
            if problem_id:
                problem_details = problem_lookup.get(str(problem_id), {})
                enhanced_team["assigned_problem_details"] = {
                    "problem_id": str(problem_id),
                    "title": problem_details.get("title", "Unknown"),
                    "description": problem_details.get("description", ""),
                    "category": problem_details.get("category", "general"),
                    "difficulty_level": problem_details.get("difficulty_level", "intermediate"),
                    "required_skills": problem_details.get("required_skills", {}),
                    "role_preferences": problem_details.get("role_preferences", {}),
                    "estimated_team_size": problem_details.get("estimated_team_size", 4),
                    "expected_hours_per_week": problem_details.get("expected_hours_per_week", 20),
                    "problem_score": problem_details.get("problem_score", 0.5)
                }
            
            enhanced_teams.append(enhanced_team)
        
        # Enhance final assignments with detailed information
        enhanced_final_assignments = []
        for assignment in final_assignments:
            enhanced_assignment = assignment.copy()
            
            # Add team details
            team_id = assignment.get("team_id")
            team_details = next((t for t in enhanced_teams if t.get("team_id") == team_id), None)
            if team_details:
                enhanced_assignment["team_details"] = {
                    "team_id": team_id,
                    "member_count": team_details.get("member_count", 0),
                    "detailed_members": team_details.get("detailed_members", []),
                    "metrics": team_details.get("metrics", {}),
                    "diversity_score": team_details.get("diversity_score", 0),
                    "skills_covered": team_details.get("skills_covered", 0),
                    "role_balance_flag": team_details.get("role_balance_flag", False)
                }
            
            # Add problem details
            problem_id = assignment.get("problem_id")
            if problem_id:
                problem_details = problem_lookup.get(str(problem_id), {})
                enhanced_assignment["problem_details"] = {
                    "problem_id": str(problem_id),
                    "title": problem_details.get("title", "Unknown"),
                    "description": problem_details.get("description", ""),
                    "category": problem_details.get("category", "general"),
                    "difficulty_level": problem_details.get("difficulty_level", "intermediate"),
                    "required_skills": problem_details.get("required_skills", {}),
                    "role_preferences": problem_details.get("role_preferences", {}),
                    "problem_score": problem_details.get("problem_score", 0.5)
                }
            
            enhanced_final_assignments.append(enhanced_assignment)
        
        # Calculate enhanced summary statistics
        total_participants_in_teams = sum(len(team.get("detailed_members", [])) for team in enhanced_teams)
        avg_team_size = total_participants_in_teams / len(enhanced_teams) if enhanced_teams else 0
        
        # Calculate skill coverage across all teams
        all_skills_covered = set()
        for team in enhanced_teams:
            for member in team.get("detailed_members", []):
                all_skills_covered.update(member.get("self_rated_skills", {}).keys())
        
        # Calculate role coverage across all teams
        all_roles_covered = set()
        for team in enhanced_teams:
            for member in team.get("detailed_members", []):
                all_roles_covered.update(member.get("primary_roles", []))
        
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "export_format": "comprehensive_detailed",
            "participants": participants,
            "problems": problems,
            "teams": enhanced_teams,
            "individual_assignments": assignments,
            "final_assignments": enhanced_final_assignments,
            "summary": {
                "total_participants": len(participants),
                "total_problems": len(problems),
                "total_teams": len(teams),
                "total_assignments": len(assignments),
                "total_final_assignments": len(final_assignments),
                "participants_in_teams": total_participants_in_teams,
                "avg_team_size": round(avg_team_size, 2),
                "unique_skills_covered": len(all_skills_covered),
                "unique_roles_covered": len(all_roles_covered),
                "skills_list": sorted(list(all_skills_covered)),
                "roles_list": sorted(list(all_roles_covered))
            }
        }
        
        return export_data
    except Exception as e:
        logger.error(f"Error in enhanced JSON export: {e}")
        raise HTTPException(status_code=500, detail="Enhanced JSON export failed")


async def export_csv():
    """Export comprehensive results as CSV with detailed participant information."""
    try:
        # Get all data
        participants = await db.participants.find({}).to_list(length=None)
        problems = await db.problems.find({}).to_list(length=None)
        teams = await db.final_teams.find({}).to_list(length=None)
        final_assignments = await db.team_problem_assignments.find({}).to_list(length=None)
        
        # Create participant and problem lookups
        participant_lookup = {str(p.get("_id", p.get("id", ""))): p for p in participants}
        problem_lookup = {str(p.get("_id", p.get("id", ""))): p for p in problems}
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write comprehensive header
        writer.writerow([
            "Team ID", "Team Size", "Problem ID", "Problem Title", "Problem Category", 
            "Assignment Cost", "Problem Score", "Diversity Score", "Skills Coverage", 
            "Role Balance", "Algorithm", "Member Name", "Member Email", "Member ID",
            "Member Roles", "Member Skills", "Member Experience Level", 
            "Member Availability Hours", "Member Motivation Summary"
        ])
        
        # Write detailed data - one row per team member
        for assignment in final_assignments:
            team_id = assignment.get("team_id", "")
            team = next((t for t in teams if t.get("team_id") == team_id), {})
            metrics = team.get("metrics", {})
            
            # Get problem details
            problem_id = assignment.get("problem_id", "")
            problem_details = problem_lookup.get(str(problem_id), {})
            
            # Get team members
            members = team.get("members", [])
            participant_ids = team.get("participant_ids", [])
            
            # If no detailed members, lookup by participant_ids
            if not members and participant_ids:
                members = []
                for pid in participant_ids:
                    participant = participant_lookup.get(str(pid), {})
                    if participant:
                        members.append({
                            "participant_id": str(pid),
                            "name": participant.get("name", "Unknown"),
                            "email": participant.get("email", "unknown@example.com"),
                            "primary_roles": participant.get("primary_roles", []),
                            "self_rated_skills": participant.get("self_rated_skills", {}),
                            "experience_level": participant.get("experience_level", "intermediate"),
                            "availability_hours": participant.get("availability_hours", 0),
                            "motivation_text": participant.get("motivation_text", "")
                        })
            
            # If still no members, create a single row for the team without member details
            if not members:
            writer.writerow([
                    team_id,
                assignment.get("team_size", 0),
                    problem_id,
                    assignment.get("problem_title", problem_details.get("title", "")),
                    problem_details.get("category", "general"),
                    round(assignment.get("assignment_cost", 0), 4),
                    round(assignment.get("problem_score", 0), 4),
                    round(metrics.get("diversity_score", 0), 4),
                    round(metrics.get("skills_covered", 0), 4),
                    metrics.get("role_balance_flag", False),
                    assignment.get("algorithm", "hungarian"),
                    "No members found", "", "", "", "", "", "", ""
                ])
                continue
            
            # Write one row per team member
            for member in members:
                # Format skills as readable string
                skills = member.get("self_rated_skills", {})
                skills_str = "; ".join([f"{skill}:{level}" for skill, level in skills.items()]) if skills else "None"
                
                # Format roles as readable string
                roles = member.get("primary_roles", [])
                roles_str = "; ".join(roles) if roles else "None"
                
                # Truncate motivation text for CSV readability
                motivation = member.get("motivation_text", "")
                motivation_summary = motivation[:100] + "..." if len(motivation) > 100 else motivation
                
                writer.writerow([
                    team_id,
                    len(members),
                    problem_id,
                    assignment.get("problem_title", problem_details.get("title", "")),
                    problem_details.get("category", "general"),
                    round(assignment.get("assignment_cost", 0), 4),
                    round(assignment.get("problem_score", 0), 4),
                    round(metrics.get("diversity_score", 0), 4),
                    round(metrics.get("skills_covered", 0), 4),
                metrics.get("role_balance_flag", False),
                    assignment.get("algorithm", "hungarian"),
                    member.get("name", "Unknown"),
                    member.get("email", "unknown@example.com"),
                    member.get("participant_id", ""),
                    roles_str,
                    skills_str,
                    member.get("experience_level", "intermediate"),
                    member.get("availability_hours", 0),
                    motivation_summary
                ])
        
        # If no final assignments, export team data directly
        if not final_assignments and teams:
            writer.writerow([])  # Empty row separator
            writer.writerow(["=== TEAMS WITHOUT FINAL ASSIGNMENTS ==="])
            writer.writerow([])
            
            for team in teams:
                team_id = team.get("team_id", "")
                problem_id = team.get("problem_id") or team.get("final_problem_id", "")
                problem_details = problem_lookup.get(str(problem_id), {}) if problem_id else {}
                
                members = team.get("members", [])
                participant_ids = team.get("participant_ids", [])
                
                # Lookup members if not detailed
                if not members and participant_ids:
                    members = []
                    for pid in participant_ids:
                        participant = participant_lookup.get(str(pid), {})
                        if participant:
                            members.append({
                                "participant_id": str(pid),
                                "name": participant.get("name", "Unknown"),
                                "email": participant.get("email", "unknown@example.com"),
                                "primary_roles": participant.get("primary_roles", []),
                                "self_rated_skills": participant.get("self_rated_skills", {}),
                                "experience_level": participant.get("experience_level", "intermediate"),
                                "availability_hours": participant.get("availability_hours", 0),
                                "motivation_text": participant.get("motivation_text", "")
                            })
                
                # Write team members
                for member in members:
                    skills = member.get("self_rated_skills", {})
                    skills_str = "; ".join([f"{skill}:{level}" for skill, level in skills.items()]) if skills else "None"
                    roles = member.get("primary_roles", [])
                    roles_str = "; ".join(roles) if roles else "None"
                    motivation = member.get("motivation_text", "")
                    motivation_summary = motivation[:100] + "..." if len(motivation) > 100 else motivation
                    
                    writer.writerow([
                        team_id,
                        len(members),
                        problem_id,
                        problem_details.get("title", "No problem assigned"),
                        problem_details.get("category", ""),
                        team.get("final_assignment_cost", 0),
                        problem_details.get("problem_score", 0),
                        team.get("diversity_score", 0),
                        team.get("skills_covered", 0),
                        team.get("role_balance_flag", False),
                        team.get("algorithm", "unknown"),
                        member.get("name", "Unknown"),
                        member.get("email", "unknown@example.com"),
                        member.get("participant_id", ""),
                        roles_str,
                        skills_str,
                        member.get("experience_level", "intermediate"),
                        member.get("availability_hours", 0),
                        motivation_summary
            ])
        
        output.seek(0)
        return StreamingResponse(
            io.StringIO(output.getvalue()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=nat_ignite_detailed_results.csv"}
        )
    except Exception as e:
        logger.error(f"Error in enhanced CSV export: {e}")
        raise HTTPException(status_code=500, detail="Enhanced CSV export failed") 