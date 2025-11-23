# Terminal-Bench Harbor Runner - Frontend

Next.js frontend for the Terminal-Bench Harbor Runner platform.

## Features

- **Task Upload**: Upload zipped Terminal-Bench tasks
- **Job Management**: View job status and all run attempts
- **Attempt Cards**: See pass/fail status, test results, and episode details
- **Log Viewer**: View container logs for each attempt
- **Real-time Updates**: Auto-refresh job status every 5 seconds

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create `.env.local` file:
```bash
cp .env.example .env.local
# Edit .env.local with your FastAPI backend URL
```

3. Run the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

## Project Structure

```
frontend/
├── app/
│   ├── page.tsx              # Main upload page
│   ├── jobs/[id]/page.tsx    # Job details page
│   ├── layout.tsx             # Root layout
│   └── globals.css            # Global styles
├── components/
│   ├── TaskUpload.tsx         # Upload form component
│   ├── AttemptCard.tsx        # Attempt/run card component
│   ├── TestCaseList.tsx       # Test case list component
│   ├── EpisodeView.tsx        # Episode details component
│   └── LogViewer.tsx          # Log viewer component
└── lib/
    ├── api.ts                 # API client
    ├── types.ts               # TypeScript types
    └── parsers.ts             # Result parsers
```

## Usage

1. **Upload a Task**:
   - Select a zipped Terminal-Bench task
   - Choose harness (Harbor or Terminus)
   - Select model
   - Enter OpenRouter API key
   - Set number of runs (default: 10)
   - Click "Upload & Run"

2. **View Job Results**:
   - After upload, you'll be redirected to the job page
   - See all attempt cards with status and test results
   - Click on an attempt to expand and see details
   - View test cases and episodes
   - Click "View Container Logs" to see logs

## API Integration

The frontend communicates with the FastAPI backend at `NEXT_PUBLIC_API_URL`.

### Endpoints Used:
- `POST /api/upload` - Upload task
- `GET /api/jobs/{job_id}` - Get job status
- `GET /api/jobs/{job_id}/runs/{run_number}/logs/stream` - Stream logs (SSE)

## Development

- Uses Next.js 16 with App Router
- Tailwind CSS for styling
- TypeScript for type safety
- Auto-refresh every 5 seconds on job page
