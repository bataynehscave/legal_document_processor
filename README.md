# Production-Ready Legal Document Processing Pipeline

A robust, enterprise-grade backend service built with **FastAPI**, **Pydantic v2**, **SQLAlchemy 2.0 (SQLite)**, and native LLM orchestration (**Google GenAI SDK** and **OpenAI SDK**) with Structured Outputs / JSON schema enforcement, async background queueing, rate limiting, deterministic business validation, and comprehensive resilience.

---

## 1. Architectural Note: Prompt Structure & Deterministic JSON Outputs

To guarantee deterministic, hallucination-free JSON outputs from LLMs:
1. **Schema-Enforced Decoding**: Rather than relying on freeform text parsing or regex, the pipeline leverages provider-native JSON Schema enforcement:
   - **Google Gemini**: Uses `types.GenerateContentConfig` with `response_mime_type="application/json"` and `response_schema=LLMContractExtraction` (Default: `gemini-3.7-flash`).
   - **OpenAI**: Uses `client.beta.chat.completions.parse()` with Pydantic response format (e.g. `gpt-4o-mini`, `gpt-4o`).
2. **System Instruction Isolation & Prompt Injection Defense**: System instructions strictly constrain the model to factual entity extraction, explicitly commanding it to ignore any adversarial instructions embedded within the lease text attempting to modify schemas or system behaviors.
3. **Decoupled Business Logic & Deterministic Math**: The LLM is strictly used as an extraction engine. Business validation rules (e.g., non-negative rent, valid ISO dates, and expiration date >= commencement date) and derived metrics (e.g. `contract_duration_days = (expiration_date - commencement_date).days`) are computed deterministically in Python. Invalid documents are rejected with `HTTP 422 Unprocessable Entity` and are never persisted to the database.

---

## 2. Enterprise & Production Hardening Features

- **Asynchronous Background Job Queue (`POST /api/v1/extract/async`)**:
  - Accepts extraction requests asynchronously, immediately returning `HTTP 202 Accepted` with a `job_id`.
  - Background worker pool processes extractions and updates job status (`PENDING` -> `PROCESSING` -> `COMPLETED` / `FAILED`).
  - Polling endpoint `GET /api/v1/jobs/{job_id}` returns extraction progress and full payload upon completion.
- **API Rate Limiting**:
  - Sliding-window in-memory rate limiter protecting LLM endpoints from abuse and quota exhaustion.
  - Returns standard `HTTP 429 Too Many Requests` with `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers.
- **Security & Tracing Middleware**:
  - Request ID tracing: Generates or propagates `X-Request-ID` and returns execution latency `X-Process-Time-Ms`.
  - Payload Size Guard: Rejects oversized requests exceeding `MAX_PAYLOAD_BYTES` with `HTTP 413 Payload Too Large`.
  - Security Headers: Injects `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`, and `Referrer-Policy`.
- **SQLite WAL Concurrency**:
  - Automatic `PRAGMA journal_mode=WAL;` and `PRAGMA busy_timeout=5000;` on connection to avoid lock contention under concurrent load.
- **Advanced Querying & Search**:
  - `GET /api/v1/contracts`: Supports full substring search across parties (`?search=Apex`), currency filtering (`?currency=AED`), and rent range filters (`?min_rent=10000&max_rent=20000`).
  - `DELETE /api/v1/contracts/{id}`: Clean single contract deletion with `HTTP 204 No Content`.

---

## 3. Architecture & Directory Structure

```
.
??? app/
?   ??? api/
?   ?   ??? errors.py                  # Global exception handlers (400, 404, 413, 422, 429, 502, 504, 500)
?   ?   ??? v1/
?   ?       ??? router.py              # Router aggregation
?   ?       ??? endpoints/
?   ?           ??? extract.py         # POST /api/v1/extract & POST /api/v1/extract/async
?   ?           ??? contracts.py       # GET/DELETE /api/v1/contracts with search & filters
?   ?           ??? jobs.py            # GET /api/v1/jobs & GET /api/v1/jobs/{job_id}
?   ??? core/
?   ?   ??? config.py                  # Pydantic Settings & environment variables
?   ?   ??? database.py                # Async SQLite engine & WAL mode configuration
?   ?   ??? exceptions.py              # Domain-specific exception hierarchy
?   ?   ??? middleware.py              # Tracing, security headers, payload size guard
?   ?   ??? rate_limiter.py            # Sliding window in-memory rate limiter
?   ??? models/
?   ?   ??? contract.py                # SQLAlchemy 2.0 Contract model
?   ?   ??? job.py                     # SQLAlchemy 2.0 ExtractionJob model
?   ??? schemas/
?   ?   ??? contract.py                # Response & error schemas
?   ?   ??? extraction.py              # Extraction request & Pydantic v2 schemas
?   ?   ??? job.py                     # Background job schemas & statuses
?   ??? services/
?   ?   ??? contract_service.py        # Business logic, search filters, persistence
?   ?   ??? job_queue.py               # Asynchronous queue manager & background worker pool
?   ?   ??? llm/
?   ?       ??? base.py                # BaseLLMClient interface & system prompts
?   ?       ??? factory.py             # LLM provider factory
?   ?       ??? gemini_client.py       # Google GenAI client (gemini-3.7-flash) with Tenacity retries
?   ?       ??? openai_client.py       # OpenAI client with Tenacity retries
?   ??? main.py                        # FastAPI application & lifespan management
??? tests/
?   ??? conftest.py                    # Pytest fixtures, in-memory DB & mock clients
?   ??? test_api_contracts.py          # Contract list & get tests
?   ??? test_api_extract.py            # Extraction & Section 5 mock tests
?   ??? test_async_queue.py            # Async background queue & worker tests
?   ??? test_business_validation.py    # Business rule validation (422) edge cases
?   ??? test_contract_search.py        # Search, filters, and deletion tests
?   ??? test_live_llm.py               # Live Gemini 3.7 Flash & OpenAI integration tests
?   ??? test_rate_limiter.py           # Rate limiting (429) tests
?   ??? test_resilience.py             # Retries, timeouts, rate limits, schema decode tests
?   ??? test_security_middleware.py    # Security headers & payload size guard (413) tests
??? .env.example
??? Dockerfile
??? docker-compose.yml
??? pyproject.toml
??? requirements.txt
??? README.md
```

---

## 4. Setup & Installation

### 1. Clone repository & create virtual environment
```bash
git clone <repository_url>
cd pwc_casestudy

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
```

### 2. Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment variables
```bash
cp .env.example .env
```

Edit `.env`:
```env
# Default provider ('gemini' or 'openai')
LLM_PROVIDER=gemini

