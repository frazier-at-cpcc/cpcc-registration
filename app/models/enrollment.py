"""Pydantic models for enrollment API responses."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EnrollmentInfo(BaseModel):
    """Enrollment information for a course section."""
    
    available: int = Field(..., description="Number of available seats")
    capacity: int = Field(..., description="Total capacity of the section")
    waitlisted: int = Field(..., description="Number of students on waitlist")
    
    @property
    def is_full(self) -> bool:
        """Check if the section is full."""
        return self.available <= 0
    
    @property
    def utilization_rate(self) -> float:
        """Calculate utilization rate as percentage."""
        if self.capacity == 0:
            return 0.0
        enrolled = self.capacity - self.available
        return (enrolled / self.capacity) * 100


class CourseSection(BaseModel):
    """Detailed information about a course section."""
    
    section_id: str = Field(..., description="Unique section identifier")
    course_id: str = Field(..., description="Course ID (e.g., CCT-110)")
    subject_code: str = Field(..., description="Subject code (e.g., CCT)")
    course_number: str = Field(..., description="Course number (e.g., 110)")
    section_number: str = Field(..., description="Section number (e.g., CCT-110-N886)")
    title: str = Field(..., description="Course title")
    available_seats: int = Field(..., description="Number of available seats")
    total_capacity: int = Field(..., description="Total capacity of the section")
    enrolled_count: int = Field(..., description="Number of enrolled students")
    waitlist_count: int = Field(default=0, description="Number of students on waitlist")
    start_date: str = Field(..., description="Section start date")
    end_date: str = Field(..., description="Section end date")
    location: str = Field(..., description="Campus location")
    credits: Optional[float] = Field(None, description="Number of credit hours")
    term: Optional[str] = Field(None, description="Academic term")
    meeting_times: List[Dict[str, Any]] = Field(default_factory=list, description="Meeting times")
    
    class Config:
        json_schema_extra = {
            "example": {
                "course_code": "CCT-110",
                "section_id": "343584",
                "section_name": "CCT-110-N886",
                "title": "Intro to Cyber Crime",
                "enrollment": {
                    "available": 19,
                    "capacity": 24,
                    "waitlisted": 0
                },
                "term": "Spring 2026",
                "start_date": "2026-01-12",
                "end_date": "2026-05-12",
                "location": "Central Campus / CPCC",
                "online": True,
                "credits": 3.0
            }
        }


class EnrollmentResponse(BaseModel):
    """Response model for enrollment data requests."""
    
    subjects: List[str] = Field(..., description="List of requested subject codes")
    term: Optional[str] = Field(None, description="Academic term")
    sections: List[CourseSection] = Field(..., description="List of course sections")
    total_sections: int = Field(..., description="Total number of sections found")
    retrieved_at: datetime = Field(..., description="When this data was retrieved")
    processing_time_seconds: float = Field(..., description="Processing time in seconds")
    errors: Optional[List[str]] = Field(None, description="Any errors encountered")
    
    class Config:
        json_schema_extra = {
            "example": {
                "subjects": ["CCT", "CSC"],
                "total_courses": 15,
                "total_sections": 24,
                "sections": [
                    {
                        "course_code": "CCT-110",
                        "section_id": "343584",
                        "section_name": "CCT-110-N886",
                        "title": "Intro to Cyber Crime",
                        "enrollment": {
                            "available": 19,
                            "capacity": 24,
                            "waitlisted": 0
                        },
                        "term": "Spring 2026",
                        "start_date": "2026-01-12",
                        "end_date": "2026-05-12",
                        "location": "Central Campus / CPCC",
                        "online": True,
                        "credits": 3.0
                    }
                ],
                "cached_at": "2025-01-11T08:30:00Z",
                "cache_expires_at": "2025-01-11T08:45:00Z"
            }
        }


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(..., description="Overall system status")
    session_valid: bool = Field(..., description="Whether CPCC session is valid")
    last_cpcc_request: Optional[datetime] = Field(None, description="Last successful CPCC request")
    cache_status: str = Field(..., description="Cache system status")
    uptime_seconds: float = Field(..., description="Application uptime in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "session_valid": True,
                "last_cpcc_request": "2025-01-11T08:30:00Z",
                "cache_status": "connected",
                "uptime_seconds": 3600.5
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid subject code provided",
                "details": {"invalid_subjects": ["INVALID"]},
                "timestamp": "2025-01-11T08:30:00Z"
            }
        }