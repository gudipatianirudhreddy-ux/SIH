# SIH 2026: University-Industry Problem-Solving Platform (Backend)

An open-source, scalable FastAPI platform enabling citizens to report real-world societal challenges, students to design and submit engineering prototypes, and industry partners to mentor, evaluate, and fund impactful solutions.

---

## 🚀 Workflow Overview

```
Citizen/User
    │ reports societal issue (Text + Image/Video + GPS location)
    ▼
AI/ML Issue Classifier
    │ automatically categorizes the issue & calculates confidence
    ▼
Interactive Map & Discovery
    │ students discover real-world issues by category and location
    ▼
Student Innovation Hub
    │ student submits solution proposal + PDF documentation + demo link
    ▼
Industry Review & Mentorship
    │ industry partners review, score, provide feedback, and shortlist
    ▼
Problem Resolved & Deployed
```

---

## 🛠️ Technology Stack

- **Framework**: FastAPI (Python 3.13)
- **Database**: PostgreSQL (Supabase managed)
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **Authentication**: Supabase Auth (Bearer JWT verification)
- **Validation**: Pydantic v2
- **Testing**: Pytest & HTTPX TestClient (with isolated in-memory SQLite fixture)

---

## 🏛️ Architecture & Project Structure

The project strictly follows a layered architecture: `Routers -> Services -> Models`:

```
SIH/
├── alembic/
│   ├── versions/
│   │   ├── ca4f00f757e1_create_profiles_table.py
│   │   ├── d2fd2379493d_add_phone_number_to_profiles.py
│   │   ├── ba3667551077_add_avatar_url_location_and_updated_at_.py
│   │   └── d800b2d30db3_add_issues_media_solutions_and_reviews.py  <-- SIH Domain Tables
│   └── env.py
├── app/
│   ├── auth.py              # Supabase auth, user extraction & role RBAC dependencies
│   ├── database.py          # SQLAlchemy engine, session maker, get_db dependency
│   ├── main.py              # FastAPI application, OpenAPI metadata, router registrations
│   ├── models/              # SQLAlchemy database domain models
│   │   ├── enums.py         # IssueStatus, SolutionStatus, IssuePriority
│   │   ├── issue.py         # Issue, IssueMedia
│   │   ├── profile.py       # Profile (Citizen, Student, Industrialist/Industry, Admin)
│   │   └── solution.py      # Solution, SolutionReview
│   ├── schemas/             # Pydantic validation schemas
│   │   ├── issue.py         # IssueCreate, IssueUpdate, IssueResponse, IssueListResponse, IssueMedia*
│   │   ├── profile.py       # ProfileCreate, ProfileUpdate, ProfileResponse, UserRole
│   │   └── solution.py      # SolutionCreate, SolutionUpdate, SolutionResponse, SolutionReview*
│   ├── services/            # Pure business logic layer
│   │   ├── issue.py         # Issue CRUD, bounding-box geographic query, media attachment
│   │   ├── media_storage.py # Media storage abstraction (Supabase Storage + Local fallback)
│   │   ├── ml_classifier.py # ML IssueClassifier interface (Clean pluggable service)
│   │   ├── profile.py       # User profile management
│   │   └── solution.py      # Solution lifecycle, status transitions, industry reviews
│   └── routers/             # API route controllers
│       ├── issue.py         # /issues endpoints
│       ├── profile.py       # /profiles endpoints
│       └── solution.py      # /solutions and /issues/{id}/solutions endpoints
├── tests/
│   ├── conftest.py          # In-memory SQLite fixture and mock authentication
│   ├── test_profile.py      # Profile management tests
│   └── test_sih_workflow.py # SIH end-to-end integration & authorization tests
├── .env                     # Environment credentials
├── pyproject.toml           # Project dependencies
└── README.md
```

---

## 🔑 Role-Based Access Control (RBAC)

The platform supports four user roles stored in the `profiles` table:

1. **`citizen`**: Can report societal issues, attach media, and track resolution status.
2. **`student`**: Can discover issues and submit solution proposals with documentation/prototypes.
3. **`industrialist` / `industry`**: Can review solutions, provide technical feedback, and award ratings (1–5).
4. **`admin`**: Full administrative access across issues, solutions, and reviews.

