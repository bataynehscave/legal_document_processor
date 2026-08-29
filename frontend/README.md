# Frontend UI - Legal Document Processing Pipeline

A responsive React + TypeScript user interface built with Vite and Tailwind CSS for ingesting commercial lease agreements, monitoring async extraction jobs, reviewing extracted structured metadata, and inspecting stored contracts.

## Features

- **Lease Extraction Form**: Large text area with a 1-click sample lease loader (Section 5 mock data).
- **Live Background Processing**: Real-time status polling for asynchronous LLM extraction jobs (`PENDING` -> `PROCESSING` -> `COMPLETED` / `FAILED`).
- **Structured Extraction Card**: Highlights extracted fields (Lessor, Lessee, Commencement Date, Expiration Date, Monthly Rent, Currency, Termination Notice Period, and calculated Contract Duration).
- **Interactive Contract Explorer**: Filterable and searchable table of processed contracts with party name search and currency filtering.
- **Contract Inspection Modal**: Deep-dive inspection fetching full stored contract records via `GET /api/v1/contracts/{id}`.
- **Robust Error Handling**: Distinct visual alerts with field-level breakdowns for HTTP 422 business validation errors, HTTP 429 rate limits, and network errors.

## Tech Stack

- **Framework**: React 19 + TypeScript
- **Bundler**: Vite 6
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios with centralized API layer (`src/api/client.ts`)

## Prerequisites

- Node.js 18+ (or Node.js 20+)
- npm or yarn
- Running FastAPI backend service (port 8000)

## Environment Variables

Create a `.env` file in the `frontend/` directory (or copy from `.env.example` if available):

```env
# Backend API Base URL
VITE_API_URL=http://localhost:8000/api/v1
```

> **Note**: If running Next.js in alternative configurations, the equivalent variable is `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`.

## Local Development Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start the Vite development server**:
   ```bash
   npm run dev
   ```

   The application will be accessible at:
   - **Local UI**: [http://localhost:3000](http://localhost:3000) or [http://localhost:5173](http://localhost:5173)

4. **Production Build**:
   ```bash
   npm run build
   npm run preview
   ```

## Project Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── client.ts       # Centralized API service layer
│   ├── types/
│   │   └── index.ts        # TypeScript schemas matching backend Pydantic models
│   ├── App.tsx             # Main dashboard, extraction form, contracts table & modal
│   ├── main.tsx            # Application entrypoint
│   └── index.css           # Tailwind styling entrypoint
├── Dockerfile              # Containerized frontend deployment
├── package.json
└── vite.config.ts
```

