"""CPCC section details service."""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx

from app.config import settings
from app.core.exceptions import CPCCRequestError, CPCCParsingError, ValidationError
from app.core.logging import LoggerMixin
from app.models.cpcc_responses import CPCCSectionsResponse, CPCCSectionDetail
from app.services.session_manager import CPCCSessionManager


class SectionDetailsService(LoggerMixin):
    """Service for retrieving section details using CPCC's Sections endpoint."""
    
    def __init__(self, session_manager: CPCCSessionManager):
        self.session_manager = session_manager
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
    
    async def get_section_details(
        self, 
        course_section_mapping: Dict[str, List[str]]
    ) -> List[CPCCSectionDetail]:
        """Get detailed information for multiple course sections."""
        if not course_section_mapping:
            return []
        
        all_sections = []
        
        # Process each course's sections
        tasks = []
        for course_id, section_ids in course_section_mapping.items():
            if section_ids:  # Only process if there are section IDs
                task = self._get_course_sections(course_id, section_ids)
                tasks.append(task)
        
        # Execute all requests concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    self.log_error(result, "section details batch processing")
                    # Continue with other results rather than failing completely
                    continue
                elif isinstance(result, list):
                    all_sections.extend(result)
        
        self.logger.info(f"Retrieved details for {len(all_sections)} sections")
        return all_sections
    
    async def _get_course_sections(self, course_id: str, section_ids: List[str]) -> List[CPCCSectionDetail]:
        """Get section details for a specific course."""
        async with self._semaphore:
            return await self._perform_sections_request(course_id, section_ids)
    
    async def _perform_sections_request(self, course_id: str, section_ids: List[str]) -> List[CPCCSectionDetail]:
        """Perform the actual sections request."""
        try:
            # Get authenticated HTTP client
            client = await self.session_manager.get_authenticated_client()
            
            # Build request payload
            payload = {
                "courseId": course_id,
                "sectionIds": section_ids
            }
            
            # Make request
            url = f"{settings.cpcc_base_url}/Student/Courses/Sections"
            
            self.log_request("POST", url, course_id=course_id, section_count=len(section_ids))
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
            
            if response.status_code in [302, 401, 403]:
                # Session might be expired, try to refresh
                # 302 redirects typically indicate redirect to login page
                self.logger.warning(f"Received status {response.status_code}, refreshing session")
                await self.session_manager.refresh_session()

                # Retry with new session
                client = await self.session_manager.get_authenticated_client()
                response = await client.post(url, json=payload, headers={
                    "Content-Type": "application/json, charset=utf-8",
                    "Accept": "application/json, text/javascript, */*; q=0.01"
                })

            if response.status_code != 200:
                raise CPCCRequestError(
                    f"Section details request failed with status {response.status_code}",
                    status_code=response.status_code,
                    details={"course_id": course_id, "section_ids": section_ids}
                )
            
            # Parse response
            return self._parse_sections_response(response.json())
            
        except httpx.RequestError as e:
            self.log_error(e, "section details request")
            raise CPCCRequestError(f"Network error during section details request: {str(e)}")
        except Exception as e:
            self.log_error(e, "section details request")
            raise
    
    def _parse_sections_response(self, response_data: Dict[str, Any]) -> List[CPCCSectionDetail]:
        """Parse the sections response from CPCC."""
        try:
            sections = []
            
            # Navigate the complex nested structure
            sections_retrieved = response_data.get("SectionsRetrieved", {})
            terms_and_sections = sections_retrieved.get("TermsAndSections", [])
            
            for term_data in terms_and_sections:
                term_info = term_data.get("Term", {})
                term_sections = term_data.get("Sections", [])
                
                for section_data in term_sections:
                    try:
                        section_info = section_data.get("Section", {})
                        
                        # Extract meeting times
                        meeting_times = []
                        for meeting in section_info.get("FormattedMeetingTimes", []):
                            meeting_times.append({
                                "days_of_week_display": meeting.get("DaysOfWeekDisplay", ""),
                                "start_time_display": meeting.get("StartTimeDisplay", ""),
                                "end_time_display": meeting.get("EndTimeDisplay", ""),
                                "instructional_method_display": meeting.get("InstructionalMethodDisplay", ""),
                                "building_display": meeting.get("BuildingDisplay", ""),
                                "room_display": meeting.get("RoomDisplay", ""),
                                "dates_display": meeting.get("DatesDisplay", ""),
                                "is_online": meeting.get("IsOnline", False)
                            })
                        
                        # Extract instructor information
                        instructor_names = []
                        
                        # Primary method: Check FacultyDisplay field (string)
                        faculty_display = section_data.get("FacultyDisplay", "")
                        if faculty_display and faculty_display.strip():
                            instructor_names.append(faculty_display.strip())
                        
                        # Secondary method: Check InstructorDetails array
                        instructor_details = section_data.get("InstructorDetails", [])
                        if instructor_details and isinstance(instructor_details, list):
                            for instructor in instructor_details:
                                if isinstance(instructor, dict):
                                    faculty_name = instructor.get("FacultyName", "")
                                    if faculty_name and faculty_name.strip():
                                        faculty_name = faculty_name.strip()
                                        if faculty_name not in instructor_names:
                                            instructor_names.append(faculty_name)
                        
                        # Create section detail
                        section = CPCCSectionDetail(
                            id=section_info.get("Id", ""),
                            course_id=section_info.get("CourseId", ""),
                            number=section_info.get("SectionNameDisplay", ""),
                            title=section_info.get("SectionTitleDisplay", ""),
                            available=section_info.get("Available", 0),
                            capacity=section_info.get("Capacity", 0),
                            enrolled=section_info.get("Enrolled", 0),
                            waitlisted=section_info.get("Waitlisted", 0),
                            start_date=section_info.get("StartDateDisplay", ""),
                            end_date=section_info.get("EndDateDisplay", ""),
                            location_display=section_info.get("LocationDisplay", ""),
                            minimum_credits=section_info.get("MinimumCredits"),
                            formatted_meeting_times=meeting_times,
                            instructor_names=instructor_names
                        )
                        
                        # Add term information to section
                        section.term = term_info.get("Description", "")
                        
                        sections.append(section)
                        
                    except Exception as e:
                        # Log error for this specific section but continue with others
                        section_num = section_data.get("Section", {}).get("SectionNameDisplay", "unknown")
                        if hasattr(self, 'logger'):
                            self.logger.error(f"Failed to parse section {section_num}: {str(e)}", exc_info=True)
                        continue
            
            return sections
            
        except Exception as e:
            self.log_error(e, "sections response parsing")
            raise CPCCParsingError(f"Failed to parse sections response: {str(e)}")
    
    async def get_single_section_details(self, course_id: str, section_id: str) -> Optional[CPCCSectionDetail]:
        """Get details for a single section."""
        sections = await self._perform_sections_request(course_id, [section_id])
        return sections[0] if sections else None
    
    def filter_sections_by_availability(
        self, 
        sections: List[CPCCSectionDetail], 
        only_available: bool = False
    ) -> List[CPCCSectionDetail]:
        """Filter sections based on availability."""
        if not only_available:
            return sections
        
        return [section for section in sections if section.available > 0]
    
    def filter_sections_by_online(
        self, 
        sections: List[CPCCSectionDetail], 
        online_only: bool = False
    ) -> List[CPCCSectionDetail]:
        """Filter sections based on online delivery."""
        if not online_only:
            return sections
        
        return [section for section in sections if section.is_online]
    
    def group_sections_by_course(
        self, 
        sections: List[CPCCSectionDetail]
    ) -> Dict[str, List[CPCCSectionDetail]]:
        """Group sections by course code."""
        grouped = {}
        for section in sections:
            course_code = section.course_code
            if course_code not in grouped:
                grouped[course_code] = []
            grouped[course_code].append(section)
        return grouped
    
    def calculate_enrollment_stats(self, sections: List[CPCCSectionDetail]) -> Dict[str, Any]:
        """Calculate enrollment statistics for a list of sections."""
        if not sections:
            return {
                "total_sections": 0,
                "total_capacity": 0,
                "total_enrolled": 0,
                "total_available": 0,
                "total_waitlisted": 0,
                "average_utilization": 0.0,
                "sections_full": 0,
                "sections_with_waitlist": 0
            }
        
        total_capacity = sum(section.capacity for section in sections)
        total_enrolled = sum(section.enrolled for section in sections)
        total_available = sum(section.available for section in sections)
        total_waitlisted = sum(section.waitlisted for section in sections)
        
        sections_full = len([s for s in sections if s.available <= 0])
        sections_with_waitlist = len([s for s in sections if s.waitlisted > 0])
        
        average_utilization = 0.0
        if total_capacity > 0:
            average_utilization = (total_enrolled / total_capacity) * 100
        
        return {
            "total_sections": len(sections),
            "total_capacity": total_capacity,
            "total_enrolled": total_enrolled,
            "total_available": total_available,
            "total_waitlisted": total_waitlisted,
            "average_utilization": round(average_utilization, 2),
            "sections_full": sections_full,
            "sections_with_waitlist": sections_with_waitlist
        }


# Alias for backward compatibility
SectionDetailsService = SectionDetailsService