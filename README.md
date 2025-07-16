# NAT Ignite Matchmaker

An intelligent team formation system for NAT Ignite 2025 that automatically matches participants to problems and forms optimal teams using advanced algorithms and AI-powered optimization.

## Overview

The NAT Ignite Matchmaker is a three-phase system that:
1. **Phase 1**: Matches individual participants to problems using cost optimization
2. **Phase 2**: Forms teams from participants assigned to the same problems
3. **Phase 3**: Assigns teams to final problems using the Hungarian algorithm

The system includes a modern React dashboard for visualization and manual overrides.

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- Docker & Docker Compose
- OpenAI API key

### Setup

1. **Clone and configure environment:**
   ```bash
   git clone <your-repo-url>
   cd nat_ignite_matchmaker
   cp env.example .env
   # Add your OPENAI_API_KEY to .env
   ```

2. **Start the system:**
   ```bash
   docker compose up --build
   ```

3. **Access the services:**
   - **Backend API**: http://localhost:8000 (FastAPI docs: /docs)
   - **Dashboard**: http://localhost:3000
   - **MongoDB**: localhost:27017
   - **Redis**: localhost:6379

### Running a Complete Matching Process

1. **Load test data and run matching:**
   ```bash
   python setup_and_test.py --size huge  # For 200 participants
   ```

2. **Or run phases individually:**
   ```bash
   curl -X POST http://localhost:8000/api/match/phase1
   curl -X POST http://localhost:8000/api/match/phase2  
   curl -X POST http://localhost:8000/api/match/phase3
   ```

3. **View results in the dashboard** at http://localhost:3000

## System Architecture

### Backend Services
- **FastAPI Application** (`app/`): Core matching logic and REST API
- **MongoDB**: Stores participants, problems, teams, and assignments
- **Redis**: Caches intermediate results and manages task queues
- **Celery Worker**: Processes background matching tasks

### Frontend Dashboard
- **React/TypeScript** (`dashboard/`): Modern UI for visualization
- **Tailwind CSS**: Clean, responsive styling
- **Parcel**: Build tool for fast development

### Core Algorithms

#### Phase 1: Individual-Problem Matching
Uses a weighted cost function with the Hungarian algorithm:

| Component | Weight | Description |
|-----------|--------|-------------|
| Skill Gap | 0.35 | Gap between participant skills and problem requirements |
| Role Alignment | 0.20 | Match between preferred roles and needed roles |
| Motivation Similarity | 0.15 | Cosine similarity of motivation vectors |
| Ambiguity Tolerance | 0.20 | Comfort level with problem uncertainty |
| Workload Fit | 0.10 | Availability vs estimated time commitment |

#### Phase 2: Team Formation  
Forms teams from participants assigned to the same problem using:
- **Strict team size enforcement** (exactly 5 members per team)
- **Role diversity optimization** 
- **Skill complementarity analysis**
- **Leadership assignment** (20% of participants marked as leaders)

#### Phase 3: Team-Problem Assignment
Final assignment of formed teams to problems using the Hungarian algorithm with team-problem cost matrices.

## API Endpoints

### Core Matching
- `POST /api/match/phase1` - Run individual-problem matching
- `POST /api/match/phase2` - Form teams from assignments  
- `POST /api/match/phase3` - Assign teams to problems
- `GET /api/match/results` - Get complete matching results
- `GET /api/match/status` - Check current status

### Data Management
- `GET /api/participants` - List all participants
- `GET /api/problems` - List all problems
- `GET /api/teams` - List all teams
- `POST /api/participants` - Add new participants
- `POST /api/problems` - Add new problems

### Export & Analytics
- `GET /api/export?format=json|csv` - Export results
- `GET /api/stats` - Get matching statistics
- `GET /api/dashboard` - Dashboard data endpoint

## Dashboard Features

### Visualization Tabs
- **Overview**: Summary statistics and quick actions
- **Participants**: Searchable participant list with assignments
- **Problems**: Problem details and requirements
- **Teams**: Team composition with AI-powered insights
- **Statistics**: Comprehensive performance metrics

### Team Management
- **Manual Editor**: Drag-and-drop interface for team reassignment
- **AI Suggestions**: Intelligent recommendations for team optimization  
- **Export Tools**: Download results in multiple formats
- **Real-time Updates**: Live statistics and status monitoring

### Key Features
- Clean, modern interface following design preferences
- Search and filter capabilities across all data
- Detailed cost explanations and help tooltips
- Individual team AI feedback for role balance
- Leadership indicators and skill visualization

## Development

### Running Tests
```bash
# Run core algorithm tests
python -m pytest tests/ -v

# Test matching pipeline
python setup_and_test.py --test
```

### Development Mode
```bash
# Backend development
cd app && uvicorn main:app --reload --port 8000

# Frontend development  
cd dashboard && npm run dev
```

### Adding New Features
1. Backend changes in `app/` (FastAPI, matching algorithms)
2. Frontend changes in `dashboard/src/` (React components)
3. Database models in `app/models.py`
4. API endpoints in `app/api/`

## Configuration

### Environment Variables
```bash
OPENAI_API_KEY=your_openai_key_here
PINECONE_API_KEY=dummy_for_local_dev
PINECONE_ENV=us-east-1
MONGODB_URL=mongodb://localhost:27017
REDIS_URL=redis://localhost:6379
```

### Matching Parameters
Key tunable parameters in `app/config.py`:
- Team size requirements (default: 5 members)
- Cost function weights
- Algorithm selection (Hungarian, strict enforcement)
- AI scoring thresholds

## Data Format

### Participant Schema
```json
{
  "participant_id": "unique_id",
  "name": "Full Name", 
  "email": "email@domain.com",
  "self_rated_skills": {"python": 8, "design": 6},
  "primary_roles": ["developer", "designer"],
  "motivation": "text description",
  "availability_hours": 30,
  "ambiguity_comfort": 7,
  "leadership_preference": false
}
```

### Problem Schema  
```json
{
  "problem_id": "unique_id",
  "title": "Problem Title",
  "description": "Detailed description", 
  "required_skills": {"python": 6, "design": 8},
  "required_roles": ["developer", "designer"],
  "estimated_hours": 120,
  "ambiguity_level": 6,
  "team_size": 5
}
```

## Troubleshooting

### Common Issues
1. **OpenAI API errors**: Verify API key in `.env` file
2. **Database connection**: Ensure MongoDB is running on port 27017
3. **Frontend build errors**: Check Node.js version (16+ required)
4. **Empty teams**: Verify participant data has required fields

### Logs and Debugging
- Backend logs: `docker compose logs app`
- Celery worker logs: `docker compose logs worker`  
- Frontend console: Browser developer tools
- Database queries: MongoDB Compass on localhost:27017

## Production Deployment

The system is designed for containerized deployment:

```bash
# Build production images
docker compose -f docker-compose.prod.yml build

# Deploy with environment variables
export OPENAI_API_KEY=your_production_key
docker compose -f docker-compose.prod.yml up -d
```

Ensure production environment has:
- Persistent MongoDB storage
- Redis persistence configuration  
- Proper SSL termination
- Environment-specific API keys

## License

This project is developed for NAT Ignite 2025. Please contact the development team for usage permissions. 