import React, { useState } from 'react';
import { Problem } from '../types';

interface ProblemsDashboardProps {
  problems: Problem[];
}

const ProblemsDashboard: React.FC<ProblemsDashboardProps> = ({ problems }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedProblem, setSelectedProblem] = useState<Problem | null>(null);

  const filteredProblems = problems.filter(problem => {
    const matchesSearch = 
      problem.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      problem.raw_prompt.toLowerCase().includes(searchTerm.toLowerCase());
    
    return matchesSearch;
  });

  const getDifficultyFromSkills = (skills: Record<string, number>) => {
    const avgSkillLevel = Object.values(skills).reduce((sum, level) => sum + level, 0) / Object.values(skills).length;
    if (avgSkillLevel >= 4) return 'Hard';
    if (avgSkillLevel >= 3) return 'Medium';
    return 'Easy';
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty.toLowerCase()) {
      case 'easy':
        return 'bg-green-100 text-green-800';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800';
      case 'hard':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTopSkills = (skills: Record<string, number>) => {
    return Object.entries(skills)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5)
      .map(([skill, level]) => ({ skill, level }));
  };

  const getTopRoles = (roles: Record<string, number>) => {
    return Object.entries(roles)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 3)
      .map(([role, weight]) => ({ role, weight }));
  };

  const closeModal = () => setSelectedProblem(null);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Problems ({problems.length})</h2>
        <input
          type="text"
          placeholder="Search problems..."
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Total Problems</h3>
          <p className="text-2xl font-bold text-gray-900">{problems.length}</p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Processed</h3>
          <p className="text-2xl font-bold text-green-600">
            {problems.filter(p => p.processed).length}
          </p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-sm font-medium text-gray-500">Avg Problem Score</h3>
          <p className="text-2xl font-bold text-purple-600">
            {(problems.reduce((sum, p) => sum + (p.problem_score || 0), 0) / problems.length).toFixed(2)}
          </p>
        </div>
      </div>

      {/* Problems Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredProblems.map((problem) => {
          const difficulty = getDifficultyFromSkills(problem.required_skills);
          const topSkills = getTopSkills(problem.required_skills);
          const topRoles = getTopRoles(problem.role_preferences);

          return (
            <div
              key={problem._id}
              className="bg-white shadow rounded-lg p-6 hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => setSelectedProblem(problem)}
            >
              <div className="flex justify-between items-start mb-4">
                <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">
                  {problem.title}
                </h3>
                <div className="flex flex-col items-end space-y-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getDifficultyColor(difficulty)}`}>
                    {difficulty}
                  </span>
                  {problem.problem_score && (
                    <span className="text-xs text-gray-500">
                      Score: {problem.problem_score.toFixed(2)}
                    </span>
                  )}
                </div>
              </div>

              <p className="text-sm text-gray-600 mb-4 line-clamp-3">
                {problem.raw_prompt}
              </p>

              <div className="space-y-3">
                {/* Team Size */}
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-500">Team Size:</span>
                  <span className="text-sm font-medium">{problem.estimated_team_size}</span>
                </div>

                {/* Top Skills */}
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Required Skills</h4>
                  <div className="space-y-1">
                    {topSkills.slice(0, 3).map(({ skill, level }) => (
                      <div key={skill} className="flex justify-between items-center">
                        <span className="text-xs text-gray-600">{skill}</span>
                        <div className="flex items-center">
                          <div className="w-12 bg-gray-200 rounded-full h-1.5 mr-2">
                            <div 
                              className="bg-blue-600 h-1.5 rounded-full" 
                              style={{ width: `${(level / 5) * 100}%` }}
                            ></div>
                          </div>
                          <span className="text-xs text-gray-500">{level}/5</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Top Roles */}
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Preferred Roles</h4>
                  <div className="flex flex-wrap gap-1">
                    {topRoles.map(({ role, weight }) => (
                      <span
                        key={role}
                        className="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded-full"
                      >
                        {role} ({Math.round(weight * 100)}%)
                      </span>
                    ))}
                  </div>
                </div>

                {/* Status */}
                <div className="pt-2 border-t border-gray-200">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-500">Status:</span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      problem.processed ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {problem.processed ? 'Processed' : 'Pending'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {filteredProblems.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">No problems found matching your criteria.</p>
        </div>
      )}

      {/* Problem Detail Modal */}
      {selectedProblem && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border max-w-2xl shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900">
                  Problem Details
                </h3>
                <button
                  onClick={closeModal}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Title</label>
                  <p className="mt-1 text-sm text-gray-900">{selectedProblem.title}</p>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Description</label>
                  <p className="mt-1 text-sm text-gray-900 whitespace-pre-wrap">{selectedProblem.raw_prompt}</p>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Estimated Team Size</label>
                    <p className="mt-1 text-sm text-gray-900">{selectedProblem.estimated_team_size}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Problem Score</label>
                    <p className="mt-1 text-sm text-gray-900">
                      {selectedProblem.problem_score ? selectedProblem.problem_score.toFixed(2) : 'N/A'}
                    </p>
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Required Skills</label>
                  <div className="mt-1 space-y-2">
                    {getTopSkills(selectedProblem.required_skills).map(({ skill, level }) => (
                      <div key={skill} className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">{skill}</span>
                        <div className="flex items-center">
                          <div className="w-24 bg-gray-200 rounded-full h-2 mr-2">
                            <div 
                              className="bg-blue-600 h-2 rounded-full" 
                              style={{ width: `${(level / 5) * 100}%` }}
                            ></div>
                          </div>
                          <span className="text-sm text-gray-500">{level}/5</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700">Role Preferences</label>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {getTopRoles(selectedProblem.role_preferences).map(({ role, weight }) => (
                      <span
                        key={role}
                        className="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded-full"
                      >
                        {role} ({Math.round(weight * 100)}%)
                      </span>
                    ))}
                  </div>
                </div>
                
                {selectedProblem.processed_at && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Processed At</label>
                    <p className="mt-1 text-sm text-gray-900">
                      {new Date(selectedProblem.processed_at).toLocaleString()}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProblemsDashboard; 