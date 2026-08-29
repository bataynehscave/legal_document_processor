# Legal Document Processing Pipeline

A full-stack application built with FastAPI and React to extract structured metadata from commercial real estate leases. It uses Google Gemini (defaulting to 3.7 Flash) to parse unstructured text into strict JSON schemas, validating business rules before saving the data to a SQLite database.

## Key Features

- **Structured Extraction**: Uses native LLM structured outputs to enforce a strict JSON schema.
- **Async Processing**: Background queue for long-running extraction jobs with frontend polling.
- **Business Validation**: Deterministic checks (e.g., non-negative rent, valid date ranges) run in Python, kept separate from the LLM.
- **Resilience**: Rate limiting, payload size limits, and automatic retries for LLM API calls.
- **Monorepo Structure**: Clean separation between the `backend/` (FastAPI) and `frontend/` (React/Vite).

## Quick Start (Docker)

The easiest way to run the application is using Docker Compose.

1. Set up your environment variables:
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```
2. Add your Gemini API key to `backend/.env`:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
3. Start the stack:
   ```bash
   docker compose up --build
   ```

- **Frontend UI**: [http://localhost:3000](http://localhost:3000)
- **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

## Local Development (Without Docker)

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Running Tests

The backend includes a 26-test Pytest suite covering extraction, validation, rate limits, and async jobs.
```bash
cd backend
pytest -v
```

## API Examples

### 1. Synchronous Extraction
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "MEMORANDUM OF LEASE\nThis agreement is entered into this 12th day of May, 2024, by and between Apex Holdings LLC (hereafter the Landlord) and Vertex Tech Solutions Corp (hereafter the Tenant). The property located at Suite 404, Dubai Sports City, is leased for a term starting on June 1st, 2024, and ending exactly two years later on May 31st, 2026. The agreed monthly consideration is 12500.00 AED, payable on the first of each month. Either party may terminate this agreement early by providing at least 90 days written notice to the other party."
  }'
```

### 2. Async Extraction
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/extract/async" \
  -H "Content-Type: application/json" \
  -d '{ "text": "MEMORANDUM OF LEASE..." }'
```

### 3. Check Job Status
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/jobs/<JOB_ID>"
```

### 4. Search Contracts
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/contracts?search=Apex&currency=AED&min_rent=10000"
```
