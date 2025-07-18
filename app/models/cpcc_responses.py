"""Pydantic models for CPCC API responses."""

from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class CPCCSession(BaseModel):
    """CPCC session information."""
    
    cookies: Dict[str, str] = Field(..., description="Session cookies")
    csrf_token: str = Field(..., description="CSRF verification token")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation time")
    expires_at: datetime = Field(..., description="Session expiration time")
    
    @property
    def is_expired(self) -> bool:
        """Check if the session is expired."""
        return datetime.utcnow() >= self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if the session is valid (has required data and not expired)."""
        return (
            bool(self.cookies.get('.ColleagueSelfServiceAntiforgery')) and
            bool(self.csrf_token) and
            not self.is_expired
        )


class CPCCCourseInfo(BaseModel):
    """Course information from CPCC search response."""
    
    id: str = Field(..., description="Course ID")
    subject_code: str = Field(..., description="Subject code (e.g., CCT)")
    number: str = Field(..., description="Course number (e.g., 110)")
    title: str = Field(..., description="Course title")
    description: str = Field(..., description="Course description")
    minimum_credits: Optional[float] = Field(None, description="Minimum credit hours")
    maximum_credits: Optional[float] = Field(None, description="Maximum credit hours")
    matching_section_ids: List[str] = Field(default_factory=list, description="Section IDs for this course")


class CPCCMeetingTime(BaseModel):
    """Meeting time information from CPCC."""
    
    days_of_week_display: str = Field(..., description="Days of week display")
    start_time_display: str = Field(..., description="Start time display")
    end_time_display: str = Field(..., description="End time display")
    instructional_method_display: str = Field(..., description="Instructional method")
    building_display: str = Field(..., description="Building")
    room_display: str = Field(..., description="Room")
    dates_display: str = Field(..., description="Date range display")
    is_online: bool = Field(default=False, description="Whether this is online")


class CPCCSectionDetail(BaseModel):
    """Section detail from CPCC response."""
    
    id: str = Field(..., description="Section ID")
    course_id: str = Field(..., description="Course ID")
    number: str = Field(..., description="Section number")
    title: str = Field(..., description="Course title")
    available: int = Field(..., description="Available seats")
    capacity: int = Field(..., description="Total capacity")
    enrolled: int = Field(..., description="Currently enrolled")
    waitlisted: int = Field(default=0, description="Waitlisted students")
    start_date: str = Field(..., description="Start date")
    end_date: str = Field(..., description="End date")
    location_display: str = Field(..., description="Location display")
    minimum_credits: Optional[float] = Field(None, description="Minimum credits")
    formatted_meeting_times: List[CPCCMeetingTime] = Field(default_factory=list, description="Meeting times")
    term: Optional[str] = Field(None, description="Academic term")
    instructor_names: List[str] = Field(default_factory=list, description="Instructor names")
    
    @property
    def is_online(self) -> bool:
        """Check if this section is online."""
        return any(meeting.is_online for meeting in self.formatted_meeting_times)
    
    @property
    def course_code(self) -> str:
        """Generate course code from section number."""
        # Extract subject and course number from section number
        # Example: "CCT-110-N886" -> "CCT-110"
        parts = self.number.split('-')
        if len(parts) >= 2:
            return f"{parts[0]}-{parts[1]}"
        return self.number


class CPCCTermInfo(BaseModel):
    """Term information from CPCC."""
    
    code: str = Field(..., description="Term code")
    description: str = Field(..., description="Term description")
    start_date: datetime = Field(..., description="Term start date")
    end_date: datetime = Field(..., description="Term end date")


class CPCCSearchResponse(BaseModel):
    """Response from CPCC PostSearchCriteria endpoint."""
    
    courses: List[CPCCCourseInfo] = Field(default_factory=list, description="Course information")
    total_items: int = Field(default=0, description="Total number of items")
    total_pages: int = Field(default=0, description="Total number of pages")
    current_page_index: int = Field(default=1, description="Current page index")
    subjects: List[Dict[str, Any]] = Field(default_factory=list, description="Subject filters")
    active_plan_terms: List[CPCCTermInfo] = Field(default_factory=list, description="Available terms")


class CPCCSectionsResponse(BaseModel):
    """Response from CPCC Sections endpoint."""
    
    sections_retrieved: Dict[str, Any] = Field(..., description="Retrieved sections data")
    course: CPCCCourseInfo = Field(..., description="Course information")
    
    def get_sections(self) -> List[CPCCSectionDetail]:
        """Extract section details from the complex response structure."""
        sections = []
        
        # Navigate the complex nested structure
        terms_and_sections = self.sections_retrieved.get("TermsAndSections", [])
        
        for term_data in terms_and_sections:
            term_sections = term_data.get("Sections", [])
            
            for section_data in term_sections:
                section_info = section_data.get("Section", {})
                
                # Extract meeting times
                meeting_times = []
                for meeting in section_info.get("FormattedMeetingTimes", []):
                    meeting_times.append(CPCCMeetingTime(
                        days_of_week_display=meeting.get("DaysOfWeekDisplay", ""),
                        start_time_display=meeting.get("StartTimeDisplay", ""),
                        end_time_display=meeting.get("EndTimeDisplay", ""),
                        instructional_method_display=meeting.get("InstructionalMethodDisplay", ""),
                        building_display=meeting.get("BuildingDisplay", ""),
                        room_display=meeting.get("RoomDisplay", ""),
                        dates_display=meeting.get("DatesDisplay", ""),
                        is_online=meeting.get("IsOnline", False)
                    ))
                
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
                    formatted_meeting_times=meeting_times
                )
                
                sections.append(section)
        
        return sections


class CPCCErrorResponse(BaseModel):
    """Error response from CPCC API."""
    
    error_message: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")