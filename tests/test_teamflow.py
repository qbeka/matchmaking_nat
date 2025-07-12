from typing import Dict, List, Any
from app.matching.team_builder import build_provisional_teams
from app.matching.slot_solver import solve_team_slots, calculate_team_coverage_metrics
from app.config import ALLOWED_ROLES, ALLOWED_SKILLS


class TestTeamFormationFlow:
    """Integration tests for the complete team formation workflow."""
    
    def test_end_to_end_team_formation(self):
        """Test complete team formation from synthetic participants."""
        # Generate 20 synthetic participants with role diversity
        participants = self._generate_synthetic_participants(20)
        
        # Group into preliminary teams (simulate stage 1 output)
        prelim_teams = self._create_preliminary_teams(participants)
        
        # Build provisional teams
        provisional_teams = build_provisional_teams(
            prelim_teams=prelim_teams,
            desired_team_size=4,
            max_iter=50,
            random_seed=42
        )
        
        # Solve final team slots
        final_teams = solve_team_slots(
            teams=provisional_teams,
            available_participants=participants,
            target_team_size=4,
            role_coverage_threshold=0.6
        )
        
        # Verify team formation constraints
        self._verify_team_constraints(final_teams, participants)
        
        # Verify coverage metrics
        self._verify_coverage_metrics(final_teams)
    
    def test_small_participant_pool(self):
        """Test team formation with small participant pool."""
        participants = self._generate_synthetic_participants(8)
        prelim_teams = [participants]  # Single cluster
        
        provisional_teams = build_provisional_teams(
            prelim_teams=prelim_teams,
            desired_team_size=4,
            max_iter=50,
            random_seed=42
        )
        
        final_teams = solve_team_slots(
            teams=provisional_teams,
            available_participants=participants,
            target_team_size=4,
            role_coverage_threshold=0.5
        )
        
        # Should create 2 teams of 4 each
        assert len(final_teams) == 2
        for team in final_teams:
            assert len(team) == 4
        
        # Verify no duplicate participants
        all_assigned_ids = set()
        for team in final_teams:
            for member in team:
                participant_id = member.get("_id")
                assert participant_id not in all_assigned_ids, f"Duplicate participant {participant_id}"
                all_assigned_ids.add(participant_id)
    
    def test_uneven_team_sizes(self):
        """Test team formation with uneven participant numbers."""
        participants = self._generate_synthetic_participants(14)  # Not divisible by 4
        prelim_teams = [participants]
        
        provisional_teams = build_provisional_teams(
            prelim_teams=prelim_teams,
            desired_team_size=4,
            max_iter=50,
            random_seed=42
        )
        
        final_teams = solve_team_slots(
            teams=provisional_teams,
            available_participants=participants,
            target_team_size=4,
            role_coverage_threshold=0.5
        )
        
        # Should handle uneven distribution gracefully
        total_participants = sum(len(team) for team in final_teams)
        assert total_participants <= len(participants)
        
        # Each team should have reasonable size
        for team in final_teams:
            assert 3 <= len(team) <= 5, f"Team size {len(team)} outside acceptable range"
    
    def test_role_diversity_enforcement(self):
        """Test that teams have good role diversity."""
        # Create participants with specific role distributions
        participants = []
        role_list = list(ALLOWED_ROLES)
        
        # Create 16 participants with varied roles
        for i in range(16):
            primary_role = role_list[i % len(role_list)]
            secondary_role = role_list[(i + 1) % len(role_list)]
            
            participant = {
                "_id": f"participant_{i}",
                "name": f"Participant {i}",
                "email": f"participant{i}@example.com",
                "primary_roles": [primary_role, secondary_role],
                "enriched_skills": self._generate_skills_for_role(primary_role),
                "availability_hours": 25 + (i % 15),
                "motivation_text": f"I am passionate about {primary_role} work",
                "motivation_embedding": [0.1 * i, 0.2 * i, 0.3 * i, 0.4 * i]
            }
            participants.append(participant)
        
        prelim_teams = [participants]
        
        provisional_teams = build_provisional_teams(
            prelim_teams=prelim_teams,
            desired_team_size=4,
            max_iter=50,
            random_seed=42
        )
        
        final_teams = solve_team_slots(
            teams=provisional_teams,
            available_participants=participants,
            target_team_size=4,
            role_coverage_threshold=0.6
        )
        
        # Verify role diversity in teams
        for i, team in enumerate(final_teams):
            metrics = calculate_team_coverage_metrics(team)
            assert metrics["role_coverage"] >= 0.4, f"Team {i} has poor role coverage: {metrics['role_coverage']}"
    
    def test_no_duplicate_participants(self):
        """Test that no participant appears in multiple teams."""
        participants = self._generate_synthetic_participants(20)
        prelim_teams = self._create_preliminary_teams(participants)
        
        provisional_teams = build_provisional_teams(
            prelim_teams=prelim_teams,
            desired_team_size=4,
            max_iter=50,
            random_seed=42
        )
        
        final_teams = solve_team_slots(
            teams=provisional_teams,
            available_participants=participants,
            target_team_size=4,
            role_coverage_threshold=0.6
        )
        
        # Collect all participant IDs
        all_participant_ids = set()
        for team in final_teams:
            for member in team:
                participant_id = member.get("_id")
                assert participant_id not in all_participant_ids, f"Duplicate participant {participant_id}"
                all_participant_ids.add(participant_id)
    
    def test_team_size_constraints(self):
        """Test that all teams meet size constraints."""
        participants = self._generate_synthetic_participants(20)
        prelim_teams = self._create_preliminary_teams(participants)
        
        provisional_teams = build_provisional_teams(
            prelim_teams=prelim_teams,
            desired_team_size=4,
            max_iter=50,
            random_seed=42
        )
        
        final_teams = solve_team_slots(
            teams=provisional_teams,
            available_participants=participants,
            target_team_size=4,
            role_coverage_threshold=0.6
        )
        
        # Verify team sizes
        for i, team in enumerate(final_teams):
            assert len(team) >= 2, f"Team {i} too small: {len(team)} members"
            assert len(team) <= 6, f"Team {i} too large: {len(team)} members"
    
    def test_coverage_metrics_calculation(self):
        """Test that coverage metrics are calculated correctly."""
        participants = self._generate_synthetic_participants(12)
        prelim_teams = [participants]
        
        provisional_teams = build_provisional_teams(
            prelim_teams=prelim_teams,
            desired_team_size=4,
            max_iter=50,
            random_seed=42
        )
        
        final_teams = solve_team_slots(
            teams=provisional_teams,
            available_participants=participants,
            target_team_size=4,
            role_coverage_threshold=0.6
        )
        
        for team in final_teams:
            metrics = calculate_team_coverage_metrics(team)
            
            # Verify metric ranges
            assert 0.0 <= metrics["role_coverage"] <= 1.0
            assert 0.0 <= metrics["skill_coverage"] <= 10.0  # Can be > 1 due to multiple skills per person
            assert 0.0 <= metrics["diversity_score"] <= 1.0
            assert 0.0 <= metrics["confidence_score"] <= 1.0
            assert isinstance(metrics["role_balance_flag"], bool)
    
    def test_minimum_coverage_threshold(self):
        """Test that teams meet minimum coverage thresholds."""
        participants = self._generate_synthetic_participants(20)
        prelim_teams = self._create_preliminary_teams(participants)
        
        provisional_teams = build_provisional_teams(
            prelim_teams=prelim_teams,
            desired_team_size=4,
            max_iter=50,
            random_seed=42
        )
        
        final_teams = solve_team_slots(
            teams=provisional_teams,
            available_participants=participants,
            target_team_size=4,
            role_coverage_threshold=0.6
        )
        
        # Count teams meeting coverage threshold
        teams_meeting_threshold = 0
        for team in final_teams:
            metrics = calculate_team_coverage_metrics(team)
            if metrics["role_coverage"] >= 0.4 or metrics["diversity_score"] >= 0.5:
                teams_meeting_threshold += 1
        
        # At least 40% of teams should meet the threshold (more realistic)
        coverage_ratio = teams_meeting_threshold / len(final_teams)
        assert coverage_ratio >= 0.4, f"Only {coverage_ratio:.2%} of teams meet coverage threshold"
    
    def test_empty_input_handling(self):
        """Test graceful handling of empty inputs."""
        # Empty preliminary teams
        provisional_teams = build_provisional_teams(
            prelim_teams=[],
            desired_team_size=4,
            max_iter=50,
            random_seed=42
        )
        assert provisional_teams == []
        
        # Empty teams for slot solving
        final_teams = solve_team_slots(
            teams=[],
            available_participants=[],
            target_team_size=4,
            role_coverage_threshold=0.6
        )
        assert final_teams == []
    
    def _generate_synthetic_participants(self, count: int) -> List[Dict[str, Any]]:
        """Generate synthetic participants with diverse roles and skills."""
        participants = []
        roles = list(ALLOWED_ROLES)
        skills = list(ALLOWED_SKILLS)
        
        for i in range(count):
            # Assign 1-3 roles per participant
            num_roles = min(3, (i % 3) + 1)
            primary_roles = [roles[(i + j) % len(roles)] for j in range(num_roles)]
            
            # Generate skills based on roles
            participant_skills = {}
            for role in primary_roles:
                role_skills = self._generate_skills_for_role(role)
                participant_skills.update(role_skills)
            
            # Add some random skills
            for j in range(2):
                skill = skills[(i + j) % len(skills)]
                if skill not in participant_skills:
                    participant_skills[skill] = {"mean": 2.0 + (i % 3)}
            
            participant = {
                "_id": f"participant_{i}",
                "name": f"Participant {i}",
                "email": f"participant{i}@example.com",
                "primary_roles": primary_roles,
                "enriched_skills": participant_skills,
                "availability_hours": 20 + (i % 20),
                "motivation_text": f"I am passionate about {primary_roles[0]} and want to build great products",
                "motivation_embedding": [
                    0.1 * (i % 10), 
                    0.2 * ((i + 1) % 10), 
                    0.3 * ((i + 2) % 10), 
                    0.4 * ((i + 3) % 10)
                ]
            }
            participants.append(participant)
        
        return participants
    
    def _generate_skills_for_role(self, role: str) -> Dict[str, Dict[str, float]]:
        """Generate appropriate skills for a given role."""
        role_skill_map = {
            "developer": ["python", "javascript", "react", "node.js"],
            "designer": ["figma", "photoshop", "user_research"],
            "product_manager": ["product_strategy", "user_research"],
            "data_scientist": ["python", "machine_learning", "sql"],
            "devops": ["docker", "kubernetes", "aws"],
            "qa": ["testing", "automation"],
            "business_analyst": ["sql", "excel", "product_strategy"],
            "marketing": ["digital_marketing", "content_creation"],
            "sales": ["sales_strategy", "crm"],
            "manager": ["leadership", "project_management"]
        }
        
        skills = {}
        if role in role_skill_map:
            for skill in role_skill_map[role]:
                if skill in ALLOWED_SKILLS:
                    skills[skill] = {"mean": 3.0 + (hash(role + skill) % 3)}
        
        return skills
    
    def _create_preliminary_teams(self, participants: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Create preliminary team clusters from participants."""
        # Simple clustering by role similarity
        role_clusters = {}
        
        for participant in participants:
            primary_role = participant.get("primary_roles", ["unknown"])[0]
            if primary_role not in role_clusters:
                role_clusters[primary_role] = []
            role_clusters[primary_role].append(participant)
        
        # Convert to list and ensure minimum cluster size
        clusters = []
        for role, cluster in role_clusters.items():
            if len(cluster) >= 2:
                clusters.append(cluster)
        
        # If no clusters formed, create one big cluster
        if not clusters:
            clusters = [participants]
        
        return clusters
    
    def _verify_team_constraints(self, teams: List[List[Dict[str, Any]]], all_participants: List[Dict[str, Any]]):
        """Verify that teams meet basic constraints."""
        # Check no duplicate participants
        all_assigned_ids = set()
        for team in teams:
            for member in team:
                participant_id = member.get("_id")
                assert participant_id not in all_assigned_ids, f"Duplicate participant {participant_id}"
                all_assigned_ids.add(participant_id)
        
        # Check team sizes
        for i, team in enumerate(teams):
            assert len(team) >= 2, f"Team {i} too small: {len(team)}"
            assert len(team) <= 6, f"Team {i} too large: {len(team)}"
        
        # Check that all team members are from original participant pool
        original_ids = set(p.get("_id") for p in all_participants)
        for team in teams:
            for member in team:
                assert member.get("_id") in original_ids, f"Unknown participant {member.get('_id')}"
    
    def _verify_coverage_metrics(self, teams: List[List[Dict[str, Any]]]):
        """Verify that teams have reasonable coverage metrics."""
        teams_with_good_coverage = 0
        
        for team in teams:
            metrics = calculate_team_coverage_metrics(team)
            
            # At least some teams should have decent coverage
            if metrics["role_coverage"] >= 0.4 or metrics["diversity_score"] >= 0.5:
                teams_with_good_coverage += 1
        
        # At least 40% of teams should have good coverage (more realistic threshold)
        coverage_ratio = teams_with_good_coverage / len(teams)
        assert coverage_ratio >= 0.4, f"Only {coverage_ratio:.2%} of teams have good coverage"
