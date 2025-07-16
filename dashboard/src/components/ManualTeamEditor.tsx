import React, { useState, useEffect } from 'react';
import { Team, Participant } from '../types';
import { calculateTeamMetrics } from '../utils/teamMetrics';

interface ManualTeamEditorProps {
  teams: Team[];
  onClose: () => void;
  onTeamsUpdate: (updatedTeams: Team[]) => void;
}

const ManualTeamEditor: React.FC<ManualTeamEditorProps> = ({ teams, onClose, onTeamsUpdate }) => {
  const [editableTeams, setEditableTeams] = useState<Team[]>(teams);
  const [draggedParticipant, setDraggedParticipant] = useState<Participant | null>(null);
  const [draggedFromTeamId, setDraggedFromTeamId] = useState<string | null>(null);

  // Calculate live statistics
  const calculateLiveStats = () => {
    const teamsWithMetrics = editableTeams.map(team => {
      const metrics = calculateTeamMetrics(team);
      return { ...team, calculatedMetrics: metrics };
    });

    const totalCost = teamsWithMetrics.reduce((sum, team) => {
      return sum + (team.final_assignment_cost || 0);
    }, 0);

    const avgDiversity = teamsWithMetrics.reduce((sum, team) => {
      return sum + team.calculatedMetrics.diversity_score;
    }, 0) / editableTeams.length;

    const avgSkillsCoverage = teamsWithMetrics.reduce((sum, team) => {
      return sum + team.calculatedMetrics.skills_covered;
    }, 0) / editableTeams.length;

    return {
      totalCost,
      avgDiversity,
      avgSkillsCoverage,
      teamsWithMetrics
    };
  };

  const stats = calculateLiveStats();

  const handleDragStart = (participant: Participant, fromTeamId: string) => {
    setDraggedParticipant(participant);
    setDraggedFromTeamId(fromTeamId);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (toTeamId: string) => {
    if (!draggedParticipant || !draggedFromTeamId || draggedFromTeamId === toTeamId) {
      setDraggedParticipant(null);
      setDraggedFromTeamId(null);
      return;
    }

    // Create updated teams
    const updatedTeams = editableTeams.map(team => {
      if (team.team_id === draggedFromTeamId || team.team_id_str === draggedFromTeamId) {
        // Remove participant from source team
        return {
          ...team,
          members: team.members.filter(member => member.participant_id !== draggedParticipant.participant_id),
          participant_ids: team.participant_ids?.filter(id => id !== draggedParticipant.participant_id)
        };
      }
      
      if (team.team_id === toTeamId || team.team_id_str === toTeamId) {
        // Add participant to target team
        return {
          ...team,
          members: [...team.members, draggedParticipant],
          participant_ids: [...(team.participant_ids || []), draggedParticipant.participant_id]
        };
      }
      
      return team;
    });

    setEditableTeams(updatedTeams);
    setDraggedParticipant(null);
    setDraggedFromTeamId(null);
  };

  const removeParticipantFromTeam = (participantId: string, teamId: string) => {
    const updatedTeams = editableTeams.map(team => {
      if (team.team_id === teamId || team.team_id_str === teamId) {
        return {
          ...team,
          members: team.members.filter(member => member.participant_id !== participantId),
          participant_ids: team.participant_ids?.filter(id => id !== participantId)
        };
      }
      return team;
    });
    setEditableTeams(updatedTeams);
  };

  const saveChanges = () => {
    onTeamsUpdate(editableTeams);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-4 mx-auto p-5 border max-w-7xl shadow-lg rounded-md bg-white min-h-screen">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-2xl font-bold text-gray-900">Manual Team Editor</h3>
            <p className="text-sm text-gray-600 mt-1">Drag and drop participants between teams to optimize assignments</p>
          </div>
          <div className="flex space-x-3">
            <button
              onClick={saveChanges}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              Save Changes
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600"
            >
              Cancel
            </button>
          </div>
        </div>

        {/* Teams Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {stats.teamsWithMetrics.map((team) => (
            <div
              key={team._id}
              className="bg-white border-2 border-gray-200 rounded-lg p-4 min-h-96"
              onDragOver={handleDragOver}
              onDrop={() => handleDrop(team.team_id || team.team_id_str || '')}
            >
              {/* Team Header */}
              <div className="mb-4">
                <h4 className="text-lg font-semibold text-gray-900">
                  {team.team_id_str || team.team_id}
                </h4>
                <div className="text-sm text-gray-600">
                  {team.members.length} members • Cost: {team.final_assignment_cost?.toFixed(3) || 'N/A'}
                </div>
                
                {/* Team Metrics */}
                <div className="mt-2 space-y-1">
                  <div className="flex justify-between text-xs">
                    <span>Diversity:</span>
                    <span className="font-medium">{(team.calculatedMetrics.diversity_score * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span>Skills:</span>
                    <span className="font-medium">{(team.calculatedMetrics.skills_covered * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span>Roles:</span>
                    <span className="font-medium">{(team.calculatedMetrics.role_coverage * 100).toFixed(1)}%</span>
                  </div>
                </div>
              </div>

              {/* Assigned Problem */}
              {team.assigned_problem && (
                <div className="mb-4 p-2 bg-gray-50 rounded">
                  <div className="text-xs text-gray-500">Assigned Problem:</div>
                  <div className="text-sm font-medium text-gray-900">{team.assigned_problem}</div>
                </div>
              )}

              {/* Participants */}
              <div className="space-y-2">
                {team.members.map((participant) => (
                  <div
                    key={participant.participant_id}
                    draggable
                    onDragStart={() => handleDragStart(participant, team.team_id || team.team_id_str || '')}
                    className="bg-gray-50 border border-gray-200 rounded p-3 cursor-move hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="font-medium text-sm text-gray-900">{participant.name}</div>
                        <div className="text-xs text-gray-600">{participant.email}</div>
                        
                        {/* Skills */}
                        <div className="mt-1">
                          <div className="text-xs text-gray-500">Skills:</div>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {Object.entries(participant.self_rated_skills || {}).slice(0, 3).map(([skill, level]) => (
                              <span key={skill} className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                                {skill} ({level})
                              </span>
                            ))}
                          </div>
                        </div>

                        {/* Roles */}
                        <div className="mt-1">
                          <div className="text-xs text-gray-500">Roles:</div>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {participant.primary_roles?.slice(0, 2).map((role) => (
                              <span key={role} className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                                {role}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>

                      <button
                        onClick={() => removeParticipantFromTeam(participant.participant_id, team.team_id || team.team_id_str || '')}
                        className="text-red-500 hover:text-red-700 text-xs ml-2"
                        title="Remove from team"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                ))}

                {/* Drop Zone */}
                <div className="border-2 border-dashed border-gray-300 rounded p-4 text-center text-gray-500 text-sm">
                  Drop participants here
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Instructions */}
        <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h5 className="font-medium text-yellow-900 mb-2">Instructions:</h5>
          <ul className="text-sm text-yellow-800 space-y-1">
            <li>• Drag participants between teams to optimize assignments</li>
            <li>• Statistics update automatically as you make changes</li>
            <li>• Lower cost scores indicate better matches</li>
            <li>• Aim for balanced diversity and skills coverage across teams</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default ManualTeamEditor; 