-- CPCC Enrollment Data Tables
-- Migration: 001_create_tables.sql

-- =============================================================================
-- Table: cpcc_sections
-- Main enrollment data for all tracked course sections
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.cpcc_sections (
    -- Primary identification
    section_id TEXT PRIMARY KEY,
    course_id TEXT NOT NULL,

    -- Course information
    subject_code TEXT NOT NULL,
    course_number TEXT NOT NULL,
    section_number TEXT NOT NULL,
    title TEXT NOT NULL,

    -- Enrollment data (the critical metrics)
    available_seats INTEGER NOT NULL DEFAULT 0,
    total_capacity INTEGER NOT NULL DEFAULT 0,
    enrolled_count INTEGER NOT NULL DEFAULT 0,
    waitlist_count INTEGER NOT NULL DEFAULT 0,

    -- Schedule and location
    start_date TEXT,
    end_date TEXT,
    location TEXT,
    credits NUMERIC(4,2),
    term TEXT,

    -- Complex data stored as JSONB
    meeting_times JSONB DEFAULT '[]'::jsonb,
    instructors JSONB DEFAULT '[]'::jsonb,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_sync_job_id UUID,

    -- Validation
    CONSTRAINT valid_enrollment CHECK (
        available_seats >= 0 AND
        total_capacity >= 0 AND
        enrolled_count >= 0 AND
        waitlist_count >= 0
    )
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_cpcc_sections_subject_code ON public.cpcc_sections(subject_code);
CREATE INDEX IF NOT EXISTS idx_cpcc_sections_term ON public.cpcc_sections(term);
CREATE INDEX IF NOT EXISTS idx_cpcc_sections_updated_at ON public.cpcc_sections(updated_at);
CREATE INDEX IF NOT EXISTS idx_cpcc_sections_availability ON public.cpcc_sections(available_seats) WHERE available_seats > 0;
CREATE INDEX IF NOT EXISTS idx_cpcc_sections_subject_term ON public.cpcc_sections(subject_code, term);
CREATE INDEX IF NOT EXISTS idx_cpcc_sections_course ON public.cpcc_sections(subject_code, course_number);

-- Full-text search on title
CREATE INDEX IF NOT EXISTS idx_cpcc_sections_title_search ON public.cpcc_sections USING gin(to_tsvector('english', title));

-- =============================================================================
-- Table: cpcc_sync_jobs
-- Tracks each synchronization job for monitoring and preventing overlaps
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.cpcc_sync_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Job configuration
    subjects TEXT[] NOT NULL,
    term TEXT,

    -- Job status
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),

    -- Progress tracking
    total_subjects INTEGER NOT NULL DEFAULT 0,
    completed_subjects INTEGER NOT NULL DEFAULT 0,
    current_subject TEXT,

    -- Results
    sections_fetched INTEGER DEFAULT 0,
    sections_updated INTEGER DEFAULT 0,
    sections_inserted INTEGER DEFAULT 0,

    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Error handling
    error_message TEXT,
    error_details JSONB,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    triggered_by TEXT DEFAULT 'manual'
        CHECK (triggered_by IN ('pg_cron', 'manual', 'edge_function', 'github_actions'))
);

-- Indexes for sync jobs
CREATE INDEX IF NOT EXISTS idx_cpcc_sync_jobs_status ON public.cpcc_sync_jobs(status);
CREATE INDEX IF NOT EXISTS idx_cpcc_sync_jobs_created_at ON public.cpcc_sync_jobs(created_at DESC);

-- =============================================================================
-- Table: cpcc_sync_logs
-- Detailed logs for each sync operation
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.cpcc_sync_logs (
    id BIGSERIAL PRIMARY KEY,
    job_id UUID REFERENCES public.cpcc_sync_jobs(id) ON DELETE CASCADE,

    -- Log details
    log_level TEXT NOT NULL DEFAULT 'info'
        CHECK (log_level IN ('debug', 'info', 'warning', 'error')),
    message TEXT NOT NULL,
    details JSONB,

    -- Context
    subject_code TEXT,
    operation TEXT,  -- 'session_init', 'search', 'details', 'upsert', etc.

    -- Timing
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for logs
CREATE INDEX IF NOT EXISTS idx_cpcc_sync_logs_job_id ON public.cpcc_sync_logs(job_id);
CREATE INDEX IF NOT EXISTS idx_cpcc_sync_logs_level ON public.cpcc_sync_logs(log_level) WHERE log_level IN ('warning', 'error');

-- =============================================================================
-- Trigger: Auto-update updated_at column
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_cpcc_sections_updated_at
    BEFORE UPDATE ON public.cpcc_sections
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Helper Function: Check if sync is running
-- =============================================================================

CREATE OR REPLACE FUNCTION is_sync_running()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM public.cpcc_sync_jobs
        WHERE status = 'running'
        AND started_at > NOW() - INTERVAL '10 minutes'  -- Safety timeout
    );
END;
$$ LANGUAGE plpgsql;
