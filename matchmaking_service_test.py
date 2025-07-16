#!/usr/bin/env python3
"""
Universal Matchmaking Service Test Script

This script loads participant and problem data from JSON files and runs the complete
NAT Ignite matchmaking pipeline (Phase 1, 2, and 3).

Usage:
    python matchmaking_service_test.py --participants participant_list.json --problems problem_list.json
    python matchmaking_service_test.py --help

Requirements:
    - participant_list.json: List of participant objects following the template format
    - problem_list.json: List of problem objects following the template format
    - Backend services running (MongoDB, Redis, FastAPI on localhost:8000)

The script will:
1. Clear existing database data
2. Load participants and problems
3. Run Phase 1 (Individual-Problem Matching)
4. Run Phase 2 (Team Formation) 
5. Run Phase 3 (Team-Problem Assignment)
6. Display results summary
"""

import argparse
import json
import time
import sys
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MatchmakingTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def check_backend_health(self) -> bool:
        """Check if the backend services are running."""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Backend services are running")
                return True
            else:
                logger.error(f"❌ Backend health check failed: HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Cannot connect to backend at {self.base_url}: {e}")
            logger.error("Make sure to run: docker compose up --build")
            return False
    
    def clear_database(self) -> bool:
        """Clear all existing data from the database."""
        logger.info("🗑️  Clearing existing database data...")
        
        collections = [
            "participants", "problems", "assignments", "teams", 
            "final_teams", "final_assignments", "team_vectors"
        ]
        
        for collection in collections:
            try:
                response = self.session.delete(f"{self.base_url}/api/clear/{collection}")
                if response.status_code in [200, 404]:
                    logger.info(f"   Cleared {collection}")
                else:
                    logger.warning(f"   Failed to clear {collection}: HTTP {response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"   Error clearing {collection}: {e}")
        
        time.sleep(2)  # Give database time to process
        logger.info("✅ Database cleared")
        return True
    
    def load_json_file(self, filepath: str) -> List[Dict[str, Any]]:
        """Load and validate JSON file."""
        try:
            path = Path(filepath)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {filepath}")
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                raise ValueError(f"JSON file must contain a list of objects, got {type(data)}")
            
            logger.info(f"📁 Loaded {len(data)} items from {filepath}")
            return data
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in {filepath}: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error loading {filepath}: {e}")
            raise
    
    def upload_participants(self, participants: List[Dict[str, Any]]) -> bool:
        """Upload participants to the backend."""
        logger.info(f"👥 Uploading {len(participants)} participants...")
        
        for i, participant in enumerate(participants, 1):
            try:
                response = self.session.post(
                    f"{self.base_url}/api/participants",
                    json=participant,
                    timeout=10
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"   ✅ Uploaded participant {i}/{len(participants)}: {participant.get('name', 'Unknown')}")
                else:
                    logger.error(f"   ❌ Failed to upload participant {i}: HTTP {response.status_code}")
                    logger.error(f"   Response: {response.text}")
                    return False
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"   ❌ Error uploading participant {i}: {e}")
                return False
        
        logger.info("✅ All participants uploaded successfully")
        return True
    
    def upload_problems(self, problems: List[Dict[str, Any]]) -> bool:
        """Upload problems to the backend."""
        logger.info(f"🧩 Uploading {len(problems)} problems...")
        
        for i, problem in enumerate(problems, 1):
            try:
                response = self.session.post(
                    f"{self.base_url}/api/problems",
                    json=problem,
                    timeout=10
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"   ✅ Uploaded problem {i}/{len(problems)}: {problem.get('title', 'Unknown')}")
                else:
                    logger.error(f"   ❌ Failed to upload problem {i}: HTTP {response.status_code}")
                    logger.error(f"   Response: {response.text}")
                    return False
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"   ❌ Error uploading problem {i}: {e}")
                return False
        
        logger.info("✅ All problems uploaded successfully")
        return True
    
    def run_phase(self, phase: int, timeout: int = 300) -> bool:
        """Run a specific matching phase and wait for completion."""
        phase_names = {1: "Individual-Problem Matching", 2: "Team Formation", 3: "Team-Problem Assignment"}
        logger.info(f"🚀 Starting Phase {phase}: {phase_names[phase]}")
        
        try:
            # Start the phase
            response = self.session.post(f"{self.base_url}/api/match/phase{phase}", timeout=10)
            
            if response.status_code != 200:
                logger.error(f"❌ Failed to start Phase {phase}: HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
            
            # Wait for completion
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    status_response = self.session.get(f"{self.base_url}/api/match/phase{phase}/status")
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data.get('status', 'unknown')
                        
                        if status == 'completed':
                            elapsed = time.time() - start_time
                            logger.info(f"✅ Phase {phase} completed successfully in {elapsed:.1f} seconds")
                            
                            # Show additional info if available
                            if 'result' in status_data:
                                result = status_data['result']
                                if 'statistics' in result:
                                    stats = result['statistics']
                                    logger.info(f"   📊 Results: {stats}")
                            
                            return True
                            
                        elif status == 'failed':
                            logger.error(f"❌ Phase {phase} failed")
                            if 'error' in status_data:
                                logger.error(f"   Error: {status_data['error']}")
                            return False
                            
                        elif status in ['running', 'started']:
                            logger.info(f"   ⏳ Phase {phase} running... ({time.time() - start_time:.1f}s elapsed)")
                            time.sleep(5)
                        else:
                            logger.warning(f"   ⚠️  Unknown status: {status}")
                            time.sleep(2)
                    else:
                        logger.warning(f"   ⚠️  Status check failed: HTTP {status_response.status_code}")
                        time.sleep(2)
                        
                except requests.exceptions.RequestException as e:
                    logger.warning(f"   ⚠️  Status check error: {e}")
                    time.sleep(2)
            
            logger.error(f"❌ Phase {phase} timed out after {timeout} seconds")
            return False
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error running Phase {phase}: {e}")
            return False
    
    def get_results_summary(self) -> Optional[Dict[str, Any]]:
        """Get final results summary."""
        try:
            response = self.session.get(f"{self.base_url}/api/match/results")
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"⚠️  Could not get results: HTTP {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️  Error getting results: {e}")
            return None
    
    def print_results_summary(self, results: Dict[str, Any]):
        """Print a formatted summary of the results."""
        logger.info("📊 MATCHMAKING RESULTS SUMMARY")
        logger.info("=" * 50)
        
        if 'summary' in results:
            summary = results['summary']
            logger.info(f"👥 Total Participants: {summary.get('total_participants', 'N/A')}")
            logger.info(f"🧩 Total Problems: {summary.get('total_problems', 'N/A')}")
            logger.info(f"👨‍👩‍👧‍👦 Total Teams: {summary.get('total_teams', 'N/A')}")
            logger.info(f"🎯 Final Assignments: {summary.get('final_assignments', 'N/A')}")
            
            if 'completion_rate' in summary:
                logger.info(f"✅ Completion Rate: {summary['completion_rate']:.1%}")
        
        if 'teams' in results:
            teams = results['teams']
            if teams:
                avg_size = sum(len(team.get('members', [])) for team in teams) / len(teams)
                logger.info(f"📏 Average Team Size: {avg_size:.1f}")
                
                # Team quality metrics
                team_scores = []
                for team in teams:
                    if 'ai_scores' in team:
                        scores = team['ai_scores']
                        diversity = scores.get('diversity_score', 0)
                        skills = scores.get('skills_coverage', 0) 
                        team_scores.append((diversity, skills))
                
                if team_scores:
                    avg_diversity = sum(score[0] for score in team_scores) / len(team_scores)
                    avg_skills = sum(score[1] for score in team_scores) / len(team_scores)
                    logger.info(f"🌈 Average Diversity Score: {avg_diversity:.2f}")
                    logger.info(f"🛠️  Average Skills Coverage: {avg_skills:.2f}")
        
        logger.info("=" * 50)
        logger.info("🎉 Matchmaking process completed successfully!")
        logger.info(f"🌐 View detailed results at: http://localhost:3000")

def main():
    parser = argparse.ArgumentParser(
        description="Universal NAT Ignite Matchmaking Service Test Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python matchmaking_service_test.py --participants participant_list.json --problems problem_list.json
    python matchmaking_service_test.py -p participants.json -pr problems.json --timeout 600
    
Template files are available in the templates/ directory.
        """
    )
    
    parser.add_argument('-p', '--participants', required=True,
                       help='Path to participant list JSON file')
    parser.add_argument('-pr', '--problems', required=True,
                       help='Path to problem list JSON file')
    parser.add_argument('--base-url', default='http://localhost:8000',
                       help='Backend API base URL (default: http://localhost:8000)')
    parser.add_argument('--timeout', type=int, default=300,
                       help='Timeout per phase in seconds (default: 300)')
    parser.add_argument('--skip-clear', action='store_true',
                       help='Skip clearing existing database data')
    parser.add_argument('--dry-run', action='store_true',
                       help='Only load data, skip running matching phases')
    
    args = parser.parse_args()
    
    # Initialize tester
    tester = MatchmakingTester(args.base_url)
    
    # Check backend health
    if not tester.check_backend_health():
        logger.error("❌ Backend services are not available. Please start them first:")
        logger.error("   docker compose up --build")
        sys.exit(1)
    
    try:
        # Clear database (unless skipped)
        if not args.skip_clear:
            if not tester.clear_database():
                sys.exit(1)
        
        # Load data files
        participants = tester.load_json_file(args.participants)
        problems = tester.load_json_file(args.problems)
        
        # Basic validation
        if len(participants) == 0:
            logger.error("❌ No participants found in file")
            sys.exit(1)
        
        if len(problems) == 0:
            logger.error("❌ No problems found in file")
            sys.exit(1)
        
        # Upload data
        if not tester.upload_participants(participants):
            sys.exit(1)
        
        if not tester.upload_problems(problems):
            sys.exit(1)
        
        # Skip matching phases if dry run
        if args.dry_run:
            logger.info("🏃‍♂️ Dry run completed - data loaded successfully")
            sys.exit(0)
        
        # Run matching phases
        total_start = time.time()
        
        phases_success = True
        for phase in [1, 2, 3]:
            if not tester.run_phase(phase, args.timeout):
                phases_success = False
                break
        
        if not phases_success:
            logger.error("❌ Matching phases failed")
            sys.exit(1)
        
        total_elapsed = time.time() - total_start
        logger.info(f"🏁 All phases completed in {total_elapsed:.1f} seconds")
        
        # Get and display results
        results = tester.get_results_summary()
        if results:
            tester.print_results_summary(results)
        
        logger.info("✨ Matchmaking test completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 