# Workaholic — Azure Infrastructure & Deployment Specification

**Version:** 1.0
**Purpose:** Define the exact Azure infrastructure, deployment architecture, configuration, and CI/CD process for the Workaholic production MVP.

---

## 1. Infrastructure Decision

Azure is the **primary backend infrastructure provider** for Workaholic.

Use:

```text
Frontend       → Vercel
Backend API    → Azure Container Apps
Workers        → Azure Container Apps
Database       → Azure Database for PostgreSQL Flexible Server
Files          → Azure Blob Storage
Images         → Azure Container Registry
Queue/Cache    → Redis
Auth           → Supabase Auth
CI/CD          → GitHub Actions
Monitoring     → Sentry + Azure monitoring
DNS            → Cloudflare
```

Do not introduce Kubernetes, VMs, or additional cloud infrastructure unless there is a documented architectural reason.

---

# 2. Target Architecture

```text
                         INTERNET
                            │
                            ▼
                   ┌─────────────────┐
                   │     Vercel      │
                   │ Next.js Web App │
                   └────────┬────────┘
                            │ HTTPS
                            ▼
                ┌────────────────────────┐
                │ Azure Container Apps   │
                │                        │
                │   FastAPI API          │
                └───────────┬────────────┘
                            │
              ┌─────────────┼──────────────┐
              │             │              │
              ▼             ▼              ▼
       ┌────────────┐ ┌───────────┐ ┌──────────────┐
       │ PostgreSQL │ │   Redis   │ │ Azure Blob   │
       │            │ │           │ │   Storage    │
       └────────────┘ └─────┬─────┘ └──────────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ Azure Container Apps│
                 │    Celery Worker    │
                 └──────────┬──────────┘
                            │
                ┌───────────┼────────────┐
                ▼           ▼            ▼
             LLM API      STT          ATS
```

---

# 3. Azure Resource Group

Create one resource group for the production environment.

Recommended name:

```text
workaholic-prod-rg
```

Everything Azure-related for the production MVP should live inside this resource group unless there is a specific reason not to.

Later environments can use:

```text
workaholic-dev-rg
workaholic-staging-rg
workaholic-prod-rg
```

For the initial MVP, production can be the first environment.

---

# 4. Azure Region

Choose a region based on:

1. availability of required Azure services
2. proximity to primary users
3. pricing
4. data residency requirements

Do **not** automatically choose a region simply because it is geographically closest.

For the first deployment, verify that the selected region supports:

* Azure Container Apps
* PostgreSQL Flexible Server
* Blob Storage
* Container Registry
* required monitoring services

The region should be configurable through infrastructure variables.

Example:

```text
AZURE_LOCATION=<selected-region>
```

Do not hardcode the region throughout application code.

---

# 5. PostgreSQL

Create:

**Azure Database for PostgreSQL Flexible Server**

Purpose:

```text
Persistent application data
```

Store:

* users/application identity mappings
* candidate profiles
* evidence
* resumes
* resume versions
* interview sessions
* interview messages
* jobs
* job analyses
* tailoring results
* ATS reports
* background-job metadata

Do **not** store:

* raw PDF files
* raw DOCX files
* generated PDFs
* raw audio

inside PostgreSQL.

Those belong in Blob Storage.

---

# 6. PostgreSQL Configuration

Use the smallest suitable development/student configuration.

Do not provision unnecessary compute.

Database requirements:

```text
PostgreSQL
SSL enabled
Automated backups enabled where available
Strong credentials
Private/controlled network access
```

The application must connect using:

```text
DATABASE_URL
```

Example format:

```text
postgresql+asyncpg://USER:PASSWORD@HOST:5432/DATABASE
```

The exact value must never be committed to Git.

---

# 7. Database Migrations

Use:

**Alembic**

Migration workflow:

```text
Developer changes SQLAlchemy models
            ↓
Create Alembic migration
            ↓
Review migration
            ↓
Run migration
            ↓
Deploy application
```

Do not allow the application to silently mutate production schema during startup.

Avoid:

```python
Base.metadata.create_all()
```

in production.

Production schema changes must use migrations.

---

# 8. Database Connection Management

FastAPI must use a connection pool.

Do not create a new database connection for every request manually.

The application should use SQLAlchemy's async engine/session architecture.

Example conceptual structure:

```text
app/
├── core/
│   └── database.py
├── models/
├── repositories/
└── services/
```

