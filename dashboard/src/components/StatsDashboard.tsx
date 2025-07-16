import React, { useState, useEffect } from 'react';
import { MatchingStats, Team } from '../types';
import { apiClient } from '../api';
import { calculateTeamMetrics } from '../utils/teamMetrics';

interface StatsDashboardProps {
  teams?: Team[];
}

const StatsDashboard: React.FC<StatsDashboardProps> = ({ teams = [] }) => {
  const [stats, setStats] = useState<MatchingStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.getStats();
      if (response.success && response.data) {
        setStats(response.data);
      } else {
        setError(response.error || 'Failed to load statistics');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600 mb-4">Error loading statistics: {error}</p>
        <button 
          onClick={loadStats}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">No statistics available</p>
      </div>
    );
  }

  const { phase1_stats, phase2_stats, phase3_stats, overall_stats } = stats;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Matchmaking Statistics</h2>
        <button 
          onClick={loadStats}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Refresh
        </button>
      </div>

      {/* Overall Statistics */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Overall Performance</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{overall_stats?.participants_count || 0}</div>
            <div className="text-sm text-gray-500">Participants</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{overall_stats?.problems_count || 0}</div>
            <div className="text-sm text-gray-500">Problems</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">{overall_stats?.teams_count || 0}</div>
            <div className="text-sm text-gray-500">Teams</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">{overall_stats?.assignments_count || 0}</div>
            <div className="text-sm text-gray-500">Assignments</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">{overall_stats?.final_assignments_count || 0}</div>
            <div className="text-sm text-gray-500">Final Assignments</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-indigo-600">{overall_stats?.completion_rate?.toFixed(1) || 0}%</div>
            <div className="text-sm text-gray-500">Completion Rate</div>
          </div>
        </div>
      </div>

      {/* Phase-by-Phase Analysis */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Phase 1: Individual-Problem Assignment */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Phase 1: Individual Assignment</h3>
            <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
              {phase1_stats?.algorithm || 'N/A'}
            </span>
          </div>
          
          {phase1_stats ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-lg font-semibold text-gray-900">{phase1_stats.total_participants}</div>
                  <div className="text-sm text-gray-500">Participants</div>
                </div>
                <div>
                  <div className="text-lg font-semibold text-gray-900">{phase1_stats.total_problems}</div>
                  <div className="text-sm text-gray-500">Problems</div>
                </div>
                <div>
                  <div className="text-lg font-semibold text-gray-900">{phase1_stats.total_assignments}</div>
                  <div className="text-sm text-gray-500">Assignments</div>
                </div>
                <div>
                  <div className="text-lg font-semibold text-gray-900">{phase1_stats.avg_assignment_cost.toFixed(3)}</div>
                  <div className="text-sm text-gray-500">Avg Cost</div>
                </div>
              </div>
              
              <div className="pt-4 border-t border-gray-200">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Assignment Efficiency</span>
                  <span className="text-sm font-medium text-green-600">
                    {((phase1_stats.total_assignments / phase1_stats.total_participants) * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500">Phase 1 not completed</p>
            </div>
          )}
        </div>

        {/* Phase 2: Team Formation */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Phase 2: Team Formation</h3>
            <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
              {phase2_stats?.algorithm || 'N/A'}
            </span>
          </div>
          
          {phase2_stats ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-lg font-semibold text-gray-900">{phase2_stats.total_teams}</div>
                  <div className="text-sm text-gray-500">Teams</div>
                </div>
                <div>
                  <div className="text-lg font-semibold text-gray-900">{phase2_stats.avg_team_size.toFixed(1)}</div>
                  <div className="text-sm text-gray-500">Avg Size</div>
                </div>
                <div>
                  <div className="text-lg font-semibold text-gray-900">{phase2_stats.total_participants_in_teams}</div>
                  <div className="text-sm text-gray-500">In Teams</div>
                </div>
                <div>
                  <div className="text-lg font-semibold text-gray-900">
                    {(() => {
                      if (teams.length > 0) {
                        const teamsWithMetrics = teams.map(team => calculateTeamMetrics(team));
                        const avgDiversityScore = teamsWithMetrics.reduce((sum, metrics) => sum + metrics.diversity_score, 0) / teams.length;
                        return (avgDiversityScore * 100).toFixed(1);
                      }
                      return (phase2_stats.avg_diversity_score * 100).toFixed(1);
                    })()}%
                  </div>
                  <div className="text-sm text-gray-500">Avg Diversity</div>
                </div>
              </div>
              
              <div className="pt-4 border-t border-gray-200">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Assignment Efficiency</span>
                  <span className="text-sm font-medium text-green-600">
                    100.0%
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500">Phase 2 not completed</p>
            </div>
          )}
        </div>

        {/* Phase 3: Team-Problem Assignment */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Phase 3: Team Assignment</h3>
            <span className="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded-full">
              {phase3_stats?.algorithm || 'N/A'}
            </span>
          </div>
          
          {phase3_stats ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-lg font-semibold text-gray-900">{phase3_stats.teams_assigned}</div>
                  <div className="text-sm text-gray-500">Teams Assigned</div>
                </div>
                <div>
                  <div className="text-lg font-semibold text-gray-900">{phase3_stats.total_assignment_cost.toFixed(2)}</div>
                  <div className="text-sm text-gray-500">Total Cost</div>
                </div>
                <div>
                  <div className="text-lg font-semibold text-gray-900">{phase3_stats.avg_assignment_cost.toFixed(3)}</div>
                  <div className="text-sm text-gray-500">Avg Cost</div>
                </div>
                <div>
                  <div className="text-lg font-semibold text-gray-900">{phase3_stats.avg_problem_score.toFixed(2)}</div>
                  <div className="text-sm text-gray-500">Avg Score</div>
                </div>
              </div>
              
              <div className="pt-4 border-t border-gray-200">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Assignment Rate</span>
                  <span className="text-sm font-medium text-purple-600">
                    {overall_stats?.teams_count ? ((phase3_stats.teams_assigned / overall_stats.teams_count) * 100).toFixed(1) : 0}%
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500">Phase 3 not completed</p>
            </div>
          )}
        </div>
      </div>

      {/* Algorithm Performance Comparison */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Algorithm Performance</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600 mb-2">Hungarian</div>
            <div className="text-sm text-gray-500 mb-4">Optimization Algorithm</div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Optimality</span>
                <span className="text-sm font-medium text-green-600">Guaranteed</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Complexity</span>
                <span className="text-sm font-medium text-orange-600">O(n³)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Scalability</span>
                <span className="text-sm font-medium text-blue-600">Good</span>
              </div>
            </div>
          </div>
          
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600 mb-2">Cost-Based</div>
            <div className="text-sm text-gray-500 mb-4">Matching Strategy</div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Avg Phase 1 Cost</span>
                <span className="text-sm font-medium text-blue-600">
                  {phase1_stats?.avg_assignment_cost.toFixed(3) || 'N/A'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Avg Phase 3 Cost</span>
                <span className="text-sm font-medium text-purple-600">
                  {phase3_stats?.avg_assignment_cost.toFixed(3) || 'N/A'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Efficiency</span>
                <span className="text-sm font-medium text-green-600">
                  {overall_stats?.completion_rate ? `${overall_stats.completion_rate.toFixed(1)}%` : 'N/A'}
                </span>
              </div>
            </div>
          </div>
          
          <div className="text-center">
            <div className="text-3xl font-bold text-purple-600 mb-2">Multi-Phase</div>
            <div className="text-sm text-gray-500 mb-4">Approach</div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Phases</span>
                <span className="text-sm font-medium text-blue-600">3</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Flexibility</span>
                <span className="text-sm font-medium text-green-600">High</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Robustness</span>
                <span className="text-sm font-medium text-purple-600">Excellent</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Performance Insights */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance Insights</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="font-medium text-gray-900 mb-3">Strengths</h4>
            <ul className="space-y-2">
              <li className="flex items-start space-x-2">
                <span className="text-green-500 mt-1">✓</span>
                <span className="text-sm text-gray-600">
                  Optimal assignments guaranteed by Hungarian algorithm
                </span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-green-500 mt-1">✓</span>
                <span className="text-sm text-gray-600">
                  High completion rate: {overall_stats?.completion_rate?.toFixed(1) || 0}%
                </span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-green-500 mt-1">✓</span>
                <span className="text-sm text-gray-600">
                  Multi-phase approach ensures balanced team formation
                </span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-green-500 mt-1">✓</span>
                <span className="text-sm text-gray-600">
                  Cost-based optimization minimizes mismatch
                </span>
              </li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-medium text-gray-900 mb-3">Recommendations</h4>
            <ul className="space-y-2">
              <li className="flex items-start space-x-2">
                <span className="text-blue-500 mt-1">•</span>
                <span className="text-sm text-gray-600">
                  Monitor diversity scores to ensure balanced teams
                </span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-blue-500 mt-1">•</span>
                <span className="text-sm text-gray-600">
                  Consider skills coverage when evaluating team effectiveness
                </span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-blue-500 mt-1">•</span>
                <span className="text-sm text-gray-600">
                  Track assignment costs to identify optimization opportunities
                </span>
              </li>
              <li className="flex items-start space-x-2">
                <span className="text-blue-500 mt-1">•</span>
                <span className="text-sm text-gray-600">
                  Regular performance analysis helps improve future matchings
                </span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatsDashboard; 