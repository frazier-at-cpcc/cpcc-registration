# Supabase Integration for CPCC Enrollment Data

This directory contains the Supabase Edge Function and database migrations for storing CPCC enrollment data.

## Architecture

```
External Scheduler (GitHub Actions)
        │
        ▼ (every 3 minutes)
┌───────────────────────────────┐
│  Edge Function                │
│  sync-cpcc-enrollment         │
│                               │
│  1. Init CPCC session         │
│  2. Search each subject       │
│  3. Get section details       │
│  4. Upsert to database        │
└───────────────────────────────┘
        │
        ▼
┌───────────────────────────────┐
│  PostgreSQL Tables            │
│  - cpcc_sections              │
│  - cpcc_sync_jobs             │
│  - cpcc_sync_logs             │
└───────────────────────────────┘
        │
        ▼
┌───────────────────────────────┐
│  Clients                      │
│  - Direct table queries       │
│  - RPC functions              │
└───────────────────────────────┘
```

## Setup Instructions

### 1. Run Database Migrations

In your Supabase dashboard SQL editor, run these migrations in order:

```bash
# Or using Supabase CLI:
supabase db push
```

1. `migrations/001_create_tables.sql` - Creates tables and indexes
2. `migrations/002_create_rls.sql` - Sets up Row Level Security
3. `migrations/003_create_rpc.sql` - Creates query functions

### 2. Deploy Edge Function

```bash
# Install Supabase CLI if needed
npm install -g supabase

# Login to Supabase
supabase login

# Link to your project
supabase link --project-ref YOUR_PROJECT_REF

# Deploy the function
supabase functions deploy sync-cpcc-enrollment
```

### 3. Configure GitHub Actions Secrets

Add these secrets to your GitHub repository:

- `SUPABASE_URL`: Your Supabase project URL (e.g., `https://xxx.supabase.co`)
- `SUPABASE_ANON_KEY`: Your Supabase anonymous/public key

The workflow will automatically run every 3 minutes.

### 4. Manual Testing

Test the Edge Function manually:

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  "https://YOUR_PROJECT.supabase.co/functions/v1/sync-cpcc-enrollment"
```

## Querying Data

### Direct Table Queries

```typescript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

// Get all sections for specific subjects
const { data: sections } = await supabase
  .from('cpcc_sections')
  .select('*')
  .in('subject_code', ['CTI', 'CSC', 'CCT'])
  .order('subject_code')
  .order('course_number')

// Get sections with available seats
const { data: available } = await supabase
  .from('cpcc_sections')
  .select('*')
  .gt('available_seats', 0)
```

### RPC Functions

```typescript
// Get enrollment statistics by subject
const { data: stats } = await supabase
  .rpc('get_enrollment_stats', { p_subjects: ['CTI', 'CSC'] })

// Check data freshness
const { data: freshness } = await supabase
  .rpc('check_data_freshness', { p_stale_threshold_minutes: 10 })

// Get last sync info
const { data: lastSync } = await supabase
  .rpc('get_last_sync_info')

// Search sections by keyword
const { data: results } = await supabase
  .rpc('search_sections', {
    p_query: 'cyber',
    p_subjects: ['CTI', 'CCT'],
    p_limit: 20
  })
```

## Monitoring

### Check Recent Sync Jobs

```sql
SELECT * FROM get_sync_history(10);
```

### Check for Errors

```sql
SELECT * FROM cpcc_sync_logs
WHERE log_level IN ('warning', 'error')
ORDER BY created_at DESC
LIMIT 50;
```

### Check Data Freshness

```sql
SELECT * FROM check_data_freshness(10);
```

## Tables

### cpcc_sections

Main enrollment data table with these columns:
- `section_id` (PK) - Unique section identifier
- `course_id` - CPCC course ID
- `subject_code` - Subject code (e.g., CTI, CSC)
- `course_number` - Course number (e.g., 110, 151)
- `section_number` - Full section name (e.g., CTI-110-N886)
- `title` - Course title
- `available_seats` - Seats available
- `total_capacity` - Total capacity
- `enrolled_count` - Currently enrolled
- `waitlist_count` - Students on waitlist
- `start_date`, `end_date` - Course dates
- `location` - Campus/location
- `credits` - Credit hours
- `term` - Academic term (e.g., "Spring 2026")
- `meeting_times` (JSONB) - Schedule details
- `instructors` (JSONB) - Instructor names
- `updated_at` - Last sync time

### cpcc_sync_jobs

Tracks sync job execution for monitoring.

### cpcc_sync_logs

Detailed logs for debugging sync issues.

## Troubleshooting

### Sync is Failing

1. Check sync logs: `SELECT * FROM cpcc_sync_logs WHERE log_level = 'error' ORDER BY created_at DESC LIMIT 10;`
2. Check if CPCC website is accessible
3. Verify Edge Function environment variables are set

### Data is Stale

1. Check last sync: `SELECT * FROM get_last_sync_info();`
2. Check GitHub Actions workflow runs
3. Manually trigger sync to test

### Missing Sections

The sync processes subjects sequentially to avoid session conflicts. If some subjects are missing:
1. Check logs for that subject
2. CPCC may be rate-limiting or having issues
3. Data will refresh on next successful sync