Repositories/services should obtain database sessions through dependency injection.

---

# 9. Azure Blob Storage

Create an Azure Storage Account for Workaholic.

Recommended logical purpose:

```text
workaholic document storage
```

Use private containers.

Recommended containers:

```text
uploads
exports
```

Optionally:

```text
temporary
```

for short-lived processing artifacts.

---

# 10. Blob Storage Structure

Objects should follow a predictable structure.

Example:

```text
uploads/
    users/
        {user_id}/
            resumes/
                {resume_id}/
                    original.pdf

            jobs/
                {job_id}/
                    job-description.pdf

exports/
    users/
        {user_id}/
            resumes/
                {resume_id}/
                    versions/
                        v1.pdf
                        v2.pdf
```

The exact path can evolve, but the ownership relationship must always be recoverable.

---

# 11. File Access

Blob containers must not be publicly accessible.

Do not create public resume URLs.

Correct flow:

```text
User
 ↓
FastAPI
 ↓
Authorization check
 ↓
Generate short-lived signed URL
 ↓
Azure Blob
```

The backend must verify:

```text
authenticated user
        ↓
owns resource
        ↓
allowed to access file
```

before issuing access.

---

# 12. File Upload Flow

```text
Browser
   ↓
FastAPI
   ↓
Validate:
  - authentication
  - ownership
  - file size
  - MIME type
  - extension
   ↓
Azure Blob Storage
   ↓
Create database record
```

The application should not trust the browser's filename or MIME type alone.

---

# 13. Azure Container Registry

Create:

**Azure Container Registry**

Recommended logical name:

```text
workaholicacr
```

Registry names must comply with Azure's naming restrictions.

Store:

```text
workaholic-api
workaholic-worker
```

container images.

---

# 14. Docker Images

The API and worker should have separate production processes.

Possible structure:

```text
apps/api/Dockerfile
```

with runtime commands:

```text
FastAPI:
uvicorn app.main:app
```

and:

```text
Celery:
celery -A app.workers.celery_app worker
```

They may use the same base image if practical, but must run as separate services.

---

# 15. Container Apps Environment

Create an Azure Container Apps Environment.

Example:

```text
workaholic-prod-env
```

Inside it:

```text
workaholic-api
workaholic-worker
```

The API and worker should be deployed as separate Container Apps.

---

# 16. FastAPI Container App

Recommended logical name:

```text
workaholic-api
```

Responsibilities:

* REST API
* authentication verification
* authorization
* database access
* AI orchestration
* job creation
* queue submission
* file authorization
* health endpoints

The API should remain stateless.

Do not store session state on the container's local filesystem.

---

# 17. Worker Container App

Recommended name:

```text
workaholic-worker
```

Responsibilities:

* Celery worker
* PDF generation
* document processing
* AI background jobs
* ATS processing
* benchmark processing

The worker must not expose public HTTP endpoints unless specifically required.

---

# 18. Container Environment Variables

Production secrets must be injected through Azure's configuration/secrets mechanism.

Required categories:

```text
DATABASE_URL

REDIS_URL

SUPABASE_URL
SUPABASE_PUBLISHABLE_KEY
SUPABASE_SECRET_KEY

AZURE_STORAGE_ACCOUNT
AZURE_STORAGE_CONTAINER_UPLOADS
AZURE_STORAGE_CONTAINER_EXPORTS

LLM_API_KEY
STT_API_KEY

SENTRY_DSN
```

Supabase's legacy `anon` / `service_role` keys are retired by the end of 2026; Workaholic uses the publishable and secret keys instead.

Additional configuration:

```text
ENVIRONMENT=production
LOG_LEVEL=INFO
```

Never commit production values.

---

# 19. Secret Management

Never:

```text
hardcode secrets
commit .env
print secrets to logs
send secrets to frontend
```

Frontend environment variables must only contain values that are explicitly safe to expose.

The Supabase secret key is **server-side only**.

The LLM API key is **server-side only**.

Azure storage credentials are **server-side only**.

---

# 20. Managed Identity

Where Azure supports it, prefer:

**Azure Managed Identity**

over long-lived Azure credentials.

For example, the Container App should ideally access Blob Storage using its managed identity rather than storing a storage account key.

Architecture:

```text
Container App
      ↓
Managed Identity
      ↓
Azure RBAC
      ↓
Blob Storage
```

