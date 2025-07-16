import React, { useState } from 'react';
import { Participant } from '../types';

interface ParticipantsDashboardProps {
  participants: Participant[];
}

const ParticipantsDashboard: React.FC<ParticipantsDashboardProps> = ({ participants }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRole, setFilterRole] = useState('');
  const [filterExperience, setFilterExperience] = useState('');
  const [filterLeadership, setFilterLeadership] = useState('');

  const filteredParticipants = participants.filter(participant => {
    const matchesSearch = 
      participant.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      participant.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      participant.primary_roles.some(role => role.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesRole = !filterRole || participant.primary_roles.includes(filterRole);
    const matchesExperience = !filterExperience || participant.experience_level === filterExperience;
    const matchesLeadership = !filterLeadership || 
      (filterLeadership === 'leader' && participant.leadership_preference) ||
      (filterLeadership === 'non-leader' && !participant.leadership_preference);
    
    return matchesSearch && matchesRole && matchesExperience && matchesLeadership;
  });

  const getExperienceColor = (level: string | undefined) => {
    switch (level) {
      case 'student':
        return 'bg-blue-100 text-blue-800';
      case 'junior':
        return 'bg-green-100 text-green-800';
      case 'mid':
        return 'bg-yellow-100 text-yellow-800';
      case 'senior':
        return 'bg-orange-100 text-orange-800';
      case 'lead':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTopSkills = (skills: Record<string, number>) => {
    return Object.entries(skills)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 3)
      .map(([skill, level]) => ({ skill, level }));
  };

  const allRoles = [...new Set(participants.flatMap(p => p.primary_roles))];
  const allExperienceLevels = [...new Set(participants.map(p => p.experience_level).filter(Boolean))];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Participants ({participants.length})</h2>
        <div className="flex space-x-4">
          <input
            type="text"
            placeholder="Search participants..."
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <select
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            value={filterRole}
            onChange={(e) => setFilterRole(e.target.value)}
          >
            <option value="">All Roles</option>
            {allRoles.map(role => (
              <option key={role} value={role}>{role}</option>
            ))}
          </select>
          <select
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            value={filterExperience}
            onChange={(e) => setFilterExperience(e.target.value)}
          >
            <option value="">All Experience</option>
            {allExperienceLevels.map(level => (
              <option key={level} value={level}>{level}</option>
            ))}
          </select>
          <select
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            value={filterLeadership}
            onChange={(e) => setFilterLeadership(e.target.value)}
          >
            <option value="">All Leadership</option>
            <option value="leader">Leaders Only</option>
            <option value="non-leader">Non-Leaders Only</option>
          </select>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Total Participants</h3>
          <p className="text-2xl font-bold text-gray-900">{participants.length}</p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Assigned</h3>
          <p className="text-2xl font-bold text-green-600">
            {participants.filter(p => p.assigned_problem_id).length}
          </p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Avg Availability</h3>
          <p className="text-2xl font-bold text-blue-600">
            {(participants.reduce((sum, p) => sum + p.availability_hours, 0) / participants.length).toFixed(1)}h
          </p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Unique Roles</h3>
          <p className="text-2xl font-bold text-purple-600">{allRoles.length}</p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Leaders</h3>
          <p className="text-2xl font-bold text-yellow-600">
            {participants.filter(p => p.leadership_preference).length}
          </p>
        </div>
      </div>

      {/* Participants Grid */}
      <div className="grid gap-4">
        {filteredParticipants.map((participant) => (
          <div
            key={participant._id}
            className="bg-white shadow rounded-lg p-4 hover:shadow-md transition-shadow"
          >
            <div className="flex justify-between items-start mb-3">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{participant.name}</h3>
                <p className="text-sm text-gray-600">{participant.email}</p>
              </div>
              <div className="flex flex-col items-end space-y-2">
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getExperienceColor(participant.experience_level)}`}>
                  {participant.experience_level || 'Unknown'}
                </span>
                {participant.leadership_preference && (
                  <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full font-medium">
                    👑 Leader
                  </span>
                )}
                <span className="text-sm text-gray-500">{participant.availability_hours}h available</span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Roles */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Primary Roles</h4>
                <div className="flex flex-wrap gap-1">
                  {participant.primary_roles.map((role) => (
                    <span
                      key={role}
                      className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full"
                    >
                      {role}
                    </span>
                  ))}
                </div>
              </div>

              {/* Top Skills */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Top Skills</h4>
                <div className="space-y-1">
                  {getTopSkills(participant.self_rated_skills).map(({ skill, level }) => (
                    <div key={skill} className="flex justify-between items-center">
                      <span className="text-xs text-gray-600">{skill}</span>
                      <div className="flex items-center">
                        <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                          <div 
                            className="bg-blue-600 h-2 rounded-full" 
                            style={{ width: `${(level / 5) * 100}%` }}
                          ></div>
                        </div>
                        <span className="text-xs text-gray-500">{level}/5</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Assignment Status */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">Assignment</h4>
                {participant.assigned_problem_id ? (
                  <div className="space-y-1">
                    <p className="text-sm text-green-600 font-medium">Assigned</p>
                    <p className="text-xs text-gray-600">{participant.assigned_problem_title}</p>
                    {participant.assignment_cost && (
                      <p className="text-xs text-gray-500">Cost: {participant.assignment_cost.toFixed(3)}</p>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">Not assigned</p>
                )}
              </div>
            </div>

            {/* Motivation (collapsible) */}
            <div className="mt-4 pt-4 border-t border-gray-200">
              <details className="group">
                <summary className="text-sm font-medium text-gray-700 cursor-pointer hover:text-gray-900">
                  Motivation
                </summary>
                <p className="text-sm text-gray-600 mt-2 leading-relaxed">
                  {participant.motivation_text}
                </p>
              </details>
            </div>
          </div>
        ))}
      </div>

      {filteredParticipants.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">No participants found matching your criteria.</p>
        </div>
      )}
    </div>
  );
};

export default ParticipantsDashboard; 