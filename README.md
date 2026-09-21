# SIH 2026 — TRANSITION

### University–Industry Problem-Solving Platform

TRANSITION is a crowdsourced societal problem-solving platform that connects **Citizens, Students, and Industry** to identify real-world community issues, develop solutions, evaluate them, and support their implementation.

The backend is built with **FastAPI, PostgreSQL/Supabase, SQLAlchemy, Supabase Auth, Alembic, and Docker**, with a separate ML service for image-based issue classification.

---

## 🚀 Live API

The FastAPI backend is deployed on Render.

- **API Base URL:** https://sih-a24k.onrender.com
- **Interactive Swagger Docs:** https://sih-a24k.onrender.com/docs
- **OpenAPI JSON:** https://sih-a24k.onrender.com/openapi.json

Use the Swagger UI to explore and test the deployed API endpoints.

---

## 🔄 Complete Workflow

```
Citizen
  │
  │ Report issue + location + media
  ▼
Issue Created
  │
  ▼
AI / ML Classification
  │
  │ category + confidence + priority
  ▼
Issue Verification
  │
  ▼
Students Discover Issue
  │
  ▼
Student Application
  │
  ▼
Application Accepted
  │
  ▼
Student Assigned
  │
  ▼
Progress / Evidence
  │
  ▼
Solution Submitted
  │
  ▼
Industry Review
  │
  ▼
Industry Sponsorship / Support
  │
  ▼
Evaluation
  │
  ▼
Issue Resolved
```

Notifications are intentionally outside the current prototype scope.

---

## 🛠️ Technology Stack

### Backend
- **Framework:** FastAPI
- **Language:** Python 3.13
- **ORM:** SQLAlchemy 2.0
- **Database:** PostgreSQL
- **Database Hosting:** Supabase
- **Authentication:** Supabase Auth / Bearer JWT
- **Validation:** Pydantic v2
- **Migrations:** Alembic
- **Testing:** Pytest + HTTPX TestClient
- **Containerization:** Docker / Docker Compose
- **Deployment:** Render

### AI / ML
- Separate ML classification service
- Image-based societal issue classification
- Returns category, confidence, and priority information to the backend

The ML service is maintained separately from this repository.

---

## 🏛️ Architecture

The backend follows a layered architecture:

```
Flutter / Frontend
       │
       ▼
    FastAPI
       │
       ├── Routers
       │
       ├── Services
       │
       ├── SQLAlchemy Models
       │
       ▼
   PostgreSQL
    (Supabase)

       │
       └──────────────► ML Classification Service
```

Project structure:

```
SIH/
├── alembic/
│   ├── versions/
│   └── env.py
├── app/
│   ├── auth.py
│   ├── database.py
│   ├── main.py
│   ├── models/
│   ├── schemas/
│   ├── services/
│   └── routers/
│       ├── profile.py
│       ├── issue.py
│       ├── application.py
│       ├── evidence.py
│       ├── solution.py
│       ├── sponsorship.py
│       └── dashboard.py
├── tests/
│   ├── conftest.py
│   ├── test_profile.py
│   ├── test_sih_workflow.py
│   └── test_transition_workflow.py
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## 👥 Role-Based Access Control

The platform supports four roles:

### Citizen
- Report societal issues
- Attach issue media
- Provide location information
- Verify/manage reported issues
- Review student applications
- Track issue progress
- Participate in resolution workflow

### Student
- Discover verified issues
- Apply to work on issues
- View assigned issues
- Upload progress/evidence
- Submit solution proposals
- Manage their own applications

### Industry / Industrialist
- Review submitted solutions
- Provide ratings and feedback
- View project progress
- Sponsor/support issues

### Admin
- Administrative access across the platform

Authentication and role authorization are handled through the existing Supabase Auth integration and RBAC dependencies.

---

# 📡 API Endpoints

## Health & Authentication

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Root health check |
| GET | `/me` | Get authenticated user information |

---

## 👤 Profiles

| Method | Endpoint | Description |
|---|---|---|
| GET | `/profiles/me` | Get current profile |
| POST | `/profiles` | Create profile |
| POST | `/profiles/me` | Create current user's profile |
| PATCH | `/profiles/me` | Update current profile |
| PUT | `/profiles/me` | Replace/update current profile |

Supported roles include `citizen`, `student`, `industrialist`, and `admin`.

---

## 🏙️ Issues

| Method | Endpoint | Description |
|---|---|---|
| POST | `/issues` | Create a societal issue |
| GET | `/issues` | List/filter issues |
| GET | `/issues/{issue_id}` | Get issue details |
| PATCH | `/issues/{issue_id}` | Update issue |
| DELETE | `/issues/{issue_id}` | Delete issue |
| GET | `/issues/me/reported` | Get issues reported by current user |
| GET | `/issues/me/assigned` | Get issues assigned to current student |
| POST | `/issues/{issue_id}/media` | Attach issue media URL |

Issue listing supports:

- Pagination
- Category filtering
- Status filtering
- Geographic bounding-box filtering using latitude/longitude

---

## 🎓 Student Applications & Assignment

| Method | Endpoint | Description |
|---|---|---|
| POST | `/issues/{issue_id}/applications` | Student applies to solve an issue |
| GET | `/issues/{issue_id}/applications` | List applications for an issue |
| GET | `/applications/me` | Get current student's applications |
| PATCH | `/applications/{application_id}` | Update application status |
| POST | `/issues/{issue_id}/assign` | Assign an applicant student to an issue |

Application workflow:

```
PENDING
   ├── ACCEPTED
   ├── REJECTED
   └── WITHDRAWN