This reduces secret exposure.

If a service cannot practically use managed identity in the first implementation, use a securely stored secret and document the limitation.

---

# 21. Redis

Redis is required for:

```text
Celery broker
Rate limiting
Temporary state
Caching
Locks
```

It is not the source of truth.

The application must be designed so that losing Redis does not destroy permanent candidate information.

Recommended interface:

```python
class CacheService:
    async def get(...)
    async def set(...)
    async def delete(...)
```

and:

```python
class QueueService:
    async def enqueue(...)
```

Business logic should not be tightly coupled to Redis implementation details.

---

# 22. Celery

Celery should use Redis as its broker.

Example:

```text
FastAPI
   ↓
Celery task
   ↓
Redis
   ↓
Celery Worker
```

Tasks should be idempotent where practical.

Example:

```text
generate_resume(resume_id, version_id)
```

rather than:

```text
generate_resume(entire_user_object)
```

Workers should retrieve required data from PostgreSQL/storage.

---

# 23. Background Job States

Every long-running job should have a state.

Example:

```text
PENDING
PROCESSING
COMPLETED
FAILED
```

Optional:

```text
CANCELLED
```

Persist the durable job state in PostgreSQL.

Redis may be used for transient execution state.

---

# 24. Job Failure Handling

A failed background job must:

1. record the failure
2. avoid corrupting existing resume data
3. expose a user-friendly message
4. allow retry where safe
5. log technical details internally
6. avoid leaking secrets or sensitive data

Example user message:

> We couldn't generate your resume right now. Your existing information is safe. Please try again.

---

# 25. Azure Container App Scaling

Initial MVP should use conservative scaling.

Do not immediately configure aggressive autoscaling.

API:

```text
Minimum replicas: low
Maximum replicas: configurable
```

Worker:

```text
Minimum replicas: low
Maximum replicas: configurable
```

Scale based on actual workload.

The exact numbers should be environment configuration, not hardcoded into application code.

---

# 26. Frontend Deployment

Deploy:

**Next.js → Vercel**

Vercel should communicate with:

```text
https://api.<workaholic-domain>
```

or the Azure Container App endpoint during initial setup.

Production should eventually use a proper API subdomain.

Example:

```text
app.workaholic.<domain>
api.workaholic.<domain>
```

---

# 27. CORS

FastAPI must configure CORS explicitly.

Development:

```text
http://localhost:3000
```

Production:

```text
https://app.workaholic.<domain>
```

Do not use:

```text
allow_origins=["*"]
```

in production when credentials/authentication are involved.

---

# 28. Domain Architecture

Recommended:

```text
workaholic.<domain>
        ↓
Marketing site / application

app.workaholic.<domain>
        ↓
Next.js

api.workaholic.<domain>
        ↓
FastAPI
```

The exact domain can be configured later.

Cloudflare can manage DNS.

---

# 29. Health Endpoints

FastAPI must provide:

```text
GET /health
GET /ready
```

### `/health`

Checks:

```text
Application process alive
```

It should remain lightweight.

### `/ready`

Checks required dependencies such as:

```text
PostgreSQL
Redis
```

where appropriate.

Do not perform expensive AI calls from health endpoints.

---

# 30. Deployment Health

Azure Container Apps should only route traffic to healthy API instances.

The API container must listen on the configured port.

Example:

```text
0.0.0.0:8000
```

Do not bind production FastAPI only to:

```text
127.0.0.1
```

---

# 31. GitHub Actions

Repository secrets/configuration must contain only what the workflow actually requires.

Deployment pipeline:

```text
Pull Request
      ↓
Lint
      ↓
Type Check
      ↓
Tests
      ↓
Build
```

Production:

```text
main
 ↓
GitHub Actions
 ↓
Backend Tests
 ↓
Docker Build
 ↓
Push to ACR
 ↓
Deploy Container App
 ↓
Health Check
```

Frontend:

```text
main
 ↓
Vercel
 ↓
Next.js Build
 ↓
Deployment
```

---

# 32. GitHub Actions Backend Pipeline

Conceptual workflow:

```text
checkout
 ↓
setup Python
 ↓
install dependencies
 ↓
lint
 ↓
pytest
 ↓
Docker build
 ↓
Azure authentication
 ↓
ACR login
 ↓
docker push
 ↓
Container App deployment
 ↓
health check
```

