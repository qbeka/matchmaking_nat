# NAT Ignite Matchmaking Templates

This directory contains templates and examples for using the NAT Ignite matchmaking service. Use these templates to understand the required data formats and expected outputs.

## Template Files

### Input Templates

#### `participant_list_template.json`
Template for participant data input. Contains examples of 3 different participant profiles:
- **Technical Specialist**: Data scientist with strong ML background
- **Design Leader**: UX designer with leadership experience  
- **Research Expert**: Academic researcher with domain expertise

**Required Fields:**
- `participant_id`: Unique identifier (string)
- `name`: Full name (string) 
- `email`: Email address (string)
- `self_rated_skills`: Object with skill names and ratings 1-10
- `primary_roles`: Array of 1-3 roles
- `motivation`: Text description of interests/goals
- `availability_hours`: Available hours (15-40 typical)
- `ambiguity_comfort`: Comfort with undefined problems (1-10)
- `leadership_preference`: Boolean for leadership interest

**Supported Roles:**
- `developer`, `designer`, `product_manager`, `data_scientist`, `researcher`, `marketer`, `business_analyst`

#### `problem_list_template.json`
Template for problem/challenge data input. Contains examples of 3 different problem types:
- **Environmental Tech**: AI-powered energy management system
- **Social Impact**: Accessibility assistant mobile app
- **Business/FinTech**: Financial analytics dashboard

**Required Fields:**
- `problem_id`: Unique identifier (string)
- `title`: Problem title (string)
- `description`: Detailed problem description (string)
- `required_skills`: Object with skill names and minimum levels 1-10
- `required_roles`: Array of needed roles
- `estimated_hours`: Total work estimate (100-150 typical)
- `ambiguity_level`: How defined the problem is (1-10)
- `team_size`: Ideal team size (4-6 typical)

### Output Templates

#### `output_results_template.json`
Complete JSON structure of matchmaking results including:
- **Summary Statistics**: Participant/team/problem counts, completion rates
- **Individual Assignments**: Each participant's team and problem assignment
- **Team Details**: Full team composition with member info and AI scores
- **Phase Statistics**: Performance metrics for each matching phase
- **Quality Metrics**: Overall matching satisfaction and compliance

#### `output_results_template.csv`
Flattened CSV export format with key columns:
- Team information (ID, name, assigned problem)
- Team metrics (size, cost, diversity, skills coverage)
- Individual participants (ID, name, email, role, leader status)
- Participant skills (top 3 skills with levels)

## Usage Instructions

### 1. Prepare Your Data

**Create Participant File:**
```bash
cp templates/participant_list_template.json my_participants.json
# Edit my_participants.json with your actual participant data
# Remove _comment fields before using
```

**Create Problem File:**
```bash
cp templates/problem_list_template.json my_problems.json  
# Edit my_problems.json with your actual problem data
# Remove _comment fields before using
```

### 2. Run Matchmaking

```bash
python matchmaking_service_test.py --participants my_participants.json --problems my_problems.json
```

### 3. View Results

- **Dashboard**: http://localhost:3000
- **API Results**: http://localhost:8000/api/match/results
- **Export CSV**: http://localhost:8000/api/export?format=csv

## Data Requirements

### Participant Guidelines
- **Team Size**: System enforces exactly 5 members per team
- **Leadership**: ~20% of participants should have `leadership_preference: true`
- **Skills**: Include 3-8 relevant skills rated 1-10
- **Roles**: Select 1-3 primary roles per participant
- **Diversity**: Include mix of technical and non-technical backgrounds

### Problem Guidelines  
- **Team Size**: Specify `team_size: 5` for optimal matching
- **Skills**: Include 4-8 required skills with minimum levels
- **Roles**: Specify 3-4 required roles for balanced teams
- **Scope**: Problems should be hackathon-appropriate (2-3 day projects)

### Optimal Ratios
- **Participants to Problems**: 10-15 participants per problem
- **Total Team Count**: Participants ÷ 5 (due to fixed team size)
- **Problem Coverage**: Each problem gets exactly 1 team

## Validation Rules

The system validates:
- ✅ All required fields present
- ✅ Skill ratings within 1-10 range
- ✅ Valid role names from supported list
- ✅ Email format correctness
- ✅ Positive availability hours
- ✅ Ambiguity comfort within 1-10 range

## Example Commands

```bash
# Basic usage
python matchmaking_service_test.py -p participants.json -pr problems.json

# With custom timeout
python matchmaking_service_test.py -p participants.json -pr problems.json --timeout 600

# Skip database clearing (append to existing data)
python matchmaking_service_test.py -p participants.json -pr problems.json --skip-clear

# Dry run (load data only, no matching)
python matchmaking_service_test.py -p participants.json -pr problems.json --dry-run

# Help and options
python matchmaking_service_test.py --help
```

## Troubleshooting

### Common Issues

**File Format Errors:**
- Ensure valid JSON syntax (use JSON validator)
- Remove all `_comment` fields before running
- Check for trailing commas in JSON

**Data Validation Errors:**
- Verify all required fields are present
- Check skill ratings are 1-10 integers
- Ensure role names match supported list
- Validate email addresses format

**Matching Failures:**
- Ensure sufficient participants (minimum 10 per problem)
- Check backend services are running (`docker compose up`)
- Verify OpenAI API key in environment

**Poor Results:**
- Review skill-problem alignment
- Ensure role diversity in participant pool
- Check ambiguity comfort levels match problem types
- Verify leadership distribution (~20%)

## Support

For issues with the matchmaking service:
1. Check the comprehensive README.md in the project root
2. Verify all services are running with health checks
3. Review logs with `docker compose logs`
4. Test with the provided example data first 