```

Accepting an application can assign the student to the issue and move the issue into the implementation workflow.

---

## 📸 Progress & Evidence

| Method | Endpoint | Description |
|---|---|---|
| POST | `/issues/{issue_id}/evidence` | Add progress/evidence |
| GET | `/issues/{issue_id}/evidence` | List issue evidence |
| DELETE | `/evidence/{evidence_id}` | Delete evidence |

Evidence can represent:

- Progress milestones
- Before/after media
- Documentation
- Other supporting evidence

Only appropriately authorized users can create, view, or delete evidence.

---

## 💡 Solutions

| Method | Endpoint | Description |
|---|---|---|
| POST | `/issues/{issue_id}/solutions` | Submit a solution |
| GET | `/issues/{issue_id}/solutions` | List solutions for an issue |
| GET | `/solutions/{solution_id}` | Get solution details |
| PATCH | `/solutions/{solution_id}` | Update solution |

Solutions support prototype/documentation information and integrate with the industry review workflow.

---

## 🏢 Industry Reviews

| Method | Endpoint | Description |
|---|---|---|
| POST | `/solutions/{solution_id}/reviews` | Submit industry review |
| GET | `/solutions/{solution_id}/reviews` | List reviews |

Industry reviews support:

- Rating
- Feedback
- Solution evaluation

---

## 💰 Industry Sponsorship

The prototype includes a lightweight sponsorship/pledge system. It does **not** process real payments.

| Method | Endpoint | Description |
|---|---|---|
| POST | `/issues/{issue_id}/sponsorships` | Create sponsorship pledge |
| GET | `/issues/{issue_id}/sponsorships` | List sponsorships |
| PATCH | `/sponsorships/{sponsorship_id}` | Update sponsorship |

Sponsorships can represent financial support, grants, materials, or other project support.

---

## 📊 Dashboards

| Method | Endpoint | Description |
|---|---|---|
| GET | `/dashboard/citizen` | Citizen issue overview |
| GET | `/dashboard/student` | Student applications, assignments, and solutions |
| GET | `/dashboard/industry` | Industry projects, sponsorships, and reviews |

These endpoints provide lightweight aggregated data for the Flutter dashboards.

---

# 🔄 Issue Lifecycle

The backend uses controlled issue states:

```
REPORTED
    ↓
AI_CLASSIFIED
    ↓
VERIFIED
    ↓
IN_PROGRESS
    ↓
SOLUTION_SUBMITTED
    ↓
EVALUATED
    ↓
RESOLVED
```

State changes are controlled by the appropriate role and workflow rather than allowing arbitrary users to jump directly between states.

---

# 🤖 ML Classification Integration

The backend contains a pluggable ML classifier service:

```
app/services/ml_classifier.py
```

The intended flow is:

```
Issue Media
     ↓
FastAPI
     ↓
ML Classification Service
     ↓