Do not deploy if tests fail.

---

# 33. Docker Requirements

Production images must:

* use a suitable Python base image
* avoid unnecessary packages
* run as a non-root user where practical
* use deterministic dependency installation
* have appropriate health configuration
* not contain `.env`
* not contain development secrets
* not contain unnecessary source files

Use `.dockerignore`.

Example exclusions:

```text
.git
.env
.venv
__pycache__
.pytest_cache
node_modules
tests
```

Adjust according to actual build requirements.

---

# 34. Dependency Management

Python dependencies must be pinned or constrained appropriately.

Frontend dependencies must use the project's lockfile.

Do not allow production builds to silently upgrade major dependency versions.

Dependency updates should be intentional.

---

# 35. Database Security

Production database access must not be publicly open to the entire internet without justification.

Use Azure networking/firewall controls appropriately.

Only required application services should be able to connect.

Database credentials must not appear in:

* GitHub commits
* Docker images
* frontend bundles
* application logs
* error messages

---

# 36. Storage Security

Azure Blob containers:

```text
Private
```

No anonymous public access.

Files must only be accessed through:

* authorized backend operations
* short-lived signed URLs

The application must store file metadata in PostgreSQL.

Example:

```text
document
├── id
├── user_id
├── storage_key
├── filename
├── mime_type
├── size
├── created_at
└── status
```

---

# 37. Document Processing Pipeline

For uploaded resumes:

```text
Browser
 ↓
FastAPI
 ↓
Upload validation
 ↓
Blob Storage
 ↓
PostgreSQL document record
 ↓
Celery job
 ↓
Text extraction
 ↓
Document parser
 ↓
Candidate data
 ↓
Evidence mapping
 ↓
User confirmation
```

Never let a document parser directly modify the canonical candidate profile without validation.

---

# 38. PDF Generation Pipeline

```text
Resume JSON
 ↓
Create HTML
 ↓
Playwright
 ↓
PDF
 ↓
Validation
 ↓
Blob Storage
 ↓
Export record
```

PDF validation should verify that:

* the file exists
* PDF is valid
* text is extractable
* expected sections exist
* generated content matches the requested resume version

---

# 39. AI Provider Architecture

Never scatter provider SDK calls across the application.

Use:

```text
app/services/ai/
```

Example:

```text
ai/
├── base.py
├── llm.py
├── providers/
│   ├── provider_a.py
│   └── provider_b.py
└── schemas/
```

Application services call:

```python
llm.structured_output(...)
```

rather than directly calling a vendor SDK everywhere.

---

# 40. Speech Provider Architecture

Use:

```text
app/services/speech/
```

Example:

```text
speech/
├── base.py
├── providers/
│   ├── azure.py
│   └── ...
└── service.py
```

This allows STT providers to be benchmarked or replaced.

---

# 41. Cost Control

Azure for Students provides the initial cloud budget.

The engineering team must treat cloud credit as limited.

Before adding a new resource, ask:

```text
Is this required?
Is there a student/free allocation?
Can an existing service handle this?
Will this create recurring cost?
```

Do not provision:

* Kubernetes
* unnecessary VMs
* dedicated load balancers
* oversized databases
* unnecessary staging environments
* multiple redundant storage accounts

during MVP development.

---

# 42. Development vs Production

Local:

```text
Next.js
FastAPI
PostgreSQL
Redis
```

Production:

```text
Vercel
Azure Container Apps
Azure PostgreSQL
Redis
Azure Blob Storage
```

The application should use environment configuration so the same business logic can run in both environments.

---

# 43. Environment Variables

Local:

```text
.env.local
.env
```

Production:

```text
Azure/Vercel environment configuration
```

Example:

```text
# Application
ENVIRONMENT=development

# Database
DATABASE_URL=

# Redis
REDIS_URL=

# Auth
SUPABASE_URL=
SUPABASE_PUBLISHABLE_KEY=
SUPABASE_SECRET_KEY=

# Storage
AZURE_STORAGE_ACCOUNT=
AZURE_STORAGE_CONTAINER_UPLOADS=
AZURE_STORAGE_CONTAINER_EXPORTS=

# AI
LLM_API_KEY=
STT_API_KEY=

# Monitoring
SENTRY_DSN=
```

Never commit actual values.

---

# 44. Local Docker Compose

Local development should provide:

