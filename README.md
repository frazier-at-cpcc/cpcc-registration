# CPCC Course Enrollment API

A FastAPI-based service for retrieving real-time course enrollment data from Central Piedmont Community College (CPCC) using their Ellucian Colleague Self-Service system.

## Features

- **Real-time enrollment data**: Direct integration with CPCC's course catalog system
- **Multi-subject queries**: Get enrollment data for multiple subjects in a single request
- **Intelligent caching**: Redis-based caching to minimize server load and improve performance
- **Comprehensive error handling**: Detailed error responses and automatic retry logic
- **Rate limiting**: Respects CPCC server limits with concurrent request management
- **Health monitoring**: Built-in health checks and performance metrics
- **Docker support**: Containerized deployment with Docker Compose

## Quick Start

### Prerequisites

- Python 3.8+
- Redis server
- Docker (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd cpcc-enrollment-api
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   # For development
   pip install -r requirements-dev.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start Redis** (if not using Docker)
   ```bash
   redis-server
   ```

5. **Run the API**
   ```bash
   python run.py
   ```

The API will be available at `http://localhost:8000`

### Docker Setup

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

## API Documentation

### Base URL
- Development: `http://localhost:8000`
- Production: Configure via `API_BASE_URL` environment variable

### Authentication
Currently, the API uses CPCC's public course catalog and doesn't require authentication. The service handles CPCC's internal authentication automatically.

## Endpoints

### Get Enrollment Data

**GET** `/api/v1/enrollment`

Retrieve course enrollment data for specified subjects.

#### Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `subjects` | string | Yes | Comma-separated subject codes | `CCT,CSC,MAT` |
| `term` | string | No | Academic term (defaults to current) | `202401` |
| `use_cache` | boolean | No | Whether to use cached data | `true` |

#### Example Requests

```bash
# Get enrollment for Computer Science and Math courses
curl "http://localhost:8000/api/v1/enrollment?subjects=CSC,MAT"

# Get enrollment for a specific term
curl "http://localhost:8000/api/v1/enrollment?subjects=CCT&term=202401"

# Get fresh data without cache
curl "http://localhost:8000/api/v1/enrollment?subjects=CSC&use_cache=false"
```

#### Response Format

```json
{
  "subjects": ["CSC", "MAT"],
  "term": "202401",
  "sections": [
    {
      "section_id": "12345",
      "course_id": "CSC-151",
      "subject_code": "CSC",
      "course_number": "151",
      "section_number": "CSC-151-001",
      "title": "JAVA Programming",
      "available_seats": 7,
      "total_capacity": 25,
      "enrolled_count": 18,
      "waitlist_count": 0,
      "start_date": "2024-01-08",
      "end_date": "2024-05-06",
      "location": "CATO 234",
      "credits": 4,
      "term": "Spring 2024",
      "instructors": ["John Doe"],
      "meeting_times": [
        {
          "days": "MW",
          "start_time": "10:00 AM",
          "end_time": "11:50 AM",
          "location": "CATO 234",
          "is_online": false
        }
      ]
    }
  ],
  "total_sections": 1,
  "retrieved_at": "2024-01-15T10:30:00Z",
  "cached_at": "2024-01-15T10:30:00Z",
  "cache_expires_at": "2024-01-15T10:35:00Z",
  "processing_time_seconds": 2.45,
  "errors": null
}
```

### Get Enrollment by Subject

**GET** `/api/v1/enrollment/subjects/{subject}`

Convenience endpoint for single subject queries.

```bash
curl "http://localhost:8000/api/v1/enrollment/subjects/CSC"
```

### Health Check

**GET** `/api/v1/enrollment/health`

Check service health and get system statistics.

```bash
curl "http://localhost:8000/api/v1/enrollment/health"
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "cache": {
      "healthy": true,
      "stats": {
        "connected": true,
        "redis_version": "7.0.0",
        "used_memory": "1.2MB",
        "enrollment_cache_keys": 15
      }
    },
    "session": {
      "healthy": true
    }
  },
  "version": "1.0.0"
}
```

### Cache Management

**POST** `/api/v1/enrollment/cache/invalidate`

Invalidate cached data (useful for development).

```bash
curl -X POST "http://localhost:8000/api/v1/enrollment/cache/invalidate"
```

**GET** `/api/v1/enrollment/cache/stats`

Get detailed cache statistics.

```bash
curl "http://localhost:8000/api/v1/enrollment/cache/stats"
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Environment (development/staging/production) |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `CACHE_TTL_SECONDS` | `300` | Cache TTL in seconds |
| `REQUEST_TIMEOUT_SECONDS` | `30` | HTTP request timeout |
| `MAX_CONCURRENT_REQUESTS` | `10` | Max concurrent requests to CPCC |
| `ALLOWED_ORIGINS` | `["*"]` | CORS allowed origins |

### CPCC Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CPCC_BASE_URL` | `https://mycollegess.cpcc.edu` | CPCC base URL |
| `CPCC_SEARCH_ENDPOINT` | `/Student/Courses/PostSearchCriteria` | Search endpoint |
| `CPCC_SECTIONS_ENDPOINT` | `/Student/Courses/Sections` | Sections endpoint |

## Development

### Running in Development Mode

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run with auto-reload
python run.py --reload --log-level debug

# Check dependencies
python run.py --check-deps

# Test Redis connection
python run.py --test-redis
```

### Project Structure

```
cpcc-enrollment-api/
├── app/
│   ├── api/                 # API endpoints
│   ├── core/               # Core utilities (logging, exceptions)
│   ├── models/             # Pydantic models
│   ├── services/           # Business logic services
│   ├── config.py           # Configuration management
│   └── main.py             # FastAPI application
├── tests/                  # Test files
├── docs/                   # Documentation
├── docker-compose.yml      # Docker Compose configuration
├── Dockerfile             # Docker image definition
├── requirements.txt       # Python dependencies
└── run.py                 # Development server runner
```

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_enrollment.py
```

## Subject Codes

Common CPCC subject codes you can query:

| Code | Subject |
|------|---------|
| `CCT` | Computer Technology |
| `CSC` | Computer Science |
| `MAT` | Mathematics |
| `ENG` | English |
| `BIO` | Biology |
| `CHM` | Chemistry |
| `PHY` | Physics |
| `HIS` | History |
| `PSY` | Psychology |
| `BUS` | Business |
| `ACC` | Accounting |
| `ART` | Art |
| `MUS` | Music |
| `NUR` | Nursing |
| `WBL` | Work-Based Learning |

## Error Handling

The API provides detailed error responses:

### Validation Errors (400)
```json
{
  "error": "Validation Error",
  "message": "At least one subject must be specified",
  "error_code": "subjects",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Authentication Errors (401)
```json
{
  "error": "Authentication Error",
  "message": "Failed to authenticate with CPCC system",
  "error_code": "auth_failed",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Service Unavailable (503)
```json
{
  "error": "Service Unavailable",
  "message": "CPCC system is temporarily unavailable",
  "error_code": "network_timeout",
  "timestamp": "2024-01-15T10:30:00Z",
  "retry_after": 60
}
```

## Performance

### Caching Strategy

- **Cache Duration**: 5 minutes (configurable)
- **Cache Keys**: Based on subjects and term
- **Cache Invalidation**: Automatic expiration + manual invalidation
- **Fallback**: Graceful degradation if cache is unavailable

### Rate Limiting

- **Concurrent Requests**: Maximum 10 concurrent requests to CPCC
- **Request Timeout**: 30 seconds per request
- **Retry Logic**: Exponential backoff for failed requests
- **Circuit Breaker**: Automatic failure detection and recovery

## Monitoring

### Logs

Structured JSON logging with contextual information:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "message": "Retrieved 25 sections with enrollment data",
  "subjects": ["CSC", "MAT"],
  "processing_time_seconds": 2.45,
  "sections_count": 25
}
```

### Metrics

Available through the health endpoint:
- Cache hit/miss rates
- Response times
- Error rates
- Active sessions
- Memory usage

## Deployment

### Docker Production Deployment

```bash
# Build production image
docker build -t cpcc-enrollment-api .

# Run with production settings
docker run -d \
  --name cpcc-api \
  -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e REDIS_URL=redis://redis:6379/0 \
  cpcc-enrollment-api
```

### Environment-Specific Configurations

#### Development
- Auto-reload enabled
- Debug logging
- CORS allows all origins
- API documentation available

#### Production
- Auto-reload disabled
- INFO level logging
- Restricted CORS
- API documentation disabled
- Health checks enabled

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```bash
   # Check Redis status
   redis-cli ping
   
   # Test connection from API
   python run.py --test-redis
   ```

2. **CPCC Authentication Issues**
   - Check CPCC website availability
   - Verify base URL configuration
   - Check network connectivity

3. **High Response Times**
   - Check Redis cache status
   - Monitor CPCC server response times
   - Adjust concurrent request limits

4. **Memory Issues**
   - Monitor cache size
   - Adjust cache TTL
   - Check for memory leaks in logs

### Debug Mode

```bash
# Run with debug logging
python run.py --log-level debug

# Check all dependencies
python run.py --check-deps

# Test individual components
python -c "from app.services.session_manager import SessionManager; print('Session manager OK')"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the logs for error details

## Changelog

### v1.0.0
- Initial release
- Basic enrollment data retrieval
- Redis caching
- Docker support
- Comprehensive error handling
- Health monitoring