import React, { useState } from 'react';
import { Team } from '../types';
import { calculateTeamMetrics } from '../utils/teamMetrics';
import CostExplanation from './CostExplanation';
import ManualTeamEditor from './ManualTeamEditor';
import AISuggestions from './AISuggestions';

// Helper function to get team metrics (AI scores first, then fallback to programmatic)
const getTeamMetrics = (team: Team) => {
  // Check if team has AI-generated scores
  if (team.ai_scores) {
    return {
      diversity_score: team.ai_scores.diversity_score || 0.6,
      skills_covered: team.ai_scores.skills_coverage || 0.6,
      role_coverage: team.ai_scores.role_coverage || 0.6,
      role_balance_flag: team.ai_scores.role_balance >= 0.7, // Convert float to boolean
      confidence_score: team.ai_scores.confidence_score || 0.6,
      team_synergy: team.ai_scores.diversity_score || 0.6, // Use diversity as synergy proxy
      is_ai_scored: true,
      ai_strengths: team.ai_scores.strengths || [],
      ai_challenges: team.ai_scores.potential_challenges || [],
      ai_recommendations: team.ai_scores.ai_recommendations || ''
    };
  }
  
  // Fallback to programmatic calculation
  const metrics = calculateTeamMetrics(team);
  return {
    ...metrics,
    is_ai_scored: false,
    ai_strengths: [],
    ai_challenges: [],
    ai_recommendations: ''
  };
};

interface TeamsDashboardProps {
  teams: Team[];
  onTeamsUpdate?: (updatedTeams: Team[]) => void;
}

