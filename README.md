# NAT Ignite Matchmaker

Automated matchmaking service for NAT Ignite 2025.

## Local Development

To launch the local development stack, you will need Docker and Docker Compose installed.

1.  Create a `.env` file from the example:
    ```bash
    cp env.example .env
    ```
2.  Add your OpenAI API key to the `.env` file.
3.  Build and run the services:
    ```bash
    docker compose up --build
    ```

This will start the following services:
-   **MongoDB:** `localhost:27017`
-   **Redis:** `localhost:6379`
-   **FastAPI:** `localhost:8000`
-   **Celery Worker:** Processes background tasks.

The API documentation will be available at `http://localhost:8000/docs`. 

## Stage One: Preliminary Matching

The first stage of the matching process creates preliminary clusters of participants who are good fits for the same problems. It works as follows:

1.  **Cost Matrix Construction:** A cost is calculated for each participant-problem pair using a weighted formula.
2.  **Assignment:** The Hungarian algorithm is used to assign each participant to a problem slot, minimizing the total cost across all assignments.

### Cost Function

The cost function is a weighted sum of five terms:

| Term                  | Weight | Description                                                                 |
| --------------------- | ------ | --------------------------------------------------------------------------- |
| Skill Gap             | 0.35   | The average gap between the participant's skills and the problem's needs.   |
| Role Alignment        | 0.20   | How well the participant's preferred roles match the problem's needs.         |
| Motivation Similarity | 0.15   | The cosine similarity between the participant and problem motivation vectors. |
| Ambiguity Fit         | 0.20   | The difference in tolerance for ambiguity between participant and problem.    |
| Workload Fit          | 0.10   | The difference between the participant's availability and the estimated load. |

### Running Stage One

To trigger the Stage One matching process, send a POST request to the `/api/match/stage1` endpoint:

```bash
curl -X POST http://localhost:8000/api/match/stage1
```

This will return a task ID:

```json
{
  "task_id": "a-celery-task-id",
  "status": "started"
}
```

You can monitor the progress of the task by connecting to the status stream:

```bash
curl http://localhost:8000/api/match/stage1/status
```

## Stage Two: Internal Team Formation

The second stage refines the preliminary clusters into final teams using sophisticated clustering and optimization algorithms:

1. **K-Medoids Clustering:** Each preliminary cluster is subdivided using k-medoids with PAM initialization
2. **Slot Optimization:** Linear assignment is used to fill remaining team slots while enforcing role coverage constraints
3. **Coverage Metrics:** Each team is evaluated on diversity, skill coverage, and role balance

### Pairwise Cost Function

The internal team formation uses a pairwise cost function between participants:

```
Cost = 0.4 × role_diversity_penalty + 0.3 × skill_overlap_penalty + 0.3 × comm_style_clash - 0.2 × motivation_similarity
```

Where:
- **Role Diversity Penalty:** Penalty for lack of role compatibility (0-1)
- **Skill Overlap Penalty:** Penalty for excessive overlap in high-skill areas (0-1)  
- **Communication Style Clash:** Mismatch in availability and communication patterns (0-1)
- **Motivation Similarity:** Cosine similarity bonus for aligned motivations (0-1)

### Team Metrics

Each final team is evaluated on:

| Metric | Description | Range |
|--------|-------------|-------|
| `skills_covered` | Ratio of unique skills to team size | 0-10+ |
| `diversity_score` | Average of role and skill diversity | 0-1 |
| `confidence_score` | Average skill proficiency level | 0-1 |
| `role_balance_flag` | No single role dominates >60% of team | Boolean |
| `role_coverage` | Fraction of total roles represented | 0-1 |

### Running Stage Two

After Stage One completes, trigger Stage Two matching:

```bash
curl -X POST http://localhost:8000/api/match/phase2
```

Monitor progress and view team summaries:

```bash
curl http://localhost:8000/api/match/phase2/status
```

### Example Final Team Output

