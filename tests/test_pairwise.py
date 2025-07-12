from app.matching.pairwise import participant_pair_cost


class TestParticipantPairCost:
    """Test suite for participant_pair_cost function."""
    
    def test_symmetry(self):
        """Test that cost(a, b) == cost(b, a)."""
        participant_a = {
            "_id": "1",
            "primary_roles": ["developer", "designer"],
            "enriched_skills": {
                "python": {"mean": 4.0},
                "javascript": {"mean": 3.5}
            },
            "availability_hours": 30,
            "motivation_text": "I love building innovative solutions",
            "motivation_embedding": [0.1, 0.2, 0.3, 0.4]
        }
        
        participant_b = {
            "_id": "2",
            "primary_roles": ["developer"],
            "enriched_skills": {
                "python": {"mean": 3.0},
                "react": {"mean": 4.0}
            },
            "availability_hours": 25,
            "motivation_text": "Building great products",
            "motivation_embedding": [0.2, 0.3, 0.4, 0.5]
        }
        
        cost_ab = participant_pair_cost(participant_a, participant_b)
        cost_ba = participant_pair_cost(participant_b, participant_a)
        
        assert abs(cost_ab - cost_ba) < 1e-10, f"Expected symmetry, got {cost_ab} != {cost_ba}"
    
    def test_zero_self_cost(self):
        """Test that cost(a, a) == 0."""
        participant = {
            "_id": "1",
            "primary_roles": ["developer"],
            "enriched_skills": {"python": {"mean": 4.0}},
            "availability_hours": 30,
            "motivation_text": "I love coding",
            "motivation_embedding": [0.1, 0.2, 0.3, 0.4]
        }
        
        cost = participant_pair_cost(participant, participant)
        assert cost == 0.0, f"Expected zero self-cost, got {cost}"
    
    def test_monotone_behavior_role_divergence(self):
        """Test that cost increases as role overlap decreases."""
        base_participant = {
            "_id": "1",
            "primary_roles": ["developer", "designer"],
            "enriched_skills": {"python": {"mean": 4.0}},
            "availability_hours": 30,
            "motivation_text": "I love coding",
            "motivation_embedding": [0.1, 0.2, 0.3, 0.4]
        }
        
        # More overlapping roles
        similar_participant = {
            "_id": "2",
            "primary_roles": ["developer"],  # Partial overlap
            "enriched_skills": {"python": {"mean": 4.0}},
            "availability_hours": 30,
            "motivation_text": "I love coding",
            "motivation_embedding": [0.1, 0.2, 0.3, 0.4]
        }
        
        # Completely different roles
        different_participant = {
            "_id": "3",
            "primary_roles": ["manager"],  # No overlap
            "enriched_skills": {"python": {"mean": 4.0}},
            "availability_hours": 30,
            "motivation_text": "I love coding",
            "motivation_embedding": [0.1, 0.2, 0.3, 0.4]
        }
        
        cost_similar = participant_pair_cost(base_participant, similar_participant)
        cost_different = participant_pair_cost(base_participant, different_participant)
        
        # Cost should be lower for more similar roles
        assert cost_similar < cost_different, f"Expected {cost_similar} < {cost_different}"
    
    def test_monotone_behavior_skill_divergence(self):
        """Test that cost changes appropriately with skill overlap."""
        base_participant = {
            "_id": "1",
            "primary_roles": ["developer"],
            "enriched_skills": {
                "python": {"mean": 4.5},
                "javascript": {"mean": 4.0}
            },
            "availability_hours": 30,
            "motivation_text": "I love coding",
            "motivation_embedding": [0.1, 0.2, 0.3, 0.4]
        }
        
        # High skill overlap (both high in same skills)
        high_overlap_participant = {
            "_id": "2",
            "primary_roles": ["developer"],
            "enriched_skills": {
                "python": {"mean": 4.0},
                "javascript": {"mean": 4.5}
            },
            "availability_hours": 30,
            "motivation_text": "I love coding",
            "motivation_embedding": [0.1, 0.2, 0.3, 0.4]
        }
        
        # Low skill overlap (different skills)
        low_overlap_participant = {
            "_id": "3",
            "primary_roles": ["developer"],
            "enriched_skills": {
                "rust": {"mean": 4.0},
                "go": {"mean": 4.5}
            },
            "availability_hours": 30,
            "motivation_text": "I love coding",
            "motivation_embedding": [0.1, 0.2, 0.3, 0.4]
        }
        
        cost_high_overlap = participant_pair_cost(base_participant, high_overlap_participant)
        cost_low_overlap = participant_pair_cost(base_participant, low_overlap_participant)
        
        # High skill overlap should have higher cost (penalty)
        assert cost_high_overlap > cost_low_overlap, f"Expected {cost_high_overlap} > {cost_low_overlap}"
    
    def test_monotone_behavior_availability_divergence(self):
        """Test that cost increases with availability mismatch."""
        base_participant = {
            "_id": "1",
            "primary_roles": ["developer"],
            "enriched_skills": {"python": {"mean": 4.0}},
            "availability_hours": 40,
            "motivation_text": "I love coding",
            "motivation_embedding": [0.1, 0.2, 0.3, 0.4]
        }
        
        # Similar availability
        similar_availability = {
            "_id": "2",
            "primary_roles": ["designer"],
            "enriched_skills": {"figma": {"mean": 4.0}},
            "availability_hours": 35,  # Close to 40
            "motivation_text": "I love coding",
            "motivation_embedding": [0.1, 0.2, 0.3, 0.4]
        }
        
        # Very different availability
        different_availability = {
            "_id": "3",
            "primary_roles": ["designer"],
            "enriched_skills": {"figma": {"mean": 4.0}},
            "availability_hours": 10,  # Very different from 40
            "motivation_text": "I love coding",
            "motivation_embedding": [0.1, 0.2, 0.3, 0.4]
        }
        
        cost_similar = participant_pair_cost(base_participant, similar_availability)
        cost_different = participant_pair_cost(base_participant, different_availability)
        
        # Different availability should have higher cost
        assert cost_different > cost_similar, f"Expected {cost_different} > {cost_similar}"
    
    def test_motivation_similarity_bonus(self):
        """Test that motivation similarity reduces cost."""
        base_participant = {
            "_id": "1",
            "primary_roles": ["developer"],
            "enriched_skills": {"python": {"mean": 4.0}},
            "availability_hours": 30,
            "motivation_text": "I love coding",
            "motivation_embedding": [1.0, 0.0, 0.0, 0.0]
        }
        
        # Very similar motivation
        similar_motivation = {
            "_id": "2",
            "primary_roles": ["manager"],  # Different role to add base cost
            "enriched_skills": {"leadership": {"mean": 4.0}},
            "availability_hours": 30,
            "motivation_text": "I love coding too",
            "motivation_embedding": [0.9, 0.1, 0.1, 0.1]  # Similar to base
        }
        
        # Very different motivation
        different_motivation = {
            "_id": "3",
            "primary_roles": ["manager"],  # Same different role
            "enriched_skills": {"leadership": {"mean": 4.0}},
            "availability_hours": 30,
            "motivation_text": "I love coding too",
            "motivation_embedding": [0.0, 0.0, 0.0, 1.0]  # Very different
        }
        
        cost_similar = participant_pair_cost(base_participant, similar_motivation)
        cost_different = participant_pair_cost(base_participant, different_motivation)
        
        # Similar motivation should have lower cost due to similarity bonus
        assert cost_similar < cost_different, f"Expected {cost_similar} < {cost_different}"
    
    def test_bounded_output(self):
        """Test that output is bounded between 0 and 1."""
        # Create participants with extreme values
        extreme_a = {
            "_id": "1",
            "primary_roles": ["developer", "designer", "manager"],
            "enriched_skills": {
                "python": {"mean": 5.0},
                "javascript": {"mean": 5.0},
                "leadership": {"mean": 5.0}
            },
            "availability_hours": 40,
            "motivation_text": "A" * 1000,  # Very long text
            "motivation_embedding": [1.0, 1.0, 1.0, 1.0]
        }
        
        extreme_b = {
            "_id": "2",
            "primary_roles": ["analyst"],
            "enriched_skills": {
                "excel": {"mean": 1.0}
            },
            "availability_hours": 5,
            "motivation_text": "B",  # Very short text
            "motivation_embedding": [-1.0, -1.0, -1.0, -1.0]
        }
        
        cost = participant_pair_cost(extreme_a, extreme_b)
        
        assert 0.0 <= cost <= 1.0, f"Expected cost in [0, 1], got {cost}"
    
    def test_missing_data_handling(self):
        """Test graceful handling of missing data."""
        minimal_a = {
            "_id": "1",
            "primary_roles": ["developer"]
        }
        
        minimal_b = {
            "_id": "2",
            "primary_roles": ["designer"]
        }
        
        # Should not crash with missing data
        cost = participant_pair_cost(minimal_a, minimal_b)
        assert isinstance(cost, float), f"Expected float, got {type(cost)}"
        assert 0.0 <= cost <= 1.0, f"Expected cost in [0, 1], got {cost}"
    
    def test_empty_embeddings(self):
        """Test handling of missing motivation embeddings."""
        participant_a = {
            "_id": "1",
            "primary_roles": ["developer"],
            "enriched_skills": {"python": {"mean": 4.0}},
            "availability_hours": 30,
            "motivation_text": "I love coding",
            "motivation_embedding": None  # Missing embedding
        }
        
        participant_b = {
            "_id": "2",
            "primary_roles": ["designer"],
            "enriched_skills": {"figma": {"mean": 4.0}},
            "availability_hours": 25,
            "motivation_text": "I love design"
            # Missing motivation_embedding key entirely
        }
        
        cost = participant_pair_cost(participant_a, participant_b)
        assert isinstance(cost, float), f"Expected float, got {type(cost)}"
        assert 0.0 <= cost <= 1.0, f"Expected cost in [0, 1], got {cost}"
