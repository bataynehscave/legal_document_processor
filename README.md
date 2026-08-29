# Legal Document Processing Pipeline

A production-ready full-stack application built with **FastAPI** (Python 3.11+) and **React** (TypeScript) to extract, validate, and store structured commercial real estate lease metadata. It uses **Google Gemini** (Gemini 3.7 Flash) with strict structured JSON schemas and deterministic Python validation rules backed by an asynchronous SQLite database.

---

## Architectural Note

> **Deterministic JSON Output & Prompt Design**  
> To guarantee reliable, deterministic extraction without hallucination, the pipeline uses Google Gemini's native Structured Outputs via the `google-genai` SDK (`response_schema=LLMContractExtraction`, `response_mime_type="application/json"`), setting sampling temperature strictly to `0.0`. System instructions establish an extraction-only persona with zero creative liberty, enforcing strict formatting: ISO 8601 dates (`YYYY-MM-DD`), 3-letter ISO 4217 currency codes, and numeric types. System instructions explicitly command the model to ignore adversarial prompt injection attempts embedded in contract text. Furthermore, the architecture enforces a strict boundary: **the LLM is never trusted to perform mathematical calculations or business rule validations**. Once raw structured JSON is returned by Gemini, the Python backend deterministically computes derived metrics (e.g., `contract_duration_days` via datetime arithmetic) and enforces business invariants (non-negative rent, expiration strictly following commencement date), returning standard HTTP 422 error payloads if violated.

---

## Key Features

- **Structured Extraction**: Pure Python native orchestration using `google-genai` with strict Pydantic v2 schemas.
- **Deterministic Business Validation**: Python-level validation for date chronologies, positive financials, and duration math.
- **Resilience & Fault Tolerance**: Tenacity-powered exponential backoff with jitter for LLM API calls, rate limiting, and request size guards.
- **Async Background Queue**: Non-blocking extraction queue with real-time job status tracking (`PENDING` → `PROCESSING` → `COMPLETED` / `FAILED`).
- **RESTful API**: Comprehensive endpoints for extraction, querying, filtering, and deep contract inspection.
- **Modern React Frontend**: Clean UI with 1-click mock lease testing, live status polling, success state breakdown, and contract details modal.
- **Dockerized Multi-Container Setup**: Multi-stage Dockerfiles and Docker Compose orchestration with persistent SQLite volume.

---

## Quick Start (Docker)

The fastest way to spin up both the FastAPI backend and React frontend:

1. **Configure Environment Variables**:
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```

2. **Add your Gemini API Key** to `backend/.env`:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

3. **Start the Stack**:
   ```bash
   docker compose up --build
   ```

- **Frontend UI**: [http://localhost:3000](http://localhost:3000)
- **Interactive OpenAPI / Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Local Development (Without Docker)

### 1. Backend Setup

```bash
cd backend

# Create & activate virtual environment
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=...

# Run FastAPI server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env

# Run Vite dev server
npm run dev
```

---

## Running Tests

The backend includes a comprehensive test suite covering end-to-end extraction, business rule validation, resilience retries, rate limiting, and background workers.

```bash
cd backend
python -m pytest -v
```

---

## API Documentation & Examples

### 1. Synchronous Extraction (`POST /api/v1/extract`)

Extracts metadata, runs deterministic validation, and stores the record in SQLite.

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "MEMORANDUM OF LEASE\nThis agreement is entered into this 12th day of May, 2024, by and between Apex Holdings LLC (hereafter the Landlord) and Vertex Tech Solutions Corp (hereafter the Tenant). The property located at Suite 404, Dubai Sports City, is leased for a term starting on June 1st, 2024, and ending exactly two years later on May 31st, 2026. The agreed monthly consideration is 12500.00 AED, payable on the first of each month. Either party may terminate this agreement early by providing at least 90 days written notice to the other party."
  }'
```

**Response (`201 Created`):**
```json
{
  "id": 1,
  "lessor": "Apex Holdings LLC",
  "lessee": "Vertex Tech Solutions Corp",
  "commencement_date": "2024-06-01",
  "expiration_date": "2026-05-31",
  "monthly_rent": 12500.0,
  "currency": "AED",
  "termination_notice_period": 90,
  "contract_duration_days": 729,
  "created_at": "2026-08-29T18:00:00Z"
}
```

### 2. Fetch Stored Contract by ID (`GET /api/v1/contracts/{id}`)

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/contracts/1"
```

### 3. List & Filter Contracts (`GET /api/v1/contracts`)

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/contracts?search=Apex&currency=AED&min_rent=10000"
```

### 4. Asynchronous Extraction (`POST /api/v1/extract/async`)

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/extract/async" \
  -H "Content-Type: application/json" \
  -d '{ "text": "MEMORANDUM OF LEASE..." }'
```

**Response (`202 Accepted`):**
```json
{
  "id": "e2c3983e-902b-4720-94e8-f7b2c0f64c12",
  "status": "PENDING",
  "contract_id": null,
  "contract": null,
  "created_at": "2026-08-29T18:00:00Z"
}
```

### 5. Check Job Status (`GET /api/v1/jobs/{job_id}`)

```bash
curl -X GET "http://127.0.0.1:8000/api/v1/jobs/e2c3983e-902b-4720-94e8-f7b2c0f64c12"
```

---

## Production & Security Considerations (Authentication Note)

- **LLM API Security**: Gemini API credentials are securely managed through server-side environment variables and never exposed to the client.
- **Client Authentication in Production**: For production deployment across organizations, endpoints can be secured with JWT bearer tokens via FastAPI `OAuth2PasswordBearer` or API Key headers (`X-API-Key`). For this recruitment evaluation, endpoints are intentionally accessible without client auth headers to enable automated reviewer test scripts, direct `curl` commands, and standard Swagger UI exploration.
- **Defense in Depth**: Includes HTTP sliding-window IP rate limiting (`429 Too Many Requests`), payload size guard (`413 Payload Too Large`), and enterprise security headers (`HSTS`, `X-Content-Type-Options`, `X-Frame-Options: DENY`, `X-XSS-Protection`).