```json
{
  "team_id": "team_1",
  "members": [
    {
      "participant_id": "507f1f77bcf86cd799439011",
      "name": "Alice Johnson",
      "email": "alice@example.com",
      "primary_roles": ["developer", "designer"],
      "availability_hours": 30
    },
    {
      "participant_id": "507f1f77bcf86cd799439012",
      "name": "Bob Smith",
      "email": "bob@example.com", 
      "primary_roles": ["product_manager"],
      "availability_hours": 25
    }
  ],
  "team_size": 4,
  "skills_covered": 0.75,
  "diversity_score": 0.82,
  "confidence_score": 0.68,
  "role_balance_flag": true,
  "role_coverage": 0.67
}
```

## Stage Three: Final Team-to-Problem Assignment

The third and final stage assigns completed teams to specific problems using optimal matching algorithms:

1. **Team Vector Aggregation:** Each team is converted into a single vector representation
2. **Cost Matrix Construction:** Team-problem costs are calculated using the same five-term formula
3. **Hungarian Algorithm:** Optimal one-to-one assignment minimizes total cost
4. **Assignment Storage:** Final mappings are stored with comprehensive statistics

### Team Vector Fields

Each team is aggregated into a `TeamVector` with the following fields:

| Field | Description | Aggregation Method |
|-------|-------------|-------------------|
| `avg_skill_levels` | Average posterior skill means per skill | Mean across team members |
| `role_weights` | Normalized role distribution | Count-based weights summing to 1.0 |
| `min_availability` | Team capacity bottleneck | Minimum member availability |
| `avg_motivation_embedding` | Team motivation vector | Element-wise mean of embeddings |
| `avg_communication_style` | Communication preference | Availability-based proxy (0-1) |
| `avg_ambiguity_tolerance` | Ambiguity handling preference | Mean tolerance across members |
| `avg_confidence_score` | Overall skill confidence | Mean normalized skill levels |

### Team-Problem Cost Function

The exact cost function equation for team-to-problem assignment is:

```
Cost = 0.35 × skill_gap + 0.20 × role_alignment + 0.15 × motivation_similarity + 0.20 × ambiguity_fit + 0.10 × workload_fit
```

Where:
- **Skill Gap:** Average gap between team skills and problem requirements
- **Role Alignment:** 1 - (team_role_weights · problem_role_preferences)
- **Motivation Similarity:** Cosine distance between team and problem embeddings
- **Ambiguity Fit:** |team_ambiguity_tolerance - problem_ambiguity|
- **Workload Fit:** max(0, required_hours - team_min_availability) / 40

### Running Stage Three

After Stage Two completes, trigger final assignment:

```bash
curl -X POST http://localhost:8000/api/match/phase3
```

Monitor progress and view assignment results:

```bash
curl http://localhost:8000/api/match/phase3/status
```

### Example Assignment Output

```json
{
  "assignment_id": "507f1f77bcf86cd799439020",
  "assignments": {
    "problem_507f1f77bcf86cd799439013": "team_1",
    "problem_507f1f77bcf86cd799439014": "team_2",
    "problem_507f1f77bcf86cd799439015": "team_3"
  },
  "statistics": {
    "assignment_count": 3,
    "total_cost": 2.45,
    "mean_cost": 0.82,
    "worst_case_cost": 1.15,
    "best_case_cost": 0.67,
    "assignment_efficiency": 0.84
  },
  "timestamp": "2025-01-27T10:30:00Z"
}
```

### Troubleshooting Assignment Diagnostics

#### Interpreting `worst_case_cost`

The `worst_case_cost` indicates the highest individual team-problem assignment cost. High values suggest:

- **> 2.0:** Significant skill gaps or role mismatches
- **> 3.0:** Major incompatibilities - consider team rebalancing
- **> 4.0:** Critical issues - manual intervention recommended

#### Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| High skill gaps | `mean_cost` dominated by skill_gap component | Add participants with missing skills |
| Role mismatches | Low `assignment_efficiency` | Adjust team role distributions |
| Workload imbalance | High workload_fit costs | Balance team availability hours |
| Motivation divergence | High motivation_similarity costs | Review problem descriptions |

#### Assignment Efficiency Interpretation

- **> 0.8:** Excellent assignments with good matches
- **0.6-0.8:** Acceptable assignments with minor issues
- **0.4-0.6:** Problematic assignments requiring review
- **< 0.4:** Poor assignments - consider rerunning previous stages 