import { ApiResponse, MatchingResults, Participant, Problem, Team, MatchingStats } from './types';

const API_BASE_URL = 'http://localhost:8000';

class ApiClient {
  private async makeRequest<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return { success: true, data };
    } catch (error) {
      console.error('API request failed:', error);
      return { 
        success: false, 
        error: error instanceof Error ? error.message : 'Unknown error' 
      };
    }
  }

  async getMatchingStatus(): Promise<ApiResponse<any>> {
    return this.makeRequest('/api/match/status');
  }

  async startMatching(): Promise<ApiResponse<any>> {
    return this.makeRequest('/api/match/start', { method: 'POST' });
  }

  async getResults(): Promise<ApiResponse<MatchingResults>> {
    try {
      // Get data from the three different endpoints
      const [participantsRes, problemsRes, teamsRes] = await Promise.all([
        this.makeRequest<Participant[]>('/api/dashboard/participants'),
        this.makeRequest<Problem[]>('/api/dashboard/problems/detailed'),
        this.makeRequest<Team[]>('/api/dashboard/teams/detailed')
      ]);

      if (participantsRes.success && problemsRes.success && teamsRes.success) {
        const participants = participantsRes.data || [];
        const problems = problemsRes.data || [];
        const teams = teamsRes.data || [];

        // Calculate summary statistics
        const totalParticipantsInTeams = teams.reduce((sum, team) => {
          if (team.participant_ids) {
            return sum + team.participant_ids.length;
          } else if (team.members) {
            return sum + team.members.length;
          } else {
            return sum + (team.team_size || 0);
          }
        }, 0);
        const avgTeamSize = teams.length > 0 ? totalParticipantsInTeams / teams.length : 0;
        
        // Calculate total assignment costs
        const totalAssignmentCost = teams.reduce((sum, team) => sum + (team.final_assignment_cost || 0), 0);
        const avgAssignmentCost = teams.length > 0 ? totalAssignmentCost / teams.length : 0;

        const summary = {
          total_participants: participants.length,
          total_problems: problems.length,
          total_teams: teams.length,
          avg_team_size: avgTeamSize,
          total_assignment_cost: totalAssignmentCost,
          avg_assignment_cost: avgAssignmentCost,
          algorithm_used: 'hungarian',
          phases_completed: ['phase1', 'phase2', 'phase3']
        };

        return {
          success: true,
          data: {
            participants,
            problems,
            teams,
            summary
          }
        };
      } else {
        return {
          success: false,
          error: 'Failed to fetch one or more data sources'
        };
      }
    } catch (error) {
      console.error('Error in getResults:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  async getStats(): Promise<ApiResponse<MatchingStats>> {
    return this.makeRequest<MatchingStats>('/api/dashboard/stats');
  }

  async startMatching(): Promise<ApiResponse<any>> {
    return this.makeRequest<any>('/api/dashboard/start-matching', {
      method: 'POST'
    });
  }

  async exportResults(format: 'json' | 'csv' = 'json'): Promise<ApiResponse<any>> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/dashboard/export?format=${format}`, {
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (format === 'csv') {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'nat_ignite_results.csv';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        return { success: true, data: 'CSV download started' };
      } else {
        const data = await response.json();
        return { success: true, data };
      }
    } catch (error) {
      console.error('Export failed:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Export failed'
      };
    }
  }
}

export const apiClient = new ApiClient(); 