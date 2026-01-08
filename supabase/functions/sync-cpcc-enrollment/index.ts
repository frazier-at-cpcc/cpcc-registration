// Supabase Edge Function: sync-cpcc-enrollment
// Fetches enrollment data from CPCC and stores it in Supabase
//
// Trigger: External scheduler (GitHub Actions, cron-job.org) every 3 minutes
// POST https://[project].supabase.co/functions/v1/sync-cpcc-enrollment

import { serve } from "https://deno.land/std@0.177.0/http/server.ts";
import { createClient, SupabaseClient } from "https://esm.sh/@supabase/supabase-js@2";

// =============================================================================
// Configuration
// =============================================================================

const CPCC_BASE_URL = "https://mycollegess.cpcc.edu";
const SUBJECTS = ["CTI", "CTS", "CCT", "CSC", "CIS", "NET", "NOS", "SEC", "DBA", "SGD", "WEB", "WBL"];
const TERMS = ["2026SP", "2025FA", "2026SU"]; // Spring 2026, Fall 2025, Summer 2026
const DELAY_BETWEEN_SUBJECTS_MS = 500;
const USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:140.0) Gecko/20100101 Firefox/140.0";

// =============================================================================
// Types
// =============================================================================

interface CpccSession {
  cookies: Record<string, string>;
  csrfToken: string;
  expiresAt: Date;
}

interface SectionData {
  section_id: string;
  course_id: string;
  subject_code: string;
  course_number: string;
  section_number: string;
  title: string;
  available_seats: number;
  total_capacity: number;
  enrolled_count: number;
  waitlist_count: number;
  start_date: string | null;
  end_date: string | null;
  location: string | null;
  credits: number | null;
  term: string | null;
  meeting_times: MeetingTime[];
  instructors: string[];
}

interface MeetingTime {
  days: string;
  start_time: string;
  end_time: string;
  location: string;
  is_online: boolean;
}

interface CourseSearchResult {
  courseId: string;
  subjectCode: string;
  courseNumber: string;
  title: string;
  sectionIds: string[];
}

// =============================================================================
// CPCC Session Management
// =============================================================================

async function initSession(): Promise<CpccSession> {
  console.log("Initializing CPCC session...");

  const response = await fetch(`${CPCC_BASE_URL}/Student/Courses/Search`, {
    method: "GET",
    headers: {
      "User-Agent": USER_AGENT,
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "en-US,en;q=0.5",
    },
    redirect: "follow",
  });

  if (!response.ok) {
    throw new Error(`Failed to init session: HTTP ${response.status}`);
  }

  // Extract cookies from Set-Cookie headers
  const cookies: Record<string, string> = {};
  const setCookieHeaders = response.headers.getSetCookie?.() || [];

  for (const cookie of setCookieHeaders) {
    const [nameValue] = cookie.split(";");
    const eqIndex = nameValue.indexOf("=");
    if (eqIndex > 0) {
      const name = nameValue.substring(0, eqIndex).trim();
      const value = nameValue.substring(eqIndex + 1).trim();
      cookies[name] = value;
    }
  }

  // Check for antiforgery cookie
  if (!cookies[".ColleagueSelfServiceAntiforgery"]) {
    // Try alternate method - check response headers directly
    const allCookies = response.headers.get("set-cookie") || "";
    const match = allCookies.match(/\.ColleagueSelfServiceAntiforgery=([^;]+)/);
    if (match) {
      cookies[".ColleagueSelfServiceAntiforgery"] = match[1];
    }
  }

  if (!cookies[".ColleagueSelfServiceAntiforgery"]) {
    throw new Error("Failed to get authentication cookie from CPCC");
  }

  // Extract CSRF token from HTML
  const html = await response.text();

  // Try multiple patterns for CSRF token extraction
  let csrfToken: string | null = null;

  // Pattern 1: Input field with name attribute
  const inputMatch = html.match(/name="__RequestVerificationToken"[^>]*value="([^"]+)"/);
  if (inputMatch) {
    csrfToken = inputMatch[1];
  }

  // Pattern 2: Input field with value first
  if (!csrfToken) {
    const valueFirstMatch = html.match(/value="([^"]+)"[^>]*name="__RequestVerificationToken"/);
    if (valueFirstMatch) {
      csrfToken = valueFirstMatch[1];
    }
  }

  // Pattern 3: Meta tag
  if (!csrfToken) {
    const metaMatch = html.match(/<meta[^>]*name="__RequestVerificationToken"[^>]*content="([^"]+)"/);
    if (metaMatch) {
      csrfToken = metaMatch[1];
    }
  }

  // Pattern 4: JavaScript variable
  if (!csrfToken) {
    const jsMatch = html.match(/antiForgeryToken['"]\s*:\s*['"]([^'"]+)['"]/);
    if (jsMatch) {
      csrfToken = jsMatch[1];
    }
  }

  if (!csrfToken) {
    throw new Error("Failed to extract CSRF token from CPCC response");
  }

  console.log("Session initialized successfully");

  return {
    cookies,
    csrfToken,
    expiresAt: new Date(Date.now() + 25 * 60 * 1000), // 25 minutes
  };
}

function buildCookieHeader(session: CpccSession): string {
  return Object.entries(session.cookies)
    .map(([k, v]) => `${k}=${v}`)
    .join("; ");
}

// =============================================================================
// CPCC Course Search
// =============================================================================

async function searchCourses(
  session: CpccSession,
  subject: string,
  term: string
): Promise<CourseSearchResult[]> {
  const payload = {
    keyword: null,
    terms: [term],
    requirement: null,
    subrequirement: null,
    courseIds: null,
    sectionIds: null,
    subjects: [subject.toUpperCase()],
    academicLevels: [],
    courseLevels: [],
    synonyms: [],
    courseTypes: [],
    topicCodes: [],
    days: [],
    locations: [],
    faculty: [],
    onlineCategories: null,
    keywordComponents: [],
    pageNumber: 1,
    quantityPerPage: 500, // Get all at once
    sortOn: "None",
    sortDirection: "Ascending",
    searchResultsView: "CatalogListing",
  };

  const response = await fetch(`${CPCC_BASE_URL}/Student/Courses/PostSearchCriteria`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Cookie": buildCookieHeader(session),
      "__RequestVerificationToken": session.csrfToken,
      "__IsGuestUser": "true",
      "X-Requested-With": "XMLHttpRequest",
      "Origin": CPCC_BASE_URL,
      "Referer": `${CPCC_BASE_URL}/Student/Courses`,
      "User-Agent": USER_AGENT,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Course search failed: HTTP ${response.status}`);
  }

  const data = await response.json();
  const courses: CourseSearchResult[] = [];

  for (const course of data.Courses || []) {
    if (course.MatchingSectionIds && course.MatchingSectionIds.length > 0) {
      courses.push({
        courseId: course.Id,
        subjectCode: course.SubjectCode || subject,
        courseNumber: course.Number || "",
        title: course.Title || "",
        sectionIds: course.MatchingSectionIds,
      });
    }
  }

  return courses;
}

// =============================================================================
// CPCC Section Details
// =============================================================================

async function getSectionDetails(
  session: CpccSession,
  courseId: string,
  sectionIds: string[]
): Promise<SectionData[]> {
  const response = await fetch(`${CPCC_BASE_URL}/Student/Courses/Sections`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Cookie": buildCookieHeader(session),
      "__RequestVerificationToken": session.csrfToken,
      "__IsGuestUser": "true",
      "X-Requested-With": "XMLHttpRequest",
      "Origin": CPCC_BASE_URL,
      "Referer": `${CPCC_BASE_URL}/Student/Courses`,
      "User-Agent": USER_AGENT,
    },
    body: JSON.stringify({ courseId, sectionIds }),
  });

  if (!response.ok) {
    throw new Error(`Section details failed: HTTP ${response.status}`);
  }

  const data = await response.json();
  const sections: SectionData[] = [];

  // Parse the complex nested structure
  const termsAndSections = data.SectionsRetrieved?.TermsAndSections || [];

  for (const termData of termsAndSections) {
    const termInfo = termData.Term || {};
    const termSections = termData.Sections || [];

    for (const sectionData of termSections) {
      const section = sectionData.Section || {};

      // Extract meeting times
      const meetingTimes: MeetingTime[] = (section.FormattedMeetingTimes || []).map((mt: any) => ({
        days: mt.DaysOfWeekDisplay || "",
        start_time: mt.StartTimeDisplay || "",
        end_time: mt.EndTimeDisplay || "",
        location: `${mt.BuildingDisplay || ""} ${mt.RoomDisplay || ""}`.trim(),
        is_online: mt.IsOnline || false,
      }));

      // Extract instructors
      const instructors: string[] = [];
      if (sectionData.FacultyDisplay) {
        instructors.push(sectionData.FacultyDisplay.trim());
      }
      for (const instructor of sectionData.InstructorDetails || []) {
        const name = instructor.FacultyName?.trim();
        if (name && !instructors.includes(name)) {
          instructors.push(name);
        }
      }

      // Parse section number to extract subject and course number
      const sectionNumber = section.SectionNameDisplay || "";
      const parts = sectionNumber.split("-");

      sections.push({
        section_id: section.Id?.toString() || "",
        course_id: section.CourseId || courseId,
        subject_code: parts[0] || "",
        course_number: parts[1] || "",
        section_number: sectionNumber,
        title: section.SectionTitleDisplay || "",
        available_seats: section.Available ?? 0,
        total_capacity: section.Capacity ?? 0,
        enrolled_count: section.Enrolled ?? 0,
        waitlist_count: section.Waitlisted ?? 0,
        start_date: section.StartDateDisplay || null,
        end_date: section.EndDateDisplay || null,
        location: section.LocationDisplay || null,
        credits: section.MinimumCredits || null,
        term: termInfo.Description || null,
        meeting_times: meetingTimes,
        instructors,
      });
    }
  }

  return sections;
}

// =============================================================================
// Logging Helper
// =============================================================================

async function logToDb(
  supabase: SupabaseClient,
  jobId: string,
  level: string,
  message: string,
  details?: Record<string, any>,
  subjectCode?: string,
  operation?: string
) {
  try {
    await supabase.from("cpcc_sync_logs").insert({
      job_id: jobId,
      log_level: level,
      message,
      details: details || null,
      subject_code: subjectCode || null,
      operation: operation || null,
    });
  } catch (e) {
    console.error("Failed to log to DB:", e);
  }
}

// =============================================================================
// Main Sync Function
// =============================================================================

async function syncEnrollment(supabase: SupabaseClient): Promise<{
  success: boolean;
  jobId?: string;
  sectionsFetched?: number;
  error?: string;
}> {
  // Check for already running job
  const { data: runningJob } = await supabase
    .from("cpcc_sync_jobs")
    .select("id")
    .eq("status", "running")
    .gte("started_at", new Date(Date.now() - 10 * 60 * 1000).toISOString())
    .maybeSingle();

  if (runningJob) {
    return {
      success: false,
      error: "Another sync job is already running",
    };
  }

  // Create job record
  const { data: job, error: jobError } = await supabase
    .from("cpcc_sync_jobs")
    .insert({
      subjects: SUBJECTS,
      total_subjects: SUBJECTS.length,
      status: "running",
      started_at: new Date().toISOString(),
      triggered_by: "edge_function",
    })
    .select()
    .single();

  if (jobError || !job) {
    throw new Error(`Failed to create job record: ${jobError?.message}`);
  }

  const jobId = job.id;

  try {
    // Initialize session
    await logToDb(supabase, jobId, "info", "Initializing CPCC session", null, null, "session_init");
    const session = await initSession();
    await logToDb(supabase, jobId, "info", "Session initialized successfully", null, null, "session_init");

    const allSections: SectionData[] = [];
    let completedSubjects = 0;

    // Process each subject sequentially
    for (const subject of SUBJECTS) {
      await supabase
        .from("cpcc_sync_jobs")
        .update({ current_subject: subject })
        .eq("id", jobId);

      try {
        await logToDb(supabase, jobId, "info", `Processing subject: ${subject}`, null, subject, "search");

        // Search for all terms
        for (const term of TERMS) {
          try {
            const courses = await searchCourses(session, subject, term);

            for (const course of courses) {
              if (course.sectionIds.length > 0) {
                const sections = await getSectionDetails(
                  session,
                  course.courseId,
                  course.sectionIds
                );
                allSections.push(...sections);
              }
            }
          } catch (termError: any) {
            await logToDb(
              supabase,
              jobId,
              "warning",
              `Failed to process ${subject} for term ${term}: ${termError.message}`,
              { error: termError.message },
              subject,
              "search"
            );
          }
        }

        completedSubjects++;

        await supabase
          .from("cpcc_sync_jobs")
          .update({
            completed_subjects: completedSubjects,
            sections_fetched: allSections.length,
          })
          .eq("id", jobId);

        // Delay between subjects to be nice to CPCC servers
        await new Promise((r) => setTimeout(r, DELAY_BETWEEN_SUBJECTS_MS));

      } catch (subjectError: any) {
        await logToDb(
          supabase,
          jobId,
          "error",
          `Failed to process subject ${subject}: ${subjectError.message}`,
          { error: subjectError.message },
          subject,
          "sync_subject"
        );
        // Continue with other subjects
      }
    }

    // Upsert all sections to database
    if (allSections.length > 0) {
      await logToDb(
        supabase,
        jobId,
        "info",
        `Upserting ${allSections.length} sections to database`,
        null,
        null,
        "upsert"
      );

      // Batch upsert in chunks of 100
      const chunkSize = 100;
      for (let i = 0; i < allSections.length; i += chunkSize) {
        const chunk = allSections.slice(i, i + chunkSize).map((s) => ({
          ...s,
          last_sync_job_id: jobId,
          updated_at: new Date().toISOString(),
        }));

        const { error: upsertError } = await supabase
          .from("cpcc_sections")
          .upsert(chunk, { onConflict: "section_id" });

        if (upsertError) {
          throw new Error(`Upsert failed: ${upsertError.message}`);
        }
      }

      await logToDb(
        supabase,
        jobId,
        "info",
        `Successfully upserted ${allSections.length} sections`,
        null,
        null,
        "upsert"
      );
    }

    // Mark job complete
    await supabase
      .from("cpcc_sync_jobs")
      .update({
        status: "completed",
        completed_at: new Date().toISOString(),
        sections_fetched: allSections.length,
        current_subject: null,
      })
      .eq("id", jobId);

    return {
      success: true,
      jobId,
      sectionsFetched: allSections.length,
    };

  } catch (error: any) {
    // Mark job as failed
    await supabase
      .from("cpcc_sync_jobs")
      .update({
        status: "failed",
        completed_at: new Date().toISOString(),
        error_message: error.message,
        current_subject: null,
      })
      .eq("id", jobId);

    await logToDb(
      supabase,
      jobId,
      "error",
      `Sync failed: ${error.message}`,
      { error: error.message, stack: error.stack },
      null,
      "sync"
    );

    return {
      success: false,
      jobId,
      error: error.message,
    };
  }
}

// =============================================================================
// HTTP Handler
// =============================================================================

serve(async (req) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
      },
    });
  }

  // Only allow POST requests
  if (req.method !== "POST") {
    return new Response(
      JSON.stringify({ error: "Method not allowed" }),
      {
        status: 405,
        headers: { "Content-Type": "application/json" },
      }
    );
  }

  try {
    // Initialize Supabase client
    const supabaseUrl = Deno.env.get("SUPABASE_URL");
    const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");

    if (!supabaseUrl || !supabaseServiceKey) {
      throw new Error("Missing Supabase environment variables");
    }

    const supabase = createClient(supabaseUrl, supabaseServiceKey);

    // Run the sync
    const result = await syncEnrollment(supabase);

    const status = result.success ? 200 : result.error?.includes("already running") ? 409 : 500;

    return new Response(JSON.stringify(result), {
      status,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
    });

  } catch (error: any) {
    console.error("Sync error:", error);

    return new Response(
      JSON.stringify({
        success: false,
        error: error.message,
      }),
      {
        status: 500,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      }
    );
  }
});
