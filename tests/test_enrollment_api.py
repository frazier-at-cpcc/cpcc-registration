"""Tests for the enrollment API endpoints."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.enrollment import EnrollmentResponse, CourseSection, EnrollmentInfo


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_enrollment_response():
    """Sample enrollment response for testing."""
    return EnrollmentResponse(
        subjects=["CSC"],
        term="202401",
        sections=[
            CourseSection(
                section_id="12345",
                course_code="CSC-151",
                course_title="JAVA Programming",
                section_number="001",
                instructor="John Doe",
                enrollment_info=EnrollmentInfo(
                    enrolled=18,
                    capacity=25,
                    available=7,
                    waitlist=0,
                    waitlist_capacity=10
                ),
                credits=4,
                status="Open"
            )
        ],
        total_sections=1,
        retrieved_at=datetime.utcnow(),
        processing_time_seconds=1.5
    )


class TestEnrollmentEndpoints:
    """Test enrollment API endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "CPCC Course Enrollment API"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data
    
    def test_health_endpoint(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"
    
    @patch('app.api.enrollment.enrollment_api.get_enrollment_data')
    def test_get_enrollment_success(self, mock_get_enrollment, client, sample_enrollment_response):
        """Test successful enrollment data retrieval."""
        mock_get_enrollment.return_value = sample_enrollment_response
        
        response = client.get("/api/v1/enrollment?subjects=CSC")
        assert response.status_code == 200
        
        data = response.json()
        assert data["subjects"] == ["CSC"]
        assert data["total_sections"] == 1
        assert len(data["sections"]) == 1
        assert data["sections"][0]["course_code"] == "CSC-151"
    
    def test_get_enrollment_missing_subjects(self, client):
        """Test enrollment endpoint with missing subjects parameter."""
        response = client.get("/api/v1/enrollment")
        assert response.status_code == 422  # Validation error
    
    def test_get_enrollment_empty_subjects(self, client):
        """Test enrollment endpoint with empty subjects."""
        response = client.get("/api/v1/enrollment?subjects=")
        assert response.status_code == 400
        
        data = response.json()
        assert "At least one subject must be specified" in data["detail"]
    
    @patch('app.api.enrollment.enrollment_api.get_enrollment_data')
    def test_get_enrollment_multiple_subjects(self, mock_get_enrollment, client, sample_enrollment_response):
        """Test enrollment with multiple subjects."""
        sample_enrollment_response.subjects = ["CSC", "MAT"]
        mock_get_enrollment.return_value = sample_enrollment_response
        
        response = client.get("/api/v1/enrollment?subjects=CSC,MAT")
        assert response.status_code == 200
        
        data = response.json()
        assert set(data["subjects"]) == {"CSC", "MAT"}
    
    @patch('app.api.enrollment.enrollment_api.get_enrollment_data')
    def test_get_enrollment_with_term(self, mock_get_enrollment, client, sample_enrollment_response):
        """Test enrollment with specific term."""
        mock_get_enrollment.return_value = sample_enrollment_response
        
        response = client.get("/api/v1/enrollment?subjects=CSC&term=202401")
        assert response.status_code == 200
        
        # Verify the mock was called with correct parameters
        mock_get_enrollment.assert_called_once()
        args, kwargs = mock_get_enrollment.call_args
        assert kwargs.get('term') == '202401'
    
    @patch('app.api.enrollment.enrollment_api.get_enrollment_data')
    def test_get_enrollment_no_cache(self, mock_get_enrollment, client, sample_enrollment_response):
        """Test enrollment without cache."""
        mock_get_enrollment.return_value = sample_enrollment_response
        
        response = client.get("/api/v1/enrollment?subjects=CSC&use_cache=false")
        assert response.status_code == 200
        
        # Verify the mock was called with cache disabled
        mock_get_enrollment.assert_called_once()
        args, kwargs = mock_get_enrollment.call_args
        assert kwargs.get('use_cache') is False
    
    @patch('app.api.enrollment.enrollment_api.get_enrollment_data')
    def test_get_enrollment_by_subject(self, mock_get_enrollment, client, sample_enrollment_response):
        """Test single subject endpoint."""
        mock_get_enrollment.return_value = sample_enrollment_response
        
        response = client.get("/api/v1/enrollment/subjects/CSC")
        assert response.status_code == 200
        
        data = response.json()
        assert data["subjects"] == ["CSC"]


class TestEnrollmentHealthAndCache:
    """Test health and cache management endpoints."""
    
    @patch('app.services.cache_service.cache_service.health_check')
    @patch('app.services.cache_service.cache_service.get_cache_stats')
    def test_enrollment_health_check(self, mock_get_stats, mock_health_check, client):
        """Test enrollment health check endpoint."""
        mock_health_check.return_value = True
        mock_get_stats.return_value = {
            "connected": True,
            "redis_version": "7.0.0",
            "enrollment_cache_keys": 5
        }
        
        response = client.get("/api/v1/enrollment/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["services"]["cache"]["healthy"] is True
    
    @patch('app.services.cache_service.cache_service.invalidate_cache')
    def test_invalidate_cache(self, mock_invalidate, client):
        """Test cache invalidation endpoint."""
        mock_invalidate.return_value = 5
        
        response = client.post("/api/v1/enrollment/cache/invalidate")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["deleted_count"] == 5
    
    @patch('app.services.cache_service.cache_service.get_cache_stats')
    def test_get_cache_stats(self, mock_get_stats, client):
        """Test cache stats endpoint."""
        mock_get_stats.return_value = {
            "connected": True,
            "redis_version": "7.0.0",
            "used_memory": "1.2MB",
            "enrollment_cache_keys": 10
        }
        
        response = client.get("/api/v1/enrollment/cache/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["stats"]["connected"] is True
        assert data["stats"]["enrollment_cache_keys"] == 10


class TestErrorHandling:
    """Test error handling in API endpoints."""
    
    @patch('app.api.enrollment.enrollment_api.get_enrollment_data')
    def test_validation_error_handling(self, mock_get_enrollment, client):
        """Test validation error handling."""
        from app.core.exceptions import ValidationError
        mock_get_enrollment.side_effect = ValidationError("Invalid subject", "subjects")
        
        response = client.get("/api/v1/enrollment?subjects=INVALID")
        assert response.status_code == 400
        
        data = response.json()
        assert "Invalid subject" in data["detail"]
    
    @patch('app.api.enrollment.enrollment_api.get_enrollment_data')
    def test_authentication_error_handling(self, mock_get_enrollment, client):
        """Test authentication error handling."""
        from app.core.exceptions import AuthenticationError
        mock_get_enrollment.side_effect = AuthenticationError("Auth failed", "auth")
        
        response = client.get("/api/v1/enrollment?subjects=CSC")
        assert response.status_code == 401
        
        data = response.json()
        assert "Auth failed" in data["detail"]
    
    @patch('app.api.enrollment.enrollment_api.get_enrollment_data')
    def test_network_error_handling(self, mock_get_enrollment, client):
        """Test network error handling."""
        from app.core.exceptions import NetworkError
        mock_get_enrollment.side_effect = NetworkError("Network timeout", "timeout")
        
        response = client.get("/api/v1/enrollment?subjects=CSC")
        assert response.status_code == 503
        
        data = response.json()
        assert "Service temporarily unavailable" in data["detail"]
    
    @patch('app.api.enrollment.enrollment_api.get_enrollment_data')
    def test_cpcc_error_handling(self, mock_get_enrollment, client):
        """Test CPCC error handling."""
        from app.core.exceptions import CPCCError
        mock_get_enrollment.side_effect = CPCCError("CPCC service error", "service")
        
        response = client.get("/api/v1/enrollment?subjects=CSC")
        assert response.status_code == 502
        
        data = response.json()
        assert "CPCC service error" in data["detail"]
    
    @patch('app.api.enrollment.enrollment_api.get_enrollment_data')
    def test_unexpected_error_handling(self, mock_get_enrollment, client):
        """Test unexpected error handling."""
        mock_get_enrollment.side_effect = Exception("Unexpected error")
        
        response = client.get("/api/v1/enrollment?subjects=CSC")
        assert response.status_code == 500
        
        data = response.json()
        assert "Internal server error" in data["detail"]


class TestRequestValidation:
    """Test request parameter validation."""
    
    def test_subjects_whitespace_handling(self, client):
        """Test subjects parameter with whitespace."""
        with patch('app.api.enrollment.enrollment_api.get_enrollment_data') as mock_get:
            mock_get.return_value = EnrollmentResponse(
                subjects=["CSC", "MAT"],
                sections=[],
                total_sections=0,
                retrieved_at=datetime.utcnow(),
                processing_time_seconds=0.1
            )
            
            response = client.get("/api/v1/enrollment?subjects= CSC , MAT ")
            assert response.status_code == 200
            
            # Verify subjects were cleaned
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            subjects = args[0] if args else kwargs.get('subjects', [])
            assert subjects == ["CSC", "MAT"]
    
    def test_subjects_case_handling(self, client):
        """Test subjects parameter case handling."""
        with patch('app.api.enrollment.enrollment_api.get_enrollment_data') as mock_get:
            mock_get.return_value = EnrollmentResponse(
                subjects=["CSC"],
                sections=[],
                total_sections=0,
                retrieved_at=datetime.utcnow(),
                processing_time_seconds=0.1
            )
            
            response = client.get("/api/v1/enrollment?subjects=csc")
            assert response.status_code == 200
            
            # Verify subjects were uppercased
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            subjects = args[0] if args else kwargs.get('subjects', [])
            assert subjects == ["CSC"]