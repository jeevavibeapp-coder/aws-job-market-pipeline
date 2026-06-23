# AI Job Intelligence Platform

> **Mission:** Find the best jobs matching your profile with minimum manual effort.

This is NOT another LinkedIn clone. It's an AI-powered job search platform built for quality over quantity — it finds real jobs from company career pages and trusted sources, filters them with LLM intelligence, and surfaces only the most relevant opportunities.

---

## Features

### Smart Job Discovery
- Aggregates jobs from **Greenhouse**, **Lever**, **Workday**, **JSearch**, **Indeed**, **LinkedIn**
- Prioritizes **direct company career page** URLs over third-party platforms
- Runs continuously via Celery background workers

### AI Filtering Engine
- LLM-powered semantic skill matching (not just keyword search)
- Intelligent **experience matching** with configurable tolerance
  - `≤ user_exp + 1yr` → Accept
  - `≤ user_exp + 2yr` → Accept with warning
  - `> user_exp + 2yr` → Auto-reject
- Per-job **AI Score (0–100)** across 5 dimensions

### Job Scoring Dimensions
| Dimension | Weight |
|---|---|
| Skill Match | 35% |
| Experience Match | 25% |
| Technology Match | 20% |
| Location Match | 10% |
| Seniority Match | 10% |

Only jobs scoring **70+** are shown by default.

### Source Priority
1. Company Career Site
2. Greenhouse
3. Lever
4. Workday
5. Indeed
6. LinkedIn

### Freshness Engine
- Filter by: 24h / 3d / 7d / 14d
- Default: **24 hours**

### Competition Score
- Estimated 1–100 based on applicant count and posting age
- Filter for **low competition** jobs

### Duplicate Detection
- Cross-platform deduplication using title + company + description similarity
- Keeps the highest-priority source version

### Resume Intelligence
- Upload PDF or DOCX resume
- AI extracts skills, experience years, certifications, projects
- Automatically improves job recommendations

### Application Tracker
- CRM-style pipeline: Saved → Applied → Interview → Offer → Rejected
- Full history and notes

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Browser                                │
│                    Next.js 14 (App Router)                      │
│              TypeScript · Tailwind · shadcn/ui                  │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API
┌────────────────────────────▼────────────────────────────────────┐
│                       FastAPI Backend                           │
│            JWT Auth · Async SQLAlchemy · Pydantic               │
├─────────────────┬───────────────────┬───────────────────────────┤
│   AI Services   │   Job Sources     │   Background Workers      │
│                 │                   │                           │
│ • LLM Scorer   │ • Greenhouse      │ • Celery (scrape)         │
│ • AI Filter    │ • Lever           │ • Celery (score)          │
│ • Resume Parser│ • Workday         │ • Celery Beat (schedule)  │
│ • NL Search    │ • JSearch API     │                           │
└────────┬────────┴────────┬──────────┴───────────────────────────┘
         │                 │
┌────────▼────────┐ ┌──────▼──────────┐
│   PostgreSQL    │ │     Redis        │
│  (primary DB)   │ │  (cache+queue)   │
└─────────────────┘ └─────────────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Python 3.11, Pydantic v2 |
| Database | PostgreSQL 16, SQLAlchemy 2.0, Alembic |
| Cache / Queue | Redis 7, Celery 5 |
| AI | OpenAI GPT-4o-mini, Anthropic Claude |
| Storage | AWS S3 (resumes) |
| Containers | Docker, Docker Compose |
| Deployment | AWS ECS (backend), AWS Amplify (frontend) |

---

## Quick Start

### Prerequisites
- Docker + Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.11+ (for local backend dev)

### 1. Clone & configure
```bash
git clone https://github.com/jeevavibeapp-coder/aws-job-market-pipeline.git
cd aws-job-market-pipeline
cp .env.example .env
# Edit .env — add your API keys
```

### 2. Start everything
```bash
docker compose up --build
```

### 3. Run migrations
```bash
docker compose exec backend alembic upgrade head
```

### 4. Open the app
- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- API health: http://localhost:8000/health

---

## Database Schema

```
users              — accounts, auth
companies          — employer profiles
jobs               — job listings (all sources)
job_scores         — AI scores per job+user
applications       — user application tracker
bookmarks          — saved jobs
resume_profiles    — parsed resume data
search_history     — past searches
notifications      — alerts for new matching jobs
```

## API Endpoints

```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
GET    /api/v1/auth/me

POST   /api/v1/search          — AI-powered job search
POST   /api/v1/search/natural  — natural language search

GET    /api/v1/jobs            — list/filter jobs
GET    /api/v1/jobs/{id}       — job detail + AI insight
GET    /api/v1/jobs/{id}/similar

GET    /api/v1/applications
POST   /api/v1/applications
PUT    /api/v1/applications/{id}
GET    /api/v1/applications/stats

GET    /api/v1/bookmarks
POST   /api/v1/bookmarks/{job_id}
DELETE /api/v1/bookmarks/{job_id}

POST   /api/v1/resume/upload
GET    /api/v1/resume
PUT    /api/v1/resume/profile
```

## Development

### Backend only
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend only
```bash
cd frontend
npm install
npm run dev
```

## Deployment

### AWS ECS (Backend)
- Build Docker image: `docker build -t job-intelligence-backend ./backend`
- Push to ECR, update ECS service
- RDS PostgreSQL + ElastiCache Redis for managed services

### AWS Amplify (Frontend)
- Connect GitHub repo, set env vars, auto-deploy on push
- Set `NEXT_PUBLIC_API_URL` to your ECS backend URL

---

## Roadmap

- [ ] Phase 1 (current): Core platform — auth, search, AI filter, tracker
- [ ] Phase 2: Browser extension for one-click job save
- [ ] Phase 3: Email alerts for new matching jobs
- [ ] Phase 4: Auto-apply with AI-tailored cover letters
- [ ] Phase 5: Interview prep based on job description