Role-checking dependencies in [`app/auth.py`](file:///C:/Users/gkira/Desktop/Python%20building/SIH/app/auth.py):
- `require_authenticated_user`
- `require_role("STUDENT")`
- `require_role("INDUSTRY")` (supports both `"industrialist"` and `"industry"`)
- `require_role("ADMIN")`

---

## 📡 API Endpoints

### Health & Auth
- `GET /` - Root health check
- `GET /me` - Current authenticated user information

### User Profiles (`/profiles`)
- `GET /profiles/me` - Get current user profile
- `POST /profiles` & `POST /profiles/me` - Create profile (`citizen`, `student`, `industrialist`, `admin`)
- `PATCH /profiles/me` & `PUT /profiles/me` - Update profile details

### Societal Issues (`/issues`)
- `POST /issues` - Report a new issue (stores description, GPS coords, triggers AI classification on media)
- `GET /issues` - List issues (paginated, sort by newest; filter by `category`, `status`, or bounding box: `min_lat`, `max_lat`, `min_lon`, `max_lon`)
- `GET /issues/{issue_id}` - Get full issue details with media and status
- `PATCH /issues/{issue_id}` - Update issue (authorized for reporter or admin)
- `DELETE /issues/{issue_id}` - Delete issue (authorized for reporter or admin)
- `POST /issues/{issue_id}/media` - Attach image/video URL to an issue and trigger classification

### Solutions (`/issues/{issue_id}/solutions` & `/solutions`)
- `POST /issues/{issue_id}/solutions` - Submit solution prototype (Students only; transitions issue to `SOLUTION_SUBMITTED`)
- `GET /issues/{issue_id}/solutions` - List all solutions submitted for an issue
- `GET /solutions/{solution_id}` - Get specific solution details and industry reviews
- `PATCH /solutions/{solution_id}` - Update solution (content edited by student owner; status updated by industry/admin)

### Industry Reviews (`/solutions/{solution_id}/reviews`)
- `POST /solutions/{solution_id}/reviews` - Submit review with rating (1-5) and feedback (Industry / Admin only)
- `GET /solutions/{solution_id}/reviews` - List all industry reviews for a solution

---

## 🤖 ML Classifier Integration

The ML classification service is located at:
[`app/services/ml_classifier.py`](file:///C:/Users/gkira/Desktop/Python%20building/SIH/app/services/ml_classifier.py)

### Architecture
```python
class IssueClassifier:
    def classify(self, image_path_or_url: str) -> dict:
        # Returns: {"category": str, "confidence": float}
        ...
```
- A development mock classifier is currently configured with heuristic categorization.
- **To plug in the real ML model**: Replace the internal logic of `IssueClassifier.classify` (or subclass `IssueClassifier`) with your PyTorch, ONNX, or TensorFlow pipeline.
- No routers or services need to be altered when replacing the classifier.

---

## 📦 Supabase Storage Integration

The media storage abstraction is located at:
[`app/services/media_storage.py`](file:///C:/Users/gkira/Desktop/Python%20building/SIH/app/services/media_storage.py)

### How It Works
- Implements `BaseStorageService` with `SupabaseStorageService` and `LocalStorageService`.
- Uses `supabase.storage.from_("issue-media").upload(...)` and `.get_public_url(...)`.
- If Supabase Storage is not set up, it automatically falls back gracefully.

---

## ⚙️ Environment Variables

Create a `.env` file in the root directory:

```env
DATABASE_URL=postgresql://postgres:<PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres
SUPABASE_URL=https://<PROJECT_REF>.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_<KEY>
```

---

## 🏃 Running the Application

### 1. Install Dependencies
Ensure Python 3.13+ is installed:
```powershell
uv sync
# OR
pip install -r requirements.txt
```

### 2. Run Database Migrations
Apply all schema migrations to your PostgreSQL / Supabase database:
```powershell
alembic upgrade head
```

To review generated SQL without executing against the database:
```powershell
alembic upgrade head --sql
```

### 3. Start the FastAPI Development Server
```powershell
uvicorn app.main:app --reload --port 8000
```

Open interactive Swagger UI at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Running Tests

The test suite runs against an isolated, in-memory SQLite database and mocks Supabase auth:

```powershell
pytest
```

Run with verbose test output:
```powershell
pytest -v
```

All 24 unit and integration tests covering profiles, issue reporting, ML triggers, student solutions, industry evaluations, and coordinate validations will execute.
