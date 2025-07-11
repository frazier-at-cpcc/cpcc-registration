"""CPCC course search service."""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx

from app.config import settings
from app.core.exceptions import CPCCRequestError, CPCCParsingError, ValidationError
from app.core.logging import LoggerMixin
from app.models.cpcc_responses import CPCCSearchResponse, CPCCCourseInfo
from app.services.session_manager import CPCCSessionManager


class CourseSearchService(LoggerMixin):
    """Service for searching courses using CPCC's PostSearchCriteria endpoint."""
    
    def __init__(self, session_manager: CPCCSessionManager):
        self.session_manager = session_manager
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
    
    async def search_courses(self, subjects: List[str], term: Optional[str] = None) -> CPCCSearchResponse:
        """Search for courses by subject codes."""
        if not subjects:
            raise ValidationError("At least one subject code is required")
        
        if len(subjects) > settings.max_subjects_per_request:
            raise ValidationError(
                f"Too many subjects requested. Maximum is {settings.max_subjects_per_request}"
            )
        
        # Validate subject codes (basic validation)
        for subject in subjects:
            if not subject or not subject.strip():
                raise ValidationError(f"Invalid subject code: '{subject}'")
            if len(subject.strip()) > 10:  # Reasonable limit
                raise ValidationError(f"Subject code too long: '{subject}'")
        
        async with self._semaphore:
            return await self._perform_search(subjects, term)
    
    async def _perform_search(self, subjects: List[str], term: Optional[str] = None) -> CPCCSearchResponse:
        """Perform the actual search request."""
        try:
            # Get authenticated HTTP client
            client = await self.session_manager.get_authenticated_client()
            
            # Build search payload
            payload = self._build_search_payload(subjects, term)
            
            # Make request
            url = f"{settings.cpcc_base_url}/Student/Courses/PostSearchCriteria"
            
            self.log_request("POST", url, subjects=subjects, term=term)
            start_time = datetime.utcnow()
            
            response = await client.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json, charset=utf-8",
                    "Accept": "application/json, text/javascript, */*; q=0.01"
                }
            )
            
            response_time = (datetime.utcnow() - start_time).total_seconds()
            self.log_response(response.status_code, response_time)
            
            if response.status_code == 401 or response.status_code == 403:
                # Session might be expired, try to refresh
                self.logger.warning("Received authentication error, refreshing session")
                await self.session_manager.refresh_session()
                
                # Retry with new session
                client = await self.session_manager.get_authenticated_client()
                response = await client.post(url, json=payload, headers={
                    "Content-Type": "application/json, charset=utf-8",
                    "Accept": "application/json, text/javascript, */*; q=0.01"
                })
            
            if response.status_code != 200:
                raise CPCCRequestError(
                    f"Course search failed with status {response.status_code}",
                    status_code=response.status_code,
                    details={"subjects": subjects, "term": term}
                )
            
            # Parse response
            return self._parse_search_response(response.json())
            
        except httpx.RequestError as e:
            self.log_error(e, "course search")
            raise CPCCRequestError(f"Network error during course search: {str(e)}")
        except Exception as e:
            self.log_error(e, "course search")
            raise
    
    def _build_search_payload(self, subjects: List[str], term: Optional[str] = None) -> Dict[str, Any]:
        """Build the search payload for CPCC API."""
        payload = {
            "keyword": None,
            "terms": [term] if term else [],
            "requirement": None,
            "subrequirement": None,
            "courseIds": None,
            "sectionIds": None,
            "requirementText": None,
            "subrequirementText": "",
            "group": None,
            "startTime": None,
            "endTime": None,
            "openSections": None,
            "subjects": [subject.strip().upper() for subject in subjects],
            "academicLevels": [],
            "courseLevels": [],
            "synonyms": [],
            "courseTypes": [],
            "topicCodes": [],
            "days": [],
            "locations": [],
            "faculty": [],
            "onlineCategories": None,
            "keywordComponents": [],
            "startDate": None,
            "endDate": None,
            "startsAtTime": None,
            "endsByTime": None,
            "pageNumber": 1,
            "sortOn": "None",
            "sortDirection": "Ascending",
            "subjectsBadge": [],
            "locationsBadge": [],
            "termFiltersBadge": [],
            "daysBadge": [],
            "facultyBadge": [],
            "academicLevelsBadge": [],
            "courseLevelsBadge": [],
            "courseTypesBadge": [],
            "topicCodesBadge": [],
            "onlineCategoriesBadge": [],
            "openSectionsBadge": "",
            "openAndWaitlistedSectionsBadge": "",
            "subRequirementText": None,
            "quantityPerPage": 30,
            "openAndWaitlistedSections": None,
            "searchResultsView": "CatalogListing"
        }
        
        return payload
    
    def _parse_search_response(self, response_data: Dict[str, Any]) -> CPCCSearchResponse:
        """Parse the search response from CPCC."""
        try:
            courses = []
            
            # Parse courses from response
            for course_data in response_data.get("Courses", []):
                course = CPCCCourseInfo(
                    id=course_data.get("Id", ""),
                    subject_code=course_data.get("SubjectCode", ""),
                    number=course_data.get("Number", ""),
                    title=course_data.get("Title", ""),
                    description=course_data.get("Description", ""),
                    minimum_credits=course_data.get("MinimumCredits"),
                    maximum_credits=course_data.get("MaximumCredits"),
                    matching_section_ids=course_data.get("MatchingSectionIds", [])
                )
                courses.append(course)
            
            # Parse terms information
            terms = []
            for term_data in response_data.get("ActivePlanTerms", []):
                # Note: We're not parsing full term info here since it's complex
                # and not immediately needed for enrollment data
                pass
            
            search_response = CPCCSearchResponse(
                courses=courses,
                total_items=response_data.get("TotalItems", 0),
                total_pages=response_data.get("TotalPages", 0),
                current_page_index=response_data.get("CurrentPageIndex", 1),
                subjects=response_data.get("Subjects", []),
                active_plan_terms=terms
            )
            
            total_sections = sum(len(course.matching_section_ids) for course in courses)
            self.logger.info(
                f"Successfully parsed search response: {len(courses)} courses found, "
                f"{total_sections} total sections"
            )
            
            return search_response
            
        except Exception as e:
            self.log_error(e, "search response parsing")
            raise CPCCParsingError(f"Failed to parse search response: {str(e)}")
    
    async def search_all_pages(self, subjects: List[str], term: Optional[str] = None) -> CPCCSearchResponse:
        """Search all pages of results for the given subjects."""
        # For now, we'll implement single page search
        # This can be extended to handle pagination if needed
        return await self.search_courses(subjects, term)
    
    def get_course_section_mapping(self, search_response: CPCCSearchResponse) -> Dict[str, List[str]]:
        """Get a mapping of course IDs to their section IDs."""
        mapping = {}
        for course in search_response.courses:
            if course.matching_section_ids:
                mapping[course.id] = course.matching_section_ids
        return mapping
    
    def get_unique_section_ids(self, search_response: CPCCSearchResponse) -> List[str]:
        """Get all unique section IDs from the search response."""
        section_ids = set()
        for course in search_response.courses:
            section_ids.update(course.matching_section_ids)
        return list(section_ids)


# Alias for backward compatibility
CourseSearchService = CourseSearchService