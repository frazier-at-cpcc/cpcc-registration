"""Enrollment API endpoints."""

import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Query, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.exceptions import (
    CPCCError, 
    AuthenticationError, 
    NetworkError, 
    ValidationError,
    CacheError
)
from app.core.logging import LoggerMixin
from app.models.enrollment import EnrollmentResponse, CourseSection
from app.services.session_manager import SessionManager
from app.services.course_search import CourseSearchService
from app.services.section_details import SectionDetailsService
from app.services.cache_service import cache_service


router = APIRouter(prefix="/api/v1", tags=["enrollment"])


class EnrollmentAPI(LoggerMixin):
    """Main enrollment API service."""
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.course_search = CourseSearchService(self.session_manager)
        self.section_details = SectionDetailsService(self.session_manager)
    
    async def get_enrollment_data(
        self,
        subjects: List[str],
        term: Optional[str] = None,
        use_cache: bool = True,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> EnrollmentResponse:
        """Get enrollment data for specified subjects."""
        
        # Validate subjects
        if not subjects:
            raise ValidationError("At least one subject must be specified", "subjects")
        
        # Clean and validate subject codes
        clean_subjects = []
        for subject in subjects:
            clean_subject = subject.strip().upper()
            if not clean_subject:
                continue
            if len(clean_subject) > 10:  # Reasonable limit
                raise ValidationError(f"Subject code too long: {clean_subject}", "subjects")
            clean_subjects.append(clean_subject)
        
        if not clean_subjects:
            raise ValidationError("No valid subjects provided", "subjects")
        
        self.logger.info(f"Processing enrollment request for subjects: {clean_subjects}")
        
        # Try cache first if enabled
        if use_cache:
            try:
                cached_data = await cache_service.get_enrollment_data(
                    subjects=clean_subjects,
                    term=term
                )
                if cached_data:
                    self.logger.info(f"Returning cached data for subjects: {clean_subjects}")
                    return cached_data
            except Exception as e:
                self.log_error(e, "cache retrieval")
                # Continue without cache
        
        # Fetch fresh data
        try:
            enrollment_data = await self._fetch_enrollment_data(clean_subjects, term)
            
            # Cache the results in background if enabled
            if use_cache and background_tasks:
                background_tasks.add_task(
                    self._cache_enrollment_data,
                    enrollment_data,
                    clean_subjects,
                    term
                )
            
            return enrollment_data
            
        except CPCCError:
            raise
        except Exception as e:
            self.log_error(e, "enrollment data fetch")
            raise CPCCError(f"Unexpected error fetching enrollment data: {str(e)}", "fetch")
    
    async def _fetch_enrollment_data(
        self, 
        subjects: List[str], 
        term: Optional[str]
    ) -> EnrollmentResponse:
        """Fetch enrollment data from CPCC."""
        
        start_time = datetime.utcnow()
        all_sections = []
        errors = []
        
        try:
            # Initialize session
            async with self.session_manager as session:
                
                # Search for courses in each subject
                search_tasks = []
                for subject in subjects:
                    task = self._search_subject_courses(session, subject, term)
                    search_tasks.append(task)
                
                # Execute searches concurrently with semaphore
                semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
                search_results = await asyncio.gather(
                    *[self._execute_with_semaphore(semaphore, task) for task in search_tasks],
                    return_exceptions=True
                )
                
                # Process search results and combine course-section mappings
                combined_mapping = {}
                for i, result in enumerate(search_results):
                    if isinstance(result, Exception):
                        error_msg = f"Failed to search subject {subjects[i]}: {str(result)}"
                        errors.append(error_msg)
                        self.log_error(result, f"subject search: {subjects[i]}")
                    else:
                        # Merge the course-section mapping
                        combined_mapping.update(result)
                
                if not combined_mapping:
                    if errors:
                        raise CPCCError(f"No sections found. Errors: {'; '.join(errors)}", "search")
                    else:
                        # Return empty response
                        return EnrollmentResponse(
                            subjects=subjects,
                            term=term,
                            sections=[],
                            total_sections=0,
                            retrieved_at=start_time,
                            processing_time_seconds=0.0,
                            errors=[]
                        )
                
                total_sections = sum(len(section_ids) for section_ids in combined_mapping.values())
                self.logger.info(f"Found {total_sections} sections across {len(subjects)} subjects")
                
                # Get section details for all courses
                try:
                    all_sections = await self._get_section_details(combined_mapping)
                except Exception as e:
                    error_msg = f"Failed to get section details: {str(e)}"
                    errors.append(error_msg)
                    self.log_error(e, "section details batch")
                    all_sections = []
                
                # Calculate processing time
                end_time = datetime.utcnow()
                processing_time = (end_time - start_time).total_seconds()
                
                self.logger.info(
                    f"Retrieved {len(all_sections)} sections with enrollment data "
                    f"(processing_time: {processing_time:.2f}s, errors: {len(errors)})"
                )
                
                return EnrollmentResponse(
                    subjects=subjects,
                    term=term,
                    sections=all_sections,
                    total_sections=len(all_sections),
                    retrieved_at=start_time,
                    processing_time_seconds=processing_time,
                    errors=errors if errors else None
                )
                
        except AuthenticationError:
            raise
        except NetworkError:
            raise
        except Exception as e:
            self.log_error(e, "enrollment data fetch")
            raise CPCCError(f"Failed to fetch enrollment data: {str(e)}", "fetch")
    
    async def _execute_with_semaphore(self, semaphore: asyncio.Semaphore, coro):
        """Execute coroutine with semaphore for rate limiting."""
        async with semaphore:
            return await coro
    
    async def _search_subject_courses(
        self,
        session: SessionManager,
        subject: str,
        term: Optional[str]
    ) -> Dict[str, List[str]]:
        """Search for courses in a subject and return course-to-section mapping."""
        try:
            search_results = await self.course_search.search_courses(
                subjects=[subject],
                term=term
            )
            
            # Extract course-to-section mapping
            course_section_mapping = {}
            for course in search_results.courses:
                if course.matching_section_ids:
                    course_section_mapping[course.id] = course.matching_section_ids
            
            return course_section_mapping
            
        except Exception as e:
            self.log_error(e, f"subject search: {subject}")
            raise
    
    async def _get_section_details(
        self,
        course_section_mapping: Dict[str, List[str]]
    ) -> List[CourseSection]:
        """Get detailed enrollment information for sections."""
        try:
            cpcc_sections = await self.section_details.get_section_details(
                course_section_mapping=course_section_mapping
            )
            
            # Convert CPCC section details to CourseSection models
            course_sections = []
            for cpcc_section in cpcc_sections:
                course_section = CourseSection(
                    section_id=cpcc_section.id,
                    course_id=cpcc_section.course_id,
                    subject_code=cpcc_section.course_id.split('-')[0] if '-' in cpcc_section.course_id else "",
                    course_number=cpcc_section.course_id.split('-')[1] if '-' in cpcc_section.course_id else "",
                    section_number=cpcc_section.number,
                    title=cpcc_section.title,
                    available_seats=cpcc_section.available,
                    total_capacity=cpcc_section.capacity,
                    enrolled_count=cpcc_section.enrolled,
                    waitlist_count=cpcc_section.waitlisted,
                    start_date=cpcc_section.start_date,
                    end_date=cpcc_section.end_date,
                    location=cpcc_section.location_display,
                    credits=cpcc_section.minimum_credits,
                    term=getattr(cpcc_section, 'term', None),
                    meeting_times=[
                        {
                            "days": mt.days_of_week_display,
                            "start_time": mt.start_time_display,
                            "end_time": mt.end_time_display,
                            "location": f"{mt.building_display} {mt.room_display}".strip(),
                            "is_online": mt.is_online
                        }
                        for mt in cpcc_section.formatted_meeting_times
                    ]
                )
                course_sections.append(course_section)
            
            return course_sections
            
        except Exception as e:
            self.log_error(e, "section details conversion")
            raise
    
    async def _cache_enrollment_data(
        self,
        enrollment_data: EnrollmentResponse,
        subjects: List[str],
        term: Optional[str]
    ) -> None:
        """Cache enrollment data in background."""
        try:
            await cache_service.cache_enrollment_data(
                enrollment_data=enrollment_data,
                subjects=subjects,
                term=term
            )
        except Exception as e:
            self.log_error(e, "background cache")
            # Don't raise exception in background task


# Global API instance
enrollment_api = EnrollmentAPI()


@router.get("/enrollment", response_model=EnrollmentResponse)
async def get_enrollment(
    subjects: str = Query(
        ...,
        description="Comma-separated list of subject codes (e.g., 'CCT,CSC,MAT')",
        example="CCT,CSC"
    ),
    term: Optional[str] = Query(
        None,
        description="Academic term (optional, uses current term if not specified)",
        example="202401"
    ),
    use_cache: bool = Query(
        True,
        description="Whether to use cached data if available"
    ),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> EnrollmentResponse:
    """
    Get course enrollment data for specified subjects.
    
    Returns enrollment information including:
    - Available seats
    - Total capacity
    - Waitlist information
    - Course and section details
    
    **Parameters:**
    - **subjects**: Comma-separated subject codes (e.g., "CCT,CSC,MAT")
    - **term**: Academic term (optional, defaults to current term)
    - **use_cache**: Whether to use cached data (default: true)
    
    **Example:**
    ```
    GET /api/v1/enrollment?subjects=CCT,CSC&term=202401
    ```
    """
    try:
        # Parse subjects from comma-separated string
        subject_list = [s.strip() for s in subjects.split(",") if s.strip()]
        
        if not subject_list:
            raise HTTPException(
                status_code=400,
                detail="At least one subject must be specified"
            )
        
        # Get enrollment data
        result = await enrollment_api.get_enrollment_data(
            subjects=subject_list,
            term=term,
            use_cache=use_cache,
            background_tasks=background_tasks
        )
        
        return result
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except NetworkError as e:
        raise HTTPException(status_code=503, detail=f"Service temporarily unavailable: {str(e)}")
    except CPCCError as e:
        raise HTTPException(status_code=502, detail=f"CPCC service error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/enrollment/subjects/{subject}", response_model=EnrollmentResponse)
async def get_enrollment_by_subject(
    subject: str,
    term: Optional[str] = Query(None, description="Academic term"),
    use_cache: bool = Query(True, description="Whether to use cached data"),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> EnrollmentResponse:
    """
    Get course enrollment data for a single subject.
    
    **Parameters:**
    - **subject**: Subject code (e.g., "CCT", "CSC", "MAT")
    - **term**: Academic term (optional)
    - **use_cache**: Whether to use cached data (default: true)
    """
    return await get_enrollment(
        subjects=subject,
        term=term,
        use_cache=use_cache,
        background_tasks=background_tasks
    )


@router.get("/enrollment/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for the enrollment service.
    
    Returns service status and basic statistics.
    """
    try:
        # Check cache service
        cache_healthy = await cache_service.health_check()
        cache_stats = await cache_service.get_cache_stats()
        
        # Basic session manager check
        session_healthy = True
        try:
            async with SessionManager() as session:
                session_healthy = session.is_authenticated()
        except Exception:
            session_healthy = False
        
        return {
            "status": "healthy" if cache_healthy and session_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "cache": {
                    "healthy": cache_healthy,
                    "stats": cache_stats
                },
                "session": {
                    "healthy": session_healthy
                }
            },
            "version": "1.0.0"
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )


@router.post("/enrollment/cache/invalidate")
async def invalidate_cache(
    pattern: str = Query(
        "enrollment:*",
        description="Cache key pattern to invalidate"
    )
) -> Dict[str, Any]:
    """
    Invalidate cached enrollment data.
    
    **Parameters:**
    - **pattern**: Cache key pattern (default: "enrollment:*")
    
    **Note:** This endpoint should be protected in production.
    """
    try:
        deleted_count = await cache_service.invalidate_cache(pattern)
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "pattern": pattern,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except CacheError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to invalidate cache")


@router.get("/enrollment/cache/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics and information.
    """
    try:
        stats = await cache_service.get_cache_stats()
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )