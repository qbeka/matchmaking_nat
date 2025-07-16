import { Team, Participant } from '../types';

interface CalculatedMetrics {
  diversity_score: number;
  skills_covered: number;
  role_coverage: number;
  role_balance_flag: boolean;
  confidence_score: number;
  synergy_score: number;
}

// Important skills with weights (matching backend)
const SKILL_IMPORTANCE: Record<string, number> = {
  'python': 1.0,
  'javascript': 1.0, 
  'react': 0.9,
  'typescript': 0.8,
  'sql': 0.9,
  'nosql': 0.7,
  'aws': 0.8,
  'gcp': 0.8,
  'azure': 0.8,
  'docker': 0.7,
  'kubernetes': 0.6,
  'fastapi': 0.7,
  'machine_learning': 0.9,
  'data_analysis': 0.8,
};

// All possible roles
const ALL_ROLES = ['fullstack', 'frontend', 'backend', 'data_science', 'devops'];

export function calculateTeamMetrics(team: Team): CalculatedMetrics {
  const members = team.members || [];
  
  if (members.length === 0) {
    return {
      diversity_score: 0,
      skills_covered: 0,
      role_coverage: 0,
      role_balance_flag: false,
      confidence_score: 0,
      synergy_score: 0
    };
  }

  // 1. Skills Coverage - what percentage of relevant skills are covered by the team
  const teamSkills = new Set<string>();
  let totalSkillLevel = 0;
  let skillCount = 0;

  members.forEach(member => {
    const skills = member.self_rated_skills || {};
    Object.entries(skills).forEach(([skill, level]) => {
      if (level > 0) {
        teamSkills.add(skill);
        totalSkillLevel += level;
        skillCount++;
      }
    });
  });

  // Skills coverage - improved calculation considering skill levels and importance
  const importantSkills = Object.keys(SKILL_IMPORTANCE);
  let skillScore = 0;
  let maxPossibleScore = 0;
  
  for (const skill of importantSkills) {
    const importance = SKILL_IMPORTANCE[skill];
    maxPossibleScore += importance;
    
    // Check if team has this skill
    let teamSkillLevel = 0;
    members.forEach(member => {
      const memberSkillLevel = member.self_rated_skills?.[skill] || 0;
      teamSkillLevel = Math.max(teamSkillLevel, memberSkillLevel); // Take highest level in team
    });
    
    if (teamSkillLevel > 0) {
      // Award points based on skill level and importance
      skillScore += (teamSkillLevel / 5) * importance; // Normalize to 0-1 and weight by importance
    }
  }
  
  const skills_covered = maxPossibleScore > 0 ? skillScore / maxPossibleScore : 0;

  // 2. Role Coverage - what percentage of roles are represented
  const teamRoles = new Set<string>();
  members.forEach(member => {
    const roles = member.primary_roles || [];
    roles.forEach(role => teamRoles.add(role));
  });

  const role_coverage = teamRoles.size / ALL_ROLES.length;

  // 3. Diversity Score - improved calculation with bonuses for team composition
  let base_diversity = 0.6 * role_coverage + 0.4 * skills_covered;
  
  // Bonus for having multiple roles represented
  const uniqueRoles = teamRoles.size;
  const roleBonus = Math.min(0.3, uniqueRoles * 0.1); // Up to 30% bonus for role diversity
  
  // Bonus for skill complementarity (different members having different strong skills)
  const skillComplementarity = teamSkills.size / Math.max(1, members.length);
  const skillBonus = Math.min(0.2, skillComplementarity * 0.1); // Up to 20% bonus
  
  const diversity_score = Math.min(1.0, base_diversity + roleBonus + skillBonus);

  // 4. Role Balance - improved calculation for realistic team sizes
  const roleCount: Record<string, number> = {};
  members.forEach(member => {
    const roles = member.primary_roles || [];
    roles.forEach(role => {
      roleCount[role] = (roleCount[role] || 0) + 1;
    });
  });

  // More generous role balance for smaller teams
  let role_balance_flag = true;
  if (Object.keys(roleCount).length > 0) {
    const maxRoleCount = Math.max(...Object.values(roleCount));
    const teamSize = members.length;
    
    if (teamSize <= 2) {
      role_balance_flag = true; // Small teams are always balanced
    } else if (teamSize <= 4) {
      role_balance_flag = maxRoleCount <= Math.ceil(teamSize * 0.75); // 75% threshold for small teams
    } else {
      role_balance_flag = maxRoleCount <= Math.ceil(teamSize * 0.6); // 60% for larger teams
    }
  }

  // 5. Confidence Score - improved calculation with experience bonus
  let base_confidence = skillCount > 0 ? (totalSkillLevel / skillCount) / 5 : 0; // Normalize to 0-1
  
  // Bonus for having experienced team members
  const experienceLevels = members.map(member => {
    const level = member.experience_level || 'intermediate';
    return level === 'senior' ? 1.0 : level === 'intermediate' ? 0.7 : 0.4;
  });
  const avgExperience = experienceLevels.reduce((sum, exp) => sum + exp, 0) / experienceLevels.length;
  
  // Bonus for team members with high availability
  const avgAvailability = members.reduce((sum, member) => {
    return sum + (member.availability_hours || 20);
  }, 0) / members.length;
  const availabilityBonus = Math.min(0.2, (avgAvailability - 20) / 100); // Bonus for >20 hours
  
  const confidence_score = Math.min(1.0, base_confidence + (avgExperience - 0.5) * 0.3 + Math.max(0, availabilityBonus));

  // 6. Team Synergy - calculate skill complementarity and role diversity bonus
  const synergy_score = calculateTeamSynergy(members);

  return {
    diversity_score: Math.min(diversity_score, 1),
    skills_covered: Math.min(skills_covered, 1),
    role_coverage: Math.min(role_coverage, 1),
    role_balance_flag,
    confidence_score: Math.min(confidence_score, 1),
    synergy_score: Math.min(synergy_score, 1)
  };
}

function calculateTeamSynergy(members: Participant[]): number {
  if (members.length <= 1) {
    return 0.6; // Give single member teams a baseline score
  }

  // Skill complementarity - award for diverse skills
  const allSkills = new Set<string>();
  let totalSkillLevels = 0;
  let skillCount = 0;

  members.forEach(member => {
    const memberSkills = member.self_rated_skills || {};
    Object.entries(memberSkills).forEach(([skill, level]) => {
      allSkills.add(skill);
      totalSkillLevels += level;
      skillCount++;
    });
  });

  // Award for skill diversity and high skill levels
  const skillDiversityScore = Math.min(1.0, allSkills.size / 8); // Normalize by 8 expected skills
  const skillQualityScore = skillCount > 0 ? (totalSkillLevels / skillCount) / 5 : 0.5;
  const skillBonus = (skillDiversityScore + skillQualityScore) / 2;

  // Role synergy - award for balanced role distribution
  const allRoles = new Set<string>();
  members.forEach(member => {
    (member.primary_roles || []).forEach(role => allRoles.add(role));
  });

  const roleDiversityScore = Math.min(1.0, allRoles.size / 3); // Normalize by 3 expected roles
  const roleBonus = roleDiversityScore * 0.8; // Up to 0.8 for perfect role diversity

  // Team size bonus - larger teams get slight bonus
  const sizeBonus = Math.min(0.2, (members.length - 1) * 0.05); // Small bonus for team size

  // Experience synergy - mixed experience levels are good
  const experienceLevels = new Set(members.map(m => m.experience_level || 'intermediate'));
  const experienceBonus = experienceLevels.size > 1 ? 0.15 : 0.05; // Bonus for mixed experience

  return Math.min(1.0, skillBonus * 0.4 + roleBonus * 0.3 + sizeBonus + experienceBonus + 0.1); // Base 0.1
}

export function getCostScoreExplanation() {
  return {
    title: "Understanding Cost Scores",
    description: "Cost scores represent how well participants or teams match their assigned problems. Lower scores indicate better matches.",
    ranges: [
      {
        range: "0.0 - 0.3",
        label: "Excellent Match",
        color: "text-green-600",
        description: "Very well-suited for the problem"
      },
      {
        range: "0.3 - 0.6",
        label: "Good Match", 
        color: "text-yellow-600",
        description: "Suitable with minor skill gaps"
      },
      {
        range: "0.6 - 1.0",
        label: "Fair Match",
        color: "text-orange-600", 
        description: "Manageable with learning curve"
      },
      {
        range: "> 1.0",
        label: "Poor Match",
        color: "text-red-600",
        description: "Significant skill or role misalignment"
      }
    ],
    factors: [
      "Skill level gaps vs problem requirements",
      "Role alignment with problem needs", 
      "Experience level vs problem complexity",
      "Availability vs time commitment"
    ]
  };
} 