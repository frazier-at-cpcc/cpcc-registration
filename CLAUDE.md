# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FastAPI service that retrieves real-time course enrollment data from CPCC (Central Piedmont Community College) using their Ellucian Colleague Self-Service system. The API handles session management, course search, and enrollment data extraction.

## Common Commands

```bash
# Run development server
python run.py
python run.py --log-level debug
python run.py --check-deps      # Verify dependencies
python run.py --test-redis      # Test Redis connection

# Testing
pytest                          # Run all tests
pytest --cov=app                # With coverage
pytest -m unit                  # Unit tests only
pytest -m integration           # Integration tests only
pytest tests/test_enrollment_api.py  # Single file

# Code quality
black app/ tests/               # Format
flake8 app/ tests/              # Lint
mypy app/                       # Type check

# Docker
docker-compose up -d            # Start API + Redis
docker-compose logs -f api      # View logs
```

## Architecture

### Request Flow
```
Client → FastAPI Endpoint → Session Manager → Course Search → Section Details → Cache → Response
```

### Key Services

**Session Manager** (`app/services/session_manager.py`)
- Handles CPCC authentication via cookies (`.ColleagueSelfServiceAntiforgery`) and CSRF tokens (`__RequestVerificationToken`)
- Thread-safe with async locks; implements automatic retry with exponential backoff
- Sessions expire after 30 minutes (configurable)

**Course Search** (`app/services/course_search.py`)
- Queries CPCC's `PostSearchCriteria` endpoint
- Accepts multiple subject codes per request

**Section Details** (`app/services/section_details.py`)
- Retrieves enrollment data from `Sections` endpoint
- Extracts: available seats, capacity, waitlist, schedule, location

**Cache Service** (`app/services/cache_service.py`)
- Redis-based with configurable TTL (default: 5 minutes for responses, 30 minutes for sessions)
- Graceful fallback if cache unavailable

### API Endpoints
- `GET /api/v1/enrollment?subjects=CCT,CSC` - Query enrollment by subjects
- `GET /api/v1/enrollment/subjects/{subject}` - Single subject query
- `GET /api/v1/enrollment/health` - Health check
- `POST /api/v1/enrollment/cache/invalidate` - Clear cache

## Exception Hierarchy

```
CPCCAPIException (base)
├── CPCCSessionError
├── CPCCAuthenticationError → AuthenticationError
├── CPCCRequestError → NetworkError
├── CPCCParsingError
├── RateLimitError
├── ServiceUnavailableError
└── CPCCError

CacheError
ValidationError
ConfigurationError
```

## Key Implementation Details

- All services use async patterns with `async with` context managers
- HTTP client uses `httpx.AsyncClient` with Firefox 140+ User-Agent headers
- CPCC base URL: `https://mycollegess.cpcc.edu`
- Use `LoggerMixin` for structured JSON logging
- Settings managed via Pydantic `BaseSettings` in `app/config.py`

## Environment Variables

Key configuration (see `.env.example` for full list):
- `CPCC_BASE_URL` - CPCC endpoint (default: https://mycollegess.cpcc.edu)
- `REDIS_URL` - Redis connection string
- `CACHE_TTL_SECONDS` - Response cache TTL (default: 300)
- `SESSION_TTL_SECONDS` - Session cache TTL (default: 1800)
- `MAX_CONCURRENT_REQUESTS` - Rate limit (default: 5)

## Test Markers

```ini
@pytest.mark.unit         # Unit tests
@pytest.mark.integration  # Integration tests
@pytest.mark.slow         # Slow tests
@pytest.mark.network      # Network-dependent tests
```
