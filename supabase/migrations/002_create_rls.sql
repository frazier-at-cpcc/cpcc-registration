-- Row Level Security Policies
-- Migration: 002_create_rls.sql

-- =============================================================================
-- Enable RLS on tables
-- =============================================================================

ALTER TABLE public.cpcc_sections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cpcc_sync_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cpcc_sync_logs ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- cpcc_sections: Public read, service role write
-- =============================================================================

-- Allow anyone to read sections (public enrollment data)
CREATE POLICY "Allow public read access on sections"
    ON public.cpcc_sections
    FOR SELECT
    TO anon, authenticated
    USING (true);

-- Only service role can insert/update/delete
CREATE POLICY "Service role full access on sections"
    ON public.cpcc_sections
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =============================================================================
-- cpcc_sync_jobs: Public read (for monitoring), service role write
-- =============================================================================

CREATE POLICY "Allow public read access on sync_jobs"
    ON public.cpcc_sync_jobs
    FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "Service role full access on sync_jobs"
    ON public.cpcc_sync_jobs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =============================================================================
-- cpcc_sync_logs: Public read (for debugging), service role write
-- =============================================================================

CREATE POLICY "Allow public read access on sync_logs"
    ON public.cpcc_sync_logs
    FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "Service role full access on sync_logs"
    ON public.cpcc_sync_logs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