# Google Gemini Configuration (Default: Gemini 3.7 Flash)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.7-flash

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

# Database Configuration
DATABASE_URL=sqlite+aiosqlite:///./contracts.db

# Rate Limiting & Queue
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
QUEUE_MAX_CONCURRENCY=2
```

---

## 5. Running the Application

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 6. API Endpoints & cURL Examples

### 1. Synchronous Extraction (`POST /api/v1/extract`)
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/extract"   -H "Content-Type: application/json"   -d '{
    "text": "MEMORANDUM OF LEASE
This agreement is entered into this 12th day of May, 2024, by and between Apex Holdings LLC (hereafter the Landlord) and Vertex Tech Solutions Corp (hereafter the Tenant). The property located at Suite 404, Dubai Sports City, is leased for a term starting on June 1st, 2024, and ending exactly two years later on May 31st, 2026. The agreed monthly consideration is 12500.00 AED, payable on the first of each month. Either party may terminate this agreement early by providing at least 90 days written notice to the other party."
  }'
```

### 2. Asynchronous Queue Extraction (`POST /api/v1/extract/async`)
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/extract/async"   -H "Content-Type: application/json"   -d '{
    "text": "MEMORANDUM OF LEASE...",
    "provider": "gemini",
    "model": "gemini-3.7-flash"
  }'
```
Response (`HTTP 202 Accepted`):
```json
{
  "id": "e3a89e1b-871d-4eb7-a7ea-314125bcf608",
  "status": "PENDING",
  "provider": "gemini",
  "model": "gemini-3.7-flash",
  "contract_id": null,
  "contract": null,
  "error_message": null,
  "error_code": null,
  "created_at": "2026-08-28T14:35:00.000000Z",
  "completed_at": null
}
```

### 3. Check Async Job Status (`GET /api/v1/jobs/{job_id}`)
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/jobs/e3a89e1b-871d-4eb7-a7ea-314125bcf608"
```

### 4. Search & Filter Contracts (`GET /api/v1/contracts`)
```bash
# Search by party substring and filter by currency & rent range
curl -X GET "http://127.0.0.1:8000/api/v1/contracts?search=Apex&currency=AED&min_rent=10000&max_rent=20000"
```

### 5. Delete Contract (`DELETE /api/v1/contracts/{id}`)
```bash
curl -X DELETE "http://127.0.0.1:8000/api/v1/contracts/1"
```

---

## 7. Running the Automated Test Suite

```bash
pytest -v
```

**26/26 tests passing:**
- End-to-end extraction with Section 5 mock input
- Inverted date rejection & negative rent rejection (`HTTP 422`)
- Rate limiting enforcement & headers (`HTTP 429`)
- Security headers & payload size guard (`HTTP 413`)
- Asynchronous queueing, status polling, and background worker execution (`HTTP 202`)
- Substring search, currency/rent filtering, and contract deletion (`HTTP 204`)
- Live Gemini 3.7 Flash and OpenAI integration tests

---

## 8. Docker Deployment (Bonus)

```bash
# Build & run with Docker Compose
docker-compose up --build
```
