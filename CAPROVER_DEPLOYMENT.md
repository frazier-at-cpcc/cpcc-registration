# CapRover Deployment Guide

This guide explains how to deploy the Registration Retrieval API to CapRover with a separate Redis instance.

## Prerequisites

- CapRover instance running
- Access to CapRover dashboard
- Docker images built and pushed to DockerHub (see [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md))

## Deployment Steps

### 1. Deploy Redis Service

First, deploy a Redis instance in CapRover:

1. Go to **Apps** in CapRover dashboard
2. Click **One-Click Apps/Databases**
3. Search for **Redis** and click **Deploy**
4. Configure Redis:
   - **App Name**: `registration-redis`
   - **Redis Password**: Set a secure password (optional but recommended)
   - Click **Deploy**

### 2. Deploy the API Application

1. Go to **Apps** → **Create New App**
2. Configure the app:
   - **App Name**: `registration-api`
   - **Has Persistent Data**: No (unless you need persistent logs)
   - Click **Create New App**

### 3. Configure Environment Variables

In the app settings, add these environment variables:

#### Required Variables:
```bash
# Redis Configuration
REDIS_URL=redis://srv-captain--registration-redis:6379

# CPCC Configuration  
CPCC_BASE_URL=https://mycollegess.cpcc.edu
CPCC_TIMEOUT_SECONDS=30

# API Configuration
MAX_CONCURRENT_REQUESTS=10
MAX_SUBJECTS_PER_REQUEST=10

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Production Settings
ENVIRONMENT=production
DEBUG=false
```

#### Optional Variables:
```bash
# Cache Settings (defaults are usually fine)
CACHE_TTL_SECONDS=300
SESSION_TTL_SECONDS=1800

# Request Timeouts
REQUEST_TIMEOUT_SECONDS=30

# CORS (adjust as needed)
ALLOWED_ORIGINS=["*"]
```

### 4. Deploy from Docker Image

1. In your app settings, go to **Deployment**
2. Select **Deploy via ImageName**
3. Enter your Docker image:
   ```
   your-dockerhub-username/registration-retrieval:latest
   ```
4. Click **Deploy Now**

### 5. Configure Networking

1. Enable **HTTPS** in the app settings
2. Set up **Custom Domain** if needed
3. Configure **Port Mapping**:
   - Container Port: `8000`
   - Host Port: `80` (CapRover handles this automatically)

## Redis Connection Patterns

### Standard Redis Connection
```bash
REDIS_URL=redis://srv-captain--registration-redis:6379
```

### Redis with Password
```bash
REDIS_URL=redis://:your-password@srv-captain--registration-redis:6379
```

### Redis with Database Selection
```bash
REDIS_URL=redis://srv-captain--registration-redis:6379/0
```

### External Redis Service
If using an external Redis service (like Redis Cloud):
```bash
REDIS_URL=redis://username:password@your-redis-host:port/database
```

## CapRover Service Discovery

CapRover uses internal DNS for service-to-service communication:

- **Pattern**: `srv-captain--{app-name}`
- **Redis Example**: `srv-captain--registration-redis`
- **Port**: Use the internal port (6379 for Redis)

## Environment-Specific Configuration

### Development/Staging
```bash
ENVIRONMENT=staging
LOG_LEVEL=DEBUG
DEBUG=true
CACHE_TTL_SECONDS=60  # Shorter cache for testing
```

### Production
```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false
CACHE_TTL_SECONDS=300
MAX_CONCURRENT_REQUESTS=20  # Higher for production load
```

## Health Checks

CapRover can monitor your app's health. Your app exposes these endpoints:

- **Health Check**: `GET /health` (if implemented)
- **API Docs**: `GET /docs` (FastAPI automatic docs)
- **OpenAPI**: `GET /openapi.json`

Configure health check in CapRover:
- **Path**: `/docs` (or implement a `/health` endpoint)
- **Port**: `8000`

## Scaling Configuration

For high-traffic scenarios:

1. **Horizontal Scaling**:
   - Increase **Instance Count** in CapRover
   - Each instance will connect to the same Redis

2. **Resource Limits**:
   - **Memory**: 512MB - 1GB per instance
   - **CPU**: 0.5 - 1.0 cores per instance

3. **Redis Scaling**:
   - Use Redis Cluster for high availability
   - Consider Redis persistence settings

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```
   Error: Connection refused to Redis
   ```
   **Solution**: Check Redis service name and port
   ```bash
   REDIS_URL=redis://srv-captain--registration-redis:6379
   ```

2. **Service Discovery Issues**
   ```
   Error: Name resolution failed
   ```
   **Solution**: Ensure Redis app is deployed and running
   - Check Apps dashboard for Redis status
   - Verify app name matches the URL pattern

3. **Environment Variables Not Loading**
   ```
   Error: Using default Redis URL
   ```
   **Solution**: Check environment variable configuration
   - Verify variables are set in CapRover app settings
   - Restart the app after adding variables

4. **Memory Issues**
   ```
   Error: Out of memory
   ```
   **Solution**: Increase memory allocation or optimize cache settings
   ```bash
   CACHE_TTL_SECONDS=60  # Reduce cache time
   MAX_CONCURRENT_REQUESTS=5  # Reduce concurrent load
   ```

### Debugging Steps

1. **Check App Logs**:
   - Go to App → Logs in CapRover
   - Look for Redis connection messages

2. **Test Redis Connection**:
   - Use CapRover's **NetData** or **Terminal** feature
   - Test connection: `redis-cli -h srv-captain--registration-redis ping`

3. **Verify Environment Variables**:
   - Check App → App Configs → Environment Variables
   - Ensure `REDIS_URL` is correctly set

## Example CapRover App Configuration

```json
{
  "appName": "registration-api",
  "imageName": "your-dockerhub-username/registration-retrieval:latest",
  "envVars": [
    {
      "key": "REDIS_URL",
      "value": "redis://srv-captain--registration-redis:6379"
    },
    {
      "key": "ENVIRONMENT",
      "value": "production"
    },
    {
      "key": "LOG_LEVEL",
      "value": "INFO"
    }
  ],
  "ports": [
    {
      "containerPort": 8000,
      "hostPort": 80
    }
  ]
}
```

## Security Considerations

1. **Redis Security**:
   - Set Redis password if handling sensitive data
   - Use Redis AUTH if available

2. **Network Security**:
   - Redis should only be accessible within CapRover network
   - Don't expose Redis port externally

3. **Environment Variables**:
   - Use CapRover's secret management for sensitive values
   - Don't log sensitive configuration values

## Monitoring

Set up monitoring for:
- **App Health**: Response times, error rates
- **Redis Health**: Memory usage, connection count
- **Resource Usage**: CPU, memory per instance

CapRover provides basic monitoring, or integrate with external services like:
- Prometheus + Grafana
- DataDog
- New Relic

## Backup Strategy

For Redis data persistence:
1. Enable Redis persistence in the Redis app configuration
2. Set up regular backups of Redis data
3. Consider Redis replication for high availability