"""Main FastAPI application for CPCC Course Enrollment API."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from app.config import settings
from app.core.exceptions import CPCCError, AuthenticationError, NetworkError, ValidationError
from app.core.logging import setup_logging, get_logger
from app.api.enrollment import router as enrollment_router
from app.services.cache_service import cache_service


# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting CPCC Course Enrollment API")
    
    try:
        # Initialize cache service
        async with cache_service:
            logger.info("Cache service initialized")
            
            # Test cache connection
            cache_healthy = await cache_service.health_check()
            if cache_healthy:
                logger.info("Cache service is healthy")
            else:
                logger.warning("Cache service is not healthy")
        
        logger.info("Application startup completed")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down CPCC Course Enrollment API")
        try:
            # Close cache service
            async with cache_service:
                pass
            logger.info("Cache service closed")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")


# Create FastAPI application
app = FastAPI(
    title="CPCC Course Enrollment API",
    description="""
    API for retrieving course enrollment data from Central Piedmont Community College (CPCC).
    
    This API provides access to real-time course enrollment information including:
    - Available seats
    - Total capacity
    - Waitlist information
    - Course and section details
    
    ## Features
    
    - **Multi-subject queries**: Get enrollment data for multiple subjects in a single request
    - **Caching**: Intelligent caching to minimize load on CPCC servers
    - **Real-time data**: Direct integration with CPCC's Ellucian Colleague system
    - **Comprehensive error handling**: Detailed error responses and logging
    - **Health monitoring**: Built-in health checks and statistics
    
    ## Usage Examples
    
    ### Get enrollment for multiple subjects:
    ```
    GET /api/v1/enrollment?subjects=CCT,CSC,MAT
    ```
    
    ### Get enrollment for a specific term:
    ```
    GET /api/v1/enrollment?subjects=CCT&term=202401
    ```
    
    ### Get enrollment without caching:
    ```
    GET /api/v1/enrollment?subjects=CSC&use_cache=false
    ```
    
    ## Rate Limiting
    
    This API implements intelligent rate limiting to respect CPCC's servers:
    - Maximum concurrent requests: {max_concurrent}
    - Request timeout: {timeout} seconds
    - Automatic retry with exponential backoff
    
    ## Caching
    
    Responses are cached for {cache_ttl} seconds to improve performance and reduce load.
    Cache can be disabled per request using the `use_cache=false` parameter.
    """.format(
        max_concurrent=settings.max_concurrent_requests,
        timeout=settings.request_timeout_seconds,
        cache_ttl=settings.cache_ttl_seconds
    ),
    version="1.0.0",
    contact={
        "name": "CPCC Enrollment API",
        "url": "https://github.com/your-repo/cpcc-enrollment-api",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)


# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# Custom middleware for request logging and timing
@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """Log requests and add timing information."""
    start_time = datetime.utcnow()
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path} - "
        f"Query: {request.query_params} - "
        f"Client: {request.client.host if request.client else 'unknown'}"
    )
    
    try:
        response = await call_next(request)
        
        # Calculate processing time
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        # Add timing header
        response.headers["X-Processing-Time"] = str(processing_time)
        
        # Log response
        logger.info(
            f"Response: {response.status_code} - "
            f"Processing time: {processing_time:.3f}s"
        )
        
        return response
        
    except Exception as e:
        # Calculate processing time for errors too
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        logger.error(
            f"Request failed: {str(e)} - "
            f"Processing time: {processing_time:.3f}s"
        )
        raise


# Global exception handlers
@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle validation errors."""
    logger.warning(f"Validation error: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation Error",
            "message": str(exc),
            "error_code": exc.error_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors."""
    logger.error(f"Authentication error: {str(exc)}")
    return JSONResponse(
        status_code=401,
        content={
            "error": "Authentication Error",
            "message": "Failed to authenticate with CPCC system",
            "error_code": exc.error_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(NetworkError)
async def network_error_handler(request: Request, exc: NetworkError):
    """Handle network errors."""
    logger.error(f"Network error: {str(exc)}")
    return JSONResponse(
        status_code=503,
        content={
            "error": "Service Unavailable",
            "message": "CPCC system is temporarily unavailable",
            "error_code": exc.error_code,
            "timestamp": datetime.utcnow().isoformat(),
            "retry_after": 60  # Suggest retry after 60 seconds
        }
    )


@app.exception_handler(CPCCError)
async def cpcc_error_handler(request: Request, exc: CPCCError):
    """Handle CPCC-specific errors."""
    logger.error(f"CPCC error: {str(exc)}")
    return JSONResponse(
        status_code=502,
        content={
            "error": "CPCC Service Error",
            "message": str(exc),
            "error_code": exc.error_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Include routers
app.include_router(enrollment_router)


# Root endpoint
@app.get("/", tags=["root"])
async def root() -> Dict[str, Any]:
    """
    Root endpoint with API information.
    """
    return {
        "name": "CPCC Course Enrollment API",
        "version": "1.0.0",
        "description": "API for retrieving course enrollment data from CPCC",
        "docs_url": "/docs" if settings.environment != "production" else None,
        "health_url": "/api/v1/enrollment/health",
        "endpoints": {
            "enrollment": "/api/v1/enrollment",
            "health": "/api/v1/enrollment/health",
            "cache_stats": "/api/v1/enrollment/cache/stats"
        },
        "timestamp": datetime.utcnow().isoformat()
    }


# Health check endpoint
@app.get("/health", tags=["health"])
async def health() -> Dict[str, Any]:
    """
    Simple health check endpoint.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


# Custom OpenAPI schema
def custom_openapi():
    """Generate custom OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="CPCC Course Enrollment API",
        version="1.0.0",
        description=app.description,
        routes=app.routes,
    )
    
    # Add custom schema information
    openapi_schema["info"]["x-logo"] = {
        "url": "https://www.cpcc.edu/sites/default/files/cpcc-logo.png"
    }
    
    # Add server information
    openapi_schema["servers"] = [
        {
            "url": settings.api_base_url or "http://localhost:8000",
            "description": "CPCC Enrollment API Server"
        }
    ]
    
    # Add security schemes if needed
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower(),
        access_log=True
    )