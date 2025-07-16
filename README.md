# NAT Ignite Matchmaker

A sophisticated automated team formation system for NAT Ignite 2025. This system uses advanced algorithms including the Hungarian method and k-medoids clustering to optimally match participants into balanced teams and assign them to appropriate problems.

## Features

- **3-Phase Matching Algorithm**: Advanced participant-to-problem assignment, team formation, and final team-problem matching
- **Hungarian Algorithm**: Optimal assignment using cost matrices
- **K-Medoids Clustering**: Sophisticated team formation with role and skill balance
- **AI-Powered Analysis**: OpenAI integration for team composition evaluation
- **Modern Web Dashboard**: React/TypeScript frontend for visualization and management
- **Real-time Processing**: Celery-based background task processing
- **Export Capabilities**: JSON and CSV export for results

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 16+ (for dashboard development)
- OpenAI API key

### Setup

1. **Clone and configure environment:**
   ```bash
   git clone <repository-url>
   cd nat_ignite_matchmaker
   cp env.example .env
   # Add your OPENAI_API_KEY to .env file
   ```

2. **Start the backend services:**
   ```bash
   docker compose up --build
   ```

3. **Start the dashboard (development):**
   ```bash
   cd dashboard
   npm install
   npm run dev
   ```

4. **Access the application:**
   - Dashboard: `http://localhost:3000`
   - API Documentation: `http://localhost:8000/docs`
   - API Server: `http://localhost:8000`

## Architecture

### Backend Services

- **FastAPI** (`localhost:8000`): REST API server
- **MongoDB** (`localhost:27017`): Primary database
- **Redis** (`localhost:6379`): Task queue and caching
- **Celery Worker**: Background task processing

### Core Components

```
app/
├── api/           # REST API endpoints
├── matching/      # Core matching algorithms
├── llm/          # OpenAI integration
├── models.py     # Database schemas
└── worker/       # Celery task definitions

dashboard/
├── src/
│   ├── components/  # React components
│   ├── types.ts    # TypeScript interfaces
│   └── api.ts      # API client
└── package.json

tests/
├── e2e/           # End-to-end tests
├── fixtures/      # Test data
└── test_*.py      # Unit tests
```

## How It Works

### Phase 1: Individual-Problem Assignment

Participants are initially assigned to problem groups using a weighted cost function:

- **Skill Gap** (35%): Measures alignment between participant skills and problem requirements
- **Role Alignment** (20%): Matches preferred roles with problem needs
- **Motivation Similarity** (15%): Uses semantic embeddings to match interests
- **Ambiguity Tolerance** (20%): Aligns comfort with undefined problem aspects
- **Workload Capacity** (10%): Matches availability with time requirements

### Phase 2: Team Formation

Within each problem group, participants are formed into optimal teams using:

- **K-Medoids Clustering**: Groups participants with complementary skills
- **Role Balance Enforcement**: Ensures diverse role representation
- **Skill Coverage Optimization**: Maximizes unique skills per team
- **Hungarian Assignment**: Fills remaining slots optimally

### Phase 3: Team-Problem Assignment

Final teams are assigned to specific problems using:

- **Team Vector Aggregation**: Converts teams to single representative vectors
- **Hungarian Algorithm**: Optimal one-to-one team-problem matching
- **Global Cost Minimization**: Achieves best overall assignment

## API Usage

### Starting the Matching Process

```bash
# Phase 1: Individual assignment
curl -X POST http://localhost:8000/api/simple/phase1

# Phase 2: Team formation  
curl -X POST http://localhost:8000/api/simple/phase2

# Phase 3: Final assignment
curl -X POST http://localhost:8000/api/simple/phase3

# Check status
curl http://localhost:8000/api/simple/status
```

### Retrieving Results

```bash
# Get all teams
curl http://localhost:8000/api/dashboard/teams/detailed

# Get participants
curl http://localhost:8000/api/dashboard/participants

# Get problems
curl http://localhost:8000/api/dashboard/problems/detailed

# Export data
curl http://localhost:8000/api/export/teams
```

## Dashboard Features

### Overview Tab
- Summary statistics and system status
- Quick action buttons for common tasks
- Real-time matching progress

### Participants Tab
- Searchable participant list with skills and roles
- Individual participant detail modals
- Assignment status tracking

### Problems Tab
- Problem gallery with categories and difficulty
- Detailed requirement specifications
- Team assignment status

### Teams Tab
- Team composition with member details
- Skill coverage and diversity metrics
- AI-generated team analysis
- Manual editing capabilities

### Statistics Tab
- Performance metrics across all phases
- Cost analysis and efficiency measures
- Historical trend tracking

## Testing

The project includes comprehensive test coverage:

```bash
# Run all tests
pytest tests/

# Run specific test categories
pytest tests/test_hungarian.py      # Algorithm tests
pytest tests/test_teamflow.py       # Team formation tests
pytest tests/e2e/                  # End-to-end tests
```

### Test Data Generation

```bash
# Generate synthetic test data
python tools/generate_demo_data.py --participants 200 --problems 15

# Run full pipeline test
python -m pytest tests/e2e/test_full_rehearsal.py -v
```

## Configuration

### Environment Variables

Create a `.env` file with:

```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional (defaults provided)
MONGODB_URI=mongodb://localhost:27017/nat_ignite_matchmaker
REDIS_URL=redis://localhost:6379
PINECONE_API_KEY=dummy_for_local_dev
PINECONE_ENV=us-east-1
```

### Algorithm Tuning

Modify matching weights in `app/config.py`:

```python
# Phase 1 weights (individual assignment)
PHASE1_WEIGHTS = {
    "skill_gap": 0.35,
    "role_alignment": 0.20,
    "motivation_similarity": 0.15,
    "ambiguity_fit": 0.20,
    "workload_fit": 0.10
}

# Team formation parameters
TEAM_SIZE_TARGET = 5
TEAM_SIZE_MIN = 3
TEAM_SIZE_MAX = 7
```

## Production Deployment

### Docker Production

```bash
# Build production images
docker compose -f docker-compose.prod.yml up --build

# Scale workers
docker compose -f docker-compose.prod.yml up --scale worker=3
```

### Dashboard Production Build

```bash
cd dashboard
npm run build
# Serve dist/ folder with your preferred web server
```

## Troubleshooting

### Common Issues

**Backend won't start:**
- Check that MongoDB and Redis are running
- Verify environment variables in `.env`
- Check logs: `docker compose logs api`

**Dashboard shows errors:**
- Ensure backend is running on `localhost:8000`
- Check browser console for specific errors
- Verify API endpoints are accessible

**Matching fails:**
- Check OpenAI API key is valid
- Verify sufficient participant and problem data
- Monitor Celery worker logs

**Performance issues:**
- Increase Docker memory allocation
- Scale Celery workers
- Optimize database indices

### Debugging Commands

```bash
# Check system health
curl http://localhost:8000/health

# View database status
docker compose exec mongo mongosh nat_ignite_matchmaker

# Monitor Celery tasks
docker compose logs worker -f

# Test API endpoints
curl http://localhost:8000/api/simple/status
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass: `pytest tests/`
5. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Support

For questions or issues:
1. Check the troubleshooting section above
2. Review the API documentation at `http://localhost:8000/docs`
3. Examine test files in `tests/` for usage examples
4. Open an issue on GitHub for bugs or feature requests 