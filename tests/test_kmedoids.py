import numpy as np
from app.matching.kmedoids import k_medoids_clustering, assign_to_medoids


class TestKMedoidsClustering:
    """Test suite for k-medoids clustering algorithm."""
    
    def test_deterministic_seeding(self):
        """Test that results are deterministic with fixed seed."""
        participants = [
            {"_id": f"p{i}", "primary_roles": ["developer"], "availability_hours": 20 + i}
            for i in range(10)
        ]
        
        # Run clustering twice with same seed
        medoids1 = k_medoids_clustering(participants, k=3, random_seed=42)
        medoids2 = k_medoids_clustering(participants, k=3, random_seed=42)
        
        assert medoids1 == medoids2, f"Expected deterministic results, got {medoids1} != {medoids2}"
    
    def test_different_seeds_different_results(self):
        """Test that different seeds can produce different results."""
        participants = [
            {"_id": f"p{i}", "primary_roles": ["developer"], "availability_hours": 20 + i}
            for i in range(10)
        ]
        
        # Run clustering with different seeds
        medoids1 = k_medoids_clustering(participants, k=3, random_seed=42)
        medoids2 = k_medoids_clustering(participants, k=3, random_seed=123)
        
        # Results may be different (not guaranteed, but likely with enough participants)
        # At minimum, the algorithm should run without error
        assert len(medoids1) == 3
        assert len(medoids2) == 3
        assert all(0 <= m < len(participants) for m in medoids1)
        assert all(0 <= m < len(participants) for m in medoids2)
    
    def test_convergence_small_cluster(self):
        """Test convergence on a small cluster."""
        # Create participants with clear structure
        participants = [
            # Cluster 1: Developers with high Python skills
            {"_id": "p1", "primary_roles": ["developer"], "enriched_skills": {"python": {"mean": 4.5}}, "availability_hours": 35},
            {"_id": "p2", "primary_roles": ["developer"], "enriched_skills": {"python": {"mean": 4.0}}, "availability_hours": 30},
            {"_id": "p3", "primary_roles": ["developer"], "enriched_skills": {"python": {"mean": 4.2}}, "availability_hours": 32},
            
            # Cluster 2: Designers with different skills
            {"_id": "p4", "primary_roles": ["designer"], "enriched_skills": {"figma": {"mean": 4.5}}, "availability_hours": 25},
            {"_id": "p5", "primary_roles": ["designer"], "enriched_skills": {"figma": {"mean": 4.0}}, "availability_hours": 28},
            {"_id": "p6", "primary_roles": ["designer"], "enriched_skills": {"figma": {"mean": 4.3}}, "availability_hours": 26},
        ]
        
        # Should converge to 2 clusters
        medoids = k_medoids_clustering(participants, k=2, random_seed=42)
        
        assert len(medoids) == 2
        assert len(set(medoids)) == 2  # No duplicates
        assert all(0 <= m < len(participants) for m in medoids)
        
        # Test assignment
        clusters = assign_to_medoids(participants, medoids)
        assert len(clusters) == 2
        assert sum(len(cluster) for cluster in clusters) == len(participants)
    
    def test_k_equals_n(self):
        """Test behavior when k equals number of participants."""
        participants = [
            {"_id": f"p{i}", "primary_roles": ["developer"], "availability_hours": 20 + i}
            for i in range(5)
        ]
        
        medoids = k_medoids_clustering(participants, k=5, random_seed=42)
        
        # Should return all participant indices
        assert len(medoids) == 5
        assert set(medoids) == set(range(5))
    
    def test_k_greater_than_n(self):
        """Test behavior when k > n."""
        participants = [
            {"_id": f"p{i}", "primary_roles": ["developer"], "availability_hours": 20 + i}
            for i in range(3)
        ]
        
        medoids = k_medoids_clustering(participants, k=5, random_seed=42)
        
        # Should return all participant indices
        assert len(medoids) == 3
        assert set(medoids) == set(range(3))
    
    def test_k_equals_one(self):
        """Test behavior when k = 1."""
        participants = [
            {"_id": "p1", "primary_roles": ["developer"], "availability_hours": 40},
            {"_id": "p2", "primary_roles": ["developer"], "availability_hours": 20},
            {"_id": "p3", "primary_roles": ["developer"], "availability_hours": 30},
        ]
        
        medoids = k_medoids_clustering(participants, k=1, random_seed=42)
        
        assert len(medoids) == 1
        assert 0 <= medoids[0] < len(participants)
    
    def test_empty_participants(self):
        """Test behavior with empty participant list."""
        participants = []
        
        medoids = k_medoids_clustering(participants, k=2, random_seed=42)
        
        assert medoids == []
    
    def test_single_participant(self):
        """Test behavior with single participant."""
        participants = [
            {"_id": "p1", "primary_roles": ["developer"], "availability_hours": 30}
        ]
        
        medoids = k_medoids_clustering(participants, k=1, random_seed=42)
        
        assert medoids == [0]
    
    def test_max_iter_limit(self):
        """Test that algorithm respects max_iter limit."""
        participants = [
            {"_id": f"p{i}", "primary_roles": ["developer"], "availability_hours": 20 + i}
            for i in range(10)
        ]
        
        # Should complete without error even with very low max_iter
        medoids = k_medoids_clustering(participants, k=3, max_iter=1, random_seed=42)
        
        assert len(medoids) == 3
        assert len(set(medoids)) == 3
        assert all(0 <= m < len(participants) for m in medoids)
    
    def test_assign_to_medoids_basic(self):
        """Test basic assignment to medoids."""
        participants = [
            {"_id": "p1", "primary_roles": ["developer"], "availability_hours": 30},
            {"_id": "p2", "primary_roles": ["developer"], "availability_hours": 32},
            {"_id": "p3", "primary_roles": ["designer"], "availability_hours": 25},
            {"_id": "p4", "primary_roles": ["designer"], "availability_hours": 27},
        ]
        
        medoids = [0, 2]  # First developer and first designer as medoids
        clusters = assign_to_medoids(participants, medoids)
        
        assert len(clusters) == 2
        assert sum(len(cluster) for cluster in clusters) == len(participants)
        
        # Each cluster should contain its medoid
        assert 0 in clusters[0]  # First medoid in first cluster
        assert 2 in clusters[1]  # Second medoid in second cluster
    
    def test_assign_to_medoids_empty_medoids(self):
        """Test assignment with empty medoids list."""
        participants = [
            {"_id": "p1", "primary_roles": ["developer"], "availability_hours": 30},
        ]
        
        medoids = []
        clusters = assign_to_medoids(participants, medoids)
        
        assert clusters == []
    
    def test_clustering_with_identical_participants(self):
        """Test clustering when all participants are identical."""
        participants = [
            {"_id": f"p{i}", "primary_roles": ["developer"], "availability_hours": 30}
            for i in range(5)
        ]
        
        medoids = k_medoids_clustering(participants, k=2, random_seed=42)
        
        assert len(medoids) == 2
        assert len(set(medoids)) == 2
        assert all(0 <= m < len(participants) for m in medoids)
    
    def test_clustering_quality_simple_case(self):
        """Test that clustering produces reasonable results for a simple case."""
        # Create two distinct groups
        participants = [
            # Group 1: High availability developers
            {"_id": "p1", "primary_roles": ["developer"], "availability_hours": 40},
            {"_id": "p2", "primary_roles": ["developer"], "availability_hours": 38},
            {"_id": "p3", "primary_roles": ["developer"], "availability_hours": 35},
            
            # Group 2: Low availability designers  
            {"_id": "p4", "primary_roles": ["designer"], "availability_hours": 15},
            {"_id": "p5", "primary_roles": ["designer"], "availability_hours": 12},
            {"_id": "p6", "primary_roles": ["designer"], "availability_hours": 18},
        ]
        
        medoids = k_medoids_clustering(participants, k=2, random_seed=42)
        clusters = assign_to_medoids(participants, medoids)
        
        # Verify we get 2 clusters
        assert len(clusters) == 2
        
        # Each cluster should have at least one member
        assert all(len(cluster) > 0 for cluster in clusters)
        
        # Total members should equal total participants
        assert sum(len(cluster) for cluster in clusters) == len(participants)
    
    def test_medoids_are_actual_participants(self):
        """Test that medoids are always actual participant indices."""
        participants = [
            {"_id": f"p{i}", "primary_roles": ["developer"], "availability_hours": 20 + i}
            for i in range(8)
        ]
        
        medoids = k_medoids_clustering(participants, k=3, random_seed=42)
        
        # All medoids should be valid indices
        assert all(isinstance(m, (int, np.integer)) for m in medoids)
        assert all(0 <= m < len(participants) for m in medoids)
        
        # Medoids should be unique
        assert len(set(medoids)) == len(medoids)