const TeamsDashboard: React.FC<TeamsDashboardProps> = ({ teams, onTeamsUpdate }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'size' | 'diversity' | 'skills'>('size');
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [showManualEditor, setShowManualEditor] = useState(false);
  const [showAISuggestions, setShowAISuggestions] = useState(false);

  const filteredAndSortedTeams = teams
    .filter(team => {
      const searchLower = searchTerm.toLowerCase();
      const teamId = team.team_id_str || team.team_id || '';
      const participantIds = team.participant_ids || [];
      const assignedProblem = team.assigned_problem || '';
      
      return teamId.toLowerCase().includes(searchLower) ||
             participantIds.some(id => id.toLowerCase().includes(searchLower)) ||
             assignedProblem.toLowerCase().includes(searchLower);
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'size':
          const sizeA = a.participant_ids?.length || a.members?.length || a.team_size || 0;
          const sizeB = b.participant_ids?.length || b.members?.length || b.team_size || 0;
          return sizeB - sizeA;
        case 'diversity':
          const metricsA = getTeamMetrics(a);
          const metricsB = getTeamMetrics(b);
          return metricsB.diversity_score - metricsA.diversity_score;
        case 'skills':
          const skillsA = getTeamMetrics(a);
          const skillsB = getTeamMetrics(b);
          return skillsB.skills_covered - skillsA.skills_covered;
        default:
          return 0;
      }
    });

  const getTeamSizeColor = (size: number) => {
    if (size <= 2) return 'bg-red-100 text-red-800';
    if (size <= 4) return 'bg-yellow-100 text-yellow-800';
    if (size <= 6) return 'bg-green-100 text-green-800';
    return 'bg-blue-100 text-blue-800';
  };

  const getDiversityColor = (score: number) => {
    if (score >= 0.7) return 'bg-green-100 text-green-800';
    if (score >= 0.5) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  const getSkillsCoverageColor = (score: number) => {
    if (score >= 0.8) return 'bg-green-100 text-green-800';
    if (score >= 0.6) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  const getRoleBalanceColor = (balanced: boolean) => {
    return balanced ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800';
  };

  const closeModal = () => setSelectedTeam(null);

  // Calculate summary statistics using calculated metrics
  const totalParticipants = teams.reduce((sum, team) => {
    return sum + (team.participant_ids?.length || team.members?.length || team.team_size || 0);
  }, 0);
  const avgTeamSize = teams.length > 0 ? totalParticipants / teams.length : 0;
  
  const teamsWithMetrics = teams.map(team => getTeamMetrics(team));
  const avgDiversityScore = teams.length > 0 ? 
    teamsWithMetrics.reduce((sum, metrics) => sum + metrics.diversity_score, 0) / teams.length : 0;
  const avgSkillsCoverage = teams.length > 0 ? 
    teamsWithMetrics.reduce((sum, metrics) => sum + metrics.skills_covered, 0) / teams.length : 0;
  const aiScoredTeams = teamsWithMetrics.filter(metrics => metrics.is_ai_scored).length;
  const teamsWithAssignedProblems = teams.filter(team => 
    (team.assigned_problem || '') !== "Not yet assigned"
  ).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Teams ({teams.length})</h2>
        <div className="flex space-x-4 items-center">
          <button
            onClick={() => setShowAISuggestions(true)}
            className="px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            AI Suggestions
          </button>
          <button
            onClick={() => setShowManualEditor(true)}
            className="px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Manual Editor
          </button>
          <CostExplanation />
          <input
            type="text"
            placeholder="Search teams..."
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <select
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'size' | 'diversity' | 'skills')}
          >
            <option value="size">Sort by Size</option>
            <option value="diversity">Sort by Diversity</option>
            <option value="skills">Sort by Skills Coverage</option>
          </select>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Total Teams</h3>
          <p className="text-2xl font-bold text-gray-900">{teams.length}</p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Avg Team Size</h3>
          <p className="text-2xl font-bold text-blue-600">{avgTeamSize.toFixed(1)}</p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Avg Diversity</h3>
          <p className="text-2xl font-bold text-green-600">{(avgDiversityScore * 100).toFixed(1)}%</p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Avg Skills Coverage</h3>
          <p className="text-2xl font-bold text-purple-600">{(avgSkillsCoverage * 100).toFixed(1)}%</p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">AI Scored Teams</h3>
          <p className="text-2xl font-bold text-blue-600">{aiScoredTeams}</p>
          <p className="text-xs text-gray-500 mt-1">of {teams.length} total</p>
        </div>
      </div>

      {/* Teams Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {filteredAndSortedTeams.map((team) => {
          const calculatedMetrics = getTeamMetrics(team);
          return (
          <div
            key={team._id}
            className="bg-white shadow rounded-lg p-6 hover:shadow-md transition-shadow cursor-pointer"
            onClick={() => setSelectedTeam(team)}
          >
            <div className="flex justify-between items-start mb-4">
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="text-lg font-semibold text-gray-900">{team.team_id_str || team.team_id || 'Team'}</h3>
                  {calculatedMetrics.is_ai_scored && (
                    <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded-full">
                      AI Scored
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-600">{team.participant_ids?.length || team.members?.length || team.team_size || 0} members</p>
              </div>
              <div className="flex flex-col items-end space-y-2">
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getTeamSizeColor(team.participant_ids?.length || team.members?.length || team.team_size || 0)}`}>
                  {team.participant_ids?.length || team.members?.length || team.team_size || 0} members
                </span>
                {team.final_assignment_cost && (
                  <span className="text-xs text-gray-500">
                    Cost: {team.final_assignment_cost.toFixed(3)}
                  </span>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              {/* Diversity Score */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-1">Diversity Score</h4>
                <div className="flex items-center space-x-2">
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-green-600 h-2 rounded-full" 
                      style={{ width: `${calculatedMetrics.diversity_score * 100}%` }}
                    ></div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getDiversityColor(calculatedMetrics.diversity_score)}`}>
                    {(calculatedMetrics.diversity_score * 100).toFixed(1)}%
                  </span>
                </div>
              </div>

              {/* Skills Coverage */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-1">Skills Coverage</h4>
                <div className="flex items-center space-x-2">
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full" 
                      style={{ width: `${calculatedMetrics.skills_covered * 100}%` }}
                    ></div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getSkillsCoverageColor(calculatedMetrics.skills_covered)}`}>
                    {(calculatedMetrics.skills_covered * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              {/* Role Coverage */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-1">Role Coverage</h4>
                <div className="flex items-center space-x-2">
                  <div className="flex-1 bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-purple-600 h-2 rounded-full" 
                      style={{ width: `${calculatedMetrics.role_coverage * 100}%` }}
                    ></div>
                  </div>
                  <span className="text-xs text-gray-500">
                    {(calculatedMetrics.role_coverage * 100).toFixed(1)}%
                  </span>
                </div>
              </div>

              {/* Role Balance */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-1">Role Balance</h4>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRoleBalanceColor(calculatedMetrics.role_balance_flag)}`}>
                  {calculatedMetrics.role_balance_flag ? 'Balanced' : 'Unbalanced'}
                </span>
              </div>
            </div>

            {/* AI Role Balance Feedback */}
            {team.role_balance_analysis && !team.role_balance_analysis.is_balanced && (
              <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div className="flex items-start space-x-2">
                  <span className="text-yellow-600 mt-0.5">⚠️</span>
                  <div className="flex-1">
                    {team.role_balance_analysis.missing_roles && team.role_balance_analysis.missing_roles.length > 0 && (
                      <div className="text-xs text-yellow-800 mb-1">
                        <span className="font-medium">Add recommended roles: </span>
                        <span className="text-yellow-700">
                          {team.role_balance_analysis.missing_roles.join(', ')}
                        </span>
                      </div>
                    )}
                    
                    <div className="text-xs text-yellow-700">
                      {team.role_balance_analysis.concise_issue || team.role_balance_analysis.balance_explanation || 'Team needs better role distribution'}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Assigned Problem */}
            <div className="pt-4 border-t border-gray-200">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Assigned Problem</h4>
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-600 flex-1">
                  {team.assigned_problem === "Not yet assigned" ? (
                    <span className="text-yellow-600">Not yet assigned</span>
                  ) : (
                    <span className="text-green-600">{team.assigned_problem}</span>
                  )}
                </p>
                {team.final_problem_id && (
                  <span className="text-xs text-gray-500 ml-2">
                    ID: {team.final_problem_id}
                  </span>
                )}
              </div>
            </div>

            {/* Member IDs Preview */}
            <div className="mt-4 pt-4 border-t border-gray-200">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Members</h4>
              <div className="flex flex-wrap gap-1">
                {(team.participant_ids || team.members?.map(m => m.name || m.id || m._id) || []).slice(0, 3).map((id, index) => (
                  <span
                    key={typeof id === 'string' ? id : index}
                    className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded"
                  >
                    {typeof id === 'string' ? id.substring(0, 12) + '...' : `Member ${index + 1}`}
                  </span>
                ))}
                {(team.participant_ids?.length || team.members?.length || 0) > 3 && (
                  <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
                    +{(team.participant_ids?.length || team.members?.length || 0) - 3} more
                  </span>
                )}
              </div>
              
              {/* Leadership Status */}
              <div className="mt-3">
                {(() => {
                  const leaders = team.members?.filter(m => m.leadership_preference) || [];
                  const leadersCount = leaders.length;
                  
                  if (leadersCount === 0) {
                    return (
                      <div className="flex items-center space-x-1">
                        <span className="text-xs text-red-600">⚠️ No leaders</span>
                      </div>
                    );
                  } else {
                    return (
                      <div className="flex items-center space-x-1">
                        <span className="text-xs text-yellow-600">👑</span>
                        <span className="text-xs text-gray-600">
                          {leadersCount} leader{leadersCount > 1 ? 's' : ''}
                          {leaders.length > 0 && leaders[0].name && (
                            <span className="text-gray-500">: {leaders.slice(0, 2).map(l => l.name).join(', ')}</span>
                          )}
                        </span>
                      </div>
                    );
                  }
                })()}
              </div>
            </div>
          </div>
        );
        })}
      </div>

      {filteredAndSortedTeams.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">No teams found matching your criteria.</p>
        </div>
      )}

      {/* Team Detail Modal */}
      {selectedTeam && (() => {
        const selectedTeamMetrics = getTeamMetrics(selectedTeam);
        return (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border max-w-4xl shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900">
                  Team Details: {selectedTeam.team_id_str}
                </h3>
                <button
                  onClick={closeModal}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Team Metrics */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Team ID</label>
                    <p className="mt-1 text-sm text-gray-900">{selectedTeam.team_id_str || selectedTeam.team_id || 'Team'}</p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Team Size</label>
                    <p className="mt-1 text-sm text-gray-900">{selectedTeam.participant_ids?.length || selectedTeam.members?.length || selectedTeam.team_size || 0} members</p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Diversity Score</label>
                    <div className="mt-1 flex items-center space-x-2">
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-green-600 h-2 rounded-full" 
                          style={{ width: `${selectedTeamMetrics.diversity_score * 100}%` }}
                        ></div>
                      </div>
                      <span className="text-sm text-gray-900">{(selectedTeamMetrics.diversity_score * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Skills Coverage</label>
                    <div className="mt-1 flex items-center space-x-2">
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full" 
                          style={{ width: `${selectedTeamMetrics.skills_covered * 100}%` }}
                        ></div>
                      </div>
                      <span className="text-sm text-gray-900">{(selectedTeamMetrics.skills_covered * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Role Coverage</label>
                    <div className="mt-1 flex items-center space-x-2">
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-purple-600 h-2 rounded-full" 
                          style={{ width: `${selectedTeamMetrics.role_coverage * 100}%` }}
                        ></div>
                      </div>
                      <span className="text-sm text-gray-900">{(selectedTeamMetrics.role_coverage * 100).toFixed(1)}%</span>
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Role Balance</label>
                    <span className={`mt-1 px-2 py-1 rounded-full text-xs font-medium ${getRoleBalanceColor(selectedTeamMetrics.role_balance_flag)}`}>
                      {selectedTeamMetrics.role_balance_flag ? 'Balanced' : 'Unbalanced'}
                    </span>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Confidence Score</label>
                    <p className="mt-1 text-sm text-gray-900">{(selectedTeamMetrics.confidence_score * 100).toFixed(1)}%</p>
                  </div>
                  
                  {selectedTeam.final_assignment_cost && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Assignment Cost</label>
                      <p className="mt-1 text-sm text-gray-900">{selectedTeam.final_assignment_cost.toFixed(3)}</p>
                    </div>
                  )}
                </div>
                
                {/* Assignment and Members */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Assigned Problem</label>
                    <p className="mt-1 text-sm text-gray-900">
                      {selectedTeam.assigned_problem === "Not yet assigned" ? (
                        <span className="text-yellow-600">Not yet assigned</span>
                      ) : (
                        selectedTeam.assigned_problem
                      )}
                    </p>
                    {selectedTeam.final_problem_id && (
                      <p className="text-xs text-gray-500 mt-1">ID: {selectedTeam.final_problem_id}</p>
                    )}
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Members</label>
                    <div className="mt-1 space-y-1">
                      {(selectedTeam.participant_ids || selectedTeam.members?.map(m => m.name || m.id || m._id) || []).map((id, index) => (
                        <div key={typeof id === 'string' ? id : index} className="flex items-center justify-between bg-gray-50 p-2 rounded">
                          <span className="text-sm text-gray-700">#{index + 1}</span>
                          <span className="text-sm text-gray-900 font-mono">{typeof id === 'string' ? id : `Member ${index + 1}`}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  {selectedTeam.final_assigned_at && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700">Assigned At</label>
                      <p className="mt-1 text-sm text-gray-900">
                        {new Date(selectedTeam.final_assigned_at).toLocaleString()}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
        );
      })()}

      {/* Manual Team Editor */}
      {showManualEditor && (
        <ManualTeamEditor
          teams={teams}
          onClose={() => setShowManualEditor(false)}
          onTeamsUpdate={(updatedTeams) => {
            if (onTeamsUpdate) {
              onTeamsUpdate(updatedTeams);
            }
            setShowManualEditor(false);
          }}
        />
      )}

      {/* AI Suggestions Modal */}
      {showAISuggestions && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-4 mx-auto p-5 border max-w-6xl shadow-lg rounded-md bg-white min-h-[90vh]">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-medium text-gray-900">AI Quality Reviews & Suggestions</h3>
              <button
                onClick={() => setShowAISuggestions(false)}
                className="text-gray-400 hover:text-gray-600 text-2xl font-bold"
              >
                ×
              </button>
            </div>
            <div className="mt-4">
              <AISuggestions />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TeamsDashboard; 