Category
Confidence
Priority
     ↓
Issue metadata updated
```

The ML model/service is maintained separately and can be connected through the classifier service abstraction without changing the core issue API.

---

# 📦 Media Storage

Media handling is abstracted through:

```
app/services/media_storage.py
```

The project supports Supabase Storage and a local storage implementation for development/testing.

Issue media is currently represented through stored media URLs, allowing the Flutter client and storage layer to determine the actual upload mechanism.

---

# 🗄️ Database & Migrations

The project uses PostgreSQL with SQLAlchemy and Alembic.

Run migrations:

```powershell
alembic upgrade head
```

Preview migration SQL:

```powershell
alembic upgrade head --sql
```

Database entities include:

- Profiles
- Issues
- Issue Media
- Applications
- Evidence
- Solutions
- Solution Reviews
- Sponsorships

---

# ⚙️ Environment Variables

Create a `.env` file in the project root.

Example:

```env
DATABASE_URL=postgresql://postgres:<PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres
SUPABASE_URL=https://<PROJECT_REF>.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_<KEY>
SIH_ML_SERVICE_URL=http://localhost:8001
```

Never commit real credentials or secrets to GitHub.

---

# 🏃 Run Locally

## 1. Install dependencies

Using uv:

```powershell
uv sync
```

Or with pip:

```powershell
pip install -r requirements.txt
```

## 2. Run migrations

```powershell
alembic upgrade head
```

## 3. Start FastAPI

```powershell
uvicorn app.main:app --reload --port 8000
```

Open:

**http://localhost:8000/docs**

---

# 🐳 Docker

Build and start the application:

```powershell
docker compose up -d --build
```

Check running containers:

```powershell
docker compose ps
```

View recent logs:

```powershell
docker compose logs --tail=100
```

Follow logs live:

```powershell
docker compose logs -f
```

After backend changes, use `--build` to ensure the Docker image contains the latest application code.

---

# 🧪 Testing

The project uses Pytest with isolated test fixtures and mocked authentication.

Run all tests:

```powershell
python -m pytest
```

Verbose output:

```powershell
python -m pytest -v
```

Run the main SIH workflow tests:

```powershell
python -m pytest tests/test_sih_workflow.py -v
```

Run the transition workflow tests:

```powershell
python -m pytest tests/test_transition_workflow.py -v
```

The test suite covers authentication, profiles, issue reporting, authorization, applications, assignment, evidence, solutions, industry reviews, sponsorships, dashboards, workflow transitions, and validation.

---

# 🌐 Deployment

The current backend deployment runs on **Render**:

**https://sih-a24k.onrender.com**

Swagger documentation:

**https://sih-a24k.onrender.com/docs**

The production database is hosted through Supabase PostgreSQL.

---

# 🎯 Current Prototype Scope

### Implemented

- [x] Supabase authentication
- [x] Role-based access control
- [x] Citizen profiles
- [x] Societal issue reporting
- [x] GPS/location support
- [x] Issue media references
- [x] Issue filtering and geographic queries
- [x] ML classifier integration layer
- [x] Student applications
- [x] Student assignment
- [x] Progress/evidence tracking
- [x] Student solution submission
- [x] Industry reviews
- [x] Industry sponsorship/pledges
- [x] Role-specific dashboards
- [x] Controlled issue lifecycle
- [x] Automated tests
- [x] Docker support
- [x] Render deployment

### Intentionally out of scope for the current prototype

- [ ] Notifications
- [ ] Real payment gateway
- [ ] Production-grade file upload pipeline beyond the current media URL/storage architecture
- [ ] Advanced analytics
- [ ] Complex assignment history

---

# 🧭 Next Integration Layer

The backend is designed to be consumed by the Flutter frontend.

Expected client flow:

```
Flutter
   │
   ├── Authentication
   │
   ├── Citizen Dashboard
   │       └── Report Issue
   │
   ├── Map / Issue Discovery
   │
   ├── Student Dashboard
   │       ├── Applications
   │       ├── Assigned Issues
   │       ├── Evidence
   │       └── Solutions
   │
   └── Industry Dashboard
           ├── Reviews
           └── Sponsorship
```

---

## 📄 License

This project is developed as a **Smart India Hackathon 2026 prototype**.
