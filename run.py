#!/usr/bin/env python3
"""
CPCC Course Enrollment API - Development Server Runner

This script provides an easy way to run the API server with different configurations.
"""

import os
import sys
import argparse
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import uvicorn
    from app.config import settings
    from app.core.logging import setup_logging, get_logger
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    print("Please install dependencies with: pip install -r requirements.txt")
    sys.exit(1)


def main():
    """Main entry point for the development server."""
    parser = argparse.ArgumentParser(
        description="CPCC Course Enrollment API Development Server"
    )
    
    parser.add_argument(
        "--host",
        default=settings.host,
        help=f"Host to bind to (default: {settings.host})"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help=f"Port to bind to (default: {settings.port})"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        default=settings.environment == "development",
        help="Enable auto-reload on code changes"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error"],
        default=settings.log_level.lower(),
        help=f"Log level (default: {settings.log_level.lower()})"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)"
    )
    
    parser.add_argument(
        "--env",
        choices=["development", "staging", "production"],
        default=settings.environment,
        help=f"Environment (default: {settings.environment})"
    )
    
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Check if all dependencies are available"
    )
    
    parser.add_argument(
        "--test-redis",
        action="store_true",
        help="Test Redis connection"
    )
    
    args = parser.parse_args()
    
    # Set environment variable if specified
    if args.env:
        os.environ["ENVIRONMENT"] = args.env
    
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    if args.check_deps:
        check_dependencies()
        return
    
    if args.test_redis:
        asyncio.run(test_redis_connection())
        return
    
    # Print startup information
    print("=" * 60)
    print("CPCC Course Enrollment API")
    print("=" * 60)
    print(f"Environment: {args.env}")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Log Level: {args.log_level}")
    print(f"Auto-reload: {args.reload}")
    print(f"Workers: {args.workers}")
    print("=" * 60)
    print(f"API Documentation: http://{args.host}:{args.port}/docs")
    print(f"Health Check: http://{args.host}:{args.port}/health")
    print(f"Example Request: http://{args.host}:{args.port}/api/v1/enrollment?subjects=CCT,CSC")
    print("=" * 60)
    
    # Run the server
    try:
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level=args.log_level,
            workers=args.workers if not args.reload else 1,  # Can't use workers with reload
            access_log=True,
            loop="asyncio"
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        sys.exit(1)


def check_dependencies():
    """Check if all required dependencies are available."""
    print("Checking dependencies...")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "httpx",
        "pydantic",
        "redis",
        "beautifulsoup4",
        "python-dotenv"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} (missing)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Install with: pip install -r requirements.txt")
        sys.exit(1)
    else:
        print("\nAll dependencies are available!")


async def test_redis_connection():
    """Test Redis connection."""
    print("Testing Redis connection...")
    
    try:
        from app.services.cache_service import cache_service
        
        async with cache_service:
            healthy = await cache_service.health_check()
            
            if healthy:
                print("✓ Redis connection successful")
                
                # Get stats
                stats = await cache_service.get_cache_stats()
                print(f"Redis version: {stats.get('redis_version', 'unknown')}")
                print(f"Used memory: {stats.get('used_memory', 'unknown')}")
                print(f"Connected clients: {stats.get('connected_clients', 0)}")
            else:
                print("✗ Redis connection failed")
                sys.exit(1)
                
    except Exception as e:
        print(f"✗ Redis connection error: {e}")
        print(f"Redis URL: {settings.redis_url}")
        print("Make sure Redis is running and accessible")
        sys.exit(1)


if __name__ == "__main__":
    main()