```yaml
services:
  postgres:
    image: postgres

  redis:
    image: redis
```

The exact versions must be pinned.

The application connects using:

```text
DATABASE_URL
REDIS_URL
```

Local infrastructure must be disposable.

Do not rely on manually configured developer machines.

---

# 45. Monitoring

Use:

**Sentry**

for application-level errors.

Use Azure monitoring for infrastructure-level observations.

Track:

```text
API errors
Container restarts
Worker failures
Database availability
Request latency
Background job failures
Storage failures
```

Do not log sensitive resume content merely to make debugging easier.

---

# 46. Application Logging

Use structured logs.

Example:

```json
{
  "level": "INFO",
  "event": "resume_generation_started",
  "request_id": "req_123",
  "resume_id": "resume_123"
}
```

Do not log:

```text
full resume
full job description
password
access token
API key
raw audio
```

unless there is an explicit secure debugging mechanism.

---

# 47. Request IDs

Every API request should have a request ID.

Example:

```text
X-Request-ID
```

If the client supplies one, validate and propagate it appropriately.

Otherwise generate one.

The request ID should appear in:

* logs
* error responses
* Sentry context where appropriate

This makes production debugging much easier.

---

# 48. AI Trace IDs

AI operations should have their own trace identifier.

Example:

```text
request_id
    ↓
ai_trace_id
    ↓
LLM call
```

Useful for debugging:

```text
Why did this resume generation fail?
Which model was used?
Which operation failed?
How long did it take?
```

Do not expose internal prompts or sensitive AI traces to end users.

---

# 49. Backups

PostgreSQL backups must be enabled according to the available Azure configuration.

Important application data includes:

```text
Candidate profiles
Evidence
Resumes
Resume versions
Jobs
Interview sessions
ATS reports
```

Blob Storage should have appropriate retention/versioning policies where practical.

A backup is not useful unless restoration is understood.

Document the recovery process.

---

# 50. Disaster Recovery

MVP recovery objective:

```text
Database can be restored
Blob files remain recoverable
Application containers can be rebuilt
Infrastructure can be recreated
```

Do not rely on:

```text
"This server is still running."
```

Infrastructure must be reproducible.

---

# 51. Infrastructure as Code

Infrastructure should eventually be defined using:

**Terraform** or another explicit infrastructure-as-code system.

Recommended repository location:

```text
infrastructure/
└── azure/
```

The first manual setup may be used to bootstrap the environment, but production infrastructure should move toward reproducible configuration.

Do not make the Azure Portal the only record of how Workaholic is deployed.

---

# 52. Resource Naming

Use predictable names.

Example:

```text
Resource Group:
workaholic-prod-rg

Container Apps Environment:
workaholic-prod-env

API:
workaholic-api

Worker:
workaholic-worker

Container Registry:
workaholicacr

Storage:
workaholicprodstorage

PostgreSQL:
workaholic-prod-db
```

Azure may impose naming restrictions on individual resources, so names must be adjusted to satisfy provider requirements.

---

# 53. Production Deployment Order

Deploy infrastructure in this order:

```text
1. Azure Resource Group
        ↓
2. PostgreSQL
        ↓
3. Storage Account / Blob Containers
        ↓
4. Container Registry
        ↓
5. Redis
        ↓
6. Container Apps Environment
        ↓
7. API Container App
        ↓
8. Worker Container App
        ↓
9. Configure secrets/environment variables
        ↓
10. Deploy frontend
        ↓
11. Configure domain/CORS
        ↓
12. Run database migrations
        ↓
13. Run health checks
        ↓
14. Run E2E smoke test
```

---

# 54. Database Migration During Deployment

Migration strategy:

```text
Build
 ↓
Deploy infrastructure
 ↓
Run Alembic migration
 ↓
Start application
```

Never make an application deployment dependent on manually editing production tables.

Migration scripts must be reviewed before production execution.

---

# 55. Smoke Test

After deployment, automatically verify:

```text
GET /health
GET /ready
```

Then manually or through E2E:

```text
Create account
 ↓
Create resume
 ↓
Save candidate data
 ↓
Generate resume
 ↓
Generate PDF
 ↓
Run ATS
```

Then verify authorization:

```text
User A cannot access User B's resume.
```

---

# 56. Production Launch Checklist

