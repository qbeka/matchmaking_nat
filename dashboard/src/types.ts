export interface Participant {
  _id: string;
  version: string;
  name: string;
  email: string;
  primary_roles: string[];
  self_rated_skills: Record<string, number>;
  availability_hours: number;
  experience_level?: string;
  motivation_text: string;
  leadership_preference?: boolean;
  team_preferences?: string[];
  challenge_preferences?: string[];
  id?: string;
  assigned_at?: string;
  assigned_problem_id?: string;
  assigned_problem_title?: string;
  assignment_cost?: number;
}

export interface Problem {
  _id: string;
  version: string;
  title: string;
  raw_prompt: string;
  estimated_team_size: number;
  preferred_roles: Record<string, any>;
  tech_constraints: any;
  problem_embedding: any;
  required_skills: Record<string, number>;
  role_preferences: Record<string, number>;
  expected_ambiguity?: number;
  expected_hours_per_week?: number;
  id?: string;
  problem_score?: number;
  processed?: boolean;
  processed_at?: string;
}

export interface AIScores {
  diversity_score: number;
  skills_coverage: number;
  role_coverage: number;
  role_balance: number;
  confidence_score: number;
  strengths: string[];
  potential_challenges: string[];
  ai_recommendations: string;
  analysis_timestamp: string;
  analysis_method: string;
  team_id?: string;
  problem_id?: string;
}

export interface RoleBalanceAnalysis {
  is_balanced: boolean;
  balance_score: number;
  missing_roles: string[];
  role_surplus?: string[];
  leadership_status?: string;
  balance_explanation?: string;
  concise_issue?: string;
  recommended_additions?: string[];
  potential_issues?: string[];
  strengths?: string[];
  urgency: string;
  confidence: number;
  team_id?: string;
  analysis_timestamp: string;
  analysis_method: string;
}

export interface Team {
  _id: string;
  team_id_str?: string;
  team_id?: string;
  participant_ids?: string[];
  team_size?: number;
  metrics?: {
    skills_covered: number;
    diversity_score: number;
    confidence_score: number;
    role_balance_flag: boolean;
    role_coverage: number;
  };
  ai_scores?: AIScores;
  ai_scored_at?: string;
  role_balance_analysis?: RoleBalanceAnalysis;
  members: Participant[];
  assigned_problem: string;
  final_problem_id?: string;
  final_problem_title?: string;
  final_assignment_cost?: number;
  final_assigned_at?: string;
  additional_problems?: Array<{
    problem_id: string;
    problem_title: string;
    assignment_cost: number;
    assigned_at: string;
  }>;
}

export interface MatchingResults {
  participants: Participant[];
  problems: Problem[];
  teams: Team[];
  summary: {
    total_participants: number;
    total_problems: number;
    total_teams: number;
    avg_team_size: number;
    total_assignment_cost?: number;
    avg_assignment_cost?: number;
    algorithm_used?: string;
    phases_completed?: string[];
  };
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface MatchingStats {
  phase1_stats?: {
    total_participants: number;
    total_problems: number;
    total_assignments: number;
    avg_assignment_cost: number;
    algorithm: string;
  };
  phase2_stats?: {
    total_teams: number;
    avg_team_size: number;
    total_participants_in_teams: number;
    avg_diversity_score: number;
    avg_skills_coverage: number;
    algorithm: string;
  };
  phase3_stats?: {
    teams_assigned: number;
    total_assignment_cost: number;
    avg_assignment_cost: number;
    avg_problem_score: number;
    algorithm: string;
  };
} 