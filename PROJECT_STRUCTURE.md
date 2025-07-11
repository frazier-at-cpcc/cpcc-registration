# CPCC Course Enrollment API - Project Structure

## 📁 Recommended Directory Structure

```
cpcc-enrollment-api/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py              # Configuration settings
│   ├── models/
│   │   ├── __init__.py
│   │   ├── enrollment.py      # Pydantic models for API responses
│   │   └── cpcc_responses.py  # Models for CPCC API responses
│   ├── services/
│   │   ├── __init__.py
│   │   ├── session_manager.py # CPCC session management
│   │   ├── course_search.py   # Course search service
│   │   ├── section_details.py # Section details service
│   │   └── cache_service.py   # Caching implementation
│   ├── api/
│   │   ├── __init__.py
│   │   ├── enrollment.py      # Enrollment endpoints
│   │   └── health.py          # Health check endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── exceptions.py      # Custom exceptions
│   │   ├── logging.py         # Logging configuration
│   │   └── utils.py           # Utility functions
│   └── dependencies.py        # FastAPI dependencies
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Pytest configuration
│   ├── test_session_manager.py
│   ├── test_course_search.py
│   ├── test_section_details.py
│   └── test_api_endpoints.py
├── docs/
│   ├── API.md                # API documentation
│   ├── DEPLOYMENT.md         # Deployment guide
│   └── EXAMPLES.md           # Usage examples
├── scripts/
│   ├── start.sh              # Development startup script
│   └── test_cpcc_connection.py # Connection testing script
├── requirements.txt          # Python dependencies
├── requirements-dev.txt      # Development dependencies
├── docker-compose.yml        # Docker setup with Redis
├── Dockerfile               # Container definition
├── .env.example             # Environment variables template
├── .gitignore              # Git ignore rules
└── README.md               # Project overview
```

## 🔧 Key Files Overview

### Core Application Files

#### `app/main.py`
- FastAPI application initialization
- Middleware configuration
- Route registration
- Startup/shutdown events

#### `app/config.py`
- Environment variable management
- Configuration classes
- Validation of settings

#### `app/dependencies.py`
- Dependency injection for FastAPI
- Session manager instances
- Cache service instances

### Service Layer

#### `app/services/session_manager.py`
- CPCC session initialization
- Cookie and token management
- Session validation and renewal

#### `app/services/course_search.py`
- PostSearchCriteria API integration
- Search payload construction
- Response parsing

#### `app/services/section_details.py`
- Sections API integration
- Enrollment data extraction
- Batch processing of sections

#### `app/services/cache_service.py`
- Redis integration
- Cache key management
- TTL handling

### Data Models

#### `app/models/enrollment.py`
- API response models
- Enrollment data structures
- Validation rules

#### `app/models/cpcc_responses.py`
- CPCC API response models
- Raw data structures
- Parsing helpers

### API Layer

#### `app/api/enrollment.py`
- GET /enrollment endpoint
- Query parameter validation
- Response formatting

#### `app/api/health.py`
- Health check endpoints
- System status monitoring
- Dependency health checks

## 🐳 Docker Configuration

### `docker-compose.yml`
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    volumes:
      - ./app:/app
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

### `Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📦 Dependencies

### `requirements.txt`
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
httpx==0.25.2
beautifulsoup4==4.12.2
pydantic==2.5.0
redis==5.0.1
python-multipart==0.0.6
```

### `requirements-dev.txt`
```
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-mock==3.12.0
httpx==0.25.2
black==23.11.0
flake8==6.1.0
mypy==1.7.1
```

## ⚙️ Environment Configuration

### `.env.example`
```bash
# CPCC Configuration
CPCC_BASE_URL=https://mycollegess.cpcc.edu
CPCC_TIMEOUT_SECONDS=30

# Caching Configuration
REDIS_URL=redis://localhost:6379
CACHE_TTL_SECONDS=900
SESSION_TTL_SECONDS=1800

# API Configuration
MAX_CONCURRENT_REQUESTS=5
MAX_SUBJECTS_PER_REQUEST=10

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Development Settings
DEBUG=false
RELOAD=false
```

## 🧪 Testing Structure

### Test Categories
1. **Unit Tests**: Individual service testing
2. **Integration Tests**: CPCC API interaction
3. **API Tests**: Endpoint functionality
4. **Performance Tests**: Load and response time testing

### Test Configuration (`conftest.py`)
- Mock CPCC responses
- Test database setup
- Fixture definitions
- Test client configuration

## 📚 Documentation Structure

### `docs/API.md`
- Endpoint specifications
- Request/response examples
- Error codes and handling
- Rate limiting information

### `docs/DEPLOYMENT.md`
- Production deployment steps
- Environment setup
- Monitoring configuration
- Scaling considerations

### `docs/EXAMPLES.md`
- Code examples in multiple languages
- Common use cases
- Integration patterns
- Troubleshooting guide

## 🚀 Development Workflow

### Local Development Setup
```bash
# 1. Clone repository
git clone <repository-url>
cd cpcc-enrollment-api

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Set up environment
cp .env.example .env
# Edit .env with your configuration

# 5. Start Redis (using Docker)
docker run -d -p 6379:6379 redis:7-alpine

# 6. Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing Commands
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_session_manager.py

# Run integration tests only
pytest -m integration
```

### Code Quality
```bash
# Format code
black app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/
```

This project structure provides a clean, maintainable codebase that follows FastAPI best practices and supports both development and production deployment scenarios.