```text
[ ] Azure subscription active
[ ] Resource group created
[ ] PostgreSQL created
[ ] Database SSL configured
[ ] Redis available
[ ] Blob Storage created
[ ] Blob containers private
[ ] Container Registry created
[ ] Container Apps environment created
[ ] API deployed
[ ] Worker deployed
[ ] Secrets configured
[ ] Managed identity configured where practical
[ ] GitHub Actions configured
[ ] Database migrations executed
[ ] Frontend deployed
[ ] CORS configured
[ ] Domain configured
[ ] HTTPS working
[ ] Sentry configured
[ ] Health endpoints working
[ ] File upload tested
[ ] PDF generation tested
[ ] AI generation tested
[ ] ATS tested
[ ] Tailoring tested
[ ] IDOR tested
[ ] Rate limiting tested
[ ] User deletion tested
[ ] Backup/recovery process documented
```

---

# 57. DEVELOPMENT RULE

Developers must not make architectural decisions that contradict `PRD.md` or this document without documenting the reason.

If a change is required:

```text
Identify problem
 ↓
Explain alternative
 ↓
Document decision
 ↓
Update architecture documentation
 ↓
Implement
```

Do not silently change:

```text
Azure → another cloud
PostgreSQL → MongoDB
FastAPI → another backend
Redis → another queue
```

without an explicit architecture decision.

---

# 58. FINAL INFRASTRUCTURE

The production MVP should ultimately look like:

```text
                         ┌─────────────────┐
                         │     Vercel      │
                         │    Next.js      │
                         └────────┬────────┘
                                  │
                                  │ HTTPS
                                  ▼
                     ┌────────────────────────┐
                     │   Azure Container Apps │
                     │                        │
                     │     FastAPI API        │
                     └───────────┬────────────┘
                                 │
             ┌───────────────────┼───────────────────┐
             │                   │                   │
             ▼                   ▼                   ▼
      ┌──────────────┐    ┌────────────┐    ┌──────────────┐
      │ PostgreSQL   │    │   Redis    │    │ Azure Blob   │
      │              │    │            │    │   Storage    │
      │ Source Truth │    │ Queue/Cache│    │    Files     │
      └──────────────┘    └─────┬──────┘    └──────────────┘
                                │
                                ▼
                     ┌────────────────────────┐
                     │   Azure Container Apps │
                     │      Celery Worker     │
                     └────────────┬───────────┘
                                  │
                   ┌──────────────┼──────────────┐
                   ▼              ▼              ▼
                ┌───────┐      ┌───────┐      ┌───────┐
                │  LLM  │      │  STT  │      │  ATS  │
                └───────┘      └───────┘      └───────┘
```

---

# 59. NON-NEGOTIABLE RULES

The coding agent must follow these rules:

1. **Azure is the primary backend cloud.**
2. **Vercel hosts the Next.js frontend.**
3. **FastAPI runs in Azure Container Apps.**
4. **Celery workers run separately from FastAPI.**
5. **PostgreSQL is the source of truth.**
6. **Redis is never the source of truth.**
7. **Blob Storage holds files, not PostgreSQL.**
8. **Container Registry stores production images.**
9. **Production secrets never enter Git.**
10. **Frontend never receives private API keys.**
11. **Every resource access requires authorization.**
12. **Uploaded documents are untrusted input.**
13. **AI output must pass schema and evidence validation.**
14. **Long-running work belongs in background jobs.**
15. **Production infrastructure must be reproducible.**
16. **Do not introduce Kubernetes for V1.**
17. **Do not introduce VMs for V1 unless technically required.**
18. **Do not add infrastructure simply because Azure offers it.**
19. **Monitor cloud usage and preserve the student credit.**
20. **When in doubt, prefer the simplest architecture that satisfies the requirement.**

---

# 60. FINAL PRINCIPLE

Workaholic's infrastructure should be boring.

That is intentional.

The complexity should exist in the **product logic**:

```text
Candidate Evidence
       ↓
Interview Intelligence
       ↓
Structured Candidate Profile
       ↓
Resume Generation
       ↓
Evidence Validation
       ↓
ATS Analysis
       ↓
Job Matching
       ↓
Tailoring
       ↓
Deterministic Rendering
```

The infrastructure should simply provide reliable primitives for that system:

```text
Compute
Database
Queue
Storage
Authentication
Monitoring
Deployment
```

Do not build infrastructure for the sake of infrastructure.

Build the minimum reliable platform required to make Workaholic a real product.
