-- RPC Functions for querying enrollment data
-- Migration: 003_create_rpc.sql

-- =============================================================================
-- Function: Get enrollment by subjects
-- Returns all sections for specified subjects, optionally filtered by term
-- =============================================================================

CREATE OR REPLACE FUNCTION get_enrollment_by_subjects(
    p_subjects TEXT[],
    p_term TEXT DEFAULT NULL
)
RETURNS SETOF public.cpcc_sections AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM public.cpcc_sections
    WHERE subject_code = ANY(p_subjects)
    AND (p_term IS NULL OR term ILIKE '%' || p_term || '%')
    ORDER BY subject_code, course_number, section_number;
END;
$$ LANGUAGE plpgsql STABLE;

-- =============================================================================
-- Function: Get available sections
-- Returns sections with available seats, optionally filtered by subjects
-- =============================================================================

CREATE OR REPLACE FUNCTION get_available_sections(
    p_subjects TEXT[] DEFAULT NULL,
    p_min_seats INTEGER DEFAULT 1
)
RETURNS SETOF public.cpcc_sections AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM public.cpcc_sections
    WHERE available_seats >= p_min_seats
    AND (p_subjects IS NULL OR subject_code = ANY(p_subjects))
    ORDER BY subject_code, course_number, section_number;
END;
$$ LANGUAGE plpgsql STABLE;

-- =============================================================================
-- Function: Get enrollment statistics
-- Returns aggregated stats by subject
-- =============================================================================

CREATE OR REPLACE FUNCTION get_enrollment_stats(
    p_subjects TEXT[] DEFAULT NULL
)
RETURNS TABLE (
    subject_code TEXT,
    total_sections BIGINT,
    total_capacity BIGINT,
    total_enrolled BIGINT,
    total_available BIGINT,
    total_waitlisted BIGINT,
    fill_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.subject_code,
        COUNT(*)::BIGINT as total_sections,
        COALESCE(SUM(s.total_capacity), 0)::BIGINT as total_capacity,
        COALESCE(SUM(s.enrolled_count), 0)::BIGINT as total_enrolled,
        COALESCE(SUM(s.available_seats), 0)::BIGINT as total_available,
        COALESCE(SUM(s.waitlist_count), 0)::BIGINT as total_waitlisted,
        ROUND(
            CASE WHEN SUM(s.total_capacity) > 0
            THEN (SUM(s.enrolled_count)::NUMERIC / SUM(s.total_capacity)::NUMERIC) * 100
            ELSE 0
            END, 2
        ) as fill_rate
    FROM public.cpcc_sections s
    WHERE p_subjects IS NULL OR s.subject_code = ANY(p_subjects)
    GROUP BY s.subject_code
    ORDER BY s.subject_code;
END;
$$ LANGUAGE plpgsql STABLE;

-- =============================================================================
-- Function: Get last sync info
-- Returns information about the most recent sync job
-- =============================================================================

CREATE OR REPLACE FUNCTION get_last_sync_info()
RETURNS TABLE (
    job_id UUID,
    status TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    sections_fetched INTEGER,
    duration_seconds NUMERIC,
    error_message TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        j.id,
        j.status,
        j.started_at,
        j.completed_at,
        j.sections_fetched,
        CASE WHEN j.completed_at IS NOT NULL AND j.started_at IS NOT NULL
            THEN EXTRACT(EPOCH FROM (j.completed_at - j.started_at))
            ELSE NULL
        END,
        j.error_message
    FROM public.cpcc_sync_jobs j
    ORDER BY j.created_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql STABLE;

-- =============================================================================
-- Function: Check data freshness
-- Returns whether the data is stale and when it was last updated
-- =============================================================================

CREATE OR REPLACE FUNCTION check_data_freshness(
    p_stale_threshold_minutes INTEGER DEFAULT 10
)
RETURNS TABLE (
    is_stale BOOLEAN,
    last_update TIMESTAMPTZ,
    staleness_minutes NUMERIC,
    total_sections BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(MAX(s.updated_at) < NOW() - (p_stale_threshold_minutes || ' minutes')::INTERVAL, TRUE) as is_stale,
        MAX(s.updated_at) as last_update,
        COALESCE(EXTRACT(EPOCH FROM (NOW() - MAX(s.updated_at))) / 60, 9999) as staleness_minutes,
        COUNT(*)::BIGINT as total_sections
    FROM public.cpcc_sections s;
END;
$$ LANGUAGE plpgsql STABLE;

-- =============================================================================
-- Function: Search sections by keyword
-- Full-text search on section titles
-- =============================================================================

CREATE OR REPLACE FUNCTION search_sections(
    p_query TEXT,
    p_subjects TEXT[] DEFAULT NULL,
    p_limit INTEGER DEFAULT 100
)
RETURNS SETOF public.cpcc_sections AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM public.cpcc_sections
    WHERE to_tsvector('english', title) @@ plainto_tsquery('english', p_query)
    AND (p_subjects IS NULL OR subject_code = ANY(p_subjects))
    ORDER BY ts_rank(to_tsvector('english', title), plainto_tsquery('english', p_query)) DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;

-- =============================================================================
-- Function: Get sync job history
-- Returns recent sync jobs for monitoring
-- =============================================================================

CREATE OR REPLACE FUNCTION get_sync_history(
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    job_id UUID,
    status TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    sections_fetched INTEGER,
    duration_seconds NUMERIC,
    triggered_by TEXT,
    error_message TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        j.id,
        j.status,
        j.started_at,
        j.completed_at,
        j.sections_fetched,
        CASE WHEN j.completed_at IS NOT NULL AND j.started_at IS NOT NULL
            THEN EXTRACT(EPOCH FROM (j.completed_at - j.started_at))
            ELSE NULL
        END,
        j.triggered_by,
        j.error_message
    FROM public.cpcc_sync_jobs j
    ORDER BY j